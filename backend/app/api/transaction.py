"""
小金库 (Golden Nest) - 交易流水路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.models import Transaction, TransactionType, FamilyMember, User, InvestmentIncome, Investment
from app.schemas.transaction import TransactionResponse, TransactionSummary, DividendCalculation, MemberDividend
from app.api.auth import get_current_user
from app.services.equity import calculate_family_equity

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


@router.get("/list", response_model=List[TransactionResponse])
async def list_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取交易流水列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()
    
    # 获取用户信息
    user_ids = [t.user_id for t in transactions if t.user_id]
    users_map = {}
    if user_ids:
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = result.scalars().all()
        users_map = {u.id: u.nickname for u in users}
    
    return [
        TransactionResponse(
            id=t.id,
            family_id=t.family_id,
            user_id=t.user_id,
            user_nickname=users_map.get(t.user_id) if t.user_id else None,
            transaction_type=t.transaction_type,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            reference_id=t.reference_id,
            reference_type=t.reference_type,
            created_at=t.created_at
        )
        for t in transactions
    ]


@router.get("/summary", response_model=TransactionSummary)
async def get_transaction_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取交易汇总"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 统计各类交易
    result = await db.execute(
        select(
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.DEPOSIT),
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.WITHDRAW),
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.INCOME),
            func.count(Transaction.id)
        )
        .where(Transaction.family_id == family_id)
    )
    row = result.one()
    
    total_deposits = row[0] or 0
    total_withdrawals = abs(row[1] or 0)
    total_income = row[2] or 0
    transaction_count = row[3] or 0
    
    # 获取当前余额
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0
    
    return TransactionSummary(
        family_id=family_id,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        total_income=total_income,
        current_balance=current_balance,
        transaction_count=transaction_count
    )


@router.get("/dividend", response_model=DividendCalculation)
async def calculate_dividend(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """计算分红"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取股权信息
    equity_summary = await calculate_family_equity(family_id, db)
    
    # 计算总收益
    result = await db.execute(
        select(func.sum(InvestmentIncome.amount))
        .join(Investment, InvestmentIncome.investment_id == Investment.id)
        .where(Investment.family_id == family_id)
    )
    total_income = result.scalar() or 0
    
    # 按股权比例计算分红
    members_dividend = []
    for member in equity_summary.members:
        dividend_amount = total_income * member.equity_ratio
        members_dividend.append(MemberDividend(
            user_id=member.user_id,
            nickname=member.nickname,
            equity_ratio=member.equity_ratio,
            dividend_amount=round(dividend_amount, 2)
        ))
    
    return DividendCalculation(
        family_id=family_id,
        total_income=total_income,
        members=members_dividend
    )
