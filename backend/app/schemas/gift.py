"""
股权赠与 Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class GiftCreate(BaseModel):
    """创建股权赠与请求"""
    to_user_id: int = Field(..., description="接收者用户ID")
    amount: float = Field(..., gt=0, le=1, description="赠与股权比例(0-1)")
    gift_money: Optional[float] = Field(None, gt=0, description="赠与绝对金额(元)，用于精确转账避免比例精度丢失")
    message: Optional[str] = Field(None, max_length=500, description="祝福语")


class GiftResponse(BaseModel):
    """股权赠与响应"""
    id: int
    family_id: int
    from_user_id: int
    from_user_nickname: str
    from_avatar_version: int = 0  # 发送者头像版本号
    to_user_id: int
    to_user_nickname: str
    to_avatar_version: int = 0  # 接收者头像版本号
    amount: float
    gift_money: Optional[float] = None
    message: Optional[str]
    status: str
    created_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True


class GiftAcceptReject(BaseModel):
    """接受/拒绝赠与请求"""
    accept: bool = Field(..., description="是否接受")


class GiftListResponse(BaseModel):
    """赠与列表响应"""
    sent: List[GiftResponse] = Field(default_factory=list, description="我发送的赠与")
    received: List[GiftResponse] = Field(default_factory=list, description="我收到的赠与")
    pending_count: int = Field(0, description="待处理的赠与数量")


class GiftStats(BaseModel):
    """赠与统计"""
    total_sent: int = Field(0, description="发送总次数")
    total_received: int = Field(0, description="接收总次数")
    total_sent_amount: float = Field(0, description="发送股权总比例")
    total_received_amount: float = Field(0, description="接收股权总比例")
