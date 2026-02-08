"""
小金库 (Golden Nest) - 分红服务
"""
from datetime import datetime
from typing import List, Dict
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import json

from app.models.models import (
    Dividend, DividendClaim, DividendType, DividendStatus, DividendClaimStatus,
    ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus,
    Deposit, Transaction, TransactionType, Investment, InvestmentIncome,
    Family, FamilyMember, User
)
from app.services.equity import calculate_family_equity


async def calculate_dividend_pool(
    family_id: int,
    dividend_type: DividendType,
    db: AsyncSession
) -> float:
    """
    计算可用于分红的资金池金额
    
    Args:
        family_id: 家庭ID
        dividend_type: 分红类型（PROFIT=收益池，CASH=自由资金池）
        db: 数据库会话
    
    Returns:
        可分红金额
    """
    if dividend_type == DividendType.PROFIT:
        # 计算所有理财收益记录的总和
        result = await db.execute(
            select(func.coalesce(func.sum(InvestmentIncome.amount), 0))
            .join(Investment, InvestmentIncome.investment_id == Investment.id)
            .where(Investment.family_id == family_id)
        )
        total_profit = result.scalar() or 0.0
        return float(total_profit)
    
    elif dividend_type == DividendType.CASH:
        # 获取最新的Transaction记录的balance_after字段
        result = await db.execute(
            select(Transaction.balance_after)
            .where(Transaction.family_id == family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        balance = result.scalar()
        return float(balance) if balance else 0.0
    
    return 0.0


async def create_dividend_claims(
    dividend_id: int,
    db: AsyncSession
) -> None:
    """
    为分红创建各成员的领取记录和个人审核
    
    Args:
        dividend_id: 分红记录ID
        db: 数据库会话
    """
    # 获取分红记录
    result = await db.execute(
        select(Dividend).where(Dividend.id == dividend_id)
    )
    dividend = result.scalar_one_or_none()
    if not dividend:
        raise ValueError(f"分红记录 {dividend_id} 不存在")
    
    # 检查状态
    if dividend.status != DividendStatus.APPROVED:
        raise ValueError(f"分红记录状态不是APPROVED: {dividend.status}")
    
    # 计算股权分布
    equity_summary = await calculate_family_equity(dividend.family_id, db)
    
    # 为每个成员创建DividendClaim记录
    for member_equity in equity_summary.members:
        # 计算该成员的分红金额
        member_amount = round(dividend.total_amount * member_equity.equity_ratio, 2)
        
        if member_amount <= 0:
            continue  # 如果股权为0，不创建记录
        
        # 创建DividendClaim记录
        claim = DividendClaim(
            dividend_id=dividend.id,
            user_id=member_equity.user_id,
            amount=member_amount,
            equity_ratio=member_equity.equity_ratio,
            status=DividendClaimStatus.PENDING
        )
        db.add(claim)
        await db.flush()  # 获取claim.id
        
        # 为该成员创建个人审核
        approval = ApprovalRequest(
            family_id=dividend.family_id,
            requester_id=dividend.created_by,  # 发起人为分红创建者（系统）
            target_user_id=member_equity.user_id,  # 目标用户（只有他能处理）
            request_type=ApprovalRequestType.DIVIDEND_CLAIM,
            title=f"分红领取 - {member_amount:.2f}元",
            description=f"您在本次分红中获得 {member_amount:.2f} 元（股权比例 {member_equity.equity_percentage:.2f}%），请选择处理方式",
            amount=member_amount,
            request_data=json.dumps({
                "dividend_id": dividend.id,
                "claim_id": claim.id,
                "equity_ratio": member_equity.equity_ratio
            }, ensure_ascii=False),
            status=ApprovalRequestStatus.PENDING
        )
        db.add(approval)
        await db.flush()
        
        # 更新claim的approval_request_id
        claim.approval_request_id = approval.id
    
    # 更新分红状态
    dividend.status = DividendStatus.DISTRIBUTING
    dividend.distributed_at = datetime.utcnow()
    
    await db.commit()


async def clear_dividend_pool(
    family_id: int,
    dividend_type: DividendType,
    amount: float,
    db: AsyncSession
) -> None:
    """
    清空分红资金池
    
    Args:
        family_id: 家庭ID
        dividend_type: 分红类型
        amount: 分红金额（用于验证）
        db: 数据库会话
    """
    if dividend_type == DividendType.PROFIT:
        # 删除所有理财收益记录（已分红的收益应该清除）
        result = await db.execute(
            select(InvestmentIncome)
            .join(Investment, InvestmentIncome.investment_id == Investment.id)
            .where(Investment.family_id == family_id)
        )
        income_records = result.scalars().all()
        for record in income_records:
            await db.delete(record)
    
    elif dividend_type == DividendType.CASH:
        # 创建一笔支出Transaction，减少balance_after
        # 获取当前余额
        result = await db.execute(
            select(Transaction.balance_after)
            .where(Transaction.family_id == family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        current_balance = result.scalar() or 0.0
        
        # 创建分红支出交易
        transaction = Transaction(
            family_id=family_id,
            user_id=None,  # 系统操作
            transaction_type=TransactionType.DIVIDEND,
            amount=-amount,  # 负数表示支出
            balance_after=current_balance - amount,
            description=f"分红发放 - {amount:.2f}元",
            reference_type="dividend",
            reference_id=None  # 可以后续关联dividend_id
        )
        db.add(transaction)
    
    await db.commit()


async def process_dividend_claim(
    claim_id: int,
    reinvest: bool,
    user_id: int,
    db: AsyncSession
) -> None:
    """
    处理分红领取
    
    Args:
        claim_id: 分红领取记录ID
        reinvest: 是否红利再投
        user_id: 用户ID
        db: 数据库会话
    """
    # 获取claim记录
    result = await db.execute(
        select(DividendClaim).where(DividendClaim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise ValueError(f"分红领取记录 {claim_id} 不存在")
    
    # 验证用户
    if claim.user_id != user_id:
        raise ValueError(f"用户 {user_id} 无权处理此分红领取记录")
    
    # 检查状态
    if claim.status != DividendClaimStatus.PENDING:
        raise ValueError(f"分红领取记录状态不是PENDING: {claim.status}")
    
    # 获取分红记录
    result = await db.execute(
        select(Dividend).where(Dividend.id == claim.dividend_id)
    )
    dividend = result.scalar_one_or_none()
    if not dividend:
        raise ValueError(f"分红记录 {claim.dividend_id} 不存在")
    
    if reinvest:
        # 创建Deposit记录（红利再投，增加股权）
        deposit = Deposit(
            user_id=user_id,
            family_id=dividend.family_id,
            amount=claim.amount,
            description=f"分红再投 - {claim.amount:.2f}元",
            deposit_date=datetime.utcnow()
        )
        db.add(deposit)
        await db.flush()
        
        # 创建Transaction记录，增加家庭自由资金
        result = await db.execute(
            select(Transaction.balance_after)
            .where(Transaction.family_id == dividend.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        current_balance = result.scalar() or 0.0
        
        transaction = Transaction(
            family_id=dividend.family_id,
            user_id=user_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=claim.amount,
            balance_after=current_balance + claim.amount,
            description=f"分红再投 - {claim.amount:.2f}元",
            reference_type="deposit",
            reference_id=deposit.id
        )
        db.add(transaction)
        
        # 更新claim记录
        claim.status = DividendClaimStatus.REINVESTED
        claim.reinvest = True
        claim.deposit_id = deposit.id
    else:
        # 提现，不做任何资金变动（资金已在分红时从池中扣除）
        claim.status = DividendClaimStatus.WITHDRAWN
        claim.reinvest = False
    
    claim.processed_at = datetime.utcnow()
    
    # 检查是否所有成员都已处理
    result = await db.execute(
        select(func.count(DividendClaim.id))
        .where(
            and_(
                DividendClaim.dividend_id == dividend.id,
                DividendClaim.status == DividendClaimStatus.PENDING
            )
        )
    )
    pending_count = result.scalar()
    
    if pending_count == 0:
        # 所有成员都已处理，更新分红状态为完成
        dividend.status = DividendStatus.COMPLETED
        dividend.completed_at = datetime.utcnow()
    
    # 不要在这里 commit，让调用者管理事务
    # await db.commit()


async def get_dividend_by_proposal(
    proposal_id: int,
    db: AsyncSession
) -> Dividend:
    """
    根据提案ID获取分红记录
    
    Args:
        proposal_id: 提案ID
        db: 数据库会话
    
    Returns:
        Dividend对象
    """
    result = await db.execute(
        select(Dividend).where(Dividend.proposal_id == proposal_id)
    )
    return result.scalar_one_or_none()
