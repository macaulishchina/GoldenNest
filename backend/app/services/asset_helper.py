"""
资产相关辅助服务函数
"""
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Asset, AssetType, CurrencyType, Transaction


async def get_cash_balance(db: AsyncSession, family_id: int) -> float:
    """
    获取家庭的活期现金余额（从Transaction表获取最新余额）
    
    Args:
        db: 数据库会话
        family_id: 家庭ID
        
    Returns:
        活期现金余额（CNY）
    """
    result = await db.execute(
        select(Transaction.balance_after)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    return last_transaction if last_transaction is not None else 0.0


async def check_cash_sufficient(db: AsyncSession, family_id: int, required_amount: float) -> bool:
    """
    检查活期余额是否充足
    
    Args:
        db: 数据库会话
        family_id: 家庭ID
        required_amount: 需要的金额（CNY）
        
    Returns:
        True表示余额充足，False表示余额不足
    """
    current_balance = await get_cash_balance(db, family_id)
    return current_balance >= required_amount


async def get_asset_summary(db: AsyncSession, family_id: int) -> dict:
    """
    获取家庭资产汇总
    
    Args:
        db: 数据库会话
        family_id: 家庭ID
        
    Returns:
        资产汇总信息
        {
            "cash_balance": 活期余额（CNY）,
            "total_investment": 投资总额（CNY）,
            "total_assets": 总资产（CNY）,
            "by_type": {按类型分组},
            "by_currency": {按币种分组}
        }
    """
    # 1. 获取活期余额（从Transaction表）
    cash_balance = await get_cash_balance(db, family_id)
    
    # 2. 获取所有投资型资产（不包括CASH类型）
    result = await db.execute(
        select(Asset)
        .where(
            and_(
                Asset.family_id == family_id,
                Asset.investment_type != AssetType.CASH,  # 排除CASH类型
                Asset.is_active == True,
                Asset.is_deleted == False
            )
        )
    )
    assets = result.scalars().all()
    
    # 3. 统计投资型资产
    total_investment = 0.0
    by_type = {}
    by_currency = {}
    
    for asset in assets:
        asset_type = asset.investment_type.value
        currency = asset.currency.value
        
        # 按类型统计
        if asset_type not in by_type:
            by_type[asset_type] = {"count": 0, "total_cny": 0.0}
        by_type[asset_type]["count"] += 1
        by_type[asset_type]["total_cny"] += asset.principal
        
        # 按币种统计
        if currency not in by_currency:
            by_currency[currency] = {"count": 0, "total_cny": 0.0, "total_foreign": 0.0}
        by_currency[currency]["count"] += 1
        by_currency[currency]["total_cny"] += asset.principal
        if asset.foreign_amount:
            by_currency[currency]["total_foreign"] += asset.foreign_amount
        
        # 累加投资总额
        total_investment += asset.principal
    
    return {
        "cash_balance": cash_balance,
        "total_investment": total_investment,
        "total_assets": cash_balance + total_investment,
        "by_type": by_type,
        "by_currency": by_currency
    }


async def get_user_assets(db: AsyncSession, user_id: int, family_id: int) -> list:
    """
    获取用户的投资型资产列表（不包括活期）
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        family_id: 家庭ID
        
    Returns:
        资产列表
    """
    result = await db.execute(
        select(Asset)
        .where(
            and_(
                Asset.family_id == family_id,
                Asset.user_id == user_id,
                Asset.investment_type != AssetType.CASH,  # 排除CASH类型
                Asset.is_active == True,
                Asset.is_deleted == False
            )
        )
        .order_by(Asset.created_at.desc())
    )
    return result.scalars().all()
