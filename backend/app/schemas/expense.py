"""
小金库 (Golden Nest) - 支出申请相关 Schemas
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.models.models import ExpenseStatus


class ExpenseDeductionRatio(BaseModel):
    """股权扣减比例"""
    user_id: int
    ratio: float = Field(..., ge=0, le=1, description="扣减比例 (0-1)")


class ExpenseRequestCreate(BaseModel):
    """创建支出申请请求"""
    title: str = Field(..., min_length=1, max_length=200, description="支出标题")
    amount: float = Field(..., gt=0, description="支出金额")
    reason: str = Field(..., min_length=1, description="支出原因")
    deduction_ratios: List[ExpenseDeductionRatio] = Field(..., description="各成员股权扣减比例")


class ExpenseApprovalCreate(BaseModel):
    """审批支出申请请求"""
    is_approved: bool = Field(..., description="是否通过")
    comment: Optional[str] = Field(None, max_length=500, description="审批意见")


class ExpenseApprovalResponse(BaseModel):
    """审批记录响应"""
    id: int
    expense_request_id: int
    approver_id: int
    approver_nickname: str
    is_approved: bool
    comment: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExpenseRequestResponse(BaseModel):
    """支出申请响应"""
    id: int
    family_id: int
    requester_id: int
    requester_nickname: str
    title: str
    amount: float
    reason: str
    equity_deduction_ratio: str  # JSON格式的扣减比例
    status: ExpenseStatus
    created_at: datetime
    updated_at: datetime
    
    # 额外字段
    approvals: List[ExpenseApprovalResponse] = []
    pending_approvers: List[int] = []  # 待审批的用户ID列表
    
    class Config:
        from_attributes = True
