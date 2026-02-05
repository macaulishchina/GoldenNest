"""
小金库 (Golden Nest) - 资金注入路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Deposit, FamilyMember, User, Transaction, TransactionType
from app.schemas.deposit import DepositCreate, DepositResponse
from app.schemas.common import TimeRange, get_time_range_filter
from app.api.auth import get_current_user
from app.services.equity import calculate_weighted_amount
from app.services.achievement import AchievementService

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


@router.post("/create")
async def create_deposit(
    deposit_data: DepositCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    [已废弃] 创建资金注入记录
    
    此接口已废弃，请使用审批接口 POST /api/approval/deposit
    所有资金注入现在需要经过家庭成员审批后才能执行。
    """
    raise HTTPException(
        status_code=400,
        detail="此接口已废弃。资金注入需要家庭成员审批，请使用 POST /api/approval/deposit 接口"
    )


@router.get("/list", response_model=List[DepositResponse])
async def list_deposits(
    time_range: TimeRange = Query(TimeRange.MONTH, description="时间范围：day/week/month/year/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭所有存款记录（支持时间范围筛选，默认最近一个月）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 构建查询
    query = select(Deposit, User).join(User, Deposit.user_id == User.id).where(Deposit.family_id == family_id)
    
    # 时间范围筛选
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(Deposit.deposit_date >= start_time)
    
    result = await db.execute(
        query.order_by(Deposit.deposit_date.desc())
    )
    rows = result.all()
    
    deposits = []
    for deposit, user in rows:
        deposits.append(DepositResponse(
            id=deposit.id,
            user_id=deposit.user_id,
            family_id=deposit.family_id,
            amount=deposit.amount,
            deposit_date=deposit.deposit_date,
            note=deposit.note,
            created_at=deposit.created_at,
            user_nickname=user.nickname
        ))
    
    return deposits


@router.get("/my", response_model=List[DepositResponse])
async def list_my_deposits(
    time_range: TimeRange = Query(TimeRange.MONTH, description="时间范围：day/week/month/year/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的存款记录（支持时间范围筛选，默认最近一个月）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 构建查询
    query = select(Deposit).where(Deposit.family_id == family_id, Deposit.user_id == current_user.id)
    
    # 时间范围筛选
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(Deposit.deposit_date >= start_time)
    
    result = await db.execute(
        query.order_by(Deposit.deposit_date.desc())
    )
    deposits = result.scalars().all()
    
    return [
        DepositResponse(
            id=d.id,
            user_id=d.user_id,
            family_id=d.family_id,
            amount=d.amount,
            deposit_date=d.deposit_date,
            note=d.note,
            created_at=d.created_at,
            user_nickname=current_user.nickname
        )
        for d in deposits
    ]
