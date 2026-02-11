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
    phone: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    created_at: datetime
    family_id: Optional[int] = None  # 用户所属家庭ID
    role: Optional[str] = None  # 家庭角色（admin/member）
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """用户个人信息更新"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    gender: Optional[str] = Field(None, description="性别: male/female/other")
    birthday: Optional[str] = Field(None, description="生日: YYYY-MM-DD")
    bio: Optional[str] = Field(None, max_length=200, description="个人简介")


class PasswordChange(BaseModel):
    """密码修改请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class Token(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """令牌数据"""
    user_id: Optional[int] = None
