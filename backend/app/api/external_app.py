"""
第三方外部应用管理 API — 全局配置，管理员管理，所有用户可查看使用
"""
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from app.core.config import BASE_DIR
from app.core.database import get_db
from app.models.models import User, FamilyMember, ExternalApp
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# 应用图标存储目录
APP_ICON_DIR = os.path.join(BASE_DIR, "uploads", "site", "app-icons")
ALLOWED_ICON_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/x-icon"}
MAX_ICON_SIZE = 2 * 1024 * 1024  # 2MB


def _ensure_icon_dir():
    os.makedirs(APP_ICON_DIR, exist_ok=True)


# ==================== Schemas ====================

class ExternalAppCreate(BaseModel):
    name: str
    url: str
    icon_type: str = "emoji"          # emoji | image
    icon_emoji: Optional[str] = None
    description: Optional[str] = None
    open_mode: str = "new_tab"        # new_tab | fullscreen
    sort_order: int = 0
    is_active: bool = True


class ExternalAppUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    icon_type: Optional[str] = None
    icon_emoji: Optional[str] = None
    description: Optional[str] = None
    open_mode: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderRequest(BaseModel):
    items: List[ReorderItem]


# ==================== Helpers ====================

async def _require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """要求管理员权限"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="请先加入或创建家庭")
    if membership.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")
    return current_user


def _app_to_dict(app: ExternalApp) -> dict:
    """将 ExternalApp 模型转为 dict"""
    return {
        "id": app.id,
        "name": app.name,
        "url": app.url,
        "icon_type": app.icon_type,
        "icon_emoji": app.icon_emoji,
        "icon_image": app.icon_image,
        "description": app.description,
        "open_mode": app.open_mode,
        "sort_order": app.sort_order,
        "is_active": app.is_active,
        "created_by": app.created_by,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


# ==================== 公开接口（登录用户） ====================

@router.get("/")
async def list_active_apps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有激活的应用列表（所有登录用户可访问），按 sort_order 排序"""
    result = await db.execute(
        select(ExternalApp)
        .where(ExternalApp.is_active == True)
        .order_by(ExternalApp.sort_order, ExternalApp.id)
    )
    apps = result.scalars().all()
    return [_app_to_dict(a) for a in apps]


# ==================== 管理接口（仅管理员） ====================

@router.get("/all")
async def list_all_apps(
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取所有应用（含未激活），仅管理员"""
    result = await db.execute(
        select(ExternalApp).order_by(ExternalApp.sort_order, ExternalApp.id)
    )
    apps = result.scalars().all()
    return [_app_to_dict(a) for a in apps]


@router.post("/")
async def create_app(
    data: ExternalAppCreate,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建外部应用"""
    app = ExternalApp(
        name=data.name,
        url=data.url,
        icon_type=data.icon_type,
        icon_emoji=data.icon_emoji,
        description=data.description,
        open_mode=data.open_mode,
        sort_order=data.sort_order,
        is_active=data.is_active,
        created_by=admin.id,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    logger.info(f"管理员 {admin.username} 创建外部应用: {app.name}")
    return _app_to_dict(app)


@router.put("/{app_id}")
async def update_app(
    app_id: int,
    data: ExternalAppUpdate,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新外部应用"""
    result = await db.execute(select(ExternalApp).where(ExternalApp.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(app, field, value)
    app.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(app)
    logger.info(f"管理员 {admin.username} 更新外部应用: {app.name}")
    return _app_to_dict(app)


@router.delete("/{app_id}")
async def delete_app(
    app_id: int,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除外部应用"""
    result = await db.execute(select(ExternalApp).where(ExternalApp.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    # 如果有图标图片，删除文件
    if app.icon_image:
        icon_path = os.path.join(BASE_DIR, app.icon_image.lstrip("/"))
        if os.path.exists(icon_path):
            try:
                os.remove(icon_path)
            except OSError:
                pass

    await db.delete(app)
    logger.info(f"管理员 {admin.username} 删除外部应用: {app.name}")
    return {"detail": "应用已删除"}


@router.post("/{app_id}/icon")
async def upload_app_icon(
    app_id: int,
    file: UploadFile = File(...),
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传应用图标图片"""
    result = await db.execute(select(ExternalApp).where(ExternalApp.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    # 验证文件类型
    if file.content_type not in ALLOWED_ICON_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式，允许: {', '.join(ALLOWED_ICON_TYPES)}")

    # 读取并验证大小
    content = await file.read()
    if len(content) > MAX_ICON_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 2MB")

    _ensure_icon_dir()

    # 删除旧图标
    if app.icon_image:
        old_path = os.path.join(BASE_DIR, app.icon_image.lstrip("/"))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    # 保存新图标
    ext = os.path.splitext(file.filename or "icon.png")[1] or ".png"
    filename = f"app-{app.id}-{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(APP_ICON_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # 更新应用记录
    app.icon_type = "image"
    app.icon_image = f"/uploads/site/app-icons/{filename}"
    app.updated_at = datetime.utcnow()
    await db.flush()

    logger.info(f"管理员 {admin.username} 上传应用图标: {app.name}")
    return {
        "icon_image": app.icon_image,
        "detail": "图标上传成功"
    }


@router.put("/reorder")
async def reorder_apps(
    data: ReorderRequest,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量更新应用排序"""
    for item in data.items:
        await db.execute(
            update(ExternalApp)
            .where(ExternalApp.id == item.id)
            .values(sort_order=item.sort_order, updated_at=datetime.utcnow())
        )
    logger.info(f"管理员 {admin.username} 更新了应用排序")
    return {"detail": "排序已更新"}
