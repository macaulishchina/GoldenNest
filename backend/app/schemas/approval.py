"""
小金库 (Golden Nest) - 通用审批相关 Schemas
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.models import ApprovalRequestType, ApprovalRequestStatus, AssetType, CurrencyType


class ApprovalRecordCreate(BaseModel):
    """创建审批记录"""
    is_approved: bool = Field(..., description="是否同意")
    comment: Optional[str] = Field(None, max_length=500, description="审批意见")


class ApprovalRecordResponse(BaseModel):
    """审批记录响应"""
    id: int
    request_id: int
    approver_id: int
    approver_nickname: str
    approver_avatar_version: int = 0  # 审批者头像版本号
    is_approved: bool
    comment: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ApprovalRequestCreate(BaseModel):
    """创建通用申请"""
    request_type: ApprovalRequestType = Field(..., description="申请类型")
    title: str = Field(..., max_length=200, description="申请标题")
    description: str = Field(..., description="申请描述")
    amount: float = Field(..., description="涉及金额")
    request_data: Dict[str, Any] = Field(..., description="申请数据")


class ApprovalRequestResponse(BaseModel):
    """通用申请响应"""
    id: int
    family_id: int
    requester_id: int
    requester_nickname: str
    requester_avatar_version: int = 0  # 申请者头像版本号
    target_user_id: Optional[int] = None  # 目标用户ID（个人专属审核）
    target_user_nickname: Optional[str] = None  # 目标用户昵称
    target_user_avatar_version: Optional[int] = None  # 目标用户头像版本号
    request_type: ApprovalRequestType
    title: str
    description: str
    amount: float
    request_data: Dict[str, Any]
    status: ApprovalRequestStatus
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime] = None
    execution_failed: bool = False  # 执行失败标记
    failure_reason: Optional[str] = None  # 失败原因
    
    # 审批详情
    approvals: List[ApprovalRecordResponse] = []
    pending_approvers: List[int] = []  # 待审批成员ID列表
    total_members: int = 0  # 家庭总成员数
    approved_count: int = 0  # 已同意数量
    rejected_count: int = 0  # 已拒绝数量
    
    class Config:
        from_attributes = True


# ============ 资金注入申请 ============

class DepositApprovalCreate(BaseModel):
    """创建资金注入申请（保留向后兼容）"""
    amount: float = Field(..., gt=0, description="存入金额")
    deposit_date: datetime = Field(..., description="存入日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 资产登记申请（统一入口）============

class AssetCreateApprovalCreate(BaseModel):
    """创建资产登记申请（统一deposit和investment）"""
    # 基础信息
    user_id: int = Field(..., description="资产归属人ID")
    name: str = Field(..., max_length=100, description="资产名称")
    asset_type: AssetType = Field(..., description="资产类型(cash/time_deposit/fund/stock/bond/other)")
    
    # 💰 多币种支持
    currency: CurrencyType = Field(CurrencyType.CNY, description="货币类型")
    amount: Optional[float] = Field(None, gt=0, description="金额（CNY，仅当currency=CNY时使用）")
    foreign_amount: Optional[float] = Field(None, gt=0, description="外币金额（当currency!=CNY时必填）")
    # exchange_rate由后端自动获取，前端无需传入
    
    # 资产属性
    start_date: datetime = Field(..., description="开始日期")
    end_date: Optional[datetime] = Field(None, description="到期日期（活期为空）")
    bank_name: Optional[str] = Field(None, max_length=100, description="银行/机构名称")
    
    # 资金来源
    deduct_from_cash: bool = Field(False, description="是否从活期扣除（True=内部转换，False=外部注资）")
    
    note: Optional[str] = Field(None, max_length=500, description="备注")
    
    @model_validator(mode='after')
    def validate_amount_by_currency(self):
        """根据币种验证金额字段"""
        if self.currency == CurrencyType.CNY:
            if self.amount is None or self.amount <= 0:
                raise ValueError('人民币资产必须提供有效的amount')
            # CNY资产不使用foreign_amount
            self.foreign_amount = None
        else:
            # 外币资产必须提供foreign_amount
            if self.foreign_amount is None or self.foreign_amount <= 0:
                raise ValueError(f'{self.currency.value}资产必须提供有效的foreign_amount')
            # 外币资产的amount将由后端根据汇率计算
            self.amount = None
        
        return self


# ============ 理财产品创建申请 ============

class InvestmentCreateApprovalCreate(BaseModel):
    """创建理财产品申请"""
    name: str = Field(..., max_length=100, description="理财产品名称")
    investment_type: str = Field(..., description="理财类型")
    principal: Optional[float] = Field(None, gt=0, description="本金（CNY，仅当currency=CNY时使用）")
    currency: CurrencyType = Field(CurrencyType.CNY, description="货币类型")
    foreign_amount: Optional[float] = Field(None, gt=0, description="外币金额（当currency!=CNY时必填）")
    start_date: datetime = Field(..., description="开始日期")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    deduct_from_cash: bool = Field(default=False, description="是否从自由资金扣除")
    note: Optional[str] = Field(None, max_length=500, description="备注")

    @model_validator(mode='after')
    def validate_amount_by_currency(self):
        """根据币种验证金额字段"""
        if self.currency == CurrencyType.CNY:
            if self.principal is None or self.principal <= 0:
                raise ValueError('人民币理财必须提供有效的principal')
            self.foreign_amount = None
        else:
            if self.foreign_amount is None or self.foreign_amount <= 0:
                raise ValueError(f'{self.currency.value}理财必须提供有效的foreign_amount')
        return self


# ============ 理财产品更新申请 ============

class InvestmentUpdateApprovalCreate(BaseModel):
    """更新理财产品申请"""
    investment_id: int = Field(..., description="理财产品ID")
    name: Optional[str] = Field(None, max_length=100, description="理财产品名称")
    principal: Optional[float] = Field(None, gt=0, description="本金")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    is_active: Optional[bool] = Field(None, description="是否激活")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 理财收益登记申请 ============

class InvestmentIncomeApprovalCreate(BaseModel):
    """登记理财收益申请"""
    investment_id: int = Field(..., description="理财产品ID")
    amount: Optional[float] = Field(None, description="收益金额（老模式）")
    current_value: Optional[float] = Field(None, gt=0, description="当前总价值（新模式）")
    income_date: datetime = Field(..., description="收益日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")
    
    @model_validator(mode='after')
    def check_at_least_one(self):
        """至少提供amount或current_value之一"""
        if self.amount is None and self.current_value is None:
            raise ValueError('必须提供amount或current_value中的至少一个')
        return self

# ============ 投资增持申请 ============

class InvestmentIncreaseApprovalCreate(BaseModel):
    """增持投资申请"""
    investment_id: int = Field(..., description="理财产品ID")
    amount: Optional[float] = Field(None, gt=0, description="增持金额（CNY，仅当投资为CNY时使用）")
    foreign_amount: Optional[float] = Field(None, gt=0, description="增持外币金额（当投资为外币时使用）")
    operation_date: datetime = Field(..., description="增持日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")
    deduct_from_cash: bool = Field(True, description="是否从自由资金扣除（False=外部资金，计入股权）")


# ============ 投资减持申请 ============

class InvestmentDecreaseApprovalCreate(BaseModel):
    """减持投资申请"""
    investment_id: int = Field(..., description="理财产品ID")
    amount: Optional[float] = Field(None, gt=0, description="减持金额（CNY，仅当投资为CNY时使用）")
    foreign_amount: Optional[float] = Field(None, gt=0, description="减持外币金额（当投资为外币时使用）")
    operation_date: datetime = Field(..., description="减持日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 删除投资申请 ============

class InvestmentDeleteApprovalCreate(BaseModel):
    """删除投资产品申请"""
    investment_id: int = Field(..., description="理财产品ID")
    reason: Optional[str] = Field(None, max_length=500, description="删除原因")


# ============ 成员加入申请 ============

class MemberJoinApprovalCreate(BaseModel):
    """创建成员加入申请"""
    invite_code: str = Field(..., description="邀请码")


# ============ 成员剔除申请 ============

class MemberRemoveApprovalCreate(BaseModel):
    """创建成员剔除申请"""
    target_user_id: int = Field(..., description="要剔除的成员ID")
    reason: Optional[str] = Field(None, max_length=500, description="剔除原因")
    
    @property
    def user_id(self) -> int:
        """兼容旧字段名"""
        return self.target_user_id


# ============ 支出申请 ============

class ExpenseDeductionRatio(BaseModel):
    """股权扣减比例"""
    user_id: int
    ratio: float = Field(..., ge=0, le=1, description="扣减比例 (0-1)")


class ExpenseApprovalCreate(BaseModel):
    """创建支出申请"""
    title: str = Field(..., min_length=1, max_length=200, description="支出标题")
    amount: float = Field(..., gt=0, description="支出金额")
    reason: str = Field(..., min_length=1, description="支出原因")
    deduction_ratios: List[ExpenseDeductionRatio] = Field(..., description="各成员股权扣减比例")


# ============ 申请列表响应 ============

class ApprovalRequestListResponse(BaseModel):
    """申请列表响应"""
    total: int
    pending_count: int
    approved_count: int
    rejected_count: int
    items: List[ApprovalRequestResponse]
