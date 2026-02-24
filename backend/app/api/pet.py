"""
宠物养成系统 API - 可升级进化的家庭虚拟宠物

特性：
- 心情系统：心情值影响EXP倍率，每日无互动衰减
- 差异化喂食：三种食物不同效果/冷却/日限
- 小游戏：记忆翻牌、迷你炒股、宠物探险RPG、扫雷（多步骤会话制）
- 里程碑：年龄/经验里程碑奖励
- 进化庆典：进化时奖励EXP + 企业微信通知
"""
from datetime import datetime, date, timedelta
from typing import Optional
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.common import TimeRange, get_time_range_filter
from app.api.auth import get_current_user
from app.models.models import User, FamilyMember, FamilyPet, PetExpLog

# ---- 游戏模块导入 ----
from app.games.memory import (
    create_memory_session, process_memory_action, sanitize_memory_state,
)
from app.games.stock import (
    create_stock_session, process_stock_action, sanitize_stock_state,
)
from app.games.adventure import (
    create_adventure_session, process_adventure_action, sanitize_adventure_state,
)
from app.games.minesweeper import (
    create_minesweeper_session, process_minesweeper_action, sanitize_minesweeper_state,
)

router = APIRouter(prefix="/pet", tags=["pet"])
logger = logging.getLogger(__name__)


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

# ==================== 喂食配置 ====================

FOOD_CONFIG = {
    "basic": {
        "name": "普通饲料",
        "emoji": "🌾",
        "happiness": 10,
        "exp": 3,
        "daily_limit": None,  # 无限
        "cooldown_hours": 2,
    },
    "premium": {
        "name": "高级饲料",
        "emoji": "🌽",
        "happiness": 25,
        "exp": 8,
        "daily_limit": 3,
        "cooldown_hours": 4,
    },
    "luxury": {
        "name": "豪华大餐",
        "emoji": "🍖",
        "happiness": 50,
        "exp": 20,
        "daily_limit": 1,
        "cooldown_hours": 4,
    },
}

# ==================== 心情系统配置 ====================

# 心情值 → EXP倍率
HAPPINESS_MULTIPLIERS = [
    (80, 1.2),   # happiness >= 80
    (50, 1.0),   # happiness 50-79
    (20, 0.8),   # happiness 20-49
    (0, 0.5),    # happiness < 20
]

# 每日无互动心情衰减值
HAPPINESS_DECAY_PER_DAY = 10

# ==================== 小游戏配置 ====================

GAME_CONFIG = {
    "memory":      {"name": "记忆翻牌", "icon": "🃏", "description": "翻开卡牌找到配对", "exp_range": "15~1000"},
    "stock":       {"name": "迷你炒股", "icon": "📈", "description": "虚拟炒股低买高卖", "exp_range": "5~1000"},
    "adventure":   {"name": "宠物探险", "icon": "⚔️", "description": "地牢探险战胜怪物", "exp_range": "5~1000"},
    "minesweeper": {"name": "扫雷", "icon": "💣", "description": "排除地雷考验逻辑", "exp_range": "20~1000"},
}

DAILY_GAME_LIMIT = 10  # 每人每天总游戏次数

# ==================== 里程碑配置 ====================

AGE_MILESTONES = {
    "age_7": {"days": 7, "bonus_exp": 50, "label": "7天纪念"},
    "age_30": {"days": 30, "bonus_exp": 100, "label": "满月纪念"},
    "age_100": {"days": 100, "bonus_exp": 300, "label": "百日纪念"},
    "age_365": {"days": 365, "bonus_exp": 1000, "label": "周年纪念"},
}

EXP_MILESTONES = {
    "exp_1000": {"total_exp": 1000, "bonus_happiness": 20, "label": "千里之行"},
    "exp_5000": {"total_exp": 5000, "bonus_happiness": 20, "label": "五千大关"},
    "exp_10000": {"total_exp": 10000, "bonus_happiness": 20, "label": "万里长征"},
    "exp_50000": {"total_exp": 50000, "bonus_happiness": 20, "label": "传说经验"},
}

# 进化奖励EXP
EVOLUTION_BONUS = {
    "golden_chick": 50,
    "golden_bird": 100,
    "golden_phoenix": 200,
    "golden_dragon": 500,
}


# ==================== 工具函数 ====================

def get_level_exp(level: int) -> int:
    """计算升级到下一级所需经验值"""
    return int(100 * (1.2 ** (level - 1)))

def get_pet_type_for_level(level: int) -> str:
    """根据等级获取宠物类型"""
    for pet_type, config in PET_EVOLUTION.items():
        if config["min_level"] <= level <= config["max_level"]:
            return pet_type
    return "golden_dragon"  # 超过100级都是神龙


def calculate_current_happiness(pet: FamilyPet) -> int:
    """实时计算当前心情值（含衰减）"""
    base_happiness = pet.happiness
    last_interaction = pet.last_interaction_at or pet.last_fed_at or pet.last_checkin_at
    if not last_interaction:
        return base_happiness
    days_since = (datetime.utcnow() - last_interaction).total_seconds() / 86400.0
    if days_since < 1:
        return base_happiness
    decay = int(days_since) * HAPPINESS_DECAY_PER_DAY
    return max(0, base_happiness - decay)


def get_happiness_multiplier(happiness: int) -> float:
    """根据心情值获取EXP倍率"""
    for threshold, multiplier in HAPPINESS_MULTIPLIERS:
        if happiness >= threshold:
            return multiplier
    return 0.5


def get_mood_state(happiness: int) -> dict:
    """根据心情值返回心情状态描述"""
    if happiness >= 80:
        return {"state": "ecstatic", "label": "兴高采烈", "emoji": "🤩", "color": "#FFD700"}
    elif happiness >= 50:
        return {"state": "happy", "label": "开心", "emoji": "😊", "color": "#4CAF50"}
    elif happiness >= 20:
        return {"state": "neutral", "label": "一般", "emoji": "😐", "color": "#FFA726"}
    else:
        return {"state": "sad", "label": "难过", "emoji": "😢", "color": "#F44336"}


def get_daily_counts(json_str: str | None) -> dict:
    """解析每日计数JSON，跨日自动重置"""
    today = date.today().isoformat()
    if json_str:
        try:
            data = json.loads(json_str)
            if data.get("date") == today:
                return data
        except (json.JSONDecodeError, TypeError):
            pass
    return {"date": today}


# ==================== Schema ====================

class PetCreate(BaseModel):
    name: str  # 宠物昵称

class PetRename(BaseModel):
    name: str

class FeedRequest(BaseModel):
    food_type: str = "basic"  # basic, premium, luxury

class GameStartRequest(BaseModel):
    game_type: str  # "memory", "stock", "adventure", "minesweeper"
    difficulty: str = "easy"  # "easy"|"medium"|"hard"|"expert"

class GameActionRequest(BaseModel):
    game_type: str
    action: dict

class MilestoneClaimRequest(BaseModel):
    milestone_key: str

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


def build_pet_response(pet: FamilyPet, user: User = None) -> dict:
    """构建宠物响应（含心情衰减、喂食/游戏状态、里程碑）"""
    pet_config = PET_EVOLUTION.get(pet.pet_type, PET_EVOLUTION["golden_egg"])
    exp_to_next = get_level_exp(pet.level)

    # 实时计算心情值（含衰减）
    current_happiness = calculate_current_happiness(pet)
    happiness_multiplier = get_happiness_multiplier(current_happiness)
    mood = get_mood_state(current_happiness)

    # 检查是否可以签到（每用户每天只能签到一次）
    can_checkin = True
    checked_in_today = False
    checkin_streak = 0
    if user:
        checkin_streak = user.pet_checkin_streak or 0
        if user.pet_last_checkin_at:
            last_checkin_date = user.pet_last_checkin_at.date()
            today = date.today()
            can_checkin = last_checkin_date < today
            checked_in_today = last_checkin_date >= today
    elif pet.last_checkin_at:
        checkin_streak = pet.checkin_streak
        last_checkin_date = pet.last_checkin_at.date()
        today = date.today()
        can_checkin = last_checkin_date < today
        checked_in_today = last_checkin_date >= today

    # 检查是否可以进化
    can_evolve = False
    next_evolution = None
    for pet_type, config in PET_EVOLUTION.items():
        if config["min_level"] > pet_config["max_level"]:
            if pet.level >= config["min_level"]:
                can_evolve = True
            next_evolution = {
                "type": pet_type,
                "name": config["name"],
                "emoji": config["emoji"],
                "required_level": config["min_level"]
            }
            break

    # 宠物年龄
    pet_age_days = (datetime.utcnow() - pet.created_at).days if pet.created_at else 0

    # 喂食状态（使用用户独立计数）
    feed_source = user.pet_daily_feed_counts if user else pet.daily_feed_counts
    feed_counts = get_daily_counts(feed_source)
    feed_status = {}
    for food_type, cfg in FOOD_CONFIG.items():
        used = feed_counts.get(food_type, 0)
        can_feed_type = True
        remaining_cooldown = 0

        # 检查日限
        if cfg["daily_limit"] is not None and used >= cfg["daily_limit"]:
            can_feed_type = False

        # 检查冷却
        if pet.last_fed_at:
            elapsed = (datetime.utcnow() - pet.last_fed_at).total_seconds()
            cooldown_secs = cfg["cooldown_hours"] * 3600
            if elapsed < cooldown_secs:
                remaining_cooldown = int(cooldown_secs - elapsed)
                can_feed_type = False

        feed_status[food_type] = {
            "name": cfg["name"],
            "emoji": cfg["emoji"],
            "happiness": cfg["happiness"],
            "exp": cfg["exp"],
            "used_today": used,
            "daily_limit": cfg["daily_limit"],
            "can_feed": can_feed_type,
            "cooldown_remaining": remaining_cooldown,
        }

    # 游戏状态（使用用户独立计数 + 全局次数限制）
    game_source = user.pet_daily_game_counts if user else pet.daily_game_counts
    game_counts = get_daily_counts(game_source)
    total_games_used = sum(v for k, v in game_counts.items() if k != "date" and isinstance(v, int))
    game_status = {}
    for game_type, cfg in GAME_CONFIG.items():
        used = game_counts.get(game_type, 0)
        has_active = get_active_session(pet, game_type) is not None
        game_status[game_type] = {
            "name": cfg["name"],
            "icon": cfg["icon"],
            "description": cfg["description"],
            "exp_range": cfg["exp_range"],
            "used_today": used,
            "can_play": total_games_used < DAILY_GAME_LIMIT or has_active,
            "has_active_session": has_active,
        }

    # 可领取的里程碑
    claimed = []
    if pet.claimed_milestones:
        try:
            claimed = json.loads(pet.claimed_milestones)
        except (json.JSONDecodeError, TypeError):
            claimed = []

    available_milestones = []
    for key, ms in AGE_MILESTONES.items():
        if key not in claimed and pet_age_days >= ms["days"]:
            available_milestones.append({"key": key, "type": "age", **ms})
    for key, ms in EXP_MILESTONES.items():
        if key not in claimed and pet.total_exp >= ms["total_exp"]:
            available_milestones.append({"key": key, "type": "exp", **ms})

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
        "happiness": current_happiness,
        "happiness_multiplier": happiness_multiplier,
        "mood": mood,
        "total_exp": pet.total_exp,
        "checkin_streak": checkin_streak,
        "can_checkin": can_checkin,
        "checked_in_today": checked_in_today,
        "can_evolve": can_evolve,
        "next_evolution": next_evolution,
        "pet_age_days": pet_age_days,
        "feed_status": feed_status,
        "game_status": game_status,
        "daily_game_limit": DAILY_GAME_LIMIT,
        "total_games_used": total_games_used,
        "available_milestones": available_milestones,
        "created_at": pet.created_at.isoformat() if pet.created_at else None,
        "game_records": get_game_sessions(pet).get("_records", {}),
    }


# 经验来源名称映射
EXP_SOURCE_NAMES = {
    "daily_checkin": "每日签到",
    "feed": "喂食宠物",
    "feed_basic": "喂食普通饲料",
    "feed_premium": "喂食高级饲料",
    "feed_luxury": "喂食豪华大餐",
    "deposit": "存款操作",
    "investment": "理财收益",
    "vote": "参与投票",
    "proposal_passed": "提案通过",
    "expense_approved": "审批支出",
    "gift": "赠送股权",
    "gift_sent": "赠送股权",
    "achievement_unlock": "解锁成就",
    "game_memory": "记忆翻牌",
    "game_stock": "迷你炒股",
    "game_adventure": "宠物探险",
    "game_minesweeper": "扫雷",
    "milestone_age": "陪伴里程碑",
    "milestone_exp": "经验里程碑",
    "evolution_bonus": "进化奖励",
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


async def add_exp(db: AsyncSession, pet: FamilyPet, exp_amount: int, source: str,
                  source_detail: str = None, operator_id: int = None,
                  apply_happiness_multiplier: bool = True) -> dict:
    """为宠物增加经验值（含心情倍率和进化奖励）"""
    # 应用心情倍率
    if apply_happiness_multiplier:
        current_happiness = calculate_current_happiness(pet)
        multiplier = get_happiness_multiplier(current_happiness)
        exp_amount = max(1, int(exp_amount * multiplier))

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

        # 进化奖励EXP
        bonus = EVOLUTION_BONUS.get(new_type, 0)
        if bonus > 0:
            pet.exp += bonus
            pet.total_exp += bonus
            # 奖励EXP也可能触发升级
            while pet.exp >= get_level_exp(pet.level):
                pet.exp -= get_level_exp(pet.level)
                pet.level += 1
            bonus_log = PetExpLog(
                family_id=pet.family_id,
                operator_id=operator_id,
                exp_amount=bonus,
                source="evolution_bonus",
                source_detail=f"进化为{PET_EVOLUTION[new_type]['name']}奖励"
            )
            db.add(bonus_log)
            result["evolution_bonus_exp"] = bonus

        # 发送企业微信进化通知（fail-safe）
        try:
            from app.services.notification import send_pet_evolved_notification
            await send_pet_evolved_notification(db, pet.family_id, pet.name, new_type)
        except Exception as e:
            logger.warning(f"发送进化通知失败: {e}")

    return result


# ==================== 游戏会话管理 ====================

def get_game_sessions(pet: FamilyPet) -> dict:
    """获取所有游戏会话"""
    if pet.game_sessions:
        try:
            return json.loads(pet.game_sessions)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def get_active_session(pet: FamilyPet, game_type: str) -> dict | None:
    """获取指定游戏的活跃会话（基于最后活跃时间超时）"""
    sessions = get_game_sessions(pet)
    session = sessions.get(game_type)
    if not session:
        return None
    # 优先使用 last_active_at，兼容旧会话回退到 started_at
    ts = session.get("last_active_at") or session.get("started_at")
    if not ts:
        return None
    last_active = datetime.fromisoformat(ts)
    # 冒险模式(尤其是无尽)允许更长的空闲时间
    timeout = 14400 if game_type == "adventure" else 1800  # 4小时 / 30分钟
    if (datetime.utcnow() - last_active).total_seconds() > timeout:
        del sessions[game_type]
        pet.game_sessions = json.dumps(sessions) if sessions else None
        return None
    return session


def save_game_session(pet: FamilyPet, game_type: str, session: dict):
    """保存游戏会话"""
    sessions = get_game_sessions(pet)
    sessions[game_type] = _strip_surrogates(session)
    pet.game_sessions = json.dumps(sessions, ensure_ascii=False)


def clear_game_session(pet: FamilyPet, game_type: str):
    """清除游戏会话"""
    sessions = get_game_sessions(pet)
    sessions.pop(game_type, None)
    pet.game_sessions = json.dumps(sessions) if sessions else None


# ==================== 状态脱敏 ====================

import re as _re
_SURROGATE_RE = _re.compile(r'[\ud800-\udfff]')

def _strip_surrogates(obj):
    """递归清除字符串中的 UTF-16 surrogate 字符，防止 JSON 序列化报错"""
    if isinstance(obj, str):
        return _SURROGATE_RE.sub('', obj)
    if isinstance(obj, dict):
        return {k: _strip_surrogates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_surrogates(v) for v in obj]
    return obj

def sanitize_state(game_type: str, session: dict) -> dict:
    """清除服务端秘密，返回客户端安全的状态（委托给各游戏模块）"""
    if game_type == "memory":
        return sanitize_memory_state(session)
    elif game_type == "stock":
        return sanitize_stock_state(session)
    elif game_type == "adventure":
        return sanitize_adventure_state(session)
    elif game_type == "minesweeper":
        return sanitize_minesweeper_state(session)
    return {}


# ==================== API ====================

@router.get("", response_model=dict)
async def get_pet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭宠物信息"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    return build_pet_response(pet, current_user)


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
        "pet": build_pet_response(pet, current_user)
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

    # 检查是否已签到（用户独立）
    if current_user.pet_last_checkin_at:
        last_checkin_date = current_user.pet_last_checkin_at.date()
        if last_checkin_date >= today:
            raise HTTPException(status_code=400, detail="今天已经签到过了")

        # 检查连续签到
        yesterday = today - timedelta(days=1)
        if last_checkin_date == yesterday:
            current_user.pet_checkin_streak = (current_user.pet_checkin_streak or 0) + 1
        else:
            current_user.pet_checkin_streak = 1
    else:
        current_user.pet_checkin_streak = 1

    now = datetime.utcnow()
    current_user.pet_last_checkin_at = now
    pet.last_interaction_at = now

    # 计算经验值
    base_exp = EXP_CONFIG["daily_checkin"]
    streak_bonus = min(current_user.pet_checkin_streak, 7) * EXP_CONFIG["streak_bonus"]  # 最多7天额外奖励
    total_exp = base_exp + streak_bonus

    # 增加经验（含心情倍率）
    exp_result = await add_exp(db, pet, total_exp, "daily_checkin", operator_id=current_user.id)

    # 增加心情值（基于衰减后的值）
    current_happiness = calculate_current_happiness(pet)
    pet.happiness = min(100, current_happiness + 5)
    await db.commit()

    return {
        "success": True,
        "message": f"签到成功！连续签到 {current_user.pet_checkin_streak} 天",
        "checkin_streak": current_user.pet_checkin_streak,
        "base_exp": base_exp,
        "streak_bonus": streak_bonus,
        "total_exp": total_exp,
        **exp_result,
        "pet": build_pet_response(pet, current_user)
    }


@router.post("/feed", response_model=dict)
async def feed_pet(
    data: FeedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """喂食宠物（差异化食物类型）"""
    if data.food_type not in FOOD_CONFIG:
        raise HTTPException(status_code=400, detail="无效的食物类型")

    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    cfg = FOOD_CONFIG[data.food_type]

    # 检查每日限制（用户独立）
    feed_counts = get_daily_counts(current_user.pet_daily_feed_counts)
    used = feed_counts.get(data.food_type, 0)
    if cfg["daily_limit"] is not None and used >= cfg["daily_limit"]:
        raise HTTPException(status_code=400, detail=f"{cfg['name']}今日已用完")

    # 检查冷却时间
    if pet.last_fed_at:
        elapsed = (datetime.utcnow() - pet.last_fed_at).total_seconds()
        cooldown = cfg["cooldown_hours"] * 3600
        if elapsed < cooldown:
            remaining = cooldown - elapsed
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            raise HTTPException(
                status_code=400,
                detail=f"宠物还不饿，{hours}小时{minutes}分钟后再来喂食吧"
            )

    # 计算心情变化（基于衰减后的值）
    current_happiness = calculate_current_happiness(pet)
    old_happiness = current_happiness
    new_happiness = min(100, current_happiness + cfg["happiness"])
    pet.happiness = new_happiness

    # 更新时间戳
    now = datetime.utcnow()
    pet.last_fed_at = now
    pet.last_interaction_at = now

    # 更新用户每日喂食计数
    feed_counts[data.food_type] = used + 1
    current_user.pet_daily_feed_counts = json.dumps(feed_counts)

    # 增加EXP（含心情倍率）
    source = f"feed_{data.food_type}"
    exp_result = await add_exp(db, pet, cfg["exp"], source,
                               operator_id=current_user.id,
                               source_detail=f"喂食{cfg['name']}")

    await db.commit()

    return {
        "success": True,
        "message": f"喂食{cfg['name']}成功！{pet.name}很开心！",
        "food_type": data.food_type,
        "happiness_before": old_happiness,
        "happiness_after": new_happiness,
        "happiness_gained": new_happiness - old_happiness,
        **exp_result,
        "pet": build_pet_response(pet, current_user)
    }


# ==================== 小游戏 ====================

@router.post("/game/start", response_model=dict)
async def start_game(
    data: GameStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """开始一局小游戏"""
    if data.game_type not in GAME_CONFIG:
        raise HTTPException(status_code=400, detail="无效的游戏类型")

    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    cfg = GAME_CONFIG[data.game_type]

    # 检查是否有正在进行的会话（可恢复）
    existing = get_active_session(pet, data.game_type)
    if existing:
        return {
            "success": True,
            "resumed": True,
            "game_type": data.game_type,
            "game_name": cfg["name"],
            "state": sanitize_state(data.game_type, existing),
        }

    # 检查每日总次数限制（用户独立）
    game_counts = get_daily_counts(current_user.pet_daily_game_counts)
    total_used = sum(v for k, v in game_counts.items() if k != "date" and isinstance(v, int))
    if total_used >= DAILY_GAME_LIMIT:
        raise HTTPException(status_code=400, detail=f"今日游戏次数已用完（{DAILY_GAME_LIMIT}次）")

    # 创建新会话 - 所有游戏都需要选择难度
    difficulty = data.difficulty or "easy"
    valid_difficulties = ["easy", "medium", "hard", "expert"]
    # 冒险游戏额外支持无尽模式
    if data.game_type == "adventure":
        valid_difficulties.append("endless")
    if difficulty not in valid_difficulties:
        raise HTTPException(status_code=400, detail=f"无效的难度，请选择: {', '.join(valid_difficulties)}")
    
    if data.game_type == "memory":
        session = create_memory_session(difficulty)
    elif data.game_type == "stock":
        session = create_stock_session(difficulty)
    elif data.game_type == "adventure":
        session = create_adventure_session(pet.level, difficulty)
    elif data.game_type == "minesweeper":
        session = create_minesweeper_session(difficulty)
    else:
        raise HTTPException(status_code=400, detail="无效的游戏类型")

    save_game_session(pet, data.game_type, session)
    pet.last_interaction_at = datetime.utcnow()
    await db.commit()

    return {
        "success": True,
        "resumed": False,
        "game_type": data.game_type,
        "game_name": cfg["name"],
        "state": sanitize_state(data.game_type, session),
    }


@router.post("/game/action", response_model=dict)
async def game_action(
    data: GameActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送游戏操作"""
    if data.game_type not in GAME_CONFIG:
        raise HTTPException(status_code=400, detail="无效的游戏类型")

    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)

    session = get_active_session(pet, data.game_type)
    if not session:
        raise HTTPException(status_code=400, detail="没有进行中的游戏会话，请先开始游戏")

    # 处理操作
    if data.game_type == "memory":
        result = process_memory_action(session, data.action)
    elif data.game_type == "stock":
        result = process_stock_action(session, data.action)
    elif data.game_type == "adventure":
        result = process_adventure_action(session, data.action)
    elif data.game_type == "minesweeper":
        result = process_minesweeper_action(session, data.action)
    else:
        raise HTTPException(status_code=400, detail="无效的游戏类型")

    # 游戏完成 → 结算EXP + 清除会话
    exp_result = {}
    if result.get("completed"):
        exp_earned = session.get("exp_earned", 0)
        if exp_earned > 0:
            source = f"game_{data.game_type}"
            exp_result = await add_exp(db, pet, exp_earned, source,
                                       operator_id=current_user.id,
                                       source_detail=f"{GAME_CONFIG[data.game_type]['name']}完成")

        # 更新用户每日游戏计数
        game_counts = get_daily_counts(current_user.pet_daily_game_counts)
        game_counts[data.game_type] = game_counts.get(data.game_type, 0) + 1
        current_user.pet_daily_game_counts = json.dumps(game_counts)

        # 更新游戏记录（例如无尽模式最高层数）
        if data.game_type == "adventure" and session.get("endless"):
            reached_floor = session.get("floor", 1)
            all_sessions = get_game_sessions(pet)
            records = all_sessions.get("_records", {})
            if reached_floor > records.get("endless_best_floor", 0):
                records["endless_best_floor"] = reached_floor
                all_sessions["_records"] = records
                pet.game_sessions = json.dumps(all_sessions, ensure_ascii=False)

        # 清除会话
        clear_game_session(pet, data.game_type)

        # 增加心情
        current_happiness = calculate_current_happiness(pet)
        pet.happiness = min(100, current_happiness + 3)
    else:
        session["last_active_at"] = datetime.utcnow().isoformat()
        save_game_session(pet, data.game_type, session)

    pet.last_interaction_at = datetime.utcnow()
    await db.commit()

    # 探险游戏成就检测
    achievement_context = {}
    if data.game_type == "adventure":
        # 难度通关
        if result.get("adventure_cleared"):
            achievement_context["adventure_cleared"] = result["adventure_cleared"]
        # 无尽模式到达新层
        if result.get("adventure_endless_floor"):
            achievement_context["adventure_endless_floor"] = result["adventure_endless_floor"]
    if achievement_context:
        try:
            from app.services.achievement import AchievementService
            ach_service = AchievementService(db)
            await ach_service.check_and_unlock(current_user.id, achievement_context)
            await db.commit()
        except Exception as e:
            import traceback
            print(f"[ACHIEVEMENT ERROR] context={achievement_context}, error={e}")
            traceback.print_exc()

    response = {
        "success": True,
        "game_type": data.game_type,
        "result": _strip_surrogates(result),
        "state": sanitize_state(data.game_type, session),
        **exp_result,
    }
    if result.get("completed"):
        response["pet"] = build_pet_response(pet, current_user)
    return response


# ==================== 里程碑 ====================

@router.post("/milestone/claim", response_model=dict)
async def claim_milestone(
    data: MilestoneClaimRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """领取里程碑奖励"""
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)

    key = data.milestone_key
    claimed = []
    if pet.claimed_milestones:
        try:
            claimed = json.loads(pet.claimed_milestones)
        except (json.JSONDecodeError, TypeError):
            claimed = []

    if key in claimed:
        raise HTTPException(status_code=400, detail="该里程碑已领取")

    pet_age_days = (datetime.utcnow() - pet.created_at).days if pet.created_at else 0

    exp_result = {}
    if key in AGE_MILESTONES:
        ms = AGE_MILESTONES[key]
        if pet_age_days < ms["days"]:
            raise HTTPException(status_code=400, detail="尚未达到该里程碑")
        label = ms["label"]
        # 年龄里程碑给EXP
        exp_result = await add_exp(db, pet, ms["bonus_exp"], "milestone_age",
                                   operator_id=current_user.id,
                                   source_detail=f"里程碑: {label}",
                                   apply_happiness_multiplier=False)
    elif key in EXP_MILESTONES:
        ms = EXP_MILESTONES[key]
        if pet.total_exp < ms["total_exp"]:
            raise HTTPException(status_code=400, detail="尚未达到该里程碑")
        label = ms["label"]
        # 经验里程碑给心情
        current_happiness = calculate_current_happiness(pet)
        pet.happiness = min(100, current_happiness + ms["bonus_happiness"])
    else:
        raise HTTPException(status_code=400, detail="无效的里程碑")

    # 标记已领取
    claimed.append(key)
    pet.claimed_milestones = json.dumps(claimed)
    pet.last_interaction_at = datetime.utcnow()

    await db.commit()

    # 触发成就检测
    try:
        from app.services.achievement import detect_user_achievements
        await detect_user_achievements(current_user.id, family_id, db)
    except Exception:
        pass

    return {
        "success": True,
        "milestone_key": key,
        "label": label,
        "message": f"恭喜达成里程碑「{label}」！",
        **exp_result,
        "pet": build_pet_response(pet, current_user)
    }


# ==================== 其他API ====================

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
            {"key": "feed_basic", "name": "喂食普通饲料", "exp": FOOD_CONFIG["basic"]["exp"], "category": "基础"},
            {"key": "feed_premium", "name": "喂食高级饲料", "exp": FOOD_CONFIG["premium"]["exp"], "category": "基础"},
            {"key": "feed_luxury", "name": "喂食豪华大餐", "exp": FOOD_CONFIG["luxury"]["exp"], "category": "基础"},
            {"key": "game_memory", "name": "记忆翻牌", "exp": GAME_CONFIG["memory"]["exp_range"], "category": "小游戏"},
            {"key": "game_stock", "name": "迷你炒股", "exp": GAME_CONFIG["stock"]["exp_range"], "category": "小游戏"},
            {"key": "game_adventure", "name": "宠物探险", "exp": GAME_CONFIG["adventure"]["exp_range"], "category": "小游戏"},
            {"key": "game_minesweeper", "name": "扫雷", "exp": GAME_CONFIG["minesweeper"]["exp_range"], "category": "小游戏"},
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
    time_range: TimeRange = Query(TimeRange.DAY, description="时间范围：day/week/month/year/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取宠物经验获取记录（支持时间范围筛选，默认最近一天）"""
    family_id = await get_user_family_id(current_user.id, db)

    # 时间范围筛选
    start_time = get_time_range_filter(time_range)

    # 构建基础查询条件
    base_conditions = [PetExpLog.family_id == family_id]
    if start_time:
        base_conditions.append(PetExpLog.created_at >= start_time)

    # 查询记录总数
    count_result = await db.execute(
        select(func.count()).select_from(PetExpLog).where(*base_conditions)
    )
    total = count_result.scalar()

    # 查询记录列表（按时间倒序），联表查询操作者信息
    from sqlalchemy.orm import aliased
    OperatorUser = aliased(User)

    result = await db.execute(
        select(PetExpLog, OperatorUser.nickname)
        .outerjoin(OperatorUser, PetExpLog.operator_id == OperatorUser.id)
        .where(*base_conditions)
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


# ==================== AI 宠物对话 ====================

class PetChatRequest(BaseModel):
    """宠物对话请求"""
    message: str
    history: list = []


class PetChatResponse(BaseModel):
    """宠物对话响应"""
    reply: str
    emotion: str  # happy, excited, sad, neutral, playful
    action: Optional[str] = None  # 宠物动作描述


@router.post("/chat", response_model=PetChatResponse)
async def chat_with_pet(
    request: PetChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    与宠物对话 - AI 赋予宠物独特的个性和语言风格
    宠物会根据当前状态、进化阶段、心情等做出不同反应
    宠物根据对话内容自主判断是否需要查询主人的财务数据
    """
    from app.services.ai_service import ai_service
    from app.services.ai_tools import build_tool_selection_prompt, execute_tools, TOOL_LIST_TEXT
    
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置")
    
    family_id = await get_user_family_id(current_user.id, db)
    pet = await get_or_create_pet(db, family_id)
    
    # 获取宠物当前状态
    pet_config = PET_EVOLUTION[pet.pet_type]
    pet_age_days = (datetime.now().date() - pet.created_at.date()).days
    
    # 计算心情
    last_fed_date = pet.last_fed_at.date() if pet.last_fed_at else pet.created_at.date()
    last_played_date = pet.last_interaction_at.date() if pet.last_interaction_at else pet.created_at.date()
    days_since_fed = (datetime.now().date() - last_fed_date).days
    days_since_played = (datetime.now().date() - last_played_date).days
    
    current_happiness = pet.happiness
    if days_since_fed > 0:
        current_happiness = max(0, current_happiness - days_since_fed * 10)
    if days_since_played > 0:
        current_happiness = max(0, current_happiness - days_since_played * 5)
    
    mood = "开心" if current_happiness >= 80 else "一般" if current_happiness >= 50 else "低落"
    checkin_streak = pet.checkin_streak
    
    # 构建历史对话
    history = [
        {"role": h.get("role", "user"), "content": h.get("content", "")}
        for h in request.history[-20:]
    ] if request.history else None

    # ===== Phase 1: AI 判断是否需要查询数据 =====
    tool_data = ""
    try:
        tool_prompt = build_tool_selection_prompt(request.message)
        recent_history = (history or [])[-6:]
        tool_decision = await ai_service.chat_json(
            user_prompt=f"用户的问题是：{request.message}",
            system_prompt=tool_prompt,
            history=recent_history if recent_history else None,
            function_key="pet_tool_call",
            prompt_vars={"tool_list_text": TOOL_LIST_TEXT, "message": request.message},
            temperature=0.1,
        )
        logger.info(f"Pet chat tool decision: {tool_decision}")

        if tool_decision and tool_decision.get("needs_data") and tool_decision.get("tools"):
            valid_tools = [t for t in tool_decision["tools"] if isinstance(t, str)][:5]
            if valid_tools:
                # ===== Phase 2: 执行查询 =====
                tool_data = await execute_tools(valid_tools, db, current_user, family_id)
                logger.info(f"Pet chat tools executed: {valid_tools}")
    except Exception as e:
        logger.warning(f"Pet chat tool selection failed (non-fatal): {e}")
    
    # ===== Phase 3: 构建宠物人格 + 查询数据 → 生成回复 =====
    data_section = ""
    if tool_data:
        data_section = f"""

以下是根据主人问题实时查询到的财务数据，请基于这些数据用宠物语气准确回答：
{tool_data}
"""

    system_prompt = f"""你是一只名叫"{pet.name}"的家庭理财宠物，当前形态是"{pet_config['name']}" {pet_config['emoji']}。

你的基本属性：
- 等级：{pet.level}级
- 总经验：{pet.total_exp} EXP
- 年龄：{pet_age_days}天
- 心情：{mood}（心情值 {current_happiness}/100）
- 连续签到：{checkin_streak}天

你的性格特点：
{_get_pet_personality(pet.pet_type, pet.level)}

主人昵称：{current_user.nickname}
{data_section}
与用户对话时：
1. 保持角色一致性，使用第一人称"我"
2. 根据当前心情调整语气（开心时更活泼，低落时略显疲惫）
3. 偶尔提到自己的状态（饿了、想玩游戏、需要休息等）
4. 当有查询数据时，必须基于数据准确回答，用宠物的可爱语气描述
5. 当没有查询数据且主人问具体数字时，可以说"让我查查看"，引导主人再说具体一点
6. 鼓励用户养成良好的理财习惯
7. 回复简短有趣，100字以内
8. 使用emoji表达情感

输出JSON格式：
{{
  "reply": "对话内容",
  "emotion": "happy/excited/sad/neutral/playful之一",
  "action": "动作描述（可选）"
}}
"""
    
    user_prompt = f"用户对你说：{request.message}\n\n请以宠物的身份回复。"
    
    try:
        result_json = await ai_service.chat_json(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            history=history,
            function_key="pet_chat",
            prompt_vars={
                "pet_name": pet.name,
                "pet_config_name": pet_config['name'],
                "pet_emoji": pet_config['emoji'],
                "level": str(pet.level),
                "total_exp": str(pet.total_exp),
                "age_days": str(pet_age_days),
                "mood": mood,
                "happiness": str(current_happiness),
                "checkin_streak": str(checkin_streak),
                "personality_text": _get_pet_personality(pet.pet_type, pet.level),
                "nickname": current_user.nickname,
                "data_section": data_section,
            },
            temperature=0.9
        )
        
        if not result_json:
            return PetChatResponse(
                reply=f"咕咕~ 我是{pet.name}，很高兴和你聊天！{pet_config['emoji']}",
                emotion="happy"
            )
        
        return PetChatResponse(
            reply=result_json.get("reply", "咕咕~"),
            emotion=result_json.get("emotion", "neutral"),
            action=result_json.get("action")
        )
    except Exception as e:
        logger.error(f"Pet chat AI error: {e}", exc_info=True)
        return PetChatResponse(
            reply=f"{pet_config['emoji']} 我有点累了，待会再聊好吗？",
            emotion="neutral"
        )


def _get_pet_personality(pet_type: str, level: int) -> str:
    """根据宠物类型和等级返回个性描述"""
    personalities = {
        "golden_egg": """
        你是一颗神秘的金蛋，充满好奇和期待。
        - 常说"咕噜咕噜"、"我感觉自己快要破壳了"
        - 对一切都很新奇，喜欢学习
        - 天真烂漫，总是问"为什么"
        """,
        "golden_chick": """
        你是一只活泼的小鸡，精力充沛。
        - 常说"叽叽喳喳"、"我要长大！"
        - 活泼好动，喜欢游戏
        - 对数字很敏感，喜欢炫耀自己帮主人存了多少钱
        """,
        "golden_bird": """
        你是一只优雅的金鸟，成熟稳重。
        - 常说"啾~"、"让我看看家里的账本"
        - 专业理性，像个小管家
        - 会给出实用的理财建议
        """,
        "golden_phoenix": """
        你是一只高贵的凤凰，智慧超群。
        - 常说"凤鸣九天"、"财富之道，在于平衡"
        - 充满哲理，语气优雅
        - 深谙投资理财之道
        """,
        "golden_dragon": """
        你是传说中的神龙，威严而慈祥。
        - 常说"龙吟"、"吾护佑汝家财运亨通"
        - 古风文雅，偶尔说文言文
        - 见多识广，能给出深刻见解
        - 但也会展现可爱的一面
        """
    }
    
    base_personality = personalities.get(pet_type, personalities["golden_egg"])
    
    # 高等级的宠物更有智慧
    if level >= 50:
        base_personality += "\n你经验丰富，说话时透露出长者的智慧。"
    elif level >= 30:
        base_personality += "\n你已经很有经验，能给出专业建议。"
    
    return base_personality
