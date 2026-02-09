"""
小金库 (Golden Nest) - 股权计算服务
"""
from datetime import datetime
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import math

from app.models.models import (
    Deposit, Family, FamilyMember, User,
    Transaction, Investment, InvestmentPosition, InvestmentIncome,
    PositionOperationType, Dividend, DividendStatus, DividendClaim, DividendClaimStatus
)
from app.schemas.equity import MemberEquity, EquitySummary


def calculate_weighted_amount(amount: float, deposit_date: datetime, rate: float, calculate_date: datetime = None) -> float:
    """
    计算时间加权后的金额
    
    使用复利公式: weighted_amount = amount * (1 + rate) ^ years
    
    Args:
        amount: 原始金额
        deposit_date: 存入日期
        rate: 时间价值系数 (如 0.03 表示 3%)，体现存的越久权重越高
        calculate_date: 计算基准日期，默认为当前时间
    
    Returns:
        时间加权后的金额
    """
    if calculate_date is None:
        calculate_date = datetime.utcnow()
    
    # 计算存入时长（年）
    delta = calculate_date - deposit_date
    years = delta.days / TimeConstants.DAYS_PER_YEAR
    
    # 如果是未来存入的（还没到存入日期），则不加权
    if years < 0:
        years = 0
    
    # 复利计算
    weighted = amount * math.pow(1 + rate, years)
    
    return round(weighted, 2)


async def calculate_family_equity(family_id: int, db: AsyncSession) -> EquitySummary:
    """
    计算家庭的股权分布
    
    Args:
        family_id: 家庭ID
        db: 数据库会话
    
    Returns:
        股权汇总信息
    """
    # 获取家庭信息
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()
    if not family:
        raise ValueError(f"家庭 {family_id} 不存在")
    
    # 获取家庭成员
    result = await db.execute(
        select(FamilyMember, User)
        .join(User, FamilyMember.user_id == User.id)
        .where(FamilyMember.family_id == family_id)
    )
    member_rows = result.all()
    
    # 获取所有存款记录
    result = await db.execute(
        select(Deposit).where(Deposit.family_id == family_id)
    )
    deposits = result.scalars().all()
    
    # 计算基准时间
    now = datetime.utcnow()
    
    # 按用户统计存款
    user_deposits: Dict[int, List[Deposit]] = {}
    for deposit in deposits:
        if deposit.user_id not in user_deposits:
            user_deposits[deposit.user_id] = []
        user_deposits[deposit.user_id].append(deposit)
    
    # 计算每个成员的股权
    members_equity: List[MemberEquity] = []
    total_original = 0.0
    
    for membership, user in member_rows:
        user_original = 0.0
        
        if user.id in user_deposits:
            for deposit in user_deposits[user.id]:
                user_original += deposit.amount
        
        total_original += user_original
        
        members_equity.append({
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_version": user.avatar_version or 0,  # 头像版本号
            "role": membership.role,  # 成员角色
            "total_deposit": user_original,
            "weighted_deposit": user_original,  # 不再使用时间加权，与 total_deposit 相同
            "equity_ratio": 0,  # 稍后计算
            "equity_percentage": 0
        })
    
    # 计算股权比例（直接按原始存入金额计算）
    for member in members_equity:
        if total_original > 0:
            member["equity_ratio"] = round(member["total_deposit"] / total_original, 6)
            member["equity_percentage"] = round(member["equity_ratio"] * 100, 2)
        else:
            member["equity_ratio"] = 0
            member["equity_percentage"] = 0
    
    # 转换为 Pydantic 模型
    member_equity_list = [MemberEquity(**m) for m in members_equity]
    
    # 🌟 计算当前储蓄 = 家庭自由资金 + 理财实际价值
    
    # 1. 获取家庭自由资金（最后一笔交易的 balance_after）
    free_cash = 0.0
    result = await db.execute(
        select(Transaction.balance_after)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.id.desc())
        .limit(1)
    )
    last_balance = result.scalar_one_or_none()
    if last_balance is not None:
        free_cash = last_balance
    
    # 2. 获取所有理财产品的实际价值
    investment_value = 0.0
    result = await db.execute(
        select(Investment)
        .where(Investment.family_id == family_id)
        .where(Investment.is_active == True)
        .where(Investment.is_deleted == False)
    )
    investments = result.scalars().all()
    
    for inv in investments:
        # 计算当前持仓本金
        result = await db.execute(
            select(InvestmentPosition)
            .where(InvestmentPosition.investment_id == inv.id)
        )
        positions = result.scalars().all()
        
        current_principal = sum(
            p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
            else -p.amount
            for p in positions
        )
        
        # 计算总收益
        result = await db.execute(
            select(InvestmentIncome)
            .where(InvestmentIncome.investment_id == inv.id)
        )
        income_records = result.scalars().all()
        
        total_return = sum(
            ir.calculated_income if ir.calculated_income is not None else ir.amount
            for ir in income_records
        )
        
        # 实际价值 = 当前持仓本金 + 总收益
        investment_value += current_principal + total_return
    
    # 3. 当前储蓄 = 家庭自由资金 + 理财实际价值
    total_savings = free_cash + investment_value
    
    # 4. 计算冻结资金（投票中或已通过但未处理的分红）
    frozen_amount = 0.0
    
    # 获取所有投票中或已通过的分红记录
    result = await db.execute(
        select(Dividend.id, Dividend.total_amount, Dividend.status)
        .where(
            Dividend.family_id == family.id,
            Dividend.status.in_([DividendStatus.VOTING, DividendStatus.APPROVED])
        )
    )
    dividends = result.all()
    
    for dividend_id, total_amount, status in dividends:
        if status == DividendStatus.VOTING:
            # 投票中：整笔金额都冻结
            frozen_amount += total_amount
        elif status == DividendStatus.APPROVED:
            # 已通过：只有未处理的claim金额仍然冻结
            result = await db.execute(
                select(func.sum(DividendClaim.amount))
                .where(
                    DividendClaim.dividend_id == dividend_id,
                    DividendClaim.status == DividendClaimStatus.PENDING
                )
            )
            pending_amount = result.scalar() or 0.0
            frozen_amount += pending_amount
    
    frozen_amount = round(frozen_amount, 2)
    
    # 计算目标进度
    target_progress = min(total_savings / family.savings_target, 1.0) if family.savings_target > 0 else 0
    
    return EquitySummary(
        family_id=family.id,
        family_name=family.name,
        savings_target=family.savings_target,
        total_savings=total_savings,
        total_weighted=total_original,  # 不再使用时间加权，与 total_savings 相同
        daily_weighted_growth=0.0,  # 不再计算时间加权增长
        target_progress=round(target_progress, 4),
        time_value_rate=family.time_value_rate,
        members=member_equity_list,
        calculated_at=now,
        frozen_amount=frozen_amount
    )
