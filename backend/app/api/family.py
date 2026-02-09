"""
小金库 (Golden Nest) - 家庭管理路由
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.encryption import encrypt_sensitive_data, decrypt_sensitive_data
from app.core.constants import ContentLimits
from app.models.models import Family, FamilyMember, User
from app.main import limiter
from app.schemas.family import (
    FamilyCreate, FamilyUpdate, FamilyResponse, FamilyMemberResponse, JoinFamilyRequest,
    NotificationConfigResponse, NotificationConfigUpdate, NotificationTestRequest
)
from app.api.auth import get_current_user
from app.services.achievement import AchievementService

router = APIRouter()


def generate_invite_code() -> str:
    """生成8位邀请码"""
    return secrets.token_urlsafe(6)[:8].upper()


@router.post("/create", response_model=FamilyResponse)
@limiter.limit("1/hour")
async def create_family(
    family_data: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建家庭"""
    # 检查用户是否已经有家庭
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="您已经加入了一个家庭")
    
    # 创建家庭
    family = Family(
        name=family_data.name,
        savings_target=family_data.savings_target,
        time_value_rate=family_data.time_value_rate,
        invite_code=generate_invite_code()
    )
    db.add(family)
    await db.flush()
    
    # 创建者成为管理员
    member = FamilyMember(
        user_id=current_user.id,
        family_id=family.id,
        role="admin"
    )
    db.add(member)
    await db.flush()
    
    # 检查创建家庭的成就
    achievement_service = AchievementService(db)
    await achievement_service.check_and_unlock(
        current_user.id,
        context={"action": "create_family"}
    )
    
    await db.commit()
    
    # 返回带成员信息的家庭
    return await get_family_with_members(family.id, db)


@router.post("/join")
@limiter.limit("5/hour")
async def join_family(
    join_data: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    通过邀请码申请加入家庭
    注意：现在需要家庭成员审批后才能加入，任一成员同意即可
    """
    from app.models.models import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus
    from app.services.approval import ApprovalService
    
    # 检查用户是否已经有家庭
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="您已经加入了一个家庭")
    
    # 查找家庭
    result = await db.execute(
        select(Family).where(Family.invite_code == join_data.invite_code.upper())
    )
    family = result.scalar_one_or_none()
    if not family:
        raise HTTPException(status_code=404, detail="邀请码无效")
    
    # 检查家庭是否只有一个成员（单人家庭直接加入）
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family.id)
    )
    members = result.scalars().all()
    
    if len(members) == 0:
        # 空家庭，直接加入（理论上不应该发生，但做个保护）
        member = FamilyMember(
            user_id=current_user.id,
            family_id=family.id,
            role="member"
        )
        db.add(member)
        await db.commit()
        return {
            "status": "joined",
            "message": "已成功加入家庭",
            "family": await get_family_with_members(family.id, db)
        }
    
    # 检查是否有未处理的加入申请
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.family_id == family.id,
            ApprovalRequest.requester_id == current_user.id,
            ApprovalRequest.request_type == ApprovalRequestType.MEMBER_JOIN,
            ApprovalRequest.status == ApprovalRequestStatus.PENDING
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="您已经有一个待处理的加入申请，请等待审批")
    
    # 创建加入申请
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family.id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.MEMBER_JOIN,
        title=f"申请加入家庭: {family.name}",
        description=f"{current_user.nickname}申请加入家庭「{family.name}」",
        amount=0,
        request_data={
            "user_id": current_user.id,
            "username": current_user.username,
            "nickname": current_user.nickname,
            "family_name": family.name
        }
    )
    
    await db.commit()
    
    # 检查申请是否已经自动通过（单人家庭的情况）
    if request.status == ApprovalRequestStatus.APPROVED:
        return {
            "status": "joined",
            "message": "已成功加入家庭",
            "family": await get_family_with_members(family.id, db)
        }
    
    return {
        "status": "pending",
        "message": f"已提交加入申请，等待家庭「{family.name}」的成员审批",
        "request_id": request.id
    }


@router.get("/my", response_model=FamilyResponse)
async def get_my_family(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的家庭信息"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    return await get_family_with_members(membership.family_id, db)


@router.put("/update", response_model=FamilyResponse)
async def update_family(
    family_data: FamilyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新家庭信息（仅管理员）"""
    # 获取用户的家庭成员记录
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    if membership.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以修改家庭信息")
    
    # 获取家庭
    result = await db.execute(select(Family).where(Family.id == membership.family_id))
    family = result.scalar_one_or_none()
    
    # 更新字段
    if family_data.name is not None:
        family.name = family_data.name
    if family_data.savings_target is not None:
        family.savings_target = family_data.savings_target
    if family_data.time_value_rate is not None:
        family.time_value_rate = family_data.time_value_rate
    
    await db.flush()
    return await get_family_with_members(family.id, db)


@router.post("/refresh-invite-code", response_model=FamilyResponse)
async def refresh_invite_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刷新邀请码（仅管理员）"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    if membership.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以刷新邀请码")
    
    result = await db.execute(select(Family).where(Family.id == membership.family_id))
    family = result.scalar_one_or_none()
    family.invite_code = generate_invite_code()
    
    await db.flush()
    return await get_family_with_members(family.id, db)


async def get_family_with_members(family_id: int, db: AsyncSession) -> dict:
    """获取带成员信息的家庭"""
    result = await db.execute(
        select(Family).where(Family.id == family_id)
    )
    family = result.scalar_one_or_none()
    
    # 获取成员
    result = await db.execute(
        select(FamilyMember, User)
        .join(User, FamilyMember.user_id == User.id)
        .where(FamilyMember.family_id == family_id)
    )
    member_rows = result.all()
    
    members = []
    for member, user in member_rows:
        members.append(FamilyMemberResponse(
            id=member.id,
            user_id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar_version=user.avatar_version or 0,
            role=member.role,
            joined_at=member.joined_at
        ))
    
    return FamilyResponse(
        id=family.id,
        name=family.name,
        savings_target=family.savings_target,
        time_value_rate=family.time_value_rate,
        invite_code=family.invite_code,
        created_at=family.created_at,
        members=members
    )


# ==================== 通知配置 API ====================

def mask_webhook_url(url: str) -> str:
    """对 Webhook URL 进行脱敏处理"""
    if not url:
        return ""
    # 保留前缀和最后8个字符
    if len(url) > ContentLimits.WEBHOOK_URL_MASK_LENGTH:
        return (url[:ContentLimits.WEBHOOK_URL_PREFIX_LENGTH] + 
                "****" + 
                url[-ContentLimits.WEBHOOK_URL_SUFFIX_LENGTH:])
    return url[:20] + "****"


@router.get("/notification/config", response_model=NotificationConfigResponse)
async def get_notification_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知配置"""
    # 获取用户的家庭
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    # 获取家庭信息
    result = await db.execute(
        select(Family).where(Family.id == membership.family_id)
    )
    family = result.scalar_one()
    
    # 解密 webhook URL（如果存在）
    decrypted_webhook = None
    if family.wechat_webhook_url:
        try:
            decrypted_webhook = decrypt_sensitive_data(family.wechat_webhook_url)
        except Exception:
            # 如果解密失败，可能是旧数据（未加密），直接使用原值
            decrypted_webhook = family.wechat_webhook_url
    
    return NotificationConfigResponse(
        notification_enabled=family.notification_enabled,
        wechat_webhook_url=mask_webhook_url(decrypted_webhook) if decrypted_webhook else None,
        has_wechat_webhook=bool(family.wechat_webhook_url),
        external_base_url=family.external_base_url
    )


@router.put("/notification/config", response_model=NotificationConfigResponse)
async def update_notification_config(
    config_data: NotificationConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新通知配置（仅管理员）"""
    # 获取用户的家庭成员记录
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    if membership.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以修改通知配置")
    
    # 获取家庭
    result = await db.execute(
        select(Family).where(Family.id == membership.family_id)
    )
    family = result.scalar_one()
    
    # 更新配置
    if config_data.notification_enabled is not None:
        family.notification_enabled = config_data.notification_enabled
    
    if config_data.wechat_webhook_url is not None:
        # 验证 Webhook URL 格式
        if config_data.wechat_webhook_url:
            if not config_data.wechat_webhook_url.startswith("https://qyapi.weixin.qq.com/"):
                raise HTTPException(
                    status_code=400, 
                    detail="无效的企业微信 Webhook URL，必须以 https://qyapi.weixin.qq.com/ 开头"
                )
            # 加密后存储
            family.wechat_webhook_url = encrypt_sensitive_data(config_data.wechat_webhook_url)
        else:
            family.wechat_webhook_url = None
    
    if config_data.external_base_url is not None:
        # 验证外网地址格式（必须以 http:// 或 https:// 开头）
        if config_data.external_base_url:
            url = config_data.external_base_url.rstrip("/")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise HTTPException(
                    status_code=400,
                    detail="无效的外网地址，必须以 http:// 或 https:// 开头"
                )
            family.external_base_url = url
        else:
            family.external_base_url = None
    
    await db.commit()
    
    # 解密 webhook URL 用于返回（如果存在）
    decrypted_webhook = None
    if family.wechat_webhook_url:
        try:
            decrypted_webhook = decrypt_sensitive_data(family.wechat_webhook_url)
        except Exception:
            # 如果解密失败，可能是旧数据（未加密），直接使用原值
            decrypted_webhook = family.wechat_webhook_url
    
    return NotificationConfigResponse(
        notification_enabled=family.notification_enabled,
        wechat_webhook_url=mask_webhook_url(decrypted_webhook) if decrypted_webhook else None,
        has_wechat_webhook=bool(family.wechat_webhook_url),
        external_base_url=family.external_base_url
    )


@router.post("/notification/test")
@limiter.limit("10/hour")
async def test_notification(
    test_data: NotificationTestRequest = NotificationTestRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    测试通知功能
    发送一条测试消息到配置的 Webhook
    """
    import httpx
    
    # 获取用户的家庭
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    # 获取家庭信息
    result = await db.execute(
        select(Family).where(Family.id == membership.family_id)
    )
    family = result.scalar_one()
    
    # 确定使用的 Webhook URL
    webhook_url = test_data.webhook_url or family.wechat_webhook_url
    
    if not webhook_url:
        raise HTTPException(status_code=400, detail="未配置企业微信 Webhook URL")
    
    # 如果使用的是数据库中的 webhook（已加密），需要解密
    if not test_data.webhook_url and family.wechat_webhook_url:
        try:
            webhook_url = decrypt_sensitive_data(family.wechat_webhook_url)
        except Exception:
            # 如果解密失败，可能是旧数据（未加密），直接使用原值
            webhook_url = family.wechat_webhook_url
    
    if not webhook_url.startswith("https://qyapi.weixin.qq.com/"):
        raise HTTPException(status_code=400, detail="无效的企业微信 Webhook URL")
    
    # 构建测试消息
    test_message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""### 🧪 小金库通知测试

**测试消息**

> 家庭：{family.name}
> 测试人：{current_user.nickname}
> 时间：收到此消息表示配置成功

<font color="info">恭喜！您的企业微信通知已配置成功</font>"""
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=test_message)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                return {
                    "success": True,
                    "message": "测试消息发送成功，请检查您的企业微信群"
                }
            else:
                return {
                    "success": False,
                    "message": f"发送失败: {result.get('errmsg', '未知错误')}"
                }
                
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")


@router.delete("/notification/webhook")
async def delete_webhook(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除企业微信 Webhook 配置（仅管理员）"""
    # 获取用户的家庭成员记录
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    if membership.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除 Webhook 配置")
    
    # 获取家庭并清除配置
    result = await db.execute(
        select(Family).where(Family.id == membership.family_id)
    )
    family = result.scalar_one()
    family.wechat_webhook_url = None
    
    await db.commit()
    
    return {"success": True, "message": "Webhook 配置已删除"}
