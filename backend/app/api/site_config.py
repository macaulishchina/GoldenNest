"""
小金库 (Golden Nest) - 站点配置管理路由
支持上传站点图标（favicon + PWA icon）、设置站点名称
"""
import os
import logging
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.config import BASE_DIR
from app.core.database import get_db
from app.models.models import User, FamilyMember
from app.api.auth import get_current_user
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()

# 站点配置存储目录
SITE_CONFIG_DIR = os.path.join(BASE_DIR, "uploads", "site")
SITE_CONFIG_FILE = os.path.join(SITE_CONFIG_DIR, "config.json")
ALLOWED_ICON_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/x-icon", "image/vnd.microsoft.icon"}
MAX_ICON_SIZE = 2 * 1024 * 1024  # 2MB


def _ensure_dir():
    os.makedirs(SITE_CONFIG_DIR, exist_ok=True)


def _load_config() -> dict:
    """加载站点配置"""
    _ensure_dir()
    if os.path.exists(SITE_CONFIG_FILE):
        try:
            with open(SITE_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(cfg: dict):
    """保存站点配置"""
    _ensure_dir()
    with open(SITE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


async def _require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")
    return current_user


# ==================== 公开接口（无需登录） ====================

@router.get("/icon/{size}")
async def get_site_icon(size: str):
    """获取站点图标（公开接口，用于 favicon / PWA icon）
    size: 'original', '192', '512', 'favicon'
    """
    cfg = _load_config()
    icon_file = cfg.get("icon_file")
    if not icon_file:
        raise HTTPException(status_code=404, detail="未设置站点图标")

    # 检查是否有对应尺寸的文件
    if size in ("192", "512"):
        sized_file = os.path.join(SITE_CONFIG_DIR, f"icon-{size}.png")
        if os.path.exists(sized_file):
            return FileResponse(sized_file, media_type="image/png",
                                headers={"Cache-Control": "public, max-age=86400"})

    # 回退到原始文件
    original = os.path.join(SITE_CONFIG_DIR, icon_file)
    if not os.path.exists(original):
        raise HTTPException(status_code=404, detail="图标文件不存在")

    content_type = cfg.get("icon_content_type", "image/png")
    return FileResponse(original, media_type=content_type,
                        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/manifest.json")
async def get_manifest():
    """动态生成 PWA manifest.json（公开接口）"""
    cfg = _load_config()
    site_name = cfg.get("site_name", "小金库 Golden Nest")
    short_name = cfg.get("short_name", "小金库")
    theme_color = cfg.get("theme_color", "#f0c040")
    bg_color = cfg.get("bg_color", "#ffffff")

    manifest = {
        "name": site_name,
        "short_name": short_name,
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "theme_color": theme_color,
        "background_color": bg_color,
        "icons": [],
    }

    # 如果有图标，添加 icon 条目
    if cfg.get("icon_file"):
        manifest["icons"] = [
            {
                "src": "/api/site-config/icon/192",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": "/api/site-config/icon/512",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ]

    return JSONResponse(content=manifest, headers={
        "Cache-Control": "public, max-age=3600",
        "Content-Type": "application/manifest+json",
    })


@router.get("/info")
async def get_site_info():
    """获取站点基本信息（公开接口）"""
    cfg = _load_config()
    return {
        "site_name": cfg.get("site_name", "小金库 Golden Nest"),
        "short_name": cfg.get("short_name", "小金库"),
        "theme_color": cfg.get("theme_color", "#f0c040"),
        "has_icon": bool(cfg.get("icon_file")),
        "icon_url": "/api/site-config/icon/original" if cfg.get("icon_file") else None,
    }


# ==================== 管理接口（需要管理员权限） ====================

@router.post("/icon")
async def upload_site_icon(
    file: UploadFile = File(...),
    _: User = Depends(_require_admin),
):
    """上传站点图标（管理员接口）"""
    if file.content_type not in ALLOWED_ICON_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式，支持: PNG, JPG, SVG, WebP, ICO")

    content = await file.read()
    if len(content) > MAX_ICON_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过2MB")

    _ensure_dir()

    # 确定文件扩展名
    ext_map = {
        "image/png": ".png", "image/jpeg": ".jpg", "image/svg+xml": ".svg",
        "image/webp": ".webp", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico",
    }
    ext = ext_map.get(file.content_type, ".png")
    filename = f"icon-original{ext}"

    # 保存原始文件
    filepath = os.path.join(SITE_CONFIG_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # 尝试用 Pillow 生成 192x192 和 512x512 的 PNG 版本
    _generate_sized_icons(content, file.content_type)

    # 更新配置
    cfg = _load_config()
    cfg["icon_file"] = filename
    cfg["icon_content_type"] = file.content_type
    cfg["icon_updated_at"] = datetime.utcnow().isoformat()
    _save_config(cfg)

    logger.info(f"站点图标已更新: {filename}")
    return {"message": "图标上传成功", "filename": filename}


class SiteConfigUpdate(BaseModel):
    site_name: Optional[str] = None
    short_name: Optional[str] = None
    theme_color: Optional[str] = None
    bg_color: Optional[str] = None


@router.put("/settings")
async def update_site_settings(
    data: SiteConfigUpdate,
    _: User = Depends(_require_admin),
):
    """更新站点设置（管理员接口）"""
    cfg = _load_config()
    if data.site_name is not None:
        cfg["site_name"] = data.site_name.strip()
    if data.short_name is not None:
        cfg["short_name"] = data.short_name.strip()
    if data.theme_color is not None:
        cfg["theme_color"] = data.theme_color.strip()
    if data.bg_color is not None:
        cfg["bg_color"] = data.bg_color.strip()
    _save_config(cfg)
    return {"message": "设置已更新"}


@router.get("/settings")
async def get_site_settings(
    _: User = Depends(_require_admin),
):
    """获取完整站点设置（管理员接口）"""
    cfg = _load_config()
    return {
        "site_name": cfg.get("site_name", "小金库 Golden Nest"),
        "short_name": cfg.get("short_name", "小金库"),
        "theme_color": cfg.get("theme_color", "#f0c040"),
        "bg_color": cfg.get("bg_color", "#ffffff"),
        "has_icon": bool(cfg.get("icon_file")),
        "icon_url": "/api/site-config/icon/original" if cfg.get("icon_file") else None,
        "icon_updated_at": cfg.get("icon_updated_at"),
    }


@router.delete("/icon")
async def delete_site_icon(
    _: User = Depends(_require_admin),
):
    """删除站点图标（管理员接口）"""
    cfg = _load_config()
    # 删除所有图标文件
    for fname in ["icon-original.png", "icon-original.jpg", "icon-original.svg",
                   "icon-original.webp", "icon-original.ico",
                   "icon-192.png", "icon-512.png"]:
        fpath = os.path.join(SITE_CONFIG_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
    cfg.pop("icon_file", None)
    cfg.pop("icon_content_type", None)
    cfg.pop("icon_updated_at", None)
    _save_config(cfg)
    return {"message": "图标已删除"}


# ==================== 工具函数 ====================

def _generate_sized_icons(content: bytes, content_type: str):
    """尝试用 Pillow 生成不同尺寸的 PNG 图标"""
    try:
        from PIL import Image
        import io

        if content_type == "image/svg+xml":
            # SVG 无法直接用 Pillow 处理，跳过
            return

        img = Image.open(io.BytesIO(content))
        # 转换为 RGBA（支持透明度）
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        for size in (192, 512):
            resized = img.copy()
            resized.thumbnail((size, size), Image.LANCZOS)
            # 创建正方形画布（居中）
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            offset = ((size - resized.width) // 2, (size - resized.height) // 2)
            canvas.paste(resized, offset, resized)
            out_path = os.path.join(SITE_CONFIG_DIR, f"icon-{size}.png")
            canvas.save(out_path, "PNG")
            logger.info(f"生成 {size}x{size} 图标: {out_path}")

    except ImportError:
        logger.warning("Pillow 未安装，跳过图标尺寸生成。将直接使用原始图标。")
    except Exception as e:
        logger.warning(f"图标尺寸生成失败: {e}")
