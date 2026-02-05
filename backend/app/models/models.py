"""
小金库 (Golden Nest) - 数据库模型
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


# ==================== 枚举类型 ====================

class TransactionType(str, enum.Enum):
    """交易类型"""
    DEPOSIT = "deposit"          # 存入
    WITHDRAW = "withdraw"        # 支出
    INCOME = "income"            # 理财收益
    DIVIDEND = "dividend"        # 分红


class ExpenseStatus(str, enum.Enum):
    """支出申请状态"""
    PENDING = "pending"          # 待审批
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    CANCELLED = "cancelled"      # 已取消


class InvestmentType(str, enum.Enum):
    """理财类型"""
    DEPOSIT = "deposit"          # 银行存款
    FUND = "fund"                # 基金
    STOCK = "stock"              # 股票
    BOND = "bond"                # 债券
    OTHER = "other"              # 其他


# ==================== 用户模型 ====================

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50))  # 昵称，显示用
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 头像 Base64
    avatar_version: Mapped[int] = mapped_column(Integer, default=0)  # 头像版本号，用于缓存失效
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    family_memberships: Mapped[List["FamilyMember"]] = relationship(back_populates="user")
    deposits: Mapped[List["Deposit"]] = relationship(back_populates="user")
    expense_requests: Mapped[List["ExpenseRequest"]] = relationship(back_populates="requester", foreign_keys="ExpenseRequest.requester_id")
    expense_approvals: Mapped[List["ExpenseApproval"]] = relationship(back_populates="approver")
    achievements: Mapped[List["UserAchievement"]] = relationship(back_populates="user")


# ==================== 家庭模型 ====================

class Family(Base):
    """家庭表"""
    __tablename__ = "families"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))  # 家庭名称
    savings_target: Mapped[float] = mapped_column(Float, default=2000000.0)  # 储蓄目标
    time_value_rate: Mapped[float] = mapped_column(Float, default=0.03)  # 时间价值系数（用于计算加权股权）
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # 邀请码
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 通知配置
    wechat_webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 企业微信机器人 Webhook URL
    notification_enabled: Mapped[bool] = mapped_column(default=True)  # 是否启用通知
    external_base_url: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 外网访问地址，用于通知中的链接
    
    # 关联关系
    members: Mapped[List["FamilyMember"]] = relationship(back_populates="family")
    deposits: Mapped[List["Deposit"]] = relationship(back_populates="family")
    investments: Mapped[List["Investment"]] = relationship(back_populates="family")
    expense_requests: Mapped[List["ExpenseRequest"]] = relationship(back_populates="family")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="family")


class FamilyMember(Base):
    """家庭成员表（多对多关联表）"""
    __tablename__ = "family_members"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin: 管理员, member: 普通成员
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    user: Mapped["User"] = relationship(back_populates="family_memberships")
    family: Mapped["Family"] = relationship(back_populates="members")


# ==================== 资金注入模型 ====================

class Deposit(Base):
    """资金注入记录表"""
    __tablename__ = "deposits"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    amount: Mapped[float] = mapped_column(Float)  # 存入金额
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 备注
    deposit_date: Mapped[datetime] = mapped_column(DateTime)  # 存入日期
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    user: Mapped["User"] = relationship(back_populates="deposits")
    family: Mapped["Family"] = relationship(back_populates="deposits")


# ==================== 理财配置模型 ====================

class Investment(Base):
    """理财配置表"""
    __tablename__ = "investments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    name: Mapped[str] = mapped_column(String(100))  # 理财产品名称
    investment_type: Mapped[InvestmentType] = mapped_column(SQLEnum(InvestmentType))
    principal: Mapped[float] = mapped_column(Float)  # 本金
    expected_rate: Mapped[float] = mapped_column(Float)  # 预期年化收益率
    start_date: Mapped[datetime] = mapped_column(DateTime)  # 开始日期
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 到期日期
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    family: Mapped["Family"] = relationship(back_populates="investments")
    income_records: Mapped[List["InvestmentIncome"]] = relationship(back_populates="investment")


class InvestmentIncome(Base):
    """理财收益记录表"""
    __tablename__ = "investment_incomes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investment_id: Mapped[int] = mapped_column(ForeignKey("investments.id"))
    amount: Mapped[float] = mapped_column(Float)  # 收益金额
    income_date: Mapped[datetime] = mapped_column(DateTime)  # 收益日期
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    investment: Mapped["Investment"] = relationship(back_populates="income_records")


# ==================== 支出申请模型 ====================

class ExpenseRequest(Base):
    """大额支出申请表"""
    __tablename__ = "expense_requests"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))  # 支出标题
    amount: Mapped[float] = mapped_column(Float)  # 支出金额
    reason: Mapped[str] = mapped_column(Text)  # 支出原因
    equity_deduction_ratio: Mapped[str] = mapped_column(String(500))  # 股权扣减比例（JSON格式存储）
    status: Mapped[ExpenseStatus] = mapped_column(SQLEnum(ExpenseStatus), default=ExpenseStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    family: Mapped["Family"] = relationship(back_populates="expense_requests")
    requester: Mapped["User"] = relationship(back_populates="expense_requests", foreign_keys=[requester_id])
    approvals: Mapped[List["ExpenseApproval"]] = relationship(back_populates="expense_request")


class ExpenseApproval(Base):
    """支出审批记录表"""
    __tablename__ = "expense_approvals"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    expense_request_id: Mapped[int] = mapped_column(ForeignKey("expense_requests.id"))
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_approved: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    expense_request: Mapped["ExpenseRequest"] = relationship(back_populates="approvals")
    approver: Mapped["User"] = relationship(back_populates="expense_approvals")


# ==================== 交易流水模型 ====================

class Transaction(Base):
    """资金流水表"""
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType))
    amount: Mapped[float] = mapped_column(Float)  # 金额（正数为入账，负数为出账）
    balance_after: Mapped[float] = mapped_column(Float)  # 交易后余额
    description: Mapped[str] = mapped_column(String(500))  # 描述
    reference_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # 关联的记录ID
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 关联类型
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    family: Mapped["Family"] = relationship(back_populates="transactions")


# ==================== 成就系统模型 ====================

class AchievementCategory(str, enum.Enum):
    """成就分类"""
    DEPOSIT = "deposit"           # 存款类
    STREAK = "streak"             # 坚持类
    FAMILY = "family"             # 家庭类
    EQUITY = "equity"             # 股权类
    INVESTMENT = "investment"     # 理财类
    EXPENSE = "expense"           # 支出类
    VOTE = "vote"                 # 投票类
    HIDDEN = "hidden"             # 隐藏彩蛋
    SPECIAL = "special"           # 特殊成就


class AchievementRarity(str, enum.Enum):
    """成就稀有度"""
    COMMON = "common"             # 普通 (N)
    RARE = "rare"                 # 稀有 (R)
    EPIC = "epic"                 # 史诗 (SR)
    LEGENDARY = "legendary"       # 传说 (SSR)
    MYTHIC = "mythic"             # 神话 (UR)


class Achievement(Base):
    """成就定义表"""
    __tablename__ = "achievements"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # 成就代码
    name: Mapped[str] = mapped_column(String(100))  # 成就名称
    description: Mapped[str] = mapped_column(String(500))  # 成就描述
    category: Mapped[str] = mapped_column(String(30))  # 成就分类
    icon: Mapped[str] = mapped_column(String(50))  # 图标(emoji)
    rarity: Mapped[str] = mapped_column(String(20))  # 稀有度
    points: Mapped[int] = mapped_column(default=10)  # 成就点数
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否隐藏成就
    trigger_type: Mapped[str] = mapped_column(String(50))  # 触发类型
    trigger_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 触发值(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    user_achievements: Mapped[List["UserAchievement"]] = relationship(back_populates="achievement")


class UserAchievement(Base):
    """用户成就解锁记录表"""
    __tablename__ = "user_achievements"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    shown: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已在客户端展示过
    
    # 关联关系
    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(back_populates="user_achievements")


# ==================== 股权赠与模型 ====================

class EquityGiftStatus(str, enum.Enum):
    """股权赠与状态"""
    PENDING = "pending"           # 待接收
    ACCEPTED = "accepted"         # 已接收
    REJECTED = "rejected"         # 已拒绝
    EXPIRED = "expired"           # 已过期


class EquityGift(Base):
    """股权赠与记录表"""
    __tablename__ = "equity_gifts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)  # 赠与股权比例(0-1)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 祝福语
    status: Mapped[EquityGiftStatus] = mapped_column(SQLEnum(EquityGiftStatus), default=EquityGiftStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ==================== 股东大会投票模型 ====================

class ProposalStatus(str, enum.Enum):
    """提案状态"""
    VOTING = "voting"             # 投票中
    PASSED = "passed"             # 已通过
    REJECTED = "rejected"         # 未通过
    EXPIRED = "expired"           # 已过期


class Proposal(Base):
    """提案表"""
    __tablename__ = "proposals"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))  # 提案标题
    description: Mapped[str] = mapped_column(Text)  # 提案描述
    options: Mapped[str] = mapped_column(Text)  # 选项(JSON数组)
    status: Mapped[ProposalStatus] = mapped_column(SQLEnum(ProposalStatus), default=ProposalStatus.VOTING)
    deadline: Mapped[datetime] = mapped_column(DateTime)  # 截止时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关联关系
    votes: Mapped[List["Vote"]] = relationship(back_populates="proposal")


class Vote(Base):
    """投票记录表"""
    __tablename__ = "votes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    option_index: Mapped[int] = mapped_column()  # 选择的选项索引
    weight: Mapped[float] = mapped_column(Float)  # 投票权重(股权比例)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    proposal: Mapped["Proposal"] = relationship(back_populates="votes")


# ==================== 家庭公告板模型 ====================

class Announcement(Base):
    """家庭公告表"""
    __tablename__ = "announcements"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)  # 公告内容
    images: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 图片URL(JSON数组)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否置顶
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    likes: Mapped[List["AnnouncementLike"]] = relationship(back_populates="announcement")
    comments: Mapped[List["AnnouncementComment"]] = relationship(back_populates="announcement")


class AnnouncementLike(Base):
    """公告点赞表"""
    __tablename__ = "announcement_likes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(ForeignKey("announcements.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    announcement: Mapped["Announcement"] = relationship(back_populates="likes")


class AnnouncementComment(Base):
    """公告评论表"""
    __tablename__ = "announcement_comments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(ForeignKey("announcements.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(String(500))  # 评论内容
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    announcement: Mapped["Announcement"] = relationship(back_populates="comments")


# ==================== 宠物养成模型 ====================

class PetType(str, enum.Enum):
    """宠物类型 - 可进化"""
    GOLDEN_EGG = "golden_egg"         # Lv.1-9: 金色蛋
    GOLDEN_CHICK = "golden_chick"     # Lv.10-29: 金色小鸡
    GOLDEN_BIRD = "golden_bird"       # Lv.30-59: 金色小鸟
    GOLDEN_PHOENIX = "golden_phoenix" # Lv.60-99: 金色凤凰
    GOLDEN_DRAGON = "golden_dragon"   # Lv.100+: 金色神龙


class FamilyPet(Base):
    """家庭宠物表"""
    __tablename__ = "family_pets"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), unique=True)
    name: Mapped[str] = mapped_column(String(50))  # 宠物昵称
    pet_type: Mapped[str] = mapped_column(String(30), default="golden_egg")  # 宠物类型
    level: Mapped[int] = mapped_column(default=1)  # 等级
    exp: Mapped[int] = mapped_column(default=0)  # 经验值
    happiness: Mapped[int] = mapped_column(default=100)  # 心情值(0-100)
    total_exp: Mapped[int] = mapped_column(default=0)  # 累计总经验值
    last_fed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 上次喂食时间
    last_checkin_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 上次签到时间
    checkin_streak: Mapped[int] = mapped_column(default=0)  # 连续签到天数
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PetExpLog(Base):
    """宠物经验获取记录表"""
    __tablename__ = "pet_exp_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 操作者用户ID
    exp_amount: Mapped[int] = mapped_column()  # 获得的经验值
    source: Mapped[str] = mapped_column(String(50))  # 来源: daily_checkin, deposit, investment, vote, gift
    source_detail: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 详细描述
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== 年度报告模型 ====================

# ==================== 通用申请审批模型 ====================

class ApprovalRequestType(str, enum.Enum):
    """申请类型"""
    DEPOSIT = "deposit"              # 资金注入
    INVESTMENT_CREATE = "investment_create"  # 创建理财产品
    INVESTMENT_UPDATE = "investment_update"  # 更新理财产品
    INVESTMENT_INCOME = "investment_income"  # 登记理财收益
    EXPENSE = "expense"              # 大额支出
    MEMBER_JOIN = "member_join"      # 成员加入（任一成员同意即可）
    MEMBER_REMOVE = "member_remove"  # 成员剔除（需要管理员同意）


class ApprovalRequestStatus(str, enum.Enum):
    """申请状态"""
    PENDING = "pending"          # 待审批
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    CANCELLED = "cancelled"      # 已取消


class ApprovalRequest(Base):
    """通用申请表"""
    __tablename__ = "approval_requests"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    request_type: Mapped[ApprovalRequestType] = mapped_column(SQLEnum(ApprovalRequestType))
    title: Mapped[str] = mapped_column(String(200))  # 申请标题
    description: Mapped[str] = mapped_column(Text)  # 申请描述
    amount: Mapped[float] = mapped_column(Float)  # 涉及金额
    request_data: Mapped[str] = mapped_column(Text)  # 申请数据（JSON格式存储具体参数）
    status: Mapped[ApprovalRequestStatus] = mapped_column(SQLEnum(ApprovalRequestStatus), default=ApprovalRequestStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 执行时间
    
    # 关联关系
    approval_records: Mapped[List["ApprovalRecord"]] = relationship(back_populates="approval_request")


class ApprovalRecord(Base):
    """审批记录表"""
    __tablename__ = "approval_records"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("approval_requests.id"))
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_approved: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    approval_request: Mapped["ApprovalRequest"] = relationship(back_populates="approval_records")


class AnnualReport(Base):
    """年度财务报告表"""
    __tablename__ = "annual_reports"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    year: Mapped[int] = mapped_column()  # 报告年份
    total_deposits: Mapped[float] = mapped_column(Float, default=0)  # 年度总存款
    total_withdrawals: Mapped[float] = mapped_column(Float, default=0)  # 年度总支出
    total_income: Mapped[float] = mapped_column(Float, default=0)  # 年度理财收益
    net_change: Mapped[float] = mapped_column(Float, default=0)  # 净资产变化
    start_balance: Mapped[float] = mapped_column(Float, default=0)  # 年初余额
    end_balance: Mapped[float] = mapped_column(Float, default=0)  # 年末余额
    equity_changes: Mapped[str] = mapped_column(Text)  # 各成员股权变化(JSON)
    monthly_data: Mapped[str] = mapped_column(Text)  # 月度数据(JSON)
    highlights: Mapped[str] = mapped_column(Text)  # 年度亮点(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== 家庭清单模型 ====================

class TodoPriority(str, enum.Enum):
    """任务优先级"""
    HIGH = "high"           # 高优先级
    MEDIUM = "medium"       # 中优先级
    LOW = "low"             # 低优先级


class TodoRepeatType(str, enum.Enum):
    """任务重复类型"""
    NONE = "none"           # 不重复
    DAILY = "daily"         # 每日
    WEEKLY = "weekly"       # 每周
    MONTHLY = "monthly"     # 每月


class TodoList(Base):
    """家庭清单表"""
    __tablename__ = "todo_lists"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    name: Mapped[str] = mapped_column(String(100))  # 清单名称
    icon: Mapped[str] = mapped_column(String(20), default="📋")  # 图标 emoji
    color: Mapped[str] = mapped_column(String(20), default="#667eea")  # 颜色主题
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # 排序顺序
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    items: Mapped[List["TodoItem"]] = relationship(back_populates="todo_list", cascade="all, delete-orphan")


class TodoItem(Base):
    """清单任务项表"""
    __tablename__ = "todo_items"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("todo_lists.id"))
    title: Mapped[str] = mapped_column(String(200))  # 任务标题
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 详细描述
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 指派给谁
    priority: Mapped[TodoPriority] = mapped_column(SQLEnum(TodoPriority), default=TodoPriority.MEDIUM)  # 优先级
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 截止日期
    repeat_type: Mapped[TodoRepeatType] = mapped_column(SQLEnum(TodoRepeatType), default=TodoRepeatType.NONE)  # 重复类型
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否完成
    completed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 完成者
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 完成时间
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # 排序顺序
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    todo_list: Mapped["TodoList"] = relationship(back_populates="items")


# ==================== 共享日历模型 ====================

class CalendarEventCategory(str, enum.Enum):
    """日历事件分类"""
    FAMILY = "family"             # 家庭活动
    PERSONAL = "personal"         # 个人日程
    BIRTHDAY = "birthday"         # 生日纪念日
    FINANCE = "finance"           # 财务提醒
    SYSTEM = "system"             # 系统提醒（自动生成）


class CalendarRepeatType(str, enum.Enum):
    """日历事件重复类型"""
    NONE = "none"                 # 不重复
    DAILY = "daily"               # 每天
    WEEKLY = "weekly"             # 每周
    MONTHLY = "monthly"           # 每月
    YEARLY = "yearly"             # 每年


class CalendarEvent(Base):
    """日历事件表"""
    __tablename__ = "calendar_events"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    title: Mapped[str] = mapped_column(String(200))  # 事件标题
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 详细描述
    category: Mapped[CalendarEventCategory] = mapped_column(
        SQLEnum(CalendarEventCategory), 
        default=CalendarEventCategory.FAMILY
    )  # 事件分类
    start_time: Mapped[datetime] = mapped_column(DateTime)  # 开始时间
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 结束时间
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否全天事件
    repeat_type: Mapped[CalendarRepeatType] = mapped_column(
        SQLEnum(CalendarRepeatType), 
        default=CalendarRepeatType.NONE
    )  # 重复类型
    repeat_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 重复截止日期
    color: Mapped[str] = mapped_column(String(20), default="#667eea")  # 自定义颜色
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 地点
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否系统自动生成
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 来源类型
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 来源ID
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    participants: Mapped[List["CalendarEventParticipant"]] = relationship(
        back_populates="event", 
        cascade="all, delete-orphan"
    )


class CalendarEventParticipant(Base):
    """日历事件参与者表"""
    __tablename__ = "calendar_event_participants"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("calendar_events.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    event: Mapped["CalendarEvent"] = relationship(back_populates="participants")
