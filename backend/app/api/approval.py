"""
小金库 (Golden Nest) - 通用审批路由
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import (
    ApprovalRequest, ApprovalRecord, ApprovalRequestType, ApprovalRequestStatus,
    FamilyMember, User, Investment, Family, ExpenseRequest, ExpenseStatus
)
from app.schemas.approval import (
    ApprovalRequestResponse, ApprovalRecordCreate, ApprovalRequestListResponse,
    DepositApprovalCreate, InvestmentCreateApprovalCreate,
    InvestmentUpdateApprovalCreate, InvestmentIncomeApprovalCreate,
    MemberJoinApprovalCreate, MemberRemoveApprovalCreate, ExpenseApprovalCreate
)
from app.schemas.common import TimeRange, get_time_range_filter
from app.api.auth import get_current_user
from app.services.approval import ApprovalService
from app.services.notification import NotificationType, send_approval_notification

router = APIRouter()


async def get_user_family_id(user_id: int, db: AsyncSession) -> int:
    """获取用户的家庭ID"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    return membership.family_id


# ==================== 资金注入申请 ====================

@router.post("/deposit", response_model=ApprovalRequestResponse)
async def create_deposit_approval(
    data: DepositApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建资金注入申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.DEPOSIT,
        title=f"资金注入申请: {data.amount}元",
        description=f"{current_user.nickname}申请注入资金{data.amount}元" + (f"，备注: {data.note}" if data.note else ""),
        amount=data.amount,
        request_data={
            "amount": data.amount,
            "deposit_date": data.deposit_date.isoformat(),
            "note": data.note
        }
    )
    
    await db.commit()
    
    # 发送通知（多人家庭才需要通知）
    member_count_result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family_id)
    )
    if len(member_count_result.scalars().all()) > 1:
        await send_approval_notification(db, NotificationType.APPROVAL_CREATED, request)
    
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)


# ==================== 支出申请 ====================

@router.post("/expense", response_model=ApprovalRequestResponse)
async def create_expense_approval(
    data: ExpenseApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建支出申请
    所有成员必须同意后才能执行支出
    """
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证扣减比例总和为1
    total_ratio = sum(r.ratio for r in data.deduction_ratios)
    if abs(total_ratio - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="扣减比例总和必须为1")
    
    # 验证所有用户都是家庭成员
    for r in data.deduction_ratios:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == r.user_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"用户ID {r.user_id} 不是家庭成员")
    
    # 创建 ExpenseRequest 记录
    expense_request = ExpenseRequest(
        family_id=family_id,
        requester_id=current_user.id,
        title=data.title,
        amount=data.amount,
        reason=data.reason,
        equity_deduction_ratio=json.dumps({str(r.user_id): r.ratio for r in data.deduction_ratios}),
        status=ExpenseStatus.PENDING
    )
    db.add(expense_request)
    await db.flush()
    await db.refresh(expense_request)
    
    # 创建审批请求
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.EXPENSE,
        title=f"支出申请: {data.title}",
        description=f"{current_user.nickname}申请支出{data.amount}元，用于: {data.reason}",
        amount=data.amount,
        request_data={
            "expense_id": expense_request.id,
            "title": data.title,
            "amount": data.amount,
            "reason": data.reason,
            "deduction_ratios": {str(r.user_id): r.ratio for r in data.deduction_ratios}
        }
    )
    
    await db.commit()
    
    # 发送通知（多人家庭才需要通知）
    member_count_result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family_id)
    )
    if len(member_count_result.scalars().all()) > 1:
        await send_approval_notification(db, NotificationType.APPROVAL_CREATED, request)
    
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)


# ==================== 理财产品创建申请 ====================

@router.post("/investment/create", response_model=ApprovalRequestResponse)
async def create_investment_create_approval(
    data: InvestmentCreateApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建理财产品申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.INVESTMENT_CREATE,
        title=f"创建理财产品: {data.name}",
        description=f"{current_user.nickname}申请创建理财产品「{data.name}」，本金{data.principal}元，预期年化收益率{data.expected_rate*100:.2f}%",
        amount=data.principal,
        request_data={
            "name": data.name,
            "investment_type": data.investment_type,
            "principal": data.principal,
            "expected_rate": data.expected_rate,
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat() if data.end_date else None,
            "note": data.note
        }
    )
    
    await db.commit()
    
    # 发送通知（多人家庭才需要通知）
    member_count_result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family_id)
    )
    if len(member_count_result.scalars().all()) > 1:
        await send_approval_notification(db, NotificationType.APPROVAL_CREATED, request)
    
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)


# ==================== 理财产品更新申请 ====================

@router.post("/investment/update", response_model=ApprovalRequestResponse)
async def create_investment_update_approval(
    data: InvestmentUpdateApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建更新理财产品申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证理财产品存在
    result = await db.execute(
        select(Investment).where(
            Investment.id == data.investment_id,
            Investment.family_id == family_id
        )
    )
    investment = result.scalar_one_or_none()
    if not investment:
        raise HTTPException(status_code=404, detail="理财产品不存在")
    
    # 构建更新描述
    changes = []
    if data.name is not None:
        changes.append(f"名称改为「{data.name}」")
    if data.principal is not None:
        changes.append(f"本金改为{data.principal}元")
    if data.expected_rate is not None:
        changes.append(f"预期收益率改为{data.expected_rate*100:.2f}%")
    if data.is_active is not None:
        changes.append("激活" if data.is_active else "停用")
    
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.INVESTMENT_UPDATE,
        title=f"更新理财产品: {investment.name}",
        description=f"{current_user.nickname}申请更新理财产品「{investment.name}」：" + "、".join(changes) if changes else "无变更",
        amount=data.principal or investment.principal,
        request_data={
            "investment_id": data.investment_id,
            "name": data.name,
            "principal": data.principal,
            "expected_rate": data.expected_rate,
            "end_date": data.end_date.isoformat() if data.end_date else None,
            "is_active": data.is_active,
            "note": data.note
        }
    )
    
    await db.commit()
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)


# ==================== 理财收益登记申请 ====================

@router.post("/investment/income", response_model=ApprovalRequestResponse)
async def create_investment_income_approval(
    data: InvestmentIncomeApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建理财收益登记申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证理财产品存在
    result = await db.execute(
        select(Investment).where(
            Investment.id == data.investment_id,
            Investment.family_id == family_id
        )
    )
    investment = result.scalar_one_or_none()
    if not investment:
        raise HTTPException(status_code=404, detail="理财产品不存在")
    
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.INVESTMENT_INCOME,
        title=f"登记理财收益: {investment.name}",
        description=f"{current_user.nickname}申请登记理财产品「{investment.name}」收益{data.amount}元",
        amount=data.amount,
        request_data={
            "investment_id": data.investment_id,
            "amount": data.amount,
            "income_date": data.income_date.isoformat(),
            "note": data.note
        }
    )
    
    await db.commit()
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)


# ==================== 审批操作 ====================

@router.post("/{request_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """同意申请"""
    try:
        service = ApprovalService(db)
        
        # 获取申请状态（用于判断是否状态变更）
        pre_result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        )
        pre_request = pre_result.scalar_one_or_none()
        pre_status = pre_request.status if pre_request else None
        
        request = await service.approve_request(
            request_id=request_id,
            approver_id=current_user.id,
            is_approved=True,
            comment=None
        )
        
        # 获取申请人昵称
        result = await db.execute(
            select(User).where(User.id == request.requester_id)
        )
        requester = result.scalar_one()
        
        await db.commit()
        
        # 发送通知
        if request.status == ApprovalRequestStatus.APPROVED and pre_status == ApprovalRequestStatus.PENDING:
            # 申请已完成（全员同意）
            await send_approval_notification(db, NotificationType.APPROVAL_COMPLETED, request)
        else:
            # 有人投了同意票
            await send_approval_notification(db, NotificationType.APPROVAL_APPROVED, request, approver=current_user)
        
        return await service.get_request_response(request, requester.nickname, requester.avatar_version or 0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class RejectRequestBody(BaseModel):
    reason: Optional[str] = None


@router.post("/{request_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    request_id: int,
    body: RejectRequestBody = RejectRequestBody(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """拒绝申请"""
    try:
        service = ApprovalService(db)
        request = await service.approve_request(
            request_id=request_id,
            approver_id=current_user.id,
            is_approved=False,
            comment=body.reason
        )
        
        # 获取申请人昵称
        result = await db.execute(
            select(User).where(User.id == request.requester_id)
        )
        requester = result.scalar_one()
        
        await db.commit()
        
        # 发送拒绝通知
        await send_approval_notification(db, NotificationType.APPROVAL_REJECTED, request, approver=current_user)
        
        return await service.get_request_response(request, requester.nickname, requester.avatar_version or 0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/cancel", response_model=ApprovalRequestResponse)
async def cancel_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取消申请"""
    try:
        service = ApprovalService(db)
        request = await service.cancel_request(request_id, current_user.id)
        
        await db.commit()
        
        # 发送取消通知
        await send_approval_notification(db, NotificationType.APPROVAL_CANCELLED, request)
        
        return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ReminderResponse(BaseModel):
    success: bool
    message: str


@router.post("/{request_id}/remind", response_model=ReminderResponse)
async def remind_approval(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    催促审核
    向企业微信发送催促通知，提醒其他成员尽快审批
    """
    from app.services.notification import NotificationService
    
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取申请信息
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == request_id,
            ApprovalRequest.family_id == family_id
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    # 只有待处理的申请才能催促
    if request.status != ApprovalRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待处理的申请才能催促")
    
    # 获取申请人信息
    result = await db.execute(
        select(User).where(User.id == request.requester_id)
    )
    requester = result.scalar_one_or_none()
    if not requester:
        raise HTTPException(status_code=404, detail="申请人信息不存在")
    
    # 获取家庭信息
    result = await db.execute(
        select(Family).where(Family.id == family_id)
    )
    family = result.scalar_one_or_none()
    if not family:
        raise HTTPException(status_code=404, detail="家庭信息不存在")
    
    # 发送催促通知
    try:
        service = NotificationService(db)
        await service.notify_approval_reminder(request, family, requester, current_user)
        return ReminderResponse(success=True, message="催促通知已发送")
    except Exception as e:
        return ReminderResponse(success=False, message=f"发送失败: {str(e)}")


# ==================== 查询接口 ====================

@router.get("/list", response_model=ApprovalRequestListResponse)
async def list_approval_requests(
    request_type: Optional[ApprovalRequestType] = Query(None, description="申请类型"),
    status: Optional[ApprovalRequestStatus] = Query(None, description="申请状态"),
    time_range: TimeRange = Query(TimeRange.MONTH, description="时间范围：day/week/month/year/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取申请列表（支持时间范围筛选，默认最近一个月）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 构建查询
    query = select(ApprovalRequest, User).join(
        User, ApprovalRequest.requester_id == User.id
    ).where(ApprovalRequest.family_id == family_id)
    
    # 时间范围筛选
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(ApprovalRequest.created_at >= start_time)
    
    if request_type:
        query = query.where(ApprovalRequest.request_type == request_type)
    if status:
        query = query.where(ApprovalRequest.status == status)
    
    query = query.order_by(ApprovalRequest.created_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    service = ApprovalService(db)
    items = []
    pending_count = 0
    approved_count = 0
    rejected_count = 0
    
    for request, requester in rows:
        items.append(await service.get_request_response(request, requester.nickname, requester.avatar_version or 0))
        if request.status == ApprovalRequestStatus.PENDING:
            pending_count += 1
        elif request.status == ApprovalRequestStatus.APPROVED:
            approved_count += 1
        elif request.status == ApprovalRequestStatus.REJECTED:
            rejected_count += 1
    
    return ApprovalRequestListResponse(
        total=len(items),
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        items=items
    )


@router.get("/pending", response_model=List[ApprovalRequestResponse])
async def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取待我审批的申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取所有待审批的申请
    result = await db.execute(
        select(ApprovalRequest, User)
        .join(User, ApprovalRequest.requester_id == User.id)
        .where(
            ApprovalRequest.family_id == family_id,
            ApprovalRequest.status == ApprovalRequestStatus.PENDING
        )
        .order_by(ApprovalRequest.created_at.desc())
    )
    rows = result.all()
    
    service = ApprovalService(db)
    pending_items = []
    
    for request, requester in rows:
        # 检查当前用户是否已经审批过
        result = await db.execute(
            select(ApprovalRecord).where(
                ApprovalRecord.request_id == request.id,
                ApprovalRecord.approver_id == current_user.id
            )
        )
        if result.scalar_one_or_none():
            continue  # 已审批过，跳过
        
        # 检查是否是申请人（多人家庭时申请人一般不需要审批，但成员剔除例外）
        result = await db.execute(
            select(FamilyMember).where(FamilyMember.family_id == family_id)
        )
        members = result.scalars().all()
        
        # 成员剔除申请：管理员可以审批自己发起的申请
        if request.request_type == ApprovalRequestType.MEMBER_REMOVE:
            # 检查当前用户是否是管理员
            current_member = next((m for m in members if m.user_id == current_user.id), None)
            if not current_member or current_member.role != "admin":
                continue  # 非管理员不能审批剔除申请
        elif len(members) > 1 and request.requester_id == current_user.id:
            continue  # 其他类型：多人家庭，申请人不需要审批自己的申请
        
        pending_items.append(await service.get_request_response(request, requester.nickname, requester.avatar_version or 0))
    
    return pending_items


@router.get("/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取申请详情"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(ApprovalRequest, User)
        .join(User, ApprovalRequest.requester_id == User.id)
        .where(
            ApprovalRequest.id == request_id,
            ApprovalRequest.family_id == family_id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    request, requester = row
    service = ApprovalService(db)
    return await service.get_request_response(request, requester.nickname, requester.avatar_version or 0)


# ==================== 成员加入申请 ====================

@router.post("/member/join", response_model=ApprovalRequestResponse)
async def create_member_join_approval(
    data: MemberJoinApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建成员加入申请
    用户通过邀请码申请加入家庭，任意一个现有成员同意即可加入
    """
    # 检查用户是否已经有家庭
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="您已经加入了一个家庭")
    
    # 查找家庭
    result = await db.execute(
        select(Family).where(Family.invite_code == data.invite_code.upper())
    )
    family = result.scalar_one_or_none()
    if not family:
        raise HTTPException(status_code=404, detail="邀请码无效")
    
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
        raise HTTPException(status_code=400, detail="您已经有一个待处理的加入申请")
    
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
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)


# ==================== 成员剔除申请 ====================

@router.post("/member/remove", response_model=ApprovalRequestResponse)
async def create_member_remove_approval(
    data: MemberRemoveApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建成员剔除申请
    需要管理员同意才能剔除成员
    """
    family_id = await get_user_family_id(current_user.id, db)
    
    # 检查目标用户是否是家庭成员
    result = await db.execute(
        select(FamilyMember, User)
        .join(User, FamilyMember.user_id == User.id)
        .where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == data.user_id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="该用户不是家庭成员")
    
    target_member, target_user = row
    
    # 不能剔除自己
    if data.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能剔除自己")
    
    # 不能剔除管理员
    if target_member.role == "admin":
        raise HTTPException(status_code=400, detail="不能剔除管理员")
    
    # 检查是否有未处理的剔除申请
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.family_id == family_id,
            ApprovalRequest.request_type == ApprovalRequestType.MEMBER_REMOVE,
            ApprovalRequest.status == ApprovalRequestStatus.PENDING,
            ApprovalRequest.request_data.contains(str(data.user_id))  # 检查是否针对同一用户
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已经有一个针对该成员的剔除申请在处理中")
    
    # 获取家庭信息
    result = await db.execute(
        select(Family).where(Family.id == family_id)
    )
    family = result.scalar_one()
    
    service = ApprovalService(db)
    request = await service.create_request(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.MEMBER_REMOVE,
        title=f"申请剔除成员: {target_user.nickname}",
        description=f"{current_user.nickname}申请将「{target_user.nickname}」从家庭「{family.name}」中剔除" + (f"，原因: {data.reason}" if data.reason else ""),
        amount=0,
        request_data={
            "user_id": data.user_id,
            "username": target_user.username,
            "nickname": target_user.nickname,
            "reason": data.reason
        }
    )
    
    await db.commit()
    return await service.get_request_response(request, current_user.nickname, current_user.avatar_version or 0)
