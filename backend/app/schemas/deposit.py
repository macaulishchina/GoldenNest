"""
小金库 (Golden Nest) - 资金注入相关 Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DepositCreate(BaseModel):
    """创建资金注入请求"""
    amount: float = Field(..., gt=0, description="存入金额")
    deposit_date: datetime = Field(..., description="存入日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


class DepositResponse(BaseModel):
    """资金注入响应"""
    id: int
    user_id: int
    family_id: int
    amount: float
    deposit_date: datetime
    note: Optional[str] = None
    created_at: datetime
    
    # 额外字段
    user_nickname: Optional[str] = None
    weighted_amount: Optional[float] = None  # 时间加权后的金额
    
    class Config:
        from_attributes = True
