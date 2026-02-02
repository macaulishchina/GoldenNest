"""
小金库 (Golden Nest) - 交易流水相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.models import TransactionType


class TransactionResponse(BaseModel):
    """交易流水响应"""
    id: int
    family_id: int
    user_id: Optional[int] = None
    user_nickname: Optional[str] = None
    transaction_type: TransactionType
    amount: float
    balance_after: float
    description: str
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionSummary(BaseModel):
    """交易汇总信息"""
    family_id: int
    total_deposits: float  # 总存入
    total_withdrawals: float  # 总支出
    total_income: float  # 总收益
    current_balance: float  # 当前余额
    transaction_count: int  # 交易笔数


class DividendCalculation(BaseModel):
    """分红计算结果"""
    family_id: int
    total_income: float  # 总收益
    members: List["MemberDividend"]  # 各成员分红


class MemberDividend(BaseModel):
    """成员分红信息"""
    user_id: int
    nickname: str
    equity_ratio: float  # 股权占比
    dividend_amount: float  # 应得分红金额


# 解决循环引用
DividendCalculation.model_rebuild()
