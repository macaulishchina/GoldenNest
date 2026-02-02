"""
小金库 (Golden Nest) - 资金注入路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Deposit, FamilyMember, User, Transaction, TransactionType
from app.schemas.deposit import DepositCreate, DepositResponse
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


@router.post("/create", response_model=DepositResponse)
async def create_deposit(
    deposit_data: DepositCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建资金注入记录"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 创建存款记录
    deposit = Deposit(
        user_id=current_user.id,
        family_id=family_id,
        amount=deposit_data.amount,
        deposit_date=deposit_data.deposit_date,
        note=deposit_data.note
    )
    db.add(deposit)
    await db.flush()
    
    # 获取当前余额
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0
    
    # 创建交易流水
    transaction = Transaction(
        family_id=family_id,
        user_id=current_user.id,
        transaction_type=TransactionType.DEPOSIT,
        amount=deposit_data.amount,
        balance_after=current_balance + deposit_data.amount,
        description=f"{current_user.nickname}存入{deposit_data.amount}元",
        reference_id=deposit.id,
        reference_type="deposit"
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(deposit)
    
    # 检查成就解锁（失败不影响主业务）
    try:
        achievement_service = AchievementService(db)
        new_unlocks = await achievement_service.check_and_unlock(
            user_id=current_user.id,
            context={"deposit_amount": deposit_data.amount, "action": "deposit"}
        )
    except Exception as e:
        # 记录日志但不抛出异常
        import logging
        logging.warning(f"Achievement check failed: {e}")
    
    await db.commit()
    
    return DepositResponse(
        id=deposit.id,
        user_id=deposit.user_id,
        family_id=deposit.family_id,
        amount=deposit.amount,
        deposit_date=deposit.deposit_date,
        note=deposit.note,
        created_at=deposit.created_at,
        user_nickname=current_user.nickname
    )


@router.get("/list", response_model=List[DepositResponse])
async def list_deposits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭所有存款记录"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Deposit, User)
        .join(User, Deposit.user_id == User.id)
        .where(Deposit.family_id == family_id)
        .order_by(Deposit.deposit_date.desc())
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的存款记录"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Deposit)
        .where(Deposit.family_id == family_id, Deposit.user_id == current_user.id)
        .order_by(Deposit.deposit_date.desc())
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
