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
from app.models.models import User, FamilyMember, FamilyPet, PetExpLog

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
    # ========== Todo 待办任务相关 ==========
    "todo_complete_low": 5,       # 完成低优先级任务
    "todo_complete_medium": 10,   # 完成中优先级任务
    "todo_complete_high": 15,     # 完成高优先级任务
    "todo_on_time_bonus": 5,      # 准时完成任务额外奖励
    "todo_assigned": 8,           # 完成他人指派的任务
    # ========== Calendar 日历事件相关 ==========
    "calendar_event_personal": 8,    # 创建个人日程
    "calendar_event_family": 15,     # 创建家庭活动
    "calendar_event_birthday": 20,   # 创建生日/纪念日事件
    "calendar_event_finance": 10,    # 创建财务提醒
    "calendar_repeat_bonus": 5,      # 创建重复事件额外奖励
    "calendar_participant_bonus": 2, # 每邀请1位参与者奖励
    "calendar_sync": 5,              # 同步系统事件基础经验
    "calendar_sync_per_event": 2,    # 每同步一个事件额外奖励
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


# 经验来源名称映射
EXP_SOURCE_NAMES = {
    "daily_checkin": "每日签到",
    "feed": "喂食宠物",
    "deposit": "存款操作",
    "investment": "理财收益",
    "vote": "参与投票",
    "proposal_passed": "提案通过",
    "expense_approved": "审批支出",
    "gift": "赠送股权",
    "gift_sent": "赠送股权",
    "achievement_unlock": "解锁成就",
    # ========== Todo 待办任务相关 ==========
    "todo_complete_low": "完成低优先级任务",
    "todo_complete_medium": "完成中优先级任务",
    "todo_complete_high": "完成高优先级任务",
    "todo_complete": "完成待办任务",
    "todo_on_time_bonus": "准时完成任务",
    "todo_assigned": "完成他人指派任务",
    # ========== Calendar 日历事件相关 ==========
    "calendar_event_personal": "创建个人日程",
    "calendar_event_family": "创建家庭活动",
    "calendar_event_birthday": "创建生日纪念日",
    "calendar_event_finance": "创建财务提醒",
    "calendar_event": "创建日历事件",
    "calendar_repeat_bonus": "创建重复事件",
    "calendar_participant_bonus": "邀请参与者",
    "calendar_sync": "同步系统事件",
}


async def add_exp(db: AsyncSession, pet: FamilyPet, exp_amount: int, source: str, source_detail: str = None, operator_id: int = None) -> dict:
    """为宠物增加经验值
    
    Args:
        db: 数据库会话
        pet: 宠物对象
        exp_amount: 经验值数量
        source: 来源类型
        source_detail: 来源详情
        operator_id: 操作者用户ID
    """
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
    
    # 记录经验获取日志
    exp_log = PetExpLog(
        family_id=pet.family_id,
        operator_id=operator_id,
        exp_amount=exp_amount,
        source=source,
        source_detail=source_detail or EXP_SOURCE_NAMES.get(source, source)
    )
    db.add(exp_log)
    
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


@router.put("", response_model=dict)
async def update_pet(
    data: PetRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新宠物信息（重命名）"""
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
        "new_name": data.name,
        "pet": build_pet_response(pet)
    }


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
    
    # 增加经验（记录操作者）
    exp_result = await add_exp(db, pet, total_exp, "daily_checkin", operator_id=current_user.id)
    
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
    
    # 喂食也给少量经验（记录操作者）
    exp_result = await add_exp(db, pet, 5, "feed", operator_id=current_user.id)
    
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
            # 基础操作
            {"key": "daily_checkin", "name": "每日签到", "exp": EXP_CONFIG["daily_checkin"], "category": "基础"},
            {"key": "streak_bonus", "name": "连续签到奖励", "exp": f"+{EXP_CONFIG['streak_bonus']}/天 (最多7天)", "category": "基础"},
            {"key": "feed", "name": "喂食宠物", "exp": 5, "category": "基础"},
            # 财务操作
            {"key": "deposit", "name": "存款操作", "exp": EXP_CONFIG["deposit"], "category": "财务"},
            {"key": "investment", "name": "理财操作", "exp": EXP_CONFIG["investment"], "category": "财务"},
            {"key": "expense_approved", "name": "审批支出", "exp": EXP_CONFIG["expense_approved"], "category": "财务"},
            {"key": "gift_sent", "name": "赠送股权", "exp": EXP_CONFIG["gift_sent"], "category": "财务"},
            # 投票提案
            {"key": "vote", "name": "参与投票", "exp": EXP_CONFIG["vote"], "category": "治理"},
            {"key": "proposal_passed", "name": "提案通过", "exp": EXP_CONFIG["proposal_passed"], "category": "治理"},
            # 待办任务
            {"key": "todo_complete_low", "name": "完成低优先级任务", "exp": EXP_CONFIG["todo_complete_low"], "category": "待办"},
            {"key": "todo_complete_medium", "name": "完成中优先级任务", "exp": EXP_CONFIG["todo_complete_medium"], "category": "待办"},
            {"key": "todo_complete_high", "name": "完成高优先级任务", "exp": EXP_CONFIG["todo_complete_high"], "category": "待办"},
            {"key": "todo_on_time_bonus", "name": "准时完成任务奖励", "exp": f"+{EXP_CONFIG['todo_on_time_bonus']}", "category": "待办"},
            {"key": "todo_assigned", "name": "完成他人指派任务", "exp": f"+{EXP_CONFIG['todo_assigned']}", "category": "待办"},
            # 日历事件
            {"key": "calendar_event_personal", "name": "创建个人日程", "exp": EXP_CONFIG["calendar_event_personal"], "category": "日历"},
            {"key": "calendar_event_family", "name": "创建家庭活动", "exp": EXP_CONFIG["calendar_event_family"], "category": "日历"},
            {"key": "calendar_event_birthday", "name": "创建生日纪念日", "exp": EXP_CONFIG["calendar_event_birthday"], "category": "日历"},
            {"key": "calendar_event_finance", "name": "创建财务提醒", "exp": EXP_CONFIG["calendar_event_finance"], "category": "日历"},
            {"key": "calendar_repeat_bonus", "name": "创建重复事件奖励", "exp": f"+{EXP_CONFIG['calendar_repeat_bonus']}", "category": "日历"},
            {"key": "calendar_participant_bonus", "name": "邀请参与者奖励", "exp": f"+{EXP_CONFIG['calendar_participant_bonus']}/人", "category": "日历"},
            {"key": "calendar_sync", "name": "同步系统事件", "exp": f"{EXP_CONFIG['calendar_sync']}+{EXP_CONFIG['calendar_sync_per_event']}/个", "category": "日历"},
            # 成就
            {"key": "achievement_unlock", "name": "解锁成就", "exp": EXP_CONFIG["achievement_unlock"], "category": "成就"},
        ]
    }


@router.get("/exp-logs", response_model=dict)
async def get_exp_logs(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取宠物经验获取记录"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 查询记录总数
    count_result = await db.execute(
        select(func.count()).select_from(PetExpLog).where(PetExpLog.family_id == family_id)
    )
    total = count_result.scalar()
    
    # 查询记录列表（按时间倒序），联表查询操作者信息
    # 使用 outerjoin 因为 operator_id 可能为空（历史记录）
    from sqlalchemy.orm import aliased
    OperatorUser = aliased(User)
    
    result = await db.execute(
        select(PetExpLog, OperatorUser.nickname)
        .outerjoin(OperatorUser, PetExpLog.operator_id == OperatorUser.id)
        .where(PetExpLog.family_id == family_id)
        .order_by(PetExpLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    
    # 构建响应
    log_list = []
    for row in rows:
        log = row[0]  # PetExpLog 对象
        operator_nickname = row[1]  # 操作者昵称（可能为 None）
        
        log_list.append({
            "id": log.id,
            "exp_amount": log.exp_amount,
            "source": log.source,
            "source_name": EXP_SOURCE_NAMES.get(log.source, log.source),
            "source_detail": log.source_detail,
            "operator_id": log.operator_id,
            "operator_nickname": operator_nickname or "系统",
            "created_at": log.created_at.isoformat() if log.created_at else None
        })
    
    return {
        "total": total,
        "logs": log_list,
        "limit": limit,
        "offset": offset
    }


# 外部调用接口 - 供其他模块调用增加经验
async def grant_pet_exp(db: AsyncSession, family_id: int, source: str, multiplier: float = 1.0, operator_id: int = None, source_detail: str = None) -> dict:
    """
    为宠物增加经验值（供其他模块调用）
    
    Args:
        db: 数据库会话
        family_id: 家庭ID
        source: 经验来源 (deposit, investment, vote, etc.)
        multiplier: 经验倍数
        operator_id: 操作者用户ID
        source_detail: 来源详情描述
    
    Returns:
        经验增加结果
    """
    pet = await get_or_create_pet(db, family_id)
    base_exp = EXP_CONFIG.get(source, 10)
    actual_exp = int(base_exp * multiplier)
    
    return await add_exp(db, pet, actual_exp, source, source_detail=source_detail, operator_id=operator_id)
