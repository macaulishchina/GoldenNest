"""
成就系统 API 路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, Achievement, UserAchievement, FamilyMember
from app.schemas.achievement import (
    AchievementDefinition,
    AchievementDefinitionWithStatus,
    UserAchievementResponse,
    AchievementCheckResponse,
    AchievementProgress,
    CategoryProgress,
    RecentFamilyUnlock,
    NewUnlock,
)
from app.services.achievement import AchievementService, CATEGORY_NAMES

router = APIRouter(prefix="/api/achievement", tags=["成就系统"])


@router.get("/definitions", response_model=List[AchievementDefinitionWithStatus])
async def get_achievement_definitions(
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有成就定义（带用户解锁状态）
    
    - include_hidden: 是否包含隐藏成就（默认不包含）
    """
    service = AchievementService(db)
    
    # 初始化成就（首次使用）
    await service.init_achievements()
    
    # 获取所有成就定义
    achievements = await service.get_all_definitions(include_hidden=include_hidden)
    
    # 获取用户已解锁的成就ID
    user_achievements = await service.get_user_achievements(current_user.id)
    unlocked_map = {ua.achievement_id: ua.unlocked_at for ua in user_achievements}
    
    # 构建响应
    result = []
    for ach in achievements:
        is_unlocked = ach.id in unlocked_map
        result.append(AchievementDefinitionWithStatus(
            id=ach.id,
            code=ach.code,
            name=ach.name,
            description=ach.description,
            category=ach.category,
            icon=ach.icon,
            rarity=ach.rarity,
            points=ach.points,
            is_hidden=ach.is_hidden,
            is_unlocked=is_unlocked,
            unlocked_at=unlocked_map.get(ach.id)
        ))
    
    return result


@router.get("/my", response_model=List[UserAchievementResponse])
async def get_my_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我已解锁的成就列表"""
    service = AchievementService(db)
    user_achievements = await service.get_user_achievements(current_user.id)
    
    result = []
    for ua in user_achievements:
        # 加载成就详情
        ach_result = await db.execute(
            select(Achievement).where(Achievement.id == ua.achievement_id)
        )
        ach = ach_result.scalar_one_or_none()
        if ach:
            result.append(UserAchievementResponse(
                id=ua.id,
                achievement_id=ach.id,
                code=ach.code,
                name=ach.name,
                description=ach.description,
                category=ach.category,
                icon=ach.icon,
                rarity=ach.rarity,
                points=ach.points,
                unlocked_at=ua.unlocked_at
            ))
    
    return result


@router.get("/progress", response_model=AchievementProgress)
async def get_achievement_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成就进度统计"""
    service = AchievementService(db)
    
    # 初始化成就
    await service.init_achievements()
    
    progress = await service.get_progress(current_user.id)
    
    # 获取最近解锁的成就（前5个）
    user_achievements = await service.get_user_achievements(current_user.id)
    recent_unlocks = []
    for ua in user_achievements[:5]:
        ach_result = await db.execute(
            select(Achievement).where(Achievement.id == ua.achievement_id)
        )
        ach = ach_result.scalar_one_or_none()
        if ach:
            recent_unlocks.append(UserAchievementResponse(
                id=ua.id,
                achievement_id=ach.id,
                code=ach.code,
                name=ach.name,
                description=ach.description,
                category=ach.category,
                icon=ach.icon,
                rarity=ach.rarity,
                points=ach.points,
                unlocked_at=ua.unlocked_at
            ))
    
    return AchievementProgress(
        total_achievements=progress["total_achievements"],
        unlocked_achievements=progress["unlocked_achievements"],
        total_points=progress["total_points"],
        earned_points=progress["earned_points"],
        percentage=progress["percentage"],
        categories=[
            CategoryProgress(
                category=cat["category"],
                category_name=cat["category_name"],
                total=cat["total"],
                unlocked=cat["unlocked"],
                percentage=cat["percentage"]
            )
            for cat in progress["categories"]
        ],
        recent_unlocks=recent_unlocks
    )


@router.post("/check", response_model=AchievementCheckResponse)
async def check_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动触发成就检查
    
    返回新解锁的成就列表
    """
    service = AchievementService(db)
    
    # 初始化成就
    await service.init_achievements()
    
    # 检查并解锁成就
    new_unlocks = await service.check_and_unlock(current_user.id)
    
    # 构建响应
    unlocks_response = []
    for ua in new_unlocks:
        ach_result = await db.execute(
            select(Achievement).where(Achievement.id == ua.achievement_id)
        )
        ach = ach_result.scalar_one_or_none()
        if ach:
            unlocks_response.append(NewUnlock(
                achievement=AchievementDefinition(
                    id=ach.id,
                    code=ach.code,
                    name=ach.name,
                    description=ach.description,
                    category=ach.category,
                    icon=ach.icon,
                    rarity=ach.rarity,
                    points=ach.points,
                    is_hidden=ach.is_hidden
                ),
                unlocked_at=ua.unlocked_at
            ))
    
    # 获取总统计
    progress = await service.get_progress(current_user.id)
    
    return AchievementCheckResponse(
        new_unlocks=unlocks_response,
        total_unlocked=progress["unlocked_achievements"],
        total_points=progress["earned_points"]
    )


@router.get("/recent", response_model=List[RecentFamilyUnlock])
async def get_recent_family_unlocks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取家庭成员最近解锁的成就
    
    - limit: 返回数量限制（默认10）
    """
    # 获取用户所属家庭
    member_result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = member_result.scalar_one_or_none()
    
    if not membership:
        return []
    
    # 获取家庭所有成员的最近成就
    family_members_result = await db.execute(
        select(FamilyMember.user_id).where(FamilyMember.family_id == membership.family_id)
    )
    member_ids = [row[0] for row in family_members_result.fetchall()]
    
    # 查询这些成员的最近成就
    recent_result = await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id.in_(member_ids))
        .order_by(UserAchievement.unlocked_at.desc())
        .limit(limit)
    )
    recent_achievements = recent_result.scalars().all()
    
    # 构建响应
    result = []
    for ua in recent_achievements:
        # 获取用户信息
        user_result = await db.execute(
            select(User).where(User.id == ua.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        # 获取成就信息
        ach_result = await db.execute(
            select(Achievement).where(Achievement.id == ua.achievement_id)
        )
        ach = ach_result.scalar_one_or_none()
        
        if user and ach:
            result.append(RecentFamilyUnlock(
                user_id=user.id,
                username=user.username,
                nickname=user.nickname,
                achievement=AchievementDefinition(
                    id=ach.id,
                    code=ach.code,
                    name=ach.name,
                    description=ach.description,
                    category=ach.category,
                    icon=ach.icon,
                    rarity=ach.rarity,
                    points=ach.points,
                    is_hidden=ach.is_hidden
                ),
                unlocked_at=ua.unlocked_at
            ))
    
    return result
