"""
成就系统 Pydantic Schemas
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel
from enum import Enum


class AchievementCategory(str, Enum):
    """成就分类"""
    DEPOSIT = "deposit"
    STREAK = "streak"
    FAMILY = "family"
    EQUITY = "equity"
    INVESTMENT = "investment"
    EXPENSE = "expense"
    VOTE = "vote"
    TODO = "todo"
    CALENDAR = "calendar"
    HIDDEN = "hidden"
    SPECIAL = "special"


class AchievementRarity(str, Enum):
    """成就稀有度"""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


# ==================== 成就定义 ====================

class AchievementDefinition(BaseModel):
    """成就定义响应"""
    id: int
    code: str
    name: str
    description: str
    category: AchievementCategory
    icon: str
    rarity: AchievementRarity
    points: int
    is_hidden: bool

    class Config:
        from_attributes = True


class AchievementDefinitionWithStatus(AchievementDefinition):
    """带解锁状态的成就定义"""
    is_unlocked: bool = False
    unlocked_at: Optional[datetime] = None


# ==================== 用户成就 ====================

class UserAchievementResponse(BaseModel):
    """用户已解锁成就响应"""
    id: int
    achievement_id: int
    code: str
    name: str
    description: str
    category: AchievementCategory
    icon: str
    rarity: AchievementRarity
    points: int
    unlocked_at: datetime

    class Config:
        from_attributes = True


class NewUnlock(BaseModel):
    """新解锁的成就"""
    achievement: AchievementDefinition
    unlocked_at: datetime


class AchievementCheckResponse(BaseModel):
    """成就检查响应"""
    new_unlocks: List[NewUnlock]
    total_unlocked: int
    total_points: int


# ==================== 成就进度 ====================

class CategoryProgress(BaseModel):
    """分类进度"""
    category: AchievementCategory
    category_name: str
    total: int
    unlocked: int
    percentage: float


class AchievementProgress(BaseModel):
    """成就进度统计"""
    total_achievements: int
    unlocked_achievements: int
    total_points: int
    earned_points: int
    percentage: float
    categories: List[CategoryProgress]
    recent_unlocks: List[UserAchievementResponse]


# ==================== 最近解锁(家庭) ====================

class RecentFamilyUnlock(BaseModel):
    """家庭成员最近解锁"""
    user_id: int
    username: str
    nickname: str
    achievement: AchievementDefinition
    unlocked_at: datetime
