"""
小金库 (Golden Nest) - 股权计算服务
"""
from datetime import datetime
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import math

from app.models.models import Deposit, Family, FamilyMember, User
from app.schemas.equity import MemberEquity, EquitySummary


def calculate_weighted_amount(amount: float, deposit_date: datetime, rate: float, calculate_date: datetime = None) -> float:
    """
    计算时间加权后的金额
    
    使用复利公式: weighted_amount = amount * (1 + rate) ^ years
    
    Args:
        amount: 原始金额
        deposit_date: 存入日期
        rate: 年化利率 (如 0.03 表示 3%)
        calculate_date: 计算基准日期，默认为当前时间
    
    Returns:
        时间加权后的金额
    """
    if calculate_date is None:
        calculate_date = datetime.utcnow()
    
    # 计算存入时长（年）
    delta = calculate_date - deposit_date
    years = delta.days / 365.0
    
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
    total_weighted = 0.0
    total_original = 0.0
    
    for membership, user in member_rows:
        user_original = 0.0
        user_weighted = 0.0
        
        if user.id in user_deposits:
            for deposit in user_deposits[user.id]:
                user_original += deposit.amount
                weighted = calculate_weighted_amount(
                    deposit.amount,
                    deposit.deposit_date,
                    family.equity_rate,
                    now
                )
                user_weighted += weighted
        
        total_original += user_original
        total_weighted += user_weighted
        
        members_equity.append({
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "total_deposit": user_original,
            "weighted_deposit": user_weighted,
            "equity_ratio": 0,  # 稍后计算
            "equity_percentage": 0
        })
    
    # 计算股权比例
    for member in members_equity:
        if total_weighted > 0:
            member["equity_ratio"] = round(member["weighted_deposit"] / total_weighted, 6)
            member["equity_percentage"] = round(member["equity_ratio"] * 100, 2)
        else:
            member["equity_ratio"] = 0
            member["equity_percentage"] = 0
    
    # 转换为 Pydantic 模型
    member_equity_list = [MemberEquity(**m) for m in members_equity]
    
    # 计算目标进度
    target_progress = min(total_original / family.savings_target, 1.0) if family.savings_target > 0 else 0
    
    return EquitySummary(
        family_id=family.id,
        family_name=family.name,
        savings_target=family.savings_target,
        total_savings=total_original,
        total_weighted=total_weighted,
        target_progress=round(target_progress, 4),
        equity_rate=family.equity_rate,
        members=member_equity_list,
        calculated_at=now
    )
