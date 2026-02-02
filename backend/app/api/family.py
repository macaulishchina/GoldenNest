"""
小金库 (Golden Nest) - 家庭管理路由
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Family, FamilyMember, User
from app.schemas.family import FamilyCreate, FamilyUpdate, FamilyResponse, FamilyMemberResponse, JoinFamilyRequest
from app.api.auth import get_current_user

router = APIRouter()


def generate_invite_code() -> str:
    """生成8位邀请码"""
    return secrets.token_urlsafe(6)[:8].upper()


@router.post("/create", response_model=FamilyResponse)
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
        equity_rate=family_data.equity_rate,
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
    
    # 返回带成员信息的家庭
    return await get_family_with_members(family.id, db)


@router.post("/join", response_model=FamilyResponse)
async def join_family(
    join_data: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """通过邀请码加入家庭"""
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
    
    # 加入家庭
    member = FamilyMember(
        user_id=current_user.id,
        family_id=family.id,
        role="member"
    )
    db.add(member)
    await db.flush()
    
    return await get_family_with_members(family.id, db)


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
    if family_data.equity_rate is not None:
        family.equity_rate = family_data.equity_rate
    
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
            avatar=user.avatar,
            role=member.role,
            joined_at=member.joined_at
        ))
    
    return FamilyResponse(
        id=family.id,
        name=family.name,
        savings_target=family.savings_target,
        equity_rate=family.equity_rate,
        invite_code=family.invite_code,
        created_at=family.created_at,
        members=members
    )
