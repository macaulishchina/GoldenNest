"""
小金库 (Golden Nest) - 认证相关 Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    nickname: str
    avatar: Optional[str] = None
    avatar_version: int = 0  # 头像版本号，用于缓存失效
    is_active: bool
    created_at: datetime
    family_id: Optional[int] = None  # 用户所属家庭ID
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """令牌数据"""
    user_id: Optional[int] = None
