"""
小金库 (Golden Nest) - 家庭赌注相关 Schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ==================== Bet Option Schemas ====================

class BetOptionBase(BaseModel):
    """赌注选项基础"""
    option_text: str = Field(..., max_length=200, description="选项文本")


class BetOptionCreate(BetOptionBase):
    """创建赌注选项"""
    pass


class BetOptionResponse(BetOptionBase):
    """赌注选项响应"""
    id: int
    bet_id: int
    is_winning_option: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Bet Participant Schemas ====================

class BetParticipantBase(BaseModel):
    """赌注参与者基础"""
    user_id: int = Field(..., description="参与者用户ID")
    stake_amount: float = Field(0.0, ge=0, description="股份押注金额")
    stake_description: Optional[str] = Field(None, max_length=500, description="其他押注内容")


class BetParticipantCreate(BetParticipantBase):
    """创建赌注参与者"""
    pass


class BetParticipantResponse(BetParticipantBase):
    """赌注参与者响应"""
    id: int
    bet_id: int
    selected_option_id: Optional[int] = None
    is_winner: Optional[bool] = None
    has_approved: bool = False
    created_at: datetime

    # 额外字段
    user_nickname: Optional[str] = None
    selected_option_text: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Bet Schemas ====================

class BetBase(BaseModel):
    """赌注基础"""
    title: str = Field(..., max_length=200, description="赌注标题")
    description: str = Field(..., description="赌注描述")


class BetCreate(BetBase):
    """创建赌注请求"""
    deadline_hours: float = Field(..., gt=0, description="下注截止倒计时（小时）")
    options: List[BetOptionCreate] = Field(..., min_length=2, description="赌注选项（至少2个）")
    participants: List[BetParticipantCreate] = Field(..., min_length=2, description="参与者（至少2人）")


class BetUpdate(BaseModel):
    """更新赌注请求"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


class BetResponse(BetBase):
    """赌注响应"""
    id: int
    family_id: int
    creator_id: int
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    settlement_date: Optional[datetime] = None
    declared_winning_option_id: Optional[int] = None
    approval_request_id: Optional[int] = None
    created_at: datetime

    # 关联数据
    options: List[BetOptionResponse] = []
    participants: List[BetParticipantResponse] = []

    # 额外字段
    creator_nickname: Optional[str] = None
    is_expired: bool = False
    can_settle: bool = False
    voted_count: int = 0

    class Config:
        from_attributes = True


class BetListResponse(BaseModel):
    """赌注列表响应"""
    total: int
    page: int
    page_size: int
    items: List[BetResponse]


# ==================== Bet Action Schemas ====================

class BetVoteRequest(BaseModel):
    """投票请求"""
    option_id: int = Field(..., description="选择的选项ID")


class BetSettleRequest(BaseModel):
    """结算请求"""
    winning_option_id: int = Field(..., description="获胜选项ID")


class BetApproveRequest(BaseModel):
    """审批请求"""
    approved: bool = Field(..., description="是否同意")
    note: Optional[str] = Field(None, max_length=500, description="审批备注")
