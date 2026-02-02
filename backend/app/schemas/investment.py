"""
小金库 (Golden Nest) - 理财相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.models import InvestmentType


class InvestmentCreate(BaseModel):
    """创建理财配置请求"""
    name: str = Field(..., min_length=1, max_length=100, description="理财产品名称")
    investment_type: InvestmentType = Field(..., description="理财类型")
    principal: float = Field(..., gt=0, description="本金")
    expected_rate: float = Field(..., ge=0, le=1, description="预期年化收益率")
    start_date: datetime = Field(..., description="开始日期")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


class InvestmentUpdate(BaseModel):
    """更新理财配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    principal: Optional[float] = Field(None, gt=0)
    expected_rate: Optional[float] = Field(None, ge=0, le=1)
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=500)


class InvestmentIncomeCreate(BaseModel):
    """创建理财收益请求"""
    amount: float = Field(..., description="收益金额")
    income_date: datetime = Field(..., description="收益日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


class InvestmentIncomeResponse(BaseModel):
    """理财收益响应"""
    id: int
    investment_id: int
    amount: float
    income_date: datetime
    note: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvestmentResponse(BaseModel):
    """理财配置响应"""
    id: int
    family_id: int
    name: str
    investment_type: InvestmentType
    principal: float
    expected_rate: float
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool
    note: Optional[str] = None
    created_at: datetime
    
    # 额外字段
    total_income: Optional[float] = None  # 累计收益
    income_records: List[InvestmentIncomeResponse] = []
    
    class Config:
        from_attributes = True


class InvestmentSummary(BaseModel):
    """理财汇总信息"""
    family_id: int
    total_principal: float  # 总本金
    total_income: float  # 总收益
    active_count: int  # 活跃理财数量
    investments: List[InvestmentResponse]
