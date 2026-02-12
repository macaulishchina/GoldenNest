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
    
    # 投票相关
    VOTE_PROPOSAL_CREATED = "vote_proposal_created"  # 新投票提案创建
    VOTE_CAST = "vote_cast"                          # 成员投票
    VOTE_PASSED = "vote_passed"                      # 投票通过
    VOTE_REJECTED = "vote_rejected"                  # 投票被拒绝
    
    # 赌注相关
    BET_CREATED = "bet_created"                  # 新赌注创建
    BET_VOTED = "bet_voted"                      # 参与者投票
    BET_AWAITING_RESULT = "bet_awaiting_result"  # 等待登记结果
    BET_RESULT_DECLARED = "bet_result_declared"  # 结果已登记待确认
    BET_SETTLED = "bet_settled"                  # 赌注已结算
    BET_CANCELLED = "bet_cancelled"              # 赌注已取消
    
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
    proposal_id: Optional[int] = None      # 投票提案 ID，用于生成详情链接
    bet_id: Optional[int] = None           # 赌注 ID，用于生成详情链接
    voter_name: Optional[str] = None       # 投票人名称
    vote_option: Optional[str] = None      # 投票选项
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
    
    def get_vote_url(self) -> Optional[str]:
        """获取投票详情页面 URL"""
        if self.base_url and self.proposal_id:
            # 前端路由：/vote?id=xxx
            return f"{self.base_url}/vote?highlight={self.proposal_id}"
        return None
    
    def get_bet_url(self) -> Optional[str]:
        """获取赌注详情页面 URL"""
        if self.base_url and self.bet_id:
            return f"{self.base_url}/bet?highlight={self.bet_id}"
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
        NotificationType.GIFT_REJECTED: "❌ 赠送已拒绝",
        NotificationType.GIFT_CANCELLED: "🚫 赠送已取消",
        # 投票相关
        NotificationType.VOTE_PROPOSAL_CREATED: "🗳️ 新投票提案",
        NotificationType.VOTE_CAST: "✅ 成员已投票",
        NotificationType.VOTE_PASSED: "🎉 投票通过",
        NotificationType.VOTE_REJECTED: "❌ 投票未通过",
        # 赌注相关
        NotificationType.BET_CREATED: "🎲 新赌注",
        NotificationType.BET_VOTED: "✅ 已投票",
        NotificationType.BET_AWAITING_RESULT: "⏳ 等待登记结果",
        NotificationType.BET_RESULT_DECLARED: "📝 结果已登记",
        NotificationType.BET_SETTLED: "🏆 赌注已结算",
        NotificationType.BET_CANCELLED: "🚫 赌注已取消",
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
        
        logging.info(f"Building markdown message for {context.notification_type}")
        
        # 构建 Markdown 消息内容
        try:
            markdown_content = self._build_markdown_message(context)
            logging.debug(f"Markdown content built, length={len(markdown_content)}")
        except Exception as e:
            logging.error(f"Failed to build markdown message: {e}", exc_info=True)
            return False
        
        # 构建请求体
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }
        
        try:
            logging.info(f"Sending to WeChatWork webhook: {webhook_url[:50]}...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if result.get("errcode") == 0:
                    logging.info(f"✅ WeChatWork notification sent successfully: {context.notification_type}")
                    return True
                else:
                    logging.warning(f"❌ WeChatWork notification failed: {result}")
                    return False
                    
        except httpx.HTTPError as e:
            logging.error(f"❌ WeChatWork notification HTTP error: {e}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"❌ WeChatWork notification error: {e}", exc_info=True)
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
        
        # 判断是否为投票通知
        vote_types = {
            NotificationType.VOTE_PROPOSAL_CREATED,
            NotificationType.VOTE_CAST,
            NotificationType.VOTE_PASSED,
            NotificationType.VOTE_REJECTED,
        }
        
        # 判断是否为赌注通知
        bet_types = {
            NotificationType.BET_CREATED,
            NotificationType.BET_VOTED,
            NotificationType.BET_AWAITING_RESULT,
            NotificationType.BET_RESULT_DECLARED,
            NotificationType.BET_SETTLED,
            NotificationType.BET_CANCELLED,
        }
        
        if context.notification_type in gift_types:
            return self._build_gift_markdown(context)
        elif context.notification_type in vote_types:
            return self._build_vote_markdown(context)
        elif context.notification_type in bet_types:
            return self._build_bet_markdown(context)
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
    
    def _build_vote_markdown(self, context: NotificationContext) -> str:
        """构建投票通知的 Markdown 消息"""
        status_label = self.STATUS_LABELS.get(context.notification_type, "🗳️ 投票")
        
        # 基础消息头
        lines = [
            f"### {status_label}",
            f"**{context.title}**",
            "",
        ]
        
        # 家庭信息
        lines.append(f"> 家庭：{context.family_name}")
        
        # 根据不同的投票类型添加信息
        if context.notification_type == NotificationType.VOTE_PROPOSAL_CREATED:
            # 新提案创建
            if context.requester_name:
                lines.append(f"> 发起人：<font color=\"info\">{context.requester_name}</font>")
        elif context.notification_type == NotificationType.VOTE_CAST:
            # 成员投票
            if context.voter_name:
                lines.append(f"> 投票人：{context.voter_name}")
            if context.vote_option:
                lines.append(f"> 选择：<font color=\"warning\">{context.vote_option}</font>")
        elif context.notification_type in [NotificationType.VOTE_PASSED, NotificationType.VOTE_REJECTED]:
            # 投票结果
            result_icon = "✅" if context.notification_type == NotificationType.VOTE_PASSED else "❌"
            result_text = "通过" if context.notification_type == NotificationType.VOTE_PASSED else "未通过"
            lines.append(f"> 结果：{result_icon} <font color=\"warning\">{result_text}</font>")
            if context.requester_name:
                lines.append(f"> 发起人：{context.requester_name}")
        
        # 金额信息（分红提案）
        if context.amount and context.amount > 0:
            lines.append(f"> 金额：<font color=\"warning\">¥{context.amount:,.2f}</font>")
        
        # 添加内容描述
        if context.content:
            lines.append("")
            lines.append(context.content)
        
        # 添加详情链接
        vote_url = context.get_vote_url()
        if vote_url:
            lines.append("")
            lines.append(f"📎 [查看详情]({vote_url})")
        
        # 额外提示
        if context.notification_type == NotificationType.VOTE_PROPOSAL_CREATED:
            lines.append("")
            if vote_url:
                lines.append("<font color=\"info\">点击上方链接进行投票</font>")
            else:
                lines.append("<font color=\"info\">请登录小金库进行投票</font>")
        elif context.notification_type == NotificationType.VOTE_PASSED:
            lines.append("")
            lines.append("<font color=\"info\">提案已自动执行</font>")
        
        return "\n".join(lines)
    
    def _build_bet_markdown(self, context: NotificationContext) -> str:
        """构建赌注通知的 Markdown 消息"""
        status_label = self.STATUS_LABELS.get(context.notification_type, "🎲 赌注")
        
        lines = [
            f"### {status_label}",
            f"**{context.title}**",
            "",
        ]
        
        lines.append(f"> 家庭：{context.family_name}")
        
        if context.requester_name:
            lines.append(f"> 发起人：{context.requester_name}")
        
        if context.notification_type == NotificationType.BET_VOTED and context.voter_name:
            lines.append(f"> 投票人：<font color=\"info\">{context.voter_name}</font>")
            if context.vote_option:
                lines.append(f"> 选择：<font color=\"warning\">{context.vote_option}</font>")
        
        if context.amount and context.amount > 0:
            lines.append(f"> 涉及金额：<font color=\"warning\">¥{context.amount:,.2f}</font>")
        
        if context.content:
            lines.append("")
            lines.append(context.content)
        
        bet_url = context.get_bet_url()
        if bet_url:
            lines.append("")
            lines.append(f"📎 [查看详情]({bet_url})")
        
        if context.notification_type == NotificationType.BET_CREATED:
            lines.append("")
            if bet_url:
                lines.append("<font color=\"info\">点击上方链接参与投票</font>")
            else:
                lines.append("<font color=\"info\">请登录小金库参与投票</font>")
        
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
        from app.core.encryption import decrypt_sensitive_data
        
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
                # 家庭配置覆盖默认配置（webhook URL 需要解密）
                if family.wechat_webhook_url:
                    config["wechat_work_webhook_url"] = decrypt_sensitive_data(family.wechat_webhook_url)
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
        # 如果有target_user_id，获取目标用户昵称
        target_user_name = None
        if request.target_user_id:
            result = await self.db.execute(
                select(User).where(User.id == request.target_user_id)
            )
            target_user = result.scalar_one_or_none()
            if target_user:
                target_user_name = target_user.nickname
        
        # 构建标题：如果有目标用户，标明是给谁的
        title = request.title
        if target_user_name:
            title = f"@{target_user_name} {request.title}"
        
        context = NotificationContext(
            notification_type=NotificationType.APPROVAL_CREATED,
            family_id=family.id,
            family_name=family.name,
            title=title,
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
    
    # ==================== 投票通知方法 ====================
    
    async def notify_vote_proposal_created(
        self,
        proposal,  # Proposal对象
        creator: User,
        family: Family
    ) -> None:
        """通知：投票提案创建"""
        import json
        import logging
        
        logging.info(f"notify_vote_proposal_created called for proposal {proposal.id}")
        
        options = json.loads(proposal.options) if isinstance(proposal.options, str) else proposal.options
        
        context = NotificationContext(
            notification_type=NotificationType.VOTE_PROPOSAL_CREATED,
            family_id=family.id,
            family_name=family.name,
            title=proposal.title,
            content=f"{proposal.description}\n\n投票选项：{'、'.join(options)}",
            requester_name=creator.nickname,
            proposal_id=proposal.id,
            base_url=get_external_base_url(),
        )
        
        logging.info(f"Sending vote proposal notification to channels, family_id={family.id}")
        await self._send_to_all_channels(context)
        logging.info(f"Vote proposal notification sent for proposal {proposal.id}")
    
    async def notify_vote_cast(
        self,
        proposal,  # Proposal对象
        voter: User,
        vote_option: str,
        family: Family
    ) -> None:
        """通知：成员投票"""
        import logging
        
        logging.info(f"notify_vote_cast called for proposal {proposal.id}, voter={voter.nickname}")
        
        context = NotificationContext(
            notification_type=NotificationType.VOTE_CAST,
            family_id=family.id,
            family_name=family.name,
            title=proposal.title,
            content=f"{voter.nickname} 已投票",
            voter_name=voter.nickname,
            vote_option=vote_option,
            proposal_id=proposal.id,
            base_url=get_external_base_url(),
        )

        await self._send_to_all_channels(context)
    
    async def notify_vote_result(
        self,
        proposal,  # Proposal对象
        passed: bool,
        creator: User,
        family: Family,
        amount: float = None
    ) -> None:
        """通知：投票结果"""        
        notification_type = NotificationType.VOTE_PASSED if passed else NotificationType.VOTE_REJECTED
        result_text = "通过" if passed else "未通过"

        context = NotificationContext(
            notification_type=notification_type,
            family_id=family.id,
            family_name=family.name,
            title=f"{proposal.title} - {result_text}",
            content=proposal.description,
            requester_name=creator.nickname,
            amount=amount,
            proposal_id=proposal.id,
            base_url=get_external_base_url(),
        )
        
        await self._send_to_all_channels(context)
    
    async def notify_bet_created(
        self,
        bet,  # Bet对象
        creator: User,
        family: Family,
        participants_names: List[str]
    ) -> None:
        """通知：新赌注创建"""
        content = f"{bet.description}\n\n参与者：{'、'.join(participants_names)}"
        
        context = NotificationContext(
            notification_type=NotificationType.BET_CREATED,
            family_id=family.id,
            family_name=family.name,
            title=bet.title,
            content=content,
            requester_name=creator.nickname,
            bet_id=bet.id,
            base_url=get_external_base_url(),
        )
        
        await self._send_to_all_channels(context)
    
    async def notify_bet_voted(
        self,
        bet,  # Bet对象
        voter: User,
        option_text: str,
        family: Family
    ) -> None:
        """通知：赌注投票"""
        context = NotificationContext(
            notification_type=NotificationType.BET_VOTED,
            family_id=family.id,
            family_name=family.name,
            title=bet.title,
            content=f"{voter.nickname} 已对赌注投票",
            requester_name=None,
            voter_name=voter.nickname,
            vote_option=option_text,
            bet_id=bet.id,
            base_url=get_external_base_url(),
        )
        
        await self._send_to_all_channels(context)
    
    async def notify_bet_status_change(
        self,
        bet,  # Bet对象
        notification_type: NotificationType,
        family: Family,
        creator_name: str,
        content: str = ""
    ) -> None:
        """通知：赌注状态变更（截止投票、结果登记、结算、取消）"""
        context = NotificationContext(
            notification_type=notification_type,
            family_id=family.id,
            family_name=family.name,
            title=bet.title,
            content=content,
            requester_name=creator_name,
            bet_id=bet.id,
            base_url=get_external_base_url(),
        )
        
        await self._send_to_all_channels(context)
    
    async def _send_to_all_channels(self, context: NotificationContext) -> None:
        """
        向所有已配置的渠道发送通知
        
        注意：通知失败不应影响主业务逻辑
        """
        try:
            logging.info(f"_send_to_all_channels called for {context.notification_type}, family_id={context.family_id}")
            
            config = await self.get_family_notification_config(context.family_id)
            
            webhook_url = config.get('wechat_work_webhook_url', '')
            logging.info(f"Notification config: enabled={config.get('notification_enabled')}, webhook={'✅ ' + webhook_url[:60] + '...' if webhook_url else '❌ 未配置'}")
            
            # 检查是否启用通知
            if not config.get("notification_enabled", True):
                logging.warning(f"Notifications disabled for family {context.family_id}")
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
            sent_count = 0
            for channel_name, channel in self.channels.items():
                if channel.is_configured(config):
                    logging.info(f"Channel {channel_name} is configured, attempting to send")
                    try:
                        success = await channel.send(context, config)
                        if success:
                            logging.info(f"✅ Notification sent successfully via {channel_name}")
                            sent_count += 1
                        else:
                            logging.warning(f"❌ Notification via {channel_name} returned false")
                    except Exception as e:
                        logging.error(f"❌ Error sending notification via {channel_name}: {e}", exc_info=True)
                else:
                    logging.debug(f"Channel {channel_name} not configured, skipping")
            
            if sent_count == 0:
                logging.warning(f"No notifications sent for {context.notification_type} (no channels configured)")
            else:
                logging.info(f"Notification sent to {sent_count} channel(s)")
                    
        except Exception as e:
            # 通知失败不应该影响主业务
            logging.error(f"Notification service error: {e}", exc_info=True)


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
        # 获取申请人信息（系统发起时requester_id=0）
        if request.requester_id == 0:
            # 系统发起的申请，创建虚拟用户对象
            requester = User(id=0, username="system", nickname="系统", email="")
        else:
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


async def send_bet_notification(
    db: AsyncSession,
    notification_type: NotificationType,
    bet,  # Bet对象
    creator_name: str = "",
    participants_names: Optional[List[str]] = None,
    voter: Optional[User] = None,
    option_text: str = "",
    content: str = ""
) -> None:
    """
    发送赌注通知的便捷函数
    
    适用于：赌注创建、投票、截止、结果登记、结算、取消
    """
    try:
        logging.info(f"[BET_NOTIFY] send_bet_notification called: type={notification_type}, bet_id={bet.id}, family_id={bet.family_id}")

        # 获取家庭信息
        result = await db.execute(
            select(Family).where(Family.id == bet.family_id)
        )
        family = result.scalar_one_or_none()
        if not family:
            logging.warning(f"[BET_NOTIFY] Family not found for bet {bet.id}, family_id={bet.family_id}")
            return

        service = NotificationService(db)

        if notification_type == NotificationType.BET_CREATED:
            # 获取创建者
            creator_result = await db.execute(
                select(User).where(User.id == bet.creator_id)
            )
            creator = creator_result.scalar_one_or_none()
            if not creator:
                logging.warning(f"[BET_NOTIFY] Creator not found for bet {bet.id}, creator_id={bet.creator_id}")
                return
            logging.info(f"[BET_NOTIFY] Calling notify_bet_created for bet {bet.id}")
            await service.notify_bet_created(
                bet, creator, family, participants_names or []
            )
        elif notification_type == NotificationType.BET_VOTED:
            if not voter:
                logging.warning(f"[BET_NOTIFY] BET_VOTED called without voter for bet {bet.id}")
                return
            logging.info(f"[BET_NOTIFY] Calling notify_bet_voted for bet {bet.id}")
            await service.notify_bet_voted(bet, voter, option_text, family)
        else:
            # 通用状态变更通知
            logging.info(f"[BET_NOTIFY] Calling notify_bet_status_change for bet {bet.id}, type={notification_type}")
            await service.notify_bet_status_change(
                bet, notification_type, family, creator_name, content
            )

        logging.info(f"[BET_NOTIFY] send_bet_notification completed for bet {bet.id}")

    except Exception as e:
        logging.error(f"[BET_NOTIFY] Failed to send bet notification: {e}", exc_info=True)
