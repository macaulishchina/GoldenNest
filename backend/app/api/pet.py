"""
宠物养成系统 API - 可升级进化的家庭虚拟宠物
"""
from datetime import datetime, date, timedelta
from typing import Optional
import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, FamilyMember, FamilyPet

router = APIRouter(prefix="/pet", tags=["pet"])


# ==================== 进化配置 ====================

PET_EVOLUTION = {
    "golden_egg": {
        "name": "金色蛋",
        "emoji": "🥚",
        "min_level": 1,
        "max_level": 9,
        "description": "神秘的金色蛋，蕴含无限可能"
    },
    "golden_chick": {
        "name": "金色小鸡",
        "emoji": "🐣",
        "min_level": 10,
        "max_level": 29,
        "description": "刚破壳而出的小鸡，充满活力"
    },
    "golden_bird": {
        "name": "金色小鸟",
        "emoji": "🐦",
        "min_level": 30,
        "max_level": 59,
        "description": "展翅高飞的金鸟，守护家庭财富"
    },
    "golden_phoenix": {
        "name": "金色凤凰",
        "emoji": "🦅",
        "min_level": 60,
        "max_level": 99,
        "description": "浴火重生的神鸟，带来无尽好运"
    },
    "golden_dragon": {
        "name": "金色神龙",
        "emoji": "🐲",
        "min_level": 100,
        "max_level": 999,
        "description": "传说中的神龙，财富的终极守护者"
    }
}

# 经验值配置
EXP_CONFIG = {
    "daily_checkin": 10,          # 每日签到
    "streak_bonus": 5,            # 连续签到额外奖励
    "deposit": 20,                # 存款操作
    "investment": 15,             # 理财操作
    "vote": 10,                   # 投票操作
    "proposal_passed": 50,        # 提案通过
    "expense_approved": 20,       # 支出审批
    "gift_sent": 30,              # 赠送股权
    "achievement_unlock": 25,     # 解锁成就
}

def get_level_exp(level: int) -> int:
    """计算升级到下一级所需经验值"""
    return int(100 * (1.2 ** (level - 1)))

def get_pet_type_for_level(level: int) -> str:
    """根据等级获取宠物类型"""
    for pet_type, config in PET_EVOLUTION.items():
        if config["min_level"] <= level <= config["max_level"]:
            return pet_type
    return "golden_dragon"  # 超过100级都是神龙


# ==================== Schema ====================

class PetCreate(BaseModel):
    name: str  # 宠物昵称

class PetRename(BaseModel):
    name: str

class PetResponse(BaseModel):
    id: int
    name: str
    pet_type: str
    type_name: str
    emoji: str
    description: str
    level: int
    exp: int
    exp_to_next: int
    exp_progress: float
    happiness: int
    total_exp: int
    checkin_streak: int
    can_checkin: bool
    can_evolve: bool
    next_evolution: Optional[dict]


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


async def get_or_create_pet(db: AsyncSession, family_id: int) -> FamilyPet:
    """获取或创建家庭宠物"""
    result = await db.execute(
        select(FamilyPet).where(FamilyPet.family_id == family_id)
    )
    pet = result.scalar_one_or_none()
    
    if not pet:
        pet = FamilyPet(
            family_id=family_id,
            name="小金",  # 默认名称
            pet_type="golden_egg",
            level=1,
            exp=0,
            happiness=100,
            total_exp=0,
            checkin_streak=0
        )
        db.add(pet)
        await db.commit()
        await db.refresh(pet)
    
    return pet


def build_pet_response(pet: FamilyPet) -> dict:
    """构建宠物响应"""
    pet_config = PET_EVOLUTION.get(pet.pet_type, PET_EVOLUTION["golden_egg"])
    exp_to_next = get_level_exp(pet.level)
    
    # 检查是否可以签到（每天只能签到一次）
    can_checkin = True
    checked_in_today = False
    if pet.last_checkin_at:
        last_checkin_date = pet.last_checkin_at.date()
        today = date.today()
        can_checkin = last_checkin_date < today
        checked_in_today = last_checkin_date >= today
    
    # 检查是否可以进化
    can_evolve = False
    next_evolution = None
    current_type = pet.pet_type
    for pet_type, config in PET_EVOLUTION.items():
        if config["min_level"] > pet_config["max_level"]:
            # 找到下一个进化形态
            if pet.level >= config["min_level"]:
                can_evolve = True
            next_evolution = {
                "type": pet_type,
                "name": config["name"],
                "emoji": config["emoji"],
                "required_level": config["min_level"]
            }
            break
    
    return {
        "id": pet.id,
        "name": pet.name,
        "pet_type": pet.pet_type,
        "type_name": pet_config["name"],
        "emoji": pet_config["emoji"],
        "description": pet_config["description"],
        "level": pet.level,
        "exp": pet.exp,
        "current_exp": pet.exp,  # 前端使用的字段名
        "exp_to_next": exp_to_next,
        "exp_progress": round((pet.exp / exp_to_next) * 100, 1) if exp_to_next > 0 else 100,
        "happiness": pet.happiness,
        "total_exp": pet.total_exp,
        "checkin_streak": pet.checkin_streak,
        "can_checkin": can_checkin,
        "checked_in_today": checked_in_today,  # 前端使用的字段名
        "can_evolve": can_evolve,
        "next_evolution": next_evolution,
        "created_at": pet.created_at.isoformat() if pet.created_at else None
    }


async def add_exp(db: AsyncSession, pet: FamilyPet, exp_amount: int, source: str) -> dict:
    """为宠物增加经验值"""
    pet.exp += exp_amount
    pet.total_exp += exp_amount
    
    leveled_up = False
    evolved = False
    old_type = pet.pet_type
    old_level = pet.level
    
    # 检查升级
    while pet.exp >= get_level_exp(pet.level):
        pet.exp -= get_level_exp(pet.level)
        pet.level += 1
        leveled_up = True
    
    # 检查进化
    new_type = get_pet_type_for_level(pet.level)
    if new_type != pet.pet_type:
        pet.pet_type = new_type
        evolved = True
    
    await db.commit()
    await db.refresh(pet)
    
    result = {
        "exp_gained": exp_amount,
        "source": source,
        "leveled_up": leveled_up,
        "evolved": evolved
    }
    
    if leveled_up:
        result["new_level"] = pet.level
        result["old_level"] = old_level
    
    if evolved:
        result["old_type"] = old_type
        result["new_type"] = new_type
        result["new_type_name"] = PET_EVOLUTION[new_type]["name"]
        result["new_emoji"] = PET_EVOLUTION[new_type]["emoji"]
    
    return result


# ==================== API ====================

@router.get("", response_model=dict)
async def get_pet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭宠物信息"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    return build_pet_response(pet)


@router.put("/rename", response_model=dict)
async def rename_pet(
    data: PetRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重命名宠物"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    
    if len(data.name) < 1 or len(data.name) > 20:
        raise HTTPException(status_code=400, detail="昵称长度应在1-20个字符之间")
    
    old_name = pet.name
    pet.name = data.name
    await db.commit()
    
    return {
        "success": True,
        "message": f"宠物已改名为「{data.name}」",
        "old_name": old_name,
        "new_name": data.name
    }


@router.post("/checkin", response_model=dict)
async def daily_checkin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """每日签到"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    
    today = date.today()
    
    # 检查是否已签到
    if pet.last_checkin_at:
        last_checkin_date = pet.last_checkin_at.date()
        if last_checkin_date >= today:
            raise HTTPException(status_code=400, detail="今天已经签到过了")
        
        # 检查连续签到
        yesterday = today - timedelta(days=1)
        if last_checkin_date == yesterday:
            pet.checkin_streak += 1
        else:
            pet.checkin_streak = 1
    else:
        pet.checkin_streak = 1
    
    pet.last_checkin_at = datetime.utcnow()
    
    # 计算经验值
    base_exp = EXP_CONFIG["daily_checkin"]
    streak_bonus = min(pet.checkin_streak, 7) * EXP_CONFIG["streak_bonus"]  # 最多7天额外奖励
    total_exp = base_exp + streak_bonus
    
    # 增加经验
    exp_result = await add_exp(db, pet, total_exp, "daily_checkin")
    
    # 增加心情值
    pet.happiness = min(100, pet.happiness + 5)
    await db.commit()
    
    return {
        "success": True,
        "message": f"签到成功！连续签到 {pet.checkin_streak} 天",
        "checkin_streak": pet.checkin_streak,
        "base_exp": base_exp,
        "streak_bonus": streak_bonus,
        "total_exp": total_exp,
        **exp_result,
        "pet": build_pet_response(pet)
    }


@router.post("/feed", response_model=dict)
async def feed_pet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """喂食宠物（增加心情值）"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    
    # 检查是否可以喂食（每4小时一次）
    if pet.last_fed_at:
        time_since_feed = datetime.utcnow() - pet.last_fed_at
        if time_since_feed < timedelta(hours=4):
            remaining = timedelta(hours=4) - time_since_feed
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            raise HTTPException(
                status_code=400, 
                detail=f"宠物还不饿，{hours}小时{minutes}分钟后再来喂食吧"
            )
    
    pet.last_fed_at = datetime.utcnow()
    old_happiness = pet.happiness
    pet.happiness = min(100, pet.happiness + 20)
    
    # 喂食也给少量经验
    exp_result = await add_exp(db, pet, 5, "feed")
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"喂食成功！{pet.name}很开心！",
        "happiness_before": old_happiness,
        "happiness_after": pet.happiness,
        **exp_result,
        "pet": build_pet_response(pet)
    }


@router.get("/evolution-preview", response_model=dict)
async def get_evolution_preview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取所有进化形态预览"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    
    evolutions = []
    for pet_type, config in PET_EVOLUTION.items():
        is_current = pet.pet_type == pet_type
        is_unlocked = pet.level >= config["min_level"]
        
        evolutions.append({
            "type": pet_type,
            "name": config["name"],
            "emoji": config["emoji"],
            "description": config["description"],
            "min_level": config["min_level"],
            "max_level": config["max_level"],
            "is_current": is_current,
            "is_unlocked": is_unlocked
        })
    
    return {
        "current_level": pet.level,
        "evolutions": evolutions
    }


@router.get("/exp-sources", response_model=dict)
async def get_exp_sources():
    """获取经验值来源配置"""
    return {
        "sources": [
            {"key": "daily_checkin", "name": "每日签到", "exp": EXP_CONFIG["daily_checkin"]},
            {"key": "streak_bonus", "name": "连续签到奖励", "exp": f"+{EXP_CONFIG['streak_bonus']}/天 (最多7天)"},
            {"key": "deposit", "name": "存款操作", "exp": EXP_CONFIG["deposit"]},
            {"key": "investment", "name": "理财操作", "exp": EXP_CONFIG["investment"]},
            {"key": "vote", "name": "参与投票", "exp": EXP_CONFIG["vote"]},
            {"key": "proposal_passed", "name": "提案通过", "exp": EXP_CONFIG["proposal_passed"]},
            {"key": "expense_approved", "name": "审批支出", "exp": EXP_CONFIG["expense_approved"]},
            {"key": "gift_sent", "name": "赠送股权", "exp": EXP_CONFIG["gift_sent"]},
            {"key": "achievement_unlock", "name": "解锁成就", "exp": EXP_CONFIG["achievement_unlock"]},
        ]
    }


# 外部调用接口 - 供其他模块调用增加经验
async def grant_pet_exp(db: AsyncSession, family_id: int, source: str, multiplier: float = 1.0) -> dict:
    """
    为宠物增加经验值（供其他模块调用）
    
    Args:
        db: 数据库会话
        family_id: 家庭ID
        source: 经验来源 (deposit, investment, vote, etc.)
        multiplier: 经验倍数
    
    Returns:
        经验增加结果
    """
    pet = await get_or_create_pet(db, family_id)
    base_exp = EXP_CONFIG.get(source, 10)
    actual_exp = int(base_exp * multiplier)
    
    return await add_exp(db, pet, actual_exp, source)
