"""
小金库 (Golden Nest) - 股权相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MemberEquity(BaseModel):
    """成员股权信息"""
    user_id: int
    username: str
    nickname: str
    avatar: Optional[str] = None
    total_deposit: float  # 原始存入总额
    weighted_deposit: float  # 时间加权后总额
    equity_ratio: float  # 股权占比 (0-1)
    equity_percentage: float  # 股权百分比 (0-100)


class EquitySummary(BaseModel):
    """股权汇总信息"""
    family_id: int
    family_name: str
    savings_target: float  # 储蓄目标
    total_savings: float  # 当前总储蓄
    total_weighted: float  # 时间加权后总额
    target_progress: float  # 目标完成进度 (0-1)
    equity_rate: float  # 时间加权年化利率
    members: List[MemberEquity]  # 各成员股权信息
    calculated_at: datetime  # 计算时间


class EquityHistory(BaseModel):
    """股权历史记录"""
    date: datetime
    user_id: int
    equity_ratio: float
    total_weighted: float
