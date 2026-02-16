"""
设计院 (Studio) - 认证 API

提供:
  1. 管理员登录 (用户名+密码)
  2. 主项目 token 验证 → 签发 Studio token
  3. 当前用户信息查询
  4. 检查是否需要认证 (初始配置检查)
"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from studio.backend.core.config import settings
from studio.backend.core.security import (
    verify_admin,
    verify_main_project_token,
    create_studio_token,
    get_studio_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio-api/auth", tags=["Auth"])


# ==================== Schemas ====================

class AdminLoginRequest(BaseModel):
    username: str = Field(..., max_length=100)
    password: str = Field(..., max_length=200)


class MainTokenRequest(BaseModel):
    token: str = Field(..., description="主项目 JWT token")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    nickname: str
    source: str


class UserInfoResponse(BaseModel):
    username: str
    nickname: str
    source: str
    main_user_id: int | None = None


# ==================== 认证状态检查 ====================

@router.get("/check")
async def auth_check():
    """
    检查认证配置状态

    前端用来决定:
      - 是否需要登录
      - 是否显示 "使用主项目账户登录" 选项
    """
    return {
        "admin_configured": bool(settings.studio_admin_pass),
        "main_project_available": bool(settings.main_api_url),
        "admin_username": settings.studio_admin_user,
    }


# ==================== 管理员登录 ====================

@router.post("/login", response_model=TokenResponse)
async def admin_login(data: AdminLoginRequest):
    """管理员账户密码登录"""
    if not verify_admin(data.username, data.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_studio_token(
        username=data.username,
        nickname="管理员",
        source="admin",
    )
    logger.info(f"✅ 管理员登录: {data.username}")
    return TokenResponse(
        access_token=token,
        username=data.username,
        nickname="管理员",
        source="admin",
    )


# ==================== 主项目 Token 认证 ====================

@router.post("/verify-main-token", response_model=TokenResponse)
async def verify_main_token(data: MainTokenRequest):
    """
    验证主项目 token 并签发 Studio token

    前端从 localStorage 获取主项目 token, 发送到此接口验证
    """
    user_info = await verify_main_project_token(data.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="主项目 token 无效或已过期")

    token = create_studio_token(
        username=user_info["username"],
        nickname=user_info["nickname"],
        source="main_project",
        user_id=user_info["id"],
    )
    logger.info(f"✅ 主项目用户登录设计院: {user_info['username']}")
    return TokenResponse(
        access_token=token,
        username=user_info["username"],
        nickname=user_info["nickname"],
        source="main_project",
    )


# ==================== 当前用户信息 ====================

@router.get("/me", response_model=UserInfoResponse)
async def get_me(user: dict = Depends(get_studio_user)):
    """获取当前登录用户信息"""
    return UserInfoResponse(**user)
