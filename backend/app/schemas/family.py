"""
小金库 (Golden Nest) - 家庭相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FamilyCreate(BaseModel):
    """创建家庭请求"""
    name: str = Field(..., min_length=1, max_length=100, description="家庭名称")
    savings_target: float = Field(default=2000000.0, ge=0, description="储蓄目标")
    time_value_rate: float = Field(default=0.03, ge=0, le=1, description="时间价值系数（用于计算加权股权）")


class FamilyUpdate(BaseModel):
    """更新家庭请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    savings_target: Optional[float] = Field(None, ge=0)
    time_value_rate: Optional[float] = Field(None, ge=0, le=1)


class FamilyMemberResponse(BaseModel):
    """家庭成员响应"""
    id: int
    user_id: int
    username: str
    nickname: str
    avatar_version: int = 0  # 头像版本号，用于缓存失效
    role: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


class FamilyResponse(BaseModel):
    """家庭信息响应"""
    id: int
    name: str
    savings_target: float
    time_value_rate: float
    invite_code: str
    created_at: datetime
    members: List[FamilyMemberResponse] = []
    
    class Config:
        from_attributes = True


class JoinFamilyRequest(BaseModel):
    """加入家庭请求"""
    invite_code: str = Field(..., description="邀请码")
