"""
小金库 (Golden Nest) - 理财相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.models.models import InvestmentType, PositionOperationType


class InvestmentCreate(BaseModel):
    """创建理财配置请求"""
    name: str = Field(..., min_length=1, max_length=100, description="理财产品名称")
    investment_type: InvestmentType = Field(..., description="理财类型")
    principal: float = Field(..., gt=0, description="本金")
    start_date: datetime = Field(..., description="开始日期")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


class InvestmentUpdate(BaseModel):
    """更新理财配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    principal: Optional[float] = Field(None, gt=0)
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
    amount: float  # 收益金额（老模式直接记录，或者新模式下的计算结果）
    current_value: Optional[float] = None  # 当前总价值（新模式）
    calculated_income: Optional[float] = None  # 计算出的收益（新模式）
    income_date: datetime
    note: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvestmentPositionResponse(BaseModel):
    """投资持仓变动响应"""
    id: int
    investment_id: int
    operation_type: PositionOperationType
    amount: float
    operation_date: datetime
    note: Optional[str] = None
    transaction_id: Optional[int] = None
    deposit_id: Optional[int] = None
    approval_request_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvestmentResponse(BaseModel):
    """理财配置响应"""
    id: int
    family_id: int
    name: str
    investment_type: InvestmentType
    principal: float  # 初始本金（CNY）
    currency: Optional[str] = "CNY"  # 货币类型
    foreign_amount: Optional[float] = None  # 外币金额
    exchange_rate: Optional[float] = None  # 汇率
    current_foreign_amount: Optional[float] = None  # 当前外币持仓
    cny_value: Optional[float] = None  # 当前人民币价值（实时汇率）
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    
    # 额外字段
    total_income: Optional[float] = None  # 累计收益
    current_principal: Optional[float] = None  # 当前持仓本金（CNY）
    total_return: Optional[float] = None  # 总收益
    roi: Optional[float] = None  # 投资回报率
    annualized_return: Optional[float] = None  # 平均年化收益率
    holding_days: Optional[int] = None  # 持有天数
    income_records: List[InvestmentIncomeResponse] = []
    positions: List[InvestmentPositionResponse] = []
    
    class Config:
        from_attributes = True


class InvestmentSummary(BaseModel):
    """理财汇总信息"""
    family_id: int
    total_principal: float  # 总本金（CNY）
    total_cny_value: Optional[float] = None  # 总人民币价值（实时汇率）
    total_income: float  # 总收益
    active_count: int  # 活跃理财数量
    average_annualized_return: Optional[float] = None  # 综合平均年化收益率
    investments: List[InvestmentResponse]


class DividendBreakdown(BaseModel):
    """分红明细（按投资产品）"""
    investment_id: int
    investment_name: str
    total_income: float  # 该产品总收益
    percentage: float  # 该产品收益占比


class InvestmentIncreaseCreate(BaseModel):
    """增持投资请求"""
    amount: float = Field(..., gt=0, description="增持金额")
    operation_date: datetime = Field(..., description="增持日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


class InvestmentDecreaseCreate(BaseModel):
    """减持投资请求"""
    amount: float = Field(..., gt=0, description="减持金额")
    operation_date: datetime = Field(..., description="减持日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")
