"""
共享日历 API - Calendar
支持多视图、重复事件、模块联动等功能
"""
from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from dateutil.relativedelta import relativedelta

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import (
    User, FamilyMember, CalendarEvent, CalendarEventParticipant,
    CalendarEventCategory, CalendarRepeatType,
    Investment, TodoItem, TodoList, EquityGift, EquityGiftStatus,
    FamilyPet
)
from app.services.achievement import AchievementService

router = APIRouter(prefix="/calendar", tags=["calendar"])


# ==================== Schema ====================

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "family"
    start_time: datetime
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    repeat_type: str = "none"
    repeat_until: Optional[datetime] = None
    color: str = "#667eea"
    location: Optional[str] = None
    participant_ids: List[int] = []


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    repeat_type: Optional[str] = None
    repeat_until: Optional[datetime] = None
    color: Optional[str] = None
    location: Optional[str] = None
    participant_ids: Optional[List[int]] = None


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: str
    start_time: datetime
    end_time: Optional[datetime]
    is_all_day: bool
    repeat_type: str
    repeat_until: Optional[datetime]
    color: str
    location: Optional[str]
    is_system: bool
    source_type: Optional[str]
    source_id: Optional[int]
    created_by: int
    created_by_name: Optional[str]
    created_at: datetime
    participants: List[dict]


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


async def get_family_members_map(family_id: int, db: AsyncSession) -> dict:
    """获取家庭成员映射表"""
    result = await db.execute(
        select(User, FamilyMember)
        .join(FamilyMember, User.id == FamilyMember.user_id)
        .where(FamilyMember.family_id == family_id)
    )
    members = {}
    for user, member in result.fetchall():
        members[user.id] = {
            "id": user.id,
            "nickname": user.nickname,
            "avatar_version": user.avatar_version or 0
        }
    return members


def expand_recurring_events(
    events: List[CalendarEvent], 
    start_date: datetime, 
    end_date: datetime,
    members_map: dict
) -> List[dict]:
    """展开重复事件到指定日期范围"""
    expanded = []
    
    for event in events:
        # 获取参与者信息
        participants = []
        if hasattr(event, 'participants'):
            for p in event.participants:
                if p.user_id in members_map:
                    participants.append(members_map[p.user_id])
        
        # 创建者信息
        creator_name = members_map.get(event.created_by, {}).get("nickname", "未知")
        
        base_event = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category.value if hasattr(event.category, 'value') else event.category,
            "is_all_day": event.is_all_day,
            "repeat_type": event.repeat_type.value if hasattr(event.repeat_type, 'value') else event.repeat_type,
            "repeat_until": event.repeat_until,
            "color": event.color,
            "location": event.location,
            "is_system": event.is_system,
            "source_type": event.source_type,
            "source_id": event.source_id,
            "created_by": event.created_by,
            "created_by_name": creator_name,
            "created_at": event.created_at,
            "participants": participants
        }
        
        # 非重复事件
        if event.repeat_type == CalendarRepeatType.NONE:
            base_event["start_time"] = event.start_time
            base_event["end_time"] = event.end_time
            expanded.append(base_event)
            continue
        
        # 重复事件 - 展开到指定日期范围
        current_start = event.start_time
        event_duration = (event.end_time - event.start_time) if event.end_time else timedelta(hours=1)
        repeat_end = event.repeat_until or end_date
        
        while current_start <= end_date and current_start <= repeat_end:
            if current_start >= start_date:
                instance = base_event.copy()
                instance["start_time"] = current_start
                instance["end_time"] = current_start + event_duration if event.end_time else None
                instance["is_recurring_instance"] = True
                instance["original_id"] = event.id
                expanded.append(instance)
            
            # 计算下一个重复时间
            if event.repeat_type == CalendarRepeatType.DAILY:
                current_start += timedelta(days=1)
            elif event.repeat_type == CalendarRepeatType.WEEKLY:
                current_start += timedelta(weeks=1)
            elif event.repeat_type == CalendarRepeatType.MONTHLY:
                current_start += relativedelta(months=1)
            elif event.repeat_type == CalendarRepeatType.YEARLY:
                current_start += relativedelta(years=1)
            else:
                break
    
    return expanded


# ==================== 事件 CRUD API ====================

@router.get("/events", response_model=List[dict])
async def get_events(
    start: datetime = Query(..., description="开始日期"),
    end: datetime = Query(..., description="结束日期"),
    category: Optional[str] = Query(None, description="事件分类筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取指定日期范围内的日历事件"""
    family_id = await get_user_family_id(current_user.id, db)
    members_map = await get_family_members_map(family_id, db)
    
    # 构建查询条件
    query = select(CalendarEvent).options(
        selectinload(CalendarEvent.participants)
    ).where(
        CalendarEvent.family_id == family_id
    )
    
    # 筛选分类
    if category:
        query = query.where(CalendarEvent.category == CalendarEventCategory(category))
    
    # 查询事件（包括在范围内开始的事件和重复事件）
    query = query.where(
        or_(
            # 非重复事件在范围内
            and_(
                CalendarEvent.repeat_type == CalendarRepeatType.NONE,
                CalendarEvent.start_time >= start,
                CalendarEvent.start_time <= end
            ),
            # 重复事件开始于范围之前
            and_(
                CalendarEvent.repeat_type != CalendarRepeatType.NONE,
                CalendarEvent.start_time <= end
            )
        )
    )
    
    result = await db.execute(query.order_by(CalendarEvent.start_time))
    events = result.scalars().all()
    
    # 展开重复事件
    expanded_events = expand_recurring_events(events, start, end, members_map)
    
    # 按开始时间排序
    expanded_events.sort(key=lambda x: x["start_time"])
    
    return expanded_events


@router.post("/events", response_model=dict)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建日历事件"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证参与者都是家庭成员
    if data.participant_ids:
        for uid in data.participant_ids:
            result = await db.execute(
                select(FamilyMember).where(
                    FamilyMember.user_id == uid,
                    FamilyMember.family_id == family_id
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"用户 {uid} 不是家庭成员")
    
    # 创建事件
    event = CalendarEvent(
        family_id=family_id,
        title=data.title,
        description=data.description,
        category=CalendarEventCategory(data.category),
        start_time=data.start_time,
        end_time=data.end_time,
        is_all_day=data.is_all_day,
        repeat_type=CalendarRepeatType(data.repeat_type),
        repeat_until=data.repeat_until,
        color=data.color,
        location=data.location,
        is_system=False,
        created_by=current_user.id
    )
    
    db.add(event)
    await db.flush()  # 获取ID
    
    # 添加参与者
    for uid in data.participant_ids:
        participant = CalendarEventParticipant(
            event_id=event.id,
            user_id=uid
        )
        db.add(participant)
    
    # ========== 成就检测和宠物经验增长 ==========
    try:
        # 检测成就
        achievement_service = AchievementService(db)
        new_achievements = await achievement_service.check_and_unlock(current_user.id)
        
        # 获取宠物并增加经验
        pet_result = await db.execute(
            select(FamilyPet).where(FamilyPet.family_id == family_id)
        )
        pet = pet_result.scalar_one_or_none()
        
        if pet:
            # 根据事件类型给予不同经验
            category_exp_map = {
                "family": 15,      # 家庭活动
                "birthday": 20,    # 生日/纪念日
                "personal": 8,     # 个人日程
                "finance": 10,     # 财务提醒
            }
            exp_gained = category_exp_map.get(data.category, 10)
            
            # 如果是重复事件，额外奖励
            if data.repeat_type != "none":
                exp_gained += 5
            
            # 如果有参与者，额外奖励（协作活动）
            if len(data.participant_ids) > 0:
                exp_gained += 2 * len(data.participant_ids)
            
            pet.experience += exp_gained
            
            # 检查升级
            while pet.experience >= pet.level * 100:
                pet.experience -= pet.level * 100
                pet.level += 1
    except Exception:
        # 成就检测失败不影响主流程
        pass
    
    await db.commit()
    
    return {
        "success": True,
        "message": "事件创建成功",
        "event_id": event.id
    }


@router.put("/events/{event_id}", response_model=dict)
async def update_event(
    event_id: int,
    data: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新日历事件"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取事件
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.family_id == family_id
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    # 系统事件不允许修改
    if event.is_system:
        raise HTTPException(status_code=400, detail="系统事件不允许修改")
    
    # 更新字段
    if data.title is not None:
        event.title = data.title
    if data.description is not None:
        event.description = data.description
    if data.category is not None:
        event.category = CalendarEventCategory(data.category)
    if data.start_time is not None:
        event.start_time = data.start_time
    if data.end_time is not None:
        event.end_time = data.end_time
    if data.is_all_day is not None:
        event.is_all_day = data.is_all_day
    if data.repeat_type is not None:
        event.repeat_type = CalendarRepeatType(data.repeat_type)
    if data.repeat_until is not None:
        event.repeat_until = data.repeat_until
    if data.color is not None:
        event.color = data.color
    if data.location is not None:
        event.location = data.location
    
    # 更新参与者
    if data.participant_ids is not None:
        # 删除现有参与者
        await db.execute(
            delete(CalendarEventParticipant).where(
                CalendarEventParticipant.event_id == event_id
            )
        )
        # 添加新参与者
        for uid in data.participant_ids:
            result = await db.execute(
                select(FamilyMember).where(
                    FamilyMember.user_id == uid,
                    FamilyMember.family_id == family_id
                )
            )
            if result.scalar_one_or_none():
                participant = CalendarEventParticipant(
                    event_id=event_id,
                    user_id=uid
                )
                db.add(participant)
    
    await db.commit()
    
    return {"success": True, "message": "事件更新成功"}


@router.delete("/events/{event_id}", response_model=dict)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除日历事件"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取事件
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.family_id == family_id
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    # 系统事件不允许删除
    if event.is_system:
        raise HTTPException(status_code=400, detail="系统事件不允许删除")
    
    await db.delete(event)
    await db.commit()
    
    return {"success": True, "message": "事件已删除"}


# ==================== 即将到来的事件 ====================

@router.get("/upcoming", response_model=List[dict])
async def get_upcoming_events(
    days: int = Query(7, description="未来多少天"),
    limit: int = Query(10, description="最大返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取即将到来的事件"""
    family_id = await get_user_family_id(current_user.id, db)
    members_map = await get_family_members_map(family_id, db)
    
    now = datetime.utcnow()
    end_date = now + timedelta(days=days)
    
    # 查询事件
    result = await db.execute(
        select(CalendarEvent).options(
            selectinload(CalendarEvent.participants)
        ).where(
            CalendarEvent.family_id == family_id,
            or_(
                # 非重复事件
                and_(
                    CalendarEvent.repeat_type == CalendarRepeatType.NONE,
                    CalendarEvent.start_time >= now,
                    CalendarEvent.start_time <= end_date
                ),
                # 重复事件
                CalendarEvent.repeat_type != CalendarRepeatType.NONE
            )
        ).order_by(CalendarEvent.start_time)
    )
    events = result.scalars().all()
    
    # 展开重复事件
    expanded = expand_recurring_events(events, now, end_date, members_map)
    
    # 只返回未来的事件
    future_events = [e for e in expanded if e["start_time"] >= now]
    future_events.sort(key=lambda x: x["start_time"])
    
    return future_events[:limit]


# ==================== 模块联动 - 同步系统事件 ====================

@router.post("/sync", response_model=dict)
async def sync_system_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """同步系统事件（理财到期、待办截止等）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    synced_count = 0
    
    # 1. 同步理财产品到期提醒
    result = await db.execute(
        select(Investment).where(
            Investment.family_id == family_id,
            Investment.is_active == True,
            Investment.end_date != None
        )
    )
    investments = result.scalars().all()
    
    for inv in investments:
        # 检查是否已存在
        existing = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "investment",
                CalendarEvent.source_id == inv.id
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        # 创建到期提醒（提前7天）
        remind_date = inv.end_date - timedelta(days=7)
        if remind_date > datetime.utcnow():
            event = CalendarEvent(
                family_id=family_id,
                title=f"💰 理财到期提醒：{inv.name}",
                description=f"理财产品「{inv.name}」将于 {inv.end_date.strftime('%Y-%m-%d')} 到期，本金 ¥{inv.principal:,.2f}",
                category=CalendarEventCategory.FINANCE,
                start_time=remind_date,
                is_all_day=True,
                repeat_type=CalendarRepeatType.NONE,
                color="#f59e0b",
                is_system=True,
                source_type="investment",
                source_id=inv.id,
                created_by=current_user.id
            )
            db.add(event)
            synced_count += 1
    
    # 2. 同步待办任务截止提醒
    result = await db.execute(
        select(TodoItem).join(TodoList).where(
            TodoList.family_id == family_id,
            TodoItem.is_completed == False,
            TodoItem.due_date != None,
            TodoItem.due_date >= datetime.utcnow()
        )
    )
    todos = result.scalars().all()
    
    for todo in todos:
        # 检查是否已存在
        existing = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "todo",
                CalendarEvent.source_id == todo.id
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"📋 待办截止：{todo.title}",
            description=todo.description,
            category=CalendarEventCategory.SYSTEM,
            start_time=todo.due_date,
            is_all_day=False,
            repeat_type=CalendarRepeatType.NONE,
            color="#ef4444",
            is_system=True,
            source_type="todo",
            source_id=todo.id,
            created_by=current_user.id
        )
        db.add(event)
        synced_count += 1
    
    # 3. 同步股权赠与待处理提醒
    result = await db.execute(
        select(EquityGift).where(
            EquityGift.family_id == family_id,
            EquityGift.status == EquityGiftStatus.PENDING
        )
    )
    gifts = result.scalars().all()
    
    for gift in gifts:
        # 检查是否已存在
        existing = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "gift",
                CalendarEvent.source_id == gift.id
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"🎁 股权赠与待处理",
            description=f"您收到一笔股权赠与，赠与比例 {gift.amount * 100:.2f}%",
            category=CalendarEventCategory.SYSTEM,
            start_time=gift.created_at,
            is_all_day=True,
            repeat_type=CalendarRepeatType.NONE,
            color="#8b5cf6",
            is_system=True,
            source_type="gift",
            source_id=gift.id,
            created_by=current_user.id
        )
        db.add(event)
        synced_count += 1
    
    # ========== 成就检测和宠物经验增长 ==========
    if synced_count > 0:
        try:
            # 检测成就（传递同步次数上下文）
            achievement_service = AchievementService(db)
            new_achievements = await achievement_service.check_and_unlock(
                current_user.id, 
                context={"sync_count": synced_count}
            )
            
            # 获取宠物并增加经验
            pet_result = await db.execute(
                select(FamilyPet).where(FamilyPet.family_id == family_id)
            )
            pet = pet_result.scalar_one_or_none()
            
            if pet:
                # 同步事件给予固定经验 + 同步数量奖励
                exp_gained = 5 + (synced_count * 2)
                pet.experience += exp_gained
                
                # 检查升级
                while pet.experience >= pet.level * 100:
                    pet.experience -= pet.level * 100
                    pet.level += 1
        except Exception:
            # 成就检测失败不影响主流程
            pass
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"同步完成，新增 {synced_count} 个系统事件",
        "synced_count": synced_count
    }


# ==================== 分类颜色配置 ====================

@router.get("/categories", response_model=List[dict])
async def get_categories():
    """获取事件分类配置"""
    return [
        {"value": "family", "label": "家庭活动", "color": "#667eea", "icon": "🏠"},
        {"value": "personal", "label": "个人日程", "color": "#10b981", "icon": "👤"},
        {"value": "birthday", "label": "生日纪念日", "color": "#ec4899", "icon": "🎂"},
        {"value": "finance", "label": "财务提醒", "color": "#f59e0b", "icon": "💰"},
        {"value": "system", "label": "系统提醒", "color": "#6b7280", "icon": "🔔"},
    ]


# ==================== 家庭成员列表 ====================

@router.get("/members", response_model=List[dict])
async def get_family_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭成员列表（用于选择参与者）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(User, FamilyMember)
        .join(FamilyMember, User.id == FamilyMember.user_id)
        .where(FamilyMember.family_id == family_id)
    )
    
    members = []
    for user, member in result.fetchall():
        members.append({
            "id": user.id,
            "nickname": user.nickname,
            "avatar_version": user.avatar_version or 0,
            "role": member.role
        })
    
    return members
