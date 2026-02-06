"""
小金库 (Golden Nest) - 通知服务

支持多种通知渠道：
- 企业微信 Webhook（当前实现）
- 预留：邮件、Telegram、钉钉等

企业微信机器人文档：
https://developer.work.weixin.qq.com/document/path/91770
"""
import logging
import httpx
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus, User, Family, EquityGift


# ==================== 外网地址上下文 ====================

# 使用 ContextVar 在请求上下文中存储外网地址
_external_base_url: ContextVar[Optional[str]] = ContextVar("external_base_url", default=None)


def set_external_base_url(url: str) -> None:
    """设置外网基础 URL（由中间件在请求开始时调用）"""
    _external_base_url.set(url)


def get_external_base_url() -> Optional[str]:
    """获取外网基础 URL"""
    return _external_base_url.get()


def detect_external_url_from_headers(
    host: Optional[str] = None,
    forwarded_host: Optional[str] = None,
    forwarded_proto: Optional[str] = None,
    x_original_host: Optional[str] = None,
    origin: Optional[str] = None
) -> Optional[str]:
    """
    从请求头中检测外网地址
    
    支持的请求头（按优先级）：
    1. Origin - 浏览器自动发送的源地址
    2. X-Forwarded-Host + X-Forwarded-Proto - 常见反向代理头
    3. X-Original-Host - 某些代理使用
    4. Host - 直接访问时使用
    
    Returns:
        检测到的外网 URL，如 https://example.com
    """
    # 优先使用 Origin（最可靠）
    if origin and origin.startswith("http"):
        return origin.rstrip("/")
    
    # 使用反向代理头
    detected_host = forwarded_host or x_original_host or host
    if detected_host:
        # 移除端口号中可能的本地端口
        if ":" in detected_host:
            host_part, port = detected_host.rsplit(":", 1)
            # 如果是标准端口或非本地端口，保留
            if port not in ("80", "443"):
                detected_host = f"{host_part}:{port}"
            else:
                detected_host = host_part
        
        # 确定协议
        proto = forwarded_proto or "https"
        return f"{proto}://{detected_host}"
    
    return None


# ==================== 通知类型枚举 ====================

class NotificationType(str, Enum):
    """通知类型"""
    # 审批相关
    APPROVAL_CREATED = "approval_created"        # 新申请创建
    APPROVAL_APPROVED = "approval_approved"      # 申请被同意
    APPROVAL_REJECTED = "approval_rejected"      # 申请被拒绝
    APPROVAL_COMPLETED = "approval_completed"    # 申请最终通过（全员同意后执行）
    APPROVAL_CANCELLED = "approval_cancelled"    # 申请被取消
    APPROVAL_REMINDER = "approval_reminder"      # 催促审核提醒
    
    # 股权赠送相关
    GIFT_SENT = "gift_sent"                      # 收到股权赠送
    GIFT_ACCEPTED = "gift_accepted"              # 赠送被接受
    GIFT_REJECTED = "gift_rejected"              # 赠送被拒绝
    GIFT_CANCELLED = "gift_cancelled"            # 赠送被取消
    
    # 其他通知类型（预留扩展）
    MEMBER_JOINED = "member_joined"              # 新成员加入
    MEMBER_REMOVED = "member_removed"            # 成员被移除
    INVESTMENT_MATURED = "investment_matured"    # 理财到期提醒
    PET_EVOLVED = "pet_evolved"                  # 宠物进化


# ==================== 通知数据模型 ====================

@dataclass
class NotificationContext:
    """通知上下文数据"""
    notification_type: NotificationType
    family_id: int
    family_name: str
    title: str
    content: str
    amount: Optional[float] = None
    requester_name: Optional[str] = None   # 发送者/申请人
    approver_name: Optional[str] = None    # 接收者/审批人
    request_type: Optional[str] = None
    request_id: Optional[int] = None       # 审批请求 ID，用于生成详情链接
    gift_id: Optional[int] = None          # 股权赠送 ID，用于生成详情链接
    base_url: Optional[str] = None         # 外网基础 URL
    extra_data: Optional[Dict[str, Any]] = None
    
    def get_approval_url(self) -> Optional[str]:
        """获取审批详情页面 URL"""
        if self.base_url and self.request_id:
            # 前端路由：/approvals?id=xxx 或 /approvals#id=xxx
            return f"{self.base_url}/approvals?highlight={self.request_id}"
        return None
    
    def get_gift_url(self) -> Optional[str]:
        """获取股权赠送页面 URL"""
        if self.base_url:
            # 前端路由：/gift 或 /gift?id=xxx
            if self.gift_id:
                return f"{self.base_url}/gift?highlight={self.gift_id}"
            return f"{self.base_url}/gift"
        return None


# ==================== 通知渠道抽象基类 ====================

class NotificationChannel(ABC):
    """通知渠道抽象基类"""
    
    @abstractmethod
    async def send(self, context: NotificationContext, config: Dict[str, Any]) -> bool:
        """
        发送通知
        
        Args:
            context: 通知上下文
            config: 渠道配置（如 webhook_url）
            
        Returns:
            是否发送成功
        """
        pass
    
    @abstractmethod
    def is_configured(self, config: Dict[str, Any]) -> bool:
        """检查渠道是否已配置"""
        pass


# ==================== 企业微信通知渠道 ====================

class WeChatWorkChannel(NotificationChannel):
    """企业微信机器人通知渠道"""
    
    # 申请类型中文映射
    REQUEST_TYPE_NAMES = {
        ApprovalRequestType.DEPOSIT: "💰 资金注入",
        ApprovalRequestType.EXPENSE: "💸 支出申请",
        ApprovalRequestType.INVESTMENT_CREATE: "📈 创建理财",
        ApprovalRequestType.INVESTMENT_UPDATE: "📊 更新理财",
        ApprovalRequestType.INVESTMENT_INCOME: "💵 理财收益",
        ApprovalRequestType.MEMBER_JOIN: "👋 成员加入",
        ApprovalRequestType.MEMBER_REMOVE: "👤 成员移除",
    }
    
    # 通知类型对应的状态标签
    STATUS_LABELS = {
        NotificationType.APPROVAL_CREATED: "🆕 新申请",
        NotificationType.APPROVAL_APPROVED: "✅ 已同意",
        NotificationType.APPROVAL_REJECTED: "❌ 已拒绝",
        NotificationType.APPROVAL_COMPLETED: "🎉 已完成",
        NotificationType.APPROVAL_CANCELLED: "🚫 已取消",
        NotificationType.APPROVAL_REMINDER: "⏰ 催促审核",
        # 股权赠送
        NotificationType.GIFT_SENT: "🎁 股权赠送",
        NotificationType.GIFT_ACCEPTED: "✅ 赠送已接受",
        NotificationType.GIFT_REJECTED: "❌ 赠送被拒绝",
        NotificationType.GIFT_CANCELLED: "🚫 赠送已取消",
        # 宠物
        NotificationType.PET_EVOLVED: "🎊 宠物进化",
    }
    
    def is_configured(self, config: Dict[str, Any]) -> bool:
        """检查企业微信 Webhook 是否已配置"""
        webhook_url = config.get("wechat_work_webhook_url")
        return bool(webhook_url and webhook_url.startswith("https://qyapi.weixin.qq.com/"))
    
    async def send(self, context: NotificationContext, config: Dict[str, Any]) -> bool:
        """
        发送企业微信机器人消息
        
        使用 Markdown 格式发送富文本消息
        """
        webhook_url = config.get("wechat_work_webhook_url")
        if not webhook_url:
            logging.debug("WeChatWork webhook URL not configured, skipping notification")
            return False
        
        # 构建 Markdown 消息内容
        markdown_content = self._build_markdown_message(context)
        
        # 构建请求体
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if result.get("errcode") == 0:
                    logging.info(f"WeChatWork notification sent successfully: {context.notification_type}")
                    return True
                else:
                    logging.warning(f"WeChatWork notification failed: {result}")
                    return False
                    
        except httpx.HTTPError as e:
            logging.error(f"WeChatWork notification HTTP error: {e}")
            return False
        except Exception as e:
            logging.error(f"WeChatWork notification error: {e}")
            return False
    
    def _build_markdown_message(self, context: NotificationContext) -> str:
        """构建企业微信 Markdown 格式消息"""
        # 判断是否为股权赠送通知
        gift_types = {
            NotificationType.GIFT_SENT,
            NotificationType.GIFT_ACCEPTED,
            NotificationType.GIFT_REJECTED,
            NotificationType.GIFT_CANCELLED,
        }
        
        if context.notification_type in gift_types:
            return self._build_gift_markdown(context)
        else:
            return self._build_approval_markdown(context)
    
    def _build_gift_markdown(self, context: NotificationContext) -> str:
        """构建股权赠送通知的 Markdown 消息"""
        status_label = self.STATUS_LABELS.get(context.notification_type, "🎁 股权赠送")
        amount_percent = context.extra_data.get("amount_percent", 0) if context.extra_data else 0
        
        # 基础消息头
        lines = [
            f"### {status_label}",
            f"**{context.title}**",
            "",
        ]
        
        # 家庭信息
        lines.append(f"> 家庭：{context.family_name}")
        
        # 赠送比例（高亮显示）
        lines.append(f"> 比例：<font color=\"warning\">{amount_percent:.2f}%</font>")
        
        # 根据通知类型显示不同的人员信息
        if context.notification_type == NotificationType.GIFT_SENT:
            # 收到赠送：显示发送者
            lines.append(f"> 赠送人：<font color=\"info\">{context.requester_name}</font>")
            lines.append(f"> 接收人：{context.approver_name}")
        elif context.notification_type == NotificationType.GIFT_ACCEPTED:
            # 赠送被接受：显示接受者
            lines.append(f"> 赠送人：{context.requester_name}")
            lines.append(f"> 接收人：<font color=\"info\">{context.approver_name}</font> ✅")
        elif context.notification_type == NotificationType.GIFT_REJECTED:
            # 赠送被拒绝：显示拒绝者
            lines.append(f"> 赠送人：{context.requester_name}")
            lines.append(f"> 接收人：<font color=\"warning\">{context.approver_name}</font> ❌")
        elif context.notification_type == NotificationType.GIFT_CANCELLED:
            # 赠送被取消：显示取消者
            lines.append(f"> 赠送人：<font color=\"warning\">{context.requester_name}</font>")
            lines.append(f"> 接收人：{context.approver_name}")
        
        # 添加内容（祝福语等）
        if context.content:
            lines.append("")
            lines.append(context.content)
        
        # 添加详情链接
        gift_url = context.get_gift_url()
        if gift_url:
            lines.append("")
            lines.append(f"📎 [查看详情]({gift_url})")
        
        # 额外提示
        if context.notification_type == NotificationType.GIFT_SENT:
            lines.append("")
            if gift_url:
                lines.append("<font color=\"info\">点击上方链接接受或拒绝赠送</font>")
            else:
                lines.append("<font color=\"info\">请登录小金库处理此赠送</font>")
        elif context.notification_type == NotificationType.GIFT_ACCEPTED:
            lines.append("")
            lines.append("<font color=\"info\">股权已自动转移</font>")
        
        return "\n".join(lines)
    
    def _build_approval_markdown(self, context: NotificationContext) -> str:
        """构建审批通知的 Markdown 消息"""
        status_label = self.STATUS_LABELS.get(context.notification_type, "📋 通知")
        
        # 基础消息头
        lines = [
            f"### {status_label}",
            f"**{context.title}**",
            "",
        ]
        
        # 家庭信息
        lines.append(f"> 家庭：{context.family_name}")
        
        # 申请类型
        if context.request_type:
            type_name = self.REQUEST_TYPE_NAMES.get(context.request_type, context.request_type)
            lines.append(f"> 类型：{type_name}")
        
        # 金额信息
        if context.amount and context.amount > 0:
            lines.append(f"> 金额：<font color=\"warning\">¥{context.amount:,.2f}</font>")
        
        # 相关人员
        if context.requester_name:
            lines.append(f"> 申请人：{context.requester_name}")
        
        if context.approver_name:
            if context.notification_type == NotificationType.APPROVAL_APPROVED:
                lines.append(f"> 审批人：{context.approver_name} ✅")
            elif context.notification_type == NotificationType.APPROVAL_REJECTED:
                lines.append(f"> 审批人：{context.approver_name} ❌")
        
        # 添加内容描述
        if context.content:
            lines.append("")
            lines.append(context.content)
        
        # 添加详情链接
        approval_url = context.get_approval_url()
        if approval_url:
            lines.append("")
            lines.append(f"📎 [查看详情]({approval_url})")
        
        # 额外提示
        if context.notification_type == NotificationType.APPROVAL_CREATED:
            lines.append("")
            if approval_url:
                lines.append("<font color=\"info\">点击上方链接进行审批</font>")
            else:
                lines.append("<font color=\"info\">请登录小金库进行审批</font>")
        elif context.notification_type == NotificationType.APPROVAL_COMPLETED:
            lines.append("")
            lines.append("<font color=\"info\">申请已自动执行</font>")
        
        return "\n".join(lines)


# ==================== 通知服务主类 ====================

class NotificationService:
    """
    通知服务
    
    负责：
    1. 管理多个通知渠道
    2. 根据家庭配置发送通知
    3. 提供统一的通知接口
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # 注册通知渠道
        self.channels: Dict[str, NotificationChannel] = {
            "wechat_work": WeChatWorkChannel(),
            # 未来可扩展：
            # "email": EmailChannel(),
            # "telegram": TelegramChannel(),
            # "dingtalk": DingTalkChannel(),
        }
    
    async def get_family_notification_config(self, family_id: int) -> Dict[str, Any]:
        """
        获取家庭的通知配置
        
        优先级：
        1. 数据库中的家庭配置（每个家庭独立配置）
        2. 环境变量（全局默认配置）
        """
        import os
        
        # 默认配置（从环境变量读取）
        config = {
            "wechat_work_webhook_url": os.getenv("WECHAT_WORK_WEBHOOK_URL", ""),
            "notification_enabled": os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true",
        }
        
        # 尝试从数据库读取家庭配置（优先级更高）
        try:
            result = await self.db.execute(
                select(Family).where(Family.id == family_id)
            )
            family = result.scalar_one_or_none()
            
            if family:
                # 家庭配置覆盖默认配置
                if family.wechat_webhook_url:
                    config["wechat_work_webhook_url"] = family.wechat_webhook_url
                config["notification_enabled"] = family.notification_enabled
                # 外网访问地址配置
                if family.external_base_url:
                    config["external_base_url"] = family.external_base_url
                
        except Exception as e:
            logging.warning(f"Failed to load family notification config: {e}")
        
        return config
    
    async def notify_approval_created(
        self,
        request: ApprovalRequest,
        requester: User,
        family: Family
    ) -> None:
        """通知：新申请创建"""
        context = NotificationContext(
            notification_type=NotificationType.APPROVAL_CREATED,
            family_id=family.id,
            family_name=family.name,
            title=request.title,
            content=request.description,
            amount=request.amount,
            requester_name=requester.nickname,
            request_type=request.request_type,
            request_id=request.id,
            base_url=get_external_base_url(),
        )
        await self._send_to_all_channels(context)
    
    async def notify_approval_voted(
        self,
        request: ApprovalRequest,
        approver: User,
        is_approved: bool,
        family: Family,
        requester: User
    ) -> None:
        """通知：申请被投票（同意/拒绝）"""
        notification_type = (
            NotificationType.APPROVAL_APPROVED if is_approved 
            else NotificationType.APPROVAL_REJECTED
        )
        
        action_text = "同意了" if is_approved else "拒绝了"
        
        context = NotificationContext(
            notification_type=notification_type,
            family_id=family.id,
            family_name=family.name,
            title=f"{approver.nickname} {action_text}申请",
            content=request.description,
            amount=request.amount,
            requester_name=requester.nickname,
            approver_name=approver.nickname,
            request_type=request.request_type,
            request_id=request.id,
            base_url=get_external_base_url(),
        )
        await self._send_to_all_channels(context)
    
    async def notify_approval_completed(
        self,
        request: ApprovalRequest,
        family: Family,
        requester: User
    ) -> None:
        """通知：申请最终通过并执行"""
        context = NotificationContext(
            notification_type=NotificationType.APPROVAL_COMPLETED,
            family_id=family.id,
            family_name=family.name,
            title=f"✅ {request.title} - 已完成",
            content="所有成员已同意，申请已自动执行",
            amount=request.amount,
            requester_name=requester.nickname,
            request_type=request.request_type,
            request_id=request.id,
            base_url=get_external_base_url(),
        )
        await self._send_to_all_channels(context)
    
    async def notify_approval_cancelled(
        self,
        request: ApprovalRequest,
        family: Family,
        requester: User
    ) -> None:
        """通知：申请被取消"""
        context = NotificationContext(
            notification_type=NotificationType.APPROVAL_CANCELLED,
            family_id=family.id,
            family_name=family.name,
            title=f"🚫 {request.title} - 已取消",
            content=f"{requester.nickname} 取消了此申请",
            amount=request.amount,
            requester_name=requester.nickname,
            request_type=request.request_type,
            request_id=request.id,
            base_url=get_external_base_url(),
        )
        await self._send_to_all_channels(context)
    
    async def notify_approval_reminder(
        self,
        request: ApprovalRequest,
        family: Family,
        requester: User,
        reminder_user: User
    ) -> None:
        """通知：催促审核提醒"""
        context = NotificationContext(
            notification_type=NotificationType.APPROVAL_REMINDER,
            family_id=family.id,
            family_name=family.name,
            title=f"⏰ 请尽快审批：{request.title}",
            content=f"{reminder_user.nickname} 催促大家尽快处理此申请",
            amount=request.amount,
            requester_name=requester.nickname,
            request_type=request.request_type,
            request_id=request.id,
            base_url=get_external_base_url(),
        )
        await self._send_to_all_channels(context)
    
    # ==================== 股权赠送通知 ====================
    
    async def notify_gift_sent(
        self,
        gift: EquityGift,
        from_user: User,
        to_user: User,
        family: Family
    ) -> None:
        """通知：收到股权赠送"""
        context = NotificationContext(
            notification_type=NotificationType.GIFT_SENT,
            family_id=family.id,
            family_name=family.name,
            title=f"🎁 收到股权赠送",
            content=f"祝福语：{gift.message}" if gift.message else "",
            requester_name=from_user.nickname,
            approver_name=to_user.nickname,
            gift_id=gift.id,
            base_url=get_external_base_url(),
            extra_data={"amount_percent": gift.amount * 100},
        )
        await self._send_to_all_channels(context)
    
    async def notify_gift_accepted(
        self,
        gift: EquityGift,
        from_user: User,
        to_user: User,
        family: Family
    ) -> None:
        """通知：股权赠送被接受"""
        context = NotificationContext(
            notification_type=NotificationType.GIFT_ACCEPTED,
            family_id=family.id,
            family_name=family.name,
            title=f"✅ 股权赠送已被接受",
            content="股权转移已完成",
            requester_name=from_user.nickname,
            approver_name=to_user.nickname,
            gift_id=gift.id,
            base_url=get_external_base_url(),
            extra_data={"amount_percent": gift.amount * 100},
        )
        await self._send_to_all_channels(context)
    
    async def notify_gift_rejected(
        self,
        gift: EquityGift,
        from_user: User,
        to_user: User,
        family: Family
    ) -> None:
        """通知：股权赠送被拒绝"""
        context = NotificationContext(
            notification_type=NotificationType.GIFT_REJECTED,
            family_id=family.id,
            family_name=family.name,
            title=f"❌ 股权赠送被拒绝",
            content="股权未发生变化",
            requester_name=from_user.nickname,
            approver_name=to_user.nickname,
            gift_id=gift.id,
            base_url=get_external_base_url(),
            extra_data={"amount_percent": gift.amount * 100},
        )
        await self._send_to_all_channels(context)
    
    async def notify_gift_cancelled(
        self,
        gift: EquityGift,
        from_user: User,
        to_user: User,
        family: Family
    ) -> None:
        """通知：股权赠送被取消"""
        context = NotificationContext(
            notification_type=NotificationType.GIFT_CANCELLED,
            family_id=family.id,
            family_name=family.name,
            title=f"🚫 股权赠送已取消",
            content="",
            requester_name=from_user.nickname,
            approver_name=to_user.nickname,
            gift_id=gift.id,
            base_url=get_external_base_url(),
            extra_data={"amount_percent": gift.amount * 100},
        )
        await self._send_to_all_channels(context)
    
    async def _send_to_all_channels(self, context: NotificationContext) -> None:
        """
        向所有已配置的渠道发送通知
        
        注意：通知失败不应影响主业务逻辑
        """
        try:
            config = await self.get_family_notification_config(context.family_id)
            
            # 检查是否启用通知
            if not config.get("notification_enabled", True):
                logging.debug(f"Notifications disabled for family {context.family_id}")
                return
            
            # 优先使用配置的外网地址，否则使用自动检测的地址
            configured_url = config.get("external_base_url")
            if configured_url:
                context.base_url = configured_url.rstrip("/")
                logging.debug(f"Using configured external URL: {context.base_url}")
            elif not context.base_url:
                # 如果都没有，使用默认值
                context.base_url = "http://localhost:8000"
                logging.debug("Using default localhost URL")
            
            # 向所有配置的渠道发送
            for channel_name, channel in self.channels.items():
                if channel.is_configured(config):
                    try:
                        success = await channel.send(context, config)
                        if success:
                            logging.info(f"Notification sent via {channel_name}")
                        else:
                            logging.warning(f"Notification via {channel_name} returned false")
                    except Exception as e:
                        logging.error(f"Error sending notification via {channel_name}: {e}")
                else:
                    logging.debug(f"Channel {channel_name} not configured, skipping")
                    
        except Exception as e:
            # 通知失败不应该影响主业务
            logging.error(f"Notification service error: {e}")


# ==================== 便捷函数 ====================

async def send_approval_notification(
    db: AsyncSession,
    notification_type: NotificationType,
    request: ApprovalRequest,
    approver: Optional[User] = None
) -> None:
    """
    发送审批相关通知的便捷函数
    
    Args:
        db: 数据库会话
        notification_type: 通知类型
        request: 审批请求
        approver: 审批人（可选）
    """
    try:
        # 获取申请人信息
        result = await db.execute(
            select(User).where(User.id == request.requester_id)
        )
        requester = result.scalar_one_or_none()
        if not requester:
            logging.warning(f"Requester not found for request {request.id}")
            return
        
        # 获取家庭信息
        result = await db.execute(
            select(Family).where(Family.id == request.family_id)
        )
        family = result.scalar_one_or_none()
        if not family:
            logging.warning(f"Family not found for request {request.id}")
            return
        
        # 创建通知服务并发送
        service = NotificationService(db)
        
        if notification_type == NotificationType.APPROVAL_CREATED:
            await service.notify_approval_created(request, requester, family)
        elif notification_type in (NotificationType.APPROVAL_APPROVED, NotificationType.APPROVAL_REJECTED):
            if approver:
                is_approved = notification_type == NotificationType.APPROVAL_APPROVED
                await service.notify_approval_voted(request, approver, is_approved, family, requester)
        elif notification_type == NotificationType.APPROVAL_COMPLETED:
            await service.notify_approval_completed(request, family, requester)
        elif notification_type == NotificationType.APPROVAL_CANCELLED:
            await service.notify_approval_cancelled(request, family, requester)
            
    except Exception as e:
        logging.error(f"Failed to send approval notification: {e}")


async def send_gift_notification(
    db: AsyncSession,
    notification_type: NotificationType,
    gift: EquityGift,
) -> None:
    """
    发送股权赠送相关通知的便捷函数
    
    Args:
        db: 数据库会话
        notification_type: 通知类型 (GIFT_SENT, GIFT_ACCEPTED, GIFT_REJECTED, GIFT_CANCELLED)
        gift: 股权赠送记录
    """
    try:
        # 获取发送者信息
        result = await db.execute(
            select(User).where(User.id == gift.from_user_id)
        )
        from_user = result.scalar_one_or_none()
        if not from_user:
            logging.warning(f"From user not found for gift {gift.id}")
            return
        
        # 获取接收者信息
        result = await db.execute(
            select(User).where(User.id == gift.to_user_id)
        )
        to_user = result.scalar_one_or_none()
        if not to_user:
            logging.warning(f"To user not found for gift {gift.id}")
            return
        
        # 获取家庭信息
        result = await db.execute(
            select(Family).where(Family.id == gift.family_id)
        )
        family = result.scalar_one_or_none()
        if not family:
            logging.warning(f"Family not found for gift {gift.id}")
            return
        
        # 创建通知服务并发送
        service = NotificationService(db)
        
        if notification_type == NotificationType.GIFT_SENT:
            await service.notify_gift_sent(gift, from_user, to_user, family)
        elif notification_type == NotificationType.GIFT_ACCEPTED:
            await service.notify_gift_accepted(gift, from_user, to_user, family)
        elif notification_type == NotificationType.GIFT_REJECTED:
            await service.notify_gift_rejected(gift, from_user, to_user, family)
        elif notification_type == NotificationType.GIFT_CANCELLED:
            await service.notify_gift_cancelled(gift, from_user, to_user, family)
            
    except Exception as e:
        logging.error(f"Failed to send gift notification: {e}")


async def send_pet_evolved_notification(
    db: AsyncSession,
    family_id: int,
    pet_name: str,
    new_type: str
) -> None:
    """
    发送宠物进化通知的便捷函数
    """
    try:
        result = await db.execute(
            select(Family).where(Family.id == family_id)
        )
        family = result.scalar_one_or_none()
        if not family:
            return

        # 进化形态信息
        evolution_names = {
            "golden_egg": ("🥚", "金色蛋"),
            "golden_chick": ("🐣", "金色小鸡"),
            "golden_bird": ("🐦", "金色小鸟"),
            "golden_phoenix": ("🦅", "金色凤凰"),
            "golden_dragon": ("🐲", "金色神龙"),
        }
        emoji, type_name = evolution_names.get(new_type, ("🌟", new_type))

        service = NotificationService(db)
        context = NotificationContext(
            notification_type=NotificationType.PET_EVOLVED,
            family_id=family.id,
            family_name=family.name,
            title=f"{emoji} 宠物进化啦！",
            content=f"家庭宠物「{pet_name}」进化为 {emoji} {type_name}！",
            base_url=get_external_base_url(),
        )
        await service._send_to_all_channels(context)

    except Exception as e:
        logging.error(f"Failed to send pet evolution notification: {e}")
