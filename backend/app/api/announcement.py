"""
家庭公告板 API - 家庭内部公告和互动功能
"""
from datetime import datetime
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import (
    User, FamilyMember, Announcement, AnnouncementLike, AnnouncementComment
)

router = APIRouter(prefix="/announcements", tags=["announcements"])


# ==================== Schema ====================

class AnnouncementCreate(BaseModel):
    content: str
    images: Optional[List[str]] = None  # 图片URL列表
    is_pinned: bool = False

class AnnouncementUpdate(BaseModel):
    content: Optional[str] = None
    images: Optional[List[str]] = None
    is_pinned: Optional[bool] = None

class CommentCreate(BaseModel):
    content: str

class AnnouncementResponse(BaseModel):
    id: int
    content: str
    images: List[str]
    is_pinned: bool
    created_at: str
    author_id: int
    author_name: str
    author_avatar_version: int = 0
    likes_count: int
    comments_count: int
    is_liked: bool
    comments: List[dict]


# ==================== Helper ====================

async def get_user_family_id(user_id: int, db: AsyncSession) -> int:
    """获取用户所属家庭ID"""
    result = await db.execute(
        select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
    )
    family_id = result.scalar_one_or_none()
    if not family_id:
        raise HTTPException(status_code=400, detail="您还没有加入家庭")
    return family_id


async def build_announcement_response(
    db: AsyncSession, 
    announcement: Announcement, 
    current_user_id: int,
    include_comments: bool = True
) -> dict:
    """构建公告响应"""
    # 获取作者信息
    result = await db.execute(select(User).where(User.id == announcement.user_id))
    author = result.scalar_one_or_none()
    
    # 获取点赞数
    result = await db.execute(
        select(func.count(AnnouncementLike.id)).where(
            AnnouncementLike.announcement_id == announcement.id
        )
    )
    likes_count = result.scalar() or 0
    
    # 检查当前用户是否点赞
    result = await db.execute(
        select(AnnouncementLike).where(
            AnnouncementLike.announcement_id == announcement.id,
            AnnouncementLike.user_id == current_user_id
        )
    )
    is_liked = result.scalar_one_or_none() is not None
    
    # 获取评论
    comments = []
    comments_count = 0
    if include_comments:
        result = await db.execute(
            select(AnnouncementComment, User)
            .join(User, AnnouncementComment.user_id == User.id)
            .where(AnnouncementComment.announcement_id == announcement.id)
            .order_by(AnnouncementComment.created_at.asc())
        )
        comment_rows = result.fetchall()
        comments_count = len(comment_rows)
        
        for comment, user in comment_rows:
            comments.append({
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "author_id": user.id,
                "author_name": user.nickname
            })
    else:
        result = await db.execute(
            select(func.count(AnnouncementComment.id)).where(
                AnnouncementComment.announcement_id == announcement.id
            )
        )
        comments_count = result.scalar() or 0
    
    # 解析图片
    images = []
    if announcement.images:
        try:
            images = json.loads(announcement.images)
        except:
            images = []
    
    return {
        "id": announcement.id,
        "content": announcement.content,
        "images": images,
        "is_pinned": announcement.is_pinned,
        "created_at": announcement.created_at.isoformat(),
        "author_id": author.id if author else 0,
        "author_name": author.nickname if author else "未知用户",
        "author_avatar_version": author.avatar_version if author else 0,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "is_liked": is_liked,
        "comments": comments
    }


# ==================== API ====================

@router.post("", response_model=dict)
async def create_announcement(
    data: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发布公告"""
    family_id = await get_user_family_id(current_user.id, db)
    
    if not data.content or len(data.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="公告内容不能为空")
    
    if len(data.content) > 2000:
        raise HTTPException(status_code=400, detail="公告内容不能超过2000字")
    
    images_json = json.dumps(data.images, ensure_ascii=False) if data.images else None
    
    announcement = Announcement(
        family_id=family_id,
        user_id=current_user.id,
        content=data.content.strip(),
        images=images_json,
        is_pinned=data.is_pinned
    )
    
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    
    return {
        "success": True,
        "message": "公告发布成功",
        "announcement": await build_announcement_response(db, announcement, current_user.id)
    }


@router.get("", response_model=dict)
async def list_announcements(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取公告列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取总数
    result = await db.execute(
        select(func.count(Announcement.id)).where(Announcement.family_id == family_id)
    )
    total = result.scalar() or 0
    
    # 获取公告列表（置顶优先，然后按时间倒序）
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Announcement)
        .where(Announcement.family_id == family_id)
        .order_by(desc(Announcement.is_pinned), desc(Announcement.created_at))
        .offset(offset)
        .limit(page_size)
    )
    announcements = result.scalars().all()
    
    items = []
    for a in announcements:
        items.append(await build_announcement_response(db, a, current_user.id, include_comments=False))
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.get("/{announcement_id}", response_model=dict)
async def get_announcement_detail(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取公告详情"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.family_id == family_id
        )
    )
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    
    return await build_announcement_response(db, announcement, current_user.id)


@router.put("/{announcement_id}", response_model=dict)
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新公告（仅作者可操作）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.family_id == family_id
        )
    )
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    
    if announcement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己发布的公告")
    
    if data.content is not None:
        announcement.content = data.content.strip()
    if data.images is not None:
        announcement.images = json.dumps(data.images, ensure_ascii=False)
    if data.is_pinned is not None:
        announcement.is_pinned = data.is_pinned
    
    await db.commit()
    
    return {
        "success": True,
        "message": "公告更新成功",
        "announcement": await build_announcement_response(db, announcement, current_user.id)
    }


@router.delete("/{announcement_id}", response_model=dict)
async def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除公告（仅作者可操作）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.family_id == family_id
        )
    )
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    
    if announcement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己发布的公告")
    
    await db.delete(announcement)
    await db.commit()
    
    return {
        "success": True,
        "message": "公告已删除"
    }


@router.post("/{announcement_id}/like", response_model=dict)
async def toggle_like(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """点赞/取消点赞"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.family_id == family_id
        )
    )
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    
    # 检查是否已点赞
    result = await db.execute(
        select(AnnouncementLike).where(
            AnnouncementLike.announcement_id == announcement_id,
            AnnouncementLike.user_id == current_user.id
        )
    )
    existing_like = result.scalar_one_or_none()
    
    if existing_like:
        # 取消点赞
        await db.delete(existing_like)
        await db.commit()
        return {
            "success": True,
            "action": "unliked",
            "message": "已取消点赞"
        }
    else:
        # 点赞
        like = AnnouncementLike(
            announcement_id=announcement_id,
            user_id=current_user.id
        )
        db.add(like)
        await db.commit()
        return {
            "success": True,
            "action": "liked",
            "message": "点赞成功"
        }


@router.get("/{announcement_id}/comments", response_model=list)
async def get_comments(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取评论列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证公告存在且属于该家庭
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.family_id == family_id
        )
    )
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    
    # 获取评论
    result = await db.execute(
        select(AnnouncementComment, User)
        .join(User, AnnouncementComment.user_id == User.id)
        .where(AnnouncementComment.announcement_id == announcement_id)
        .order_by(AnnouncementComment.created_at.asc())
    )
    comment_rows = result.fetchall()
    
    comments = []
    for comment, user in comment_rows:
        comments.append({
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "author_id": user.id,
            "author_name": user.nickname
        })
    
    return comments


@router.post("/{announcement_id}/comments", response_model=dict)
async def add_comment(
    announcement_id: int,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加评论"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.family_id == family_id
        )
    )
    announcement = result.scalar_one_or_none()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    
    if not data.content or len(data.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    
    if len(data.content) > 500:
        raise HTTPException(status_code=400, detail="评论内容不能超过500字")
    
    comment = AnnouncementComment(
        announcement_id=announcement_id,
        user_id=current_user.id,
        content=data.content.strip()
    )
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    return {
        "success": True,
        "message": "评论成功",
        "comment": {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "author_id": current_user.id,
            "author_name": current_user.nickname
        }
    }


@router.delete("/{announcement_id}/comment/{comment_id}", response_model=dict)
async def delete_comment(
    announcement_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除评论（仅评论作者可操作）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(AnnouncementComment).where(
            AnnouncementComment.id == comment_id,
            AnnouncementComment.announcement_id == announcement_id
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的评论")
    
    await db.delete(comment)
    await db.commit()
    
    return {
        "success": True,
        "message": "评论已删除"
    }


@router.get("/stats/summary", response_model=dict)
async def get_announcement_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取公告统计（用于成就系统）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 用户发布的公告数
    result = await db.execute(
        select(func.count(Announcement.id)).where(
            Announcement.user_id == current_user.id,
            Announcement.family_id == family_id
        )
    )
    total_announcements = result.scalar() or 0
    
    # 用户的评论数
    result = await db.execute(
        select(func.count(AnnouncementComment.id))
        .join(Announcement, AnnouncementComment.announcement_id == Announcement.id)
        .where(
            AnnouncementComment.user_id == current_user.id,
            Announcement.family_id == family_id
        )
    )
    total_comments = result.scalar() or 0
    
    # 用户收到的点赞数
    result = await db.execute(
        select(func.count(AnnouncementLike.id))
        .join(Announcement, AnnouncementLike.announcement_id == Announcement.id)
        .where(
            Announcement.user_id == current_user.id,
            Announcement.family_id == family_id
        )
    )
    total_likes_received = result.scalar() or 0
    
    return {
        "total_announcements": total_announcements,
        "total_comments": total_comments,
        "total_likes_received": total_likes_received
    }
