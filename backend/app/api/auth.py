"""
小金库 (Golden Nest) - 认证路由
"""
import base64
import hashlib
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.limiter import limiter
from app.models.models import User, FamilyMember
from app.schemas.auth import UserCreate, UserResponse, Token, UserLogin

router = APIRouter()


class AvatarUpdate(BaseModel):
    """头像更新请求"""
    avatar: str  # Base64 编码的图片
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/register", response_model=UserResponse)
@limiter.limit("3/hour")  # 每小时最多3次注册尝试
async def register(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册（频率限制: 3次/小时）"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        nickname=user_data.nickname or user_data.username
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # 每分钟最多5次登录尝试
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """用户登录（频率限制: 5次/分钟）"""
    # 查找用户
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌 - sub 必须是字符串
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户信息"""
    # 查询用户的家庭成员关系
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar=current_user.avatar,
        avatar_version=current_user.avatar_version or 0,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        family_id=membership.family_id if membership else None
    )


@router.put("/avatar", response_model=dict)
async def update_avatar(
    data: AvatarUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户头像"""
    # 验证 base64 图片格式
    avatar = data.avatar.strip()
    
    # 检查是否是有效的 base64 图片
    if not avatar.startswith('data:image/'):
        raise HTTPException(status_code=400, detail="无效的图片格式，请上传 JPG/PNG/GIF 格式的图片")
    
    # 限制图片大小（base64 字符串长度约为原文件大小的 1.37 倍）
    # 限制为 2MB 原图 → 约 2.7M base64 字符串
    max_length = 3 * 1024 * 1024  # 3MB base64 字符串
    if len(avatar) > max_length:
        raise HTTPException(status_code=400, detail="图片过大，请上传小于 2MB 的图片")
    
    # 更新头像和版本号
    current_user.avatar = avatar
    current_user.avatar_version = (current_user.avatar_version or 0) + 1
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "success": True,
        "message": "头像更新成功",
        "avatar_version": current_user.avatar_version
    }


@router.get("/users/{user_id}/avatar")
async def get_user_avatar(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户头像图片
    
    - 返回图片二进制数据，支持浏览器缓存
    - 使用 ETag 和 Cache-Control 头优化缓存
    - 无头像时返回 404
    """
    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if not user.avatar:
        raise HTTPException(status_code=404, detail="用户未设置头像")
    
    try:
        # 解析 Base64 数据
        # 格式: data:image/jpeg;base64,/9j/4AAQ...
        avatar_data = user.avatar
        
        # 提取 MIME 类型和 Base64 数据
        if avatar_data.startswith('data:'):
            # 分离 header 和 data
            header, encoded = avatar_data.split(',', 1)
            # 提取 MIME 类型 (如 image/jpeg)
            mime_type = header.split(':')[1].split(';')[0]
        else:
            # 如果没有 data URI 前缀，假设是纯 Base64 JPEG
            encoded = avatar_data
            mime_type = 'image/jpeg'
        
        # 解码 Base64
        image_bytes = base64.b64decode(encoded)
        
        # 生成 ETag (基于内容的哈希)
        etag = hashlib.md5(image_bytes).hexdigest()
        
        # 检查客户端缓存 (If-None-Match)
        client_etag = request.headers.get('if-none-match')
        if client_etag and client_etag.strip('"') == etag:
            return Response(status_code=304)
        
        # 返回图片响应
        return Response(
            content=image_bytes,
            media_type=mime_type,
            headers={
                'Cache-Control': 'public, max-age=3600',  # 缓存1小时
                'ETag': f'"{etag}"',
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"头像解析失败: {str(e)}")
