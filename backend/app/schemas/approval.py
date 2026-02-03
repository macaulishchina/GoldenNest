"""
小金库 (Golden Nest) - 通用审批相关 Schemas
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

from app.models.models import ApprovalRequestType, ApprovalRequestStatus


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
    request_type: ApprovalRequestType
    title: str
    description: str
    amount: float
    request_data: Dict[str, Any]
    status: ApprovalRequestStatus
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime] = None
    
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
    """创建资金注入申请"""
    amount: float = Field(..., gt=0, description="存入金额")
    deposit_date: datetime = Field(..., description="存入日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 理财产品创建申请 ============

class InvestmentCreateApprovalCreate(BaseModel):
    """创建理财产品申请"""
    name: str = Field(..., max_length=100, description="理财产品名称")
    investment_type: str = Field(..., description="理财类型")
    principal: float = Field(..., gt=0, description="本金")
    expected_rate: float = Field(..., ge=0, le=1, description="预期年化收益率")
    start_date: datetime = Field(..., description="开始日期")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 理财产品更新申请 ============

class InvestmentUpdateApprovalCreate(BaseModel):
    """更新理财产品申请"""
    investment_id: int = Field(..., description="理财产品ID")
    name: Optional[str] = Field(None, max_length=100, description="理财产品名称")
    principal: Optional[float] = Field(None, gt=0, description="本金")
    expected_rate: Optional[float] = Field(None, ge=0, le=1, description="预期年化收益率")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    is_active: Optional[bool] = Field(None, description="是否激活")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 理财收益登记申请 ============

class InvestmentIncomeApprovalCreate(BaseModel):
    """登记理财收益申请"""
    investment_id: int = Field(..., description="理财产品ID")
    amount: float = Field(..., description="收益金额")
    income_date: datetime = Field(..., description="收益日期")
    note: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 成员加入申请 ============

class MemberJoinApprovalCreate(BaseModel):
    """创建成员加入申请"""
    invite_code: str = Field(..., description="邀请码")


# ============ 成员剔除申请 ============

class MemberRemoveApprovalCreate(BaseModel):
    """创建成员剔除申请"""
    user_id: int = Field(..., description="要剔除的成员ID")
    reason: Optional[str] = Field(None, max_length=500, description="剔除原因")


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
