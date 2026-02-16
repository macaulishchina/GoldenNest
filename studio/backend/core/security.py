"""
设计院 (Studio) - 认证安全模块

认证策略:
  1. 管理员账户: 用户名+密码登录, 由环境变量配置
  2. 主项目 session 复用: 检测 localStorage 中的主项目 JWT,
     通过主项目 API 验证后签发 Studio token
  3. Studio 签发独立 JWT, 包含 source 和 user_info
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from jose import jwt, JWTError
from fastapi import Request, HTTPException, status

from studio.backend.core.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


# ==================== Token 操作 ====================

def create_studio_token(
    username: str,
    nickname: str = "",
    source: str = "admin",
    user_id: Optional[int] = None,
) -> str:
    """
    创建 Studio JWT

    Args:
        username: 用户名 (admin 或主项目用户名)
        nickname: 显示昵称
        source: 'admin' 或 'main_project'
        user_id: 主项目用户ID (仅 source=main_project 时)
    """
    expire = datetime.utcnow() + timedelta(days=settings.studio_token_expire_days)
    payload = {
        "sub": username,
        "nickname": nickname or username,
        "source": source,
        "exp": expire,
    }
    if user_id is not None:
        payload["main_user_id"] = user_id
    return jwt.encode(payload, settings.studio_secret_key, algorithm=ALGORITHM)


def decode_studio_token(token: str) -> Optional[dict]:
    """解码 Studio JWT, 返回 payload 或 None"""
    try:
        return jwt.decode(token, settings.studio_secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ==================== 管理员登录 ====================

def verify_admin(username: str, password: str) -> bool:
    """验证管理员凭据"""
    return (
        username == settings.studio_admin_user
        and password == settings.studio_admin_pass
    )


# ==================== 主项目 Token 验证 ====================

async def verify_main_project_token(token: str) -> Optional[dict]:
    """
    通过主项目 API 验证 token, 返回用户信息

    Returns:
        {"id": 1, "username": "xxx", "nickname": "xxx"} 或 None
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.main_api_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": data.get("id"),
                    "username": data.get("username", ""),
                    "nickname": data.get("nickname", data.get("username", "")),
                }
    except Exception as e:
        logger.warning(f"主项目 token 验证失败: {e}")
    return None


# ==================== 请求认证依赖 ====================

def get_studio_user(request: Request) -> dict:
    """
    FastAPI 依赖: 从请求中获取当前用户

    检查顺序:
      1. Authorization: Bearer <studio_token>
      2. 返回 401

    Returns:
        {"username": "...", "nickname": "...", "source": "admin"|"main_project"}
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]
    payload = decode_studio_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "username": payload.get("sub", "unknown"),
        "nickname": payload.get("nickname", payload.get("sub", "unknown")),
        "source": payload.get("source", "admin"),
        "main_user_id": payload.get("main_user_id"),
    }


def get_optional_studio_user(request: Request) -> Optional[dict]:
    """
    FastAPI 依赖: 获取当前用户 (可选, 不强制)
    """
    try:
        return get_studio_user(request)
    except HTTPException:
        return None
