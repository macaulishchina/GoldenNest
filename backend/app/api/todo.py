"""
家庭清单 API - Todo List
支持多清单、任务指派、截止日期、重复任务等功能
"""
import logging
from datetime import datetime, timedelta, timezone
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Integer
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import (
    User, FamilyMember, TodoList, TodoItem,
    TodoPriority, TodoRepeatType
)
from app.services.calendar import calendar_service
from app.services.achievement import AchievementService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/todo", tags=["todo"])


# ==================== Schema ====================

class TodoListCreate(BaseModel):
    name: str
    icon: str = "📋"
    color: str = "#667eea"


class TodoListUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class TodoItemCreate(BaseModel):
    list_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    repeat_type: str = "none"


class TodoItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    repeat_type: Optional[str] = None
    sort_order: Optional[int] = None


class TodoListResponse(BaseModel):
    id: int
    name: str
    icon: str
    color: str
    sort_order: int
    item_count: int
    completed_count: int
    created_by: int
    created_at: datetime


class TodoItemResponse(BaseModel):
    id: int
    list_id: int
    title: str
    description: Optional[str]
    assignee_id: Optional[int]
    assignee_name: Optional[str]
    assignee_avatar_version: Optional[int]
    priority: str
    due_date: Optional[datetime]
    repeat_type: str
    is_completed: bool
    completed_by: Optional[int]
    completed_by_name: Optional[str]
    completed_at: Optional[datetime]
    sort_order: int
    created_by: int
    created_at: datetime


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


async def verify_list_access(list_id: int, family_id: int, db: AsyncSession) -> TodoList:
    """验证清单访问权限"""
    result = await db.execute(
        select(TodoList).where(
            TodoList.id == list_id,
            TodoList.family_id == family_id
        )
    )
    todo_list = result.scalar_one_or_none()
    if not todo_list:
        raise HTTPException(status_code=404, detail="清单不存在")
    return todo_list


# ==================== 清单 API ====================

@router.get("/lists", response_model=List[TodoListResponse])
async def get_lists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭所有清单"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取清单列表及统计
    result = await db.execute(
        select(TodoList)
        .where(TodoList.family_id == family_id)
        .order_by(TodoList.sort_order, TodoList.created_at)
    )
    lists = result.scalars().all()
    
    response = []
    for lst in lists:
        # 统计任务数量
        result = await db.execute(
            select(
                func.count(TodoItem.id),
                func.sum(func.cast(TodoItem.is_completed, Integer))
            ).where(TodoItem.list_id == lst.id)
        )
        counts = result.one()
        item_count = counts[0] or 0
        completed_count = int(counts[1] or 0)
        
        response.append(TodoListResponse(
            id=lst.id,
            name=lst.name,
            icon=lst.icon,
            color=lst.color,
            sort_order=lst.sort_order,
            item_count=item_count,
            completed_count=completed_count,
            created_by=lst.created_by,
            created_at=lst.created_at
        ))
    
    return response


@router.post("/lists", response_model=dict)
async def create_list(
    data: TodoListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新清单"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取最大排序值
    result = await db.execute(
        select(func.max(TodoList.sort_order))
        .where(TodoList.family_id == family_id)
    )
    max_order = result.scalar() or 0
    
    todo_list = TodoList(
        family_id=family_id,
        name=data.name,
        icon=data.icon,
        color=data.color,
        sort_order=max_order + 1,
        created_by=current_user.id
    )
    
    db.add(todo_list)
    await db.commit()
    await db.refresh(todo_list)
    
    return {
        "success": True,
        "message": "清单创建成功",
        "list_id": todo_list.id
    }


@router.put("/lists/{list_id}", response_model=dict)
async def update_list(
    list_id: int,
    data: TodoListUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新清单"""
    family_id = await get_user_family_id(current_user.id, db)
    todo_list = await verify_list_access(list_id, family_id, db)
    
    if data.name is not None:
        todo_list.name = data.name
    if data.icon is not None:
        todo_list.icon = data.icon
    if data.color is not None:
        todo_list.color = data.color
    if data.sort_order is not None:
        todo_list.sort_order = data.sort_order
    
    await db.commit()
    
    return {"success": True, "message": "清单更新成功"}


@router.delete("/lists/{list_id}", response_model=dict)
async def delete_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除清单（及其所有任务）"""
    family_id = await get_user_family_id(current_user.id, db)
    todo_list = await verify_list_access(list_id, family_id, db)
    
    await db.delete(todo_list)
    await db.commit()
    
    return {"success": True, "message": "清单已删除"}


# ==================== 任务 API ====================

@router.get("/lists/{list_id}/items", response_model=List[TodoItemResponse])
async def get_items(
    list_id: int,
    show_completed: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取清单中的任务"""
    family_id = await get_user_family_id(current_user.id, db)
    await verify_list_access(list_id, family_id, db)
    
    query = select(TodoItem).where(TodoItem.list_id == list_id)
    if not show_completed:
        query = query.where(TodoItem.is_completed == False)
    query = query.order_by(TodoItem.is_completed, TodoItem.sort_order, TodoItem.created_at.desc())
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # 获取用户信息用于显示指派人和完成者
    user_ids = set()
    for item in items:
        if item.assignee_id:
            user_ids.add(item.assignee_id)
        if item.completed_by:
            user_ids.add(item.completed_by)
    
    users_map = {}
    if user_ids:
        result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        for user in result.scalars().all():
            users_map[user.id] = user
    
    response = []
    for item in items:
        assignee = users_map.get(item.assignee_id) if item.assignee_id else None
        completer = users_map.get(item.completed_by) if item.completed_by else None
        
        response.append(TodoItemResponse(
            id=item.id,
            list_id=item.list_id,
            title=item.title,
            description=item.description,
            assignee_id=item.assignee_id,
            assignee_name=assignee.nickname if assignee else None,
            assignee_avatar_version=assignee.avatar_version if assignee else None,
            priority=item.priority.value if hasattr(item.priority, 'value') else item.priority,
            due_date=item.due_date,
            repeat_type=item.repeat_type.value if hasattr(item.repeat_type, 'value') else item.repeat_type,
            is_completed=item.is_completed,
            completed_by=item.completed_by,
            completed_by_name=completer.nickname if completer else None,
            completed_at=item.completed_at,
            sort_order=item.sort_order,
            created_by=item.created_by,
            created_at=item.created_at
        ))
    
    return response


@router.post("/items", response_model=dict)
async def create_item(
    data: TodoItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新任务"""
    family_id = await get_user_family_id(current_user.id, db)
    await verify_list_access(data.list_id, family_id, db)
    
    # 验证指派人是否是家庭成员
    if data.assignee_id:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.user_id == data.assignee_id,
                FamilyMember.family_id == family_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="指派的用户不是家庭成员")
    
    # 获取最大排序值
    result = await db.execute(
        select(func.max(TodoItem.sort_order))
        .where(TodoItem.list_id == data.list_id)
    )
    max_order = result.scalar() or 0
    
    item = TodoItem(
        list_id=data.list_id,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_id,
        priority=TodoPriority(data.priority),
        due_date=data.due_date,
        repeat_type=TodoRepeatType(data.repeat_type),
        sort_order=max_order + 1,
        created_by=current_user.id
    )
    
    db.add(item)
    await db.flush()  # 获取 item.id
    
    # 自动创建日历提醒（如果有截止日期）
    if data.due_date:
        # 移除时区信息进行比较
        due_date_naive = data.due_date.replace(tzinfo=None) if data.due_date.tzinfo else data.due_date
        if due_date_naive > datetime.utcnow():
            await calendar_service.create_todo_reminder(
                db=db,
                family_id=family_id,
                todo=item,
                created_by=current_user.id,
                assignee_id=data.assignee_id
            )
    
    await db.commit()
    await db.refresh(item)
    
    return {
        "success": True,
        "message": "任务创建成功",
        "item_id": item.id
    }


@router.put("/items/{item_id}", response_model=dict)
async def update_item(
    item_id: int,
    data: TodoItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新任务"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取任务并验证权限
    result = await db.execute(
        select(TodoItem).join(TodoList).where(
            TodoItem.id == item_id,
            TodoList.family_id == family_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if data.title is not None:
        item.title = data.title
    if data.description is not None:
        item.description = data.description
    if data.assignee_id is not None:
        # 验证指派人
        if data.assignee_id > 0:
            result = await db.execute(
                select(FamilyMember).where(
                    FamilyMember.user_id == data.assignee_id,
                    FamilyMember.family_id == family_id
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="指派的用户不是家庭成员")
            item.assignee_id = data.assignee_id
        else:
            item.assignee_id = None
    if data.priority is not None:
        item.priority = TodoPriority(data.priority)
    if data.due_date is not None:
        item.due_date = data.due_date
    if data.repeat_type is not None:
        item.repeat_type = TodoRepeatType(data.repeat_type)
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    
    # 更新日历提醒（如果标题、截止日期或优先级发生变化）
    if data.title is not None or data.due_date is not None or data.priority is not None:
        await calendar_service.update_todo_reminder(
            db=db,
            family_id=family_id,
            todo=item,
            created_by=current_user.id,
            assignee_id=item.assignee_id
        )
    
    await db.commit()
    
    return {"success": True, "message": "任务更新成功"}


@router.post("/items/{item_id}/complete", response_model=dict)
async def complete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """完成任务"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取任务并验证权限
    result = await db.execute(
        select(TodoItem).join(TodoList).where(
            TodoItem.id == item_id,
            TodoList.family_id == family_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if item.is_completed:
        raise HTTPException(status_code=400, detail="任务已完成")
    
    item.is_completed = True
    item.completed_by = current_user.id
    item.completed_at = datetime.utcnow()
    
    # 如果是重复任务，创建下一个任务
    if item.repeat_type != TodoRepeatType.NONE:
        next_due_date = None
        if item.due_date:
            if item.repeat_type == TodoRepeatType.DAILY:
                next_due_date = item.due_date + timedelta(days=1)
            elif item.repeat_type == TodoRepeatType.WEEKLY:
                next_due_date = item.due_date + timedelta(weeks=1)
            elif item.repeat_type == TodoRepeatType.MONTHLY:
                # 简单处理，加30天
                next_due_date = item.due_date + timedelta(days=30)
        
        new_item = TodoItem(
            list_id=item.list_id,
            title=item.title,
            description=item.description,
            assignee_id=item.assignee_id,
            priority=item.priority,
            due_date=next_due_date,
            repeat_type=item.repeat_type,
            sort_order=item.sort_order,
            created_by=item.created_by
        )
        db.add(new_item)
        await db.flush()  # 获取 new_item.id
        
        # 为新的重复任务创建日历提醒
        if next_due_date:
            # 移除时区信息进行比较
            next_due_naive = next_due_date.replace(tzinfo=None) if next_due_date.tzinfo else next_due_date
            if next_due_naive > datetime.utcnow():
                await calendar_service.create_todo_reminder(
                    db=db,
                    family_id=family_id,
                    todo=new_item,
                    created_by=current_user.id,
                    assignee_id=item.assignee_id
                )
    
    # 删除原任务的日历提醒（任务已完成）
    await calendar_service.delete_todo_reminder(
        db=db,
        family_id=family_id,
        todo_id=item_id
    )
    
    # ========== 成就检测和宠物经验增长 ==========
    try:
        # 检测成就
        achievement_service = AchievementService(db)
        new_achievements = await achievement_service.check_and_unlock(current_user.id)
        
        # 获取宠物并增加经验
        from app.models.models import FamilyPet
        pet_result = await db.execute(
            select(FamilyPet).where(FamilyPet.family_id == family_id)
        )
        pet = pet_result.scalar_one_or_none()
        
        if pet:
            # 根据任务优先级给予不同经验
            priority_value = item.priority.value if hasattr(item.priority, 'value') else item.priority
            exp_map = {
                "high": 15,
                "medium": 10,
                "low": 5
            }
            exp_gained = exp_map.get(priority_value, 10)
            
            # 如果是准时完成（有截止日期且在截止日期前完成），额外奖励
            if item.due_date and item.completed_at and item.completed_at <= item.due_date:
                exp_gained += 5  # 准时完成奖励
            
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
        "message": "任务已完成",
        "completed_by": current_user.nickname
    }


@router.post("/items/{item_id}/uncomplete", response_model=dict)
async def uncomplete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取消完成任务"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取任务并验证权限
    result = await db.execute(
        select(TodoItem).join(TodoList).where(
            TodoItem.id == item_id,
            TodoList.family_id == family_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if not item.is_completed:
        raise HTTPException(status_code=400, detail="任务未完成")
    
    item.is_completed = False
    item.completed_by = None
    item.completed_at = None
    
    # 重新创建日历提醒（如果有截止日期且未过期）
    if item.due_date:
        # 移除时区信息进行比较
        due_date_naive = item.due_date.replace(tzinfo=None) if item.due_date.tzinfo else item.due_date
        if due_date_naive > datetime.utcnow():
            await calendar_service.create_todo_reminder(
                db=db,
                family_id=family_id,
            todo=item,
            created_by=current_user.id,
            assignee_id=item.assignee_id
        )
    
    await db.commit()
    
    return {"success": True, "message": "已取消完成"}


@router.delete("/items/{item_id}", response_model=dict)
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除任务"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取任务并验证权限
    result = await db.execute(
        select(TodoItem).join(TodoList).where(
            TodoItem.id == item_id,
            TodoList.family_id == family_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 删除关联的日历提醒
    await calendar_service.delete_todo_reminder(
        db=db,
        family_id=family_id,
        todo_id=item_id
    )
    
    await db.delete(item)
    await db.commit()
    
    return {"success": True, "message": "任务已删除"}


# ==================== 统计 API ====================

@router.get("/stats", response_model=dict)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取任务统计"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 家庭总任务统计
    result = await db.execute(
        select(
            func.count(TodoItem.id),
            func.sum(func.cast(TodoItem.is_completed, Integer))
        )
        .join(TodoList)
        .where(TodoList.family_id == family_id)
    )
    counts = result.one()
    total_tasks = counts[0] or 0
    completed_tasks = int(counts[1] or 0)
    
    # 当前用户完成的任务数
    result = await db.execute(
        select(func.count(TodoItem.id))
        .join(TodoList)
        .where(
            TodoList.family_id == family_id,
            TodoItem.completed_by == current_user.id
        )
    )
    my_completed = result.scalar() or 0
    
    # 指派给当前用户的未完成任务
    result = await db.execute(
        select(func.count(TodoItem.id))
        .join(TodoList)
        .where(
            TodoList.family_id == family_id,
            TodoItem.assignee_id == current_user.id,
            TodoItem.is_completed == False
        )
    )
    my_pending = result.scalar() or 0
    
    # 今日截止任务
    today = datetime.utcnow().replace(hour=23, minute=59, second=59)
    result = await db.execute(
        select(func.count(TodoItem.id))
        .join(TodoList)
        .where(
            TodoList.family_id == family_id,
            TodoItem.is_completed == False,
            TodoItem.due_date != None,
            func.datetime(TodoItem.due_date) <= today
        )
    )
    due_today = result.scalar() or 0
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": total_tasks - completed_tasks,
        "my_completed": my_completed,
        "my_pending": my_pending,
        "due_today": due_today,
        "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
    }


# ==================== 家庭成员列表 ====================

@router.get("/members", response_model=List[dict])
async def get_family_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭成员列表（用于任务指派）"""
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


# ==================== AI 功能 ====================

class SuggestedTask(BaseModel):
    """AI 建议的任务"""
    title: str
    description: str
    priority: str
    due_days: int
    
    class Config:
        from_attributes = True

class TodoAISuggestionRequest(BaseModel):
    """AI 任务建议请求"""
    context: str  # 用户输入的任务描述或目标


class TodoAISuggestionResponse(BaseModel):
    """AI 任务建议响应"""
    suggested_tasks: List[SuggestedTask]
    reasoning: str
    
    class Config:
        from_attributes = True


class TodoAIPrioritizeRequest(BaseModel):
    """AI 任务优先级分析请求"""
    task_ids: Optional[List[int]] = None  # 如果为空，分析所有未完成任务


class PrioritizedTask(BaseModel):
    """AI 优先级分析的任务"""
    task_id: int
    title: str
    suggested_priority: str
    reasoning: str
    urgency_score: float
    
    class Config:
        from_attributes = True


class TodoAIPrioritizeResponse(BaseModel):
    """AI 任务优先级分析响应"""
    prioritized_tasks: List[PrioritizedTask]
    overall_advice: str
    
    class Config:
        from_attributes = True


@router.post("/ai/suggest", response_model=TodoAISuggestionResponse)
async def ai_suggest_tasks(
    request: TodoAISuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 智能任务建议 - 根据用户输入的目标或描述，生成结构化的任务列表
    例如："我要准备全家的春节旅行" -> 分解为多个具体任务
    """
    from app.services.ai_service import ai_service
    
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置")
    
    system_prompt = """你是一个任务规划专家，擅长将大目标分解为可执行的小任务。

任务分解原则：
1. 每个任务应该具体、可执行
2. 设置合理的优先级（low/medium/high）
3. 建议合理的完成时间（从现在开始的天数）
4. 任务数量通常3-7个为宜

优先级判断：
- high：紧急重要，需立即处理
- medium：重要但不紧急，或紧急但不重要
- low：可以延后处理

输出JSON格式：
{
  "suggested_tasks": [
    {
      "title": "任务标题（简短）",
      "description": "任务详细描述",
      "priority": "low/medium/high",
      "due_days": 3
    }
  ],
  "reasoning": "分解思路简述"
}
"""
    
    user_prompt = f"""请帮我分解以下目标/需求为具体的待办任务：

{request.context}

请给出任务列表和分解理由。"""
    
    try:
        result_json = await ai_service.chat_json(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            function_key="todo_suggest",
            prompt_vars={"context": request.context},
            temperature=0.7
        )
        
        if not result_json:
            raise ValueError("AI 返回了无效的响应")
        
        # 确保返回正确的数据结构
        suggested_tasks_raw = result_json.get("suggested_tasks", [])
        reasoning = result_json.get("reasoning", "")
        
        # 验证数据并转换为 SuggestedTask 对象
        suggested_tasks = []
        if isinstance(suggested_tasks_raw, list):
            for task_dict in suggested_tasks_raw:
                try:
                    task = SuggestedTask(**task_dict)
                    suggested_tasks.append(task)
                except Exception as e:
                    logger.warning(f"Failed to parse task: {task_dict}, error: {e}")
        
        return TodoAISuggestionResponse(
            suggested_tasks=suggested_tasks,
            reasoning=reasoning
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI suggest failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 任务建议失败: {str(e)}")


@router.post("/ai/prioritize", response_model=TodoAIPrioritizeResponse)
async def ai_prioritize_tasks(
    request: TodoAIPrioritizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 智能任务优先级分析 - 分析待办任务，给出优先级建议和执行顺序
    """
    from app.services.ai_service import ai_service
    
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置")
    
    family_id = await get_user_family_id(current_user.id, db)
    
    # 查询该家庭下所有清单ID
    list_id_query = select(TodoList.id).where(TodoList.family_id == family_id)
    result = await db.execute(list_id_query)
    list_ids = [row[0] for row in result.fetchall()]
    if not list_ids:
        raise HTTPException(status_code=404, detail="没有找到家庭清单")

    # 查询待办任务（属于这些清单，未删除、未完成）
    query = select(TodoItem).where(
        TodoItem.list_id.in_(list_ids),
        getattr(TodoItem, "is_deleted", False) == False,
        getattr(TodoItem, "is_completed", False) == False
    )
    if request.task_ids:
        query = query.where(TodoItem.id.in_(request.task_ids))
    result = await db.execute(query)
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(status_code=404, detail="没有找到待办任务")
    
    # 构建任务信息
    task_info = []
    for task in tasks:
        due_info = ""
        if task.due_date:
            days_until_due = (task.due_date - datetime.now()).days
            if days_until_due < 0:
                due_info = f"已逾期 {abs(days_until_due)} 天"
            elif days_until_due == 0:
                due_info = "今天到期"
            else:
                due_info = f"{days_until_due} 天后到期"
        
        task_info.append({
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "current_priority": task.priority,
            "due_info": due_info,
            "repeat": task.repeat_type != "none"
        })
    
    system_prompt = """你是一个时间管理专家，帮助用户合理安排任务优先级。

分析要点：
1. 考虑任务的紧急程度（截止日期）
2. 考虑任务的重要程度（从描述推断）
3. 重复任务通常优先级较高（养成习惯）
4. 已逾期的任务需立即处理

优先级建议：
- high：必须立即处理的任务
- medium：重要且应尽快处理的任务
- low：可以稍后处理的任务

输出JSON格式：
{
  "prioritized_tasks": [
    {
      "task_id": 1,
      "title": "任务标题",
      "suggested_priority": "high",
      "reasoning": "建议理由（30字内）",
      "urgency_score": 95
    }
  ],
  "overall_advice": "整体建议（80字内）"
}

urgency_score: 0-100，数字越大越紧急
"""
    
    user_prompt = f"""请分析以下待办任务，给出优先级建议：

任务列表：
{json.dumps(task_info, ensure_ascii=False, indent=2)}

请按紧急程度排序并给出建议。"""
    
    try:
        import json as json_lib
        result_json = await ai_service.chat_json(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            function_key="todo_prioritize",
            prompt_vars={"task_info": json.dumps(task_info, ensure_ascii=False, indent=2)},
            temperature=0.3
        )
        
        if not result_json:
            raise ValueError("AI 返回了无效的响应")
        
        # 转换为 PrioritizedTask 对象
        prioritized_tasks_raw = result_json.get("prioritized_tasks", [])
        overall_advice = result_json.get("overall_advice", "")
        
        prioritized_tasks = []
        if isinstance(prioritized_tasks_raw, list):
            for task_dict in prioritized_tasks_raw:
                try:
                    task = PrioritizedTask(**task_dict)
                    prioritized_tasks.append(task)
                except Exception as e:
                    logger.warning(f"Failed to parse prioritized task: {task_dict}, error: {e}")
        
        return TodoAIPrioritizeResponse(
            prioritized_tasks=prioritized_tasks,
            overall_advice=overall_advice
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI prioritize failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 优先级分析失败: {str(e)}")
