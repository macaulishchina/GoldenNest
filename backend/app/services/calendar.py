"""
日历服务 - 提供模块联动的自动事件生成功能
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.constants import NotificationConstants
from app.models.models import (
    CalendarEvent, CalendarEventParticipant,
    CalendarEventCategory, CalendarRepeatType,
    Investment, TodoItem, EquityGift
)


class CalendarService:
    """日历服务类"""
    
    @staticmethod
    async def create_investment_reminder(
        db: AsyncSession,
        family_id: int,
        investment: Investment,
        created_by: int
    ) -> Optional[CalendarEvent]:
        """
        创建理财到期提醒事件
        - 在理财产品到期前7天生成提醒
        """
        if not investment.end_date:
            return None
        
        # 检查是否已存在
        existing = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "investment",
                CalendarEvent.source_id == investment.id
            )
        )
        if existing.scalar_one_or_none():
            return None
        
        # 计算提醒时间（提前7天）
        remind_date = investment.end_date - timedelta(days=NotificationConstants.REMINDER_DAYS_BEFORE_DUE)
        if remind_date <= datetime.utcnow():
            # 如果已经过了提醒时间，则在当天提醒
            remind_date = datetime.utcnow()
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"💰 理财到期：{investment.name}",
            description=f"理财产品「{investment.name}」将于 {investment.end_date.strftime('%Y-%m-%d')} 到期\n"
                       f"本金：¥{investment.principal:,.2f}\n"
                       f"预期年化收益率：{investment.expected_rate * 100:.2f}%",
            category=CalendarEventCategory.FINANCE,
            start_time=remind_date,
            is_all_day=True,
            repeat_type=CalendarRepeatType.NONE,
            color="#f59e0b",
            is_system=True,
            source_type="investment",
            source_id=investment.id,
            created_by=created_by
        )
        
        db.add(event)
        return event
    
    @staticmethod
    async def update_investment_reminder(
        db: AsyncSession,
        family_id: int,
        investment: Investment,
        created_by: int
    ) -> Optional[CalendarEvent]:
        """
        更新理财到期提醒事件
        - 删除旧事件，创建新事件
        """
        # 删除旧事件
        await db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "investment",
                CalendarEvent.source_id == investment.id
            )
        )
        
        # 如果没有到期日或已不活跃，不创建新事件
        if not investment.end_date or not investment.is_active:
            return None
        
        # 创建新提醒
        remind_date = investment.end_date - timedelta(days=NotificationConstants.REMINDER_DAYS_BEFORE_DUE)
        if remind_date <= datetime.utcnow():
            remind_date = investment.end_date
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"💰 理财到期：{investment.name}",
            description=f"理财产品「{investment.name}」将于 {investment.end_date.strftime('%Y-%m-%d')} 到期\n"
                       f"本金：¥{investment.principal:,.2f}\n"
                       f"预期年化收益率：{investment.expected_rate * 100:.2f}%",
            category=CalendarEventCategory.FINANCE,
            start_time=remind_date,
            is_all_day=True,
            repeat_type=CalendarRepeatType.NONE,
            color="#f59e0b",
            is_system=True,
            source_type="investment",
            source_id=investment.id,
            created_by=created_by
        )
        
        db.add(event)
        return event
    
    @staticmethod
    async def delete_investment_reminder(
        db: AsyncSession,
        family_id: int,
        investment_id: int
    ):
        """删除理财到期提醒事件"""
        await db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "investment",
                CalendarEvent.source_id == investment_id
            )
        )
    
    @staticmethod
    async def create_todo_reminder(
        db: AsyncSession,
        family_id: int,
        todo: TodoItem,
        created_by: int,
        assignee_id: Optional[int] = None
    ) -> Optional[CalendarEvent]:
        """
        创建待办截止提醒事件
        - 在截止日当天提醒
        """
        if not todo.due_date:
            return None
        
        # 检查是否已存在
        existing = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "todo",
                CalendarEvent.source_id == todo.id
            )
        )
        if existing.scalar_one_or_none():
            return None
        
        # 根据优先级设置颜色
        priority_colors = {
            "high": "#ef4444",    # 红色
            "medium": "#f59e0b",  # 橙色
            "low": "#10b981"      # 绿色
        }
        priority_value = todo.priority.value if hasattr(todo.priority, 'value') else str(todo.priority)
        color = priority_colors.get(priority_value, "#667eea")
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"📋 待办截止：{todo.title}",
            description=todo.description or f"任务「{todo.title}」截止日期",
            category=CalendarEventCategory.SYSTEM,
            start_time=todo.due_date,
            is_all_day=False,
            repeat_type=CalendarRepeatType.NONE,
            color=color,
            is_system=True,
            source_type="todo",
            source_id=todo.id,
            created_by=created_by
        )
        
        db.add(event)
        await db.flush()  # 获取 event.id
        
        # 如果有指派人，添加为参与者
        if assignee_id:
            participant = CalendarEventParticipant(
                event_id=event.id,
                user_id=assignee_id
            )
            db.add(participant)
        
        return event
    
    @staticmethod
    async def update_todo_reminder(
        db: AsyncSession,
        family_id: int,
        todo: TodoItem,
        created_by: int,
        assignee_id: Optional[int] = None
    ) -> Optional[CalendarEvent]:
        """
        更新待办截止提醒事件
        - 如果任务已完成，删除提醒
        - 如果截止日期变更，更新事件
        """
        # 先删除旧事件
        await db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "todo",
                CalendarEvent.source_id == todo.id
            )
        )
        
        # 如果已完成或无截止日期，不创建新事件
        if todo.is_completed or not todo.due_date:
            return None
        
        # 如果截止日期已过，不创建提醒
        if todo.due_date < datetime.utcnow():
            return None
        
        # 根据优先级设置颜色
        priority_colors = {
            "high": "#ef4444",
            "medium": "#f59e0b",
            "low": "#10b981"
        }
        priority_value = todo.priority.value if hasattr(todo.priority, 'value') else str(todo.priority)
        color = priority_colors.get(priority_value, "#667eea")
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"📋 待办截止：{todo.title}",
            description=todo.description or f"任务「{todo.title}」截止日期",
            category=CalendarEventCategory.SYSTEM,
            start_time=todo.due_date,
            is_all_day=False,
            repeat_type=CalendarRepeatType.NONE,
            color=color,
            is_system=True,
            source_type="todo",
            source_id=todo.id,
            created_by=created_by
        )
        
        db.add(event)
        await db.flush()
        
        if assignee_id:
            participant = CalendarEventParticipant(
                event_id=event.id,
                user_id=assignee_id
            )
            db.add(participant)
        
        return event
    
    @staticmethod
    async def delete_todo_reminder(
        db: AsyncSession,
        family_id: int,
        todo_id: int
    ):
        """删除待办截止提醒事件"""
        await db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "todo",
                CalendarEvent.source_id == todo_id
            )
        )
    
    @staticmethod
    async def create_gift_reminder(
        db: AsyncSession,
        family_id: int,
        gift: EquityGift,
        to_user_id: int,
        created_by: int
    ) -> Optional[CalendarEvent]:
        """
        创建股权赠与提醒事件
        - 在赠与创建时生成提醒，通知接收人
        """
        # 检查是否已存在
        existing = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "gift",
                CalendarEvent.source_id == gift.id
            )
        )
        if existing.scalar_one_or_none():
            return None
        
        event = CalendarEvent(
            family_id=family_id,
            title=f"🎁 股权赠与待接收",
            description=f"您收到一笔股权赠与\n"
                       f"赠与比例：{gift.amount * 100:.2f}%\n"
                       f"祝福语：{gift.message or '无'}",
            category=CalendarEventCategory.SYSTEM,
            start_time=gift.created_at,
            is_all_day=True,
            repeat_type=CalendarRepeatType.NONE,
            color="#8b5cf6",
            is_system=True,
            source_type="gift",
            source_id=gift.id,
            created_by=created_by
        )
        
        db.add(event)
        await db.flush()
        
        # 添加接收人为参与者
        participant = CalendarEventParticipant(
            event_id=event.id,
            user_id=to_user_id
        )
        db.add(participant)
        
        return event
    
    @staticmethod
    async def update_gift_status(
        db: AsyncSession,
        family_id: int,
        gift_id: int,
        is_accepted: bool
    ):
        """
        更新股权赠与状态
        - 如果已接收或拒绝，更新事件标题
        """
        result = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "gift",
                CalendarEvent.source_id == gift_id
            )
        )
        event = result.scalar_one_or_none()
        
        if event:
            if is_accepted:
                event.title = "🎁 股权赠与已接收"
                event.color = "#10b981"  # 绿色
            else:
                event.title = "🎁 股权赠与已拒绝"
                event.color = "#6b7280"  # 灰色
    
    @staticmethod
    async def delete_gift_reminder(
        db: AsyncSession,
        family_id: int,
        gift_id: int
    ):
        """删除股权赠与提醒事件"""
        await db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.family_id == family_id,
                CalendarEvent.source_type == "gift",
                CalendarEvent.source_id == gift_id
            )
        )
    
    @staticmethod
    async def create_birthday_reminder(
        db: AsyncSession,
        family_id: int,
        title: str,
        date: datetime,
        description: Optional[str] = None,
        created_by: int = 0
    ) -> CalendarEvent:
        """
        创建生日/纪念日提醒事件
        - 自动设置为每年重复
        """
        event = CalendarEvent(
            family_id=family_id,
            title=f"🎂 {title}",
            description=description or f"今天是{title}",
            category=CalendarEventCategory.BIRTHDAY,
            start_time=date,
            is_all_day=True,
            repeat_type=CalendarRepeatType.YEARLY,
            color="#ec4899",
            is_system=False,
            created_by=created_by
        )
        
        db.add(event)
        return event


# 导出单例
calendar_service = CalendarService()
