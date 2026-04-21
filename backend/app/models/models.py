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
    FREEZE = "freeze"            # 冻结（用于分红提案）
    UNFREEZE = "unfreeze"        # 解冻（投票未通过时）
    INVESTMENT_BUY = "investment_buy"       # 投资买入（从自由资金购买理财）
    INVESTMENT_REDEEM = "investment_redeem" # 投资赎回（理财赎回到自由资金）
    BET_WIN = "bet_win"                    # 赌注获胜（股权增加）
    BET_LOSE = "bet_lose"                  # 赌注失败（股权减少）
    DAILY_EXPENSE = "daily_expense"        # 日常消费（不影响家庭自由资金）


class ExpenseStatus(str, enum.Enum):
    """支出申请状态"""
    PENDING = "pending"          # 待审批
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    CANCELLED = "cancelled"      # 已取消


class AssetType(str, enum.Enum):
    """资产类型（原理财类型）"""
    CASH = "cash"                # 活期现金
    TIME_DEPOSIT = "time_deposit"  # 定期存款（原deposit）
    FUND = "fund"                # 基金
    STOCK = "stock"              # 股票
    BOND = "bond"                # 债券
    OTHER = "other"              # 其他

# 向后兼容：InvestmentType 作为 AssetType 的别名
InvestmentType = AssetType


class CurrencyType(str, enum.Enum):
    """货币类型"""
    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    HKD = "HKD"  # 港元
    JPY = "JPY"  # 日元
    EUR = "EUR"  # 欧元
    GBP = "GBP"  # 英镑
    AUD = "AUD"  # 澳元
    CAD = "CAD"  # 加元
    SGD = "SGD"  # 新加坡元
    KRW = "KRW"  # 韩元


class PositionOperationType(str, enum.Enum):
    """持仓操作类型"""
    CREATE = "create"            # 创建投资
    INCREASE = "increase"        # 增持
    DECREASE = "decrease"        # 减持
    UPDATE = "update"            # 更新信息
    DELETE = "delete"            # 删除投资


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
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 手机号
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 性别: male/female/other
    birthday: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 生日: YYYY-MM-DD
    bio: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 个人简介
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    family_memberships: Mapped[List["FamilyMember"]] = relationship(back_populates="user")
    deposits: Mapped[List["Deposit"]] = relationship(back_populates="user")
    expense_requests: Mapped[List["ExpenseRequest"]] = relationship(back_populates="requester", foreign_keys="ExpenseRequest.requester_id")
    expense_approvals: Mapped[List["ExpenseApproval"]] = relationship(back_populates="approver")
    achievements: Mapped[List["UserAchievement"]] = relationship(back_populates="user")

    # 宠物互动统计（每用户独立）
    pet_last_checkin_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pet_checkin_streak: Mapped[int] = mapped_column(Integer, default=0)
    pet_daily_game_counts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pet_daily_feed_counts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


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
    """理财配置表（将重命名为Asset - 资产登记表）"""
    __tablename__ = "investments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 🌟 NEW: 资产归属人
    name: Mapped[str] = mapped_column(String(100))  # 理财产品名称
    investment_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType))  # 使用AssetType
    
    # 💰 多币种支持
    currency: Mapped[CurrencyType] = mapped_column(SQLEnum(CurrencyType), default=CurrencyType.CNY)  # 🌟 NEW: 货币类型
    foreign_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 NEW: 外币金额
    exchange_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 NEW: 汇率（外币→CNY）
    
    principal: Mapped[float] = mapped_column(Float)  # 本金（CNY，用于股权计算）
    start_date: Mapped[datetime] = mapped_column(DateTime)  # 开始日期
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 到期日期
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 🌟 NEW: 银行/机构名称
    deduct_from_cash: Mapped[bool] = mapped_column(Boolean, default=False)  # 🌟 NEW: 是否从活期扣除
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)  # 添加索引
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 添加索引
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 删除时间
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_data: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 凭证图片路径
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    family: Mapped["Family"] = relationship(back_populates="investments")
    user: Mapped[Optional["User"]] = relationship(foreign_keys=[user_id])  # 🌟 NEW: 归属人关系
    income_records: Mapped[List["InvestmentIncome"]] = relationship(back_populates="investment")
    positions: Mapped[List["InvestmentPosition"]] = relationship(back_populates="investment")

# 🌟 NEW: Asset作为Investment的别名（逐步迁移）
Asset = Investment


class InvestmentIncome(Base):
    """理财收益记录表（将重命名为AssetIncome）"""
    __tablename__ = "investment_incomes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investment_id: Mapped[int] = mapped_column(ForeignKey("investments.id"))
    
    # 💰 多币种支持
    foreign_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 NEW: 外币收益金额
    exchange_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 NEW: 收益时汇率
    
    amount: Mapped[float] = mapped_column(Float)  # CNY收益金额（计入活期）
    current_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 当前总价值（新模式）
    calculated_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 计算出的收益（新模式）
    income_date: Mapped[datetime] = mapped_column(DateTime)  # 收益日期
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_data: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 凭证图片路径
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    investment: Mapped["Investment"] = relationship(back_populates="income_records")

# 🌟 NEW: AssetIncome作为InvestmentIncome的别名
AssetIncome = InvestmentIncome


class InvestmentPosition(Base):
    """投资持仓变动记录表（将重命名为AssetPosition）"""
    __tablename__ = "investment_positions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investment_id: Mapped[int] = mapped_column(ForeignKey("investments.id"))
    operation_type: Mapped[PositionOperationType] = mapped_column(SQLEnum(PositionOperationType))
    
    # 💰 多币种支持
    foreign_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 NEW: 外币金额变化
    exchange_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 🌟 NEW: 本次操作汇率
    
    amount: Mapped[float] = mapped_column(Float)  # CNY金额变化（用于股权计算）
    principal_before: Mapped[float] = mapped_column(Float, default=0)  # 操作前本金（CNY）
    principal_after: Mapped[float] = mapped_column(Float)  # 操作后本金（CNY）
    operation_date: Mapped[datetime] = mapped_column(DateTime)  # 操作日期
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_data: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 凭证图片路径
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transactions.id"), nullable=True)  # 关联资金流水
    deposit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deposits.id"), nullable=True)  # 关联权益记录
    approval_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("approval_requests.id"), nullable=True)  # 关联审批
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    investment: Mapped["Investment"] = relationship(back_populates="positions")

# 🌟 NEW: AssetPosition作为InvestmentPosition的别名
AssetPosition = InvestmentPosition


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
    """资金流水表 - 记录活期资产的变化"""
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType))
    amount: Mapped[float] = mapped_column(Float)  # 金额（正数为入账，负数为出账）
    balance_after: Mapped[float] = mapped_column(Float)  # 🌟 交易后的活期余额（仅CNY活期资产，不含投资）
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
    gift_money: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 赠与绝对金额(元)，用于精确转账
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
    # 宠物互动深化字段
    daily_feed_counts: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)  # JSON: 每日喂食计数
    daily_game_counts: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)  # JSON: 每日游戏计数
    claimed_milestones: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)  # JSON: 已领取里程碑
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 最近互动时间
    game_sessions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)  # JSON: 游戏会话状态


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
    ASSET_CREATE = "asset_create"    # 🌟 NEW: 资产登记（统一入口）
    DEPOSIT = "deposit"              # 资金注入（保留兼容）
    INVESTMENT_CREATE = "investment_create"  # 创建理财产品（保留兼容）
    INVESTMENT_UPDATE = "investment_update"  # 更新理财产品
    INVESTMENT_INCOME = "investment_income"  # 登记理财收益
    INVESTMENT_INCREASE = "investment_increase"  # 投资增持
    INVESTMENT_DECREASE = "investment_decrease"  # 投资减持
    INVESTMENT_DELETE = "investment_delete"  # 删除投资产品
    EXPENSE = "expense"              # 大额支出
    DIVIDEND_CLAIM = "dividend_claim"  # 分红领取处理
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
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), index=True)  # 添加索引
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 🌟 NEW: 目标用户（用于个人专属审核）
    request_type: Mapped[ApprovalRequestType] = mapped_column(SQLEnum(ApprovalRequestType))
    title: Mapped[str] = mapped_column(String(200))  # 申请标题
    description: Mapped[str] = mapped_column(Text)  # 申请描述
    amount: Mapped[float] = mapped_column(Float)  # 涉及金额
    request_data: Mapped[str] = mapped_column(Text)  # 申请数据（JSON格式存储具体参数）
    status: Mapped[ApprovalRequestStatus] = mapped_column(SQLEnum(ApprovalRequestStatus), default=ApprovalRequestStatus.PENDING, index=True)  # 添加索引
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 执行时间
    execution_failed: Mapped[bool] = mapped_column(Boolean, default=False)  # 执行失败标记
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 失败原因
    
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


# ==================== 分红系统模型 ====================

class DividendType(str, enum.Enum):
    """分红类型"""
    PROFIT = "profit"             # 理财收益分红
    CASH = "cash"                 # 自有资金分红


class DividendStatus(str, enum.Enum):
    """分红状态"""
    VOTING = "voting"             # 投票中
    APPROVED = "approved"         # 已批准，待分配
    DISTRIBUTING = "distributing" # 分配中（已创建个人审核）
    COMPLETED = "completed"       # 已完成（所有成员处理完毕）
    REJECTED = "rejected"         # 已拒绝


class DividendClaimStatus(str, enum.Enum):
    """分红领取状态"""
    PENDING = "pending"           # 待处理
    REINVESTED = "reinvested"     # 已再投
    WITHDRAWN = "withdrawn"       # 已提现


class Dividend(Base):
    """分红记录表"""
    __tablename__ = "dividends"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    type: Mapped[DividendType] = mapped_column(SQLEnum(DividendType))  # 分红类型
    total_amount: Mapped[float] = mapped_column(Float)  # 分红总额
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"))  # 关联投票提案
    status: Mapped[DividendStatus] = mapped_column(SQLEnum(DividendStatus), default=DividendStatus.VOTING)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 发起人
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 批准时间
    distributed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 分配时间
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 完成时间
    
    # 关联关系
    claims: Mapped[List["DividendClaim"]] = relationship(back_populates="dividend", cascade="all, delete-orphan")


class DividendClaim(Base):
    """分红领取记录表"""
    __tablename__ = "dividend_claims"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dividend_id: Mapped[int] = mapped_column(ForeignKey("dividends.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 领取人
    amount: Mapped[float] = mapped_column(Float)  # 分红金额
    equity_ratio: Mapped[float] = mapped_column(Float)  # 当时的股权比例（快照）
    status: Mapped[DividendClaimStatus] = mapped_column(SQLEnum(DividendClaimStatus), default=DividendClaimStatus.PENDING)
    reinvest: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # 是否再投
    deposit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deposits.id"), nullable=True)  # 如果再投，关联的Deposit记录
    approval_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("approval_requests.id"), nullable=True)  # 关联审核
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 处理时间
    
    # 关联关系
    dividend: Mapped["Dividend"] = relationship(back_populates="claims")


# ==================== 家庭赌注系统 ====================

class BetStatus(str, enum.Enum):
    """赌注状态"""
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待审批
    ACTIVE = "active"         # 进行中（下注阶段）
    AWAITING_RESULT = "awaiting_result"  # 等待结果登记（截止后，创建者登记结果）
    RESULT_PENDING = "result_pending"    # 结果待确认（参与者审批中）
    SETTLED = "settled"       # 已结算
    CANCELLED = "cancelled"   # 已取消


class Bet(Base):
    """家庭赌注表"""
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[BetStatus] = mapped_column(SQLEnum(BetStatus), default=BetStatus.DRAFT)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)  # 下注截止时间
    settlement_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    declared_winning_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bet_options.id", use_alter=True), nullable=True)  # 创建者登记的获胜选项
    approval_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("approval_requests.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联关系
    participants: Mapped[List["BetParticipant"]] = relationship(back_populates="bet", cascade="all, delete-orphan")
    options: Mapped[List["BetOption"]] = relationship(back_populates="bet", cascade="all, delete-orphan", foreign_keys="[BetOption.bet_id]")


class BetParticipant(Base):
    """赌注参与者表"""
    __tablename__ = "bet_participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bets.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    selected_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bet_options.id"), nullable=True)
    stake_amount: Mapped[float] = mapped_column(Float, default=0.0)  # 股份押注（可为0）
    stake_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 其他押注内容
    is_winner: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联关系
    bet: Mapped["Bet"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()
    selected_option: Mapped[Optional["BetOption"]] = relationship()


class BetOption(Base):
    """赌注选项表"""
    __tablename__ = "bet_options"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bets.id"))
    option_text: Mapped[str] = mapped_column(String(200))
    is_winning_option: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联关系
    bet: Mapped["Bet"] = relationship(back_populates="options", foreign_keys=[bet_id])


# ==================== 记账系统 ====================

class AccountingCategory(str, enum.Enum):
    """记账分类 - 兼容历史数据，新增分类带后缀区分"""
    # 原有分类（保留兼容）
    FOOD = "food"                      # 餐饮
    TRANSPORT = "transport"            # 交通
    SHOPPING = "shopping"              # 购物
    ENTERTAINMENT = "entertainment"    # 娱乐
    HEALTHCARE = "healthcare"          # 医疗
    EDUCATION = "education"            # 教育
    HOUSING = "housing"                # 住房
    UTILITIES = "utilities"            # 水电煤
    OTHER = "other"                    # 其他

    # 新增分类
    COMMUNICATION = "communication"    # 通讯（手机费、网络费）
    CLOTHING = "clothing"              # 服装鞋帽
    BEAUTY = "beauty"                  # 美容美发
    PET = "pet"                        # 宠物
    INSURANCE = "insurance"            # 保险
    GIFT = "gift"                      # 礼品红包
    TRAVEL = "travel"                  # 旅行
    FITNESS = "fitness"                # 运动健身
    APPLIANCES = "appliances"          # 家用电器
    MAINTENANCE = "maintenance"        # 维修维护
    TAX = "tax"                        # 税费
    INVESTMENT = "investment"          # 投资理财
    INCOME = "income"                  # 收入
    SALARY = "salary"                  # 工资
    REIMBURSEMENT = "reimbursement"    # 报销
    TRANSFER = "transfer"              # 转账
    REFUND = "refund"                  # 退款
    SUBSIDY = "subsidy"                # 补贴
    BONUS = "bonus"                    # 奖金
    ALLOWANCE = "allowance"            # 津贴


class AccountingEntrySource(str, enum.Enum):
    """记账来源"""
    MANUAL = "manual"    # 手动输入
    PHOTO = "photo"      # 拍照识别
    VOICE = "voice"      # 语音输入
    IMPORT = "import"    # 批量导入
    AUTO = "auto"        # 自动生成


class AccountingEntry(Base):
    """记账条目表"""
    __tablename__ = "accounting_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 记账人
    consumer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 消费人（可为空，表示家庭共同消费）
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[AccountingCategory] = mapped_column(SQLEnum(AccountingCategory))
    description: Mapped[str] = mapped_column(String(500))
    entry_date: Mapped[datetime] = mapped_column(DateTime)  # 消费日期
    source: Mapped[AccountingEntrySource] = mapped_column(SQLEnum(AccountingEntrySource), default=AccountingEntrySource.MANUAL)
    image_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 照片Base64数据（拍照识别时）
    is_accounted: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已入账（转为支出申请）
    expense_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("expense_requests.id"), nullable=True)  # 关联的支出申请
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联关系
    family: Mapped["Family"] = relationship(foreign_keys=[family_id])
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    consumer: Mapped[Optional["User"]] = relationship(foreign_keys=[consumer_id])
    expense_request: Mapped[Optional["ExpenseRequest"]] = relationship(foreign_keys=[expense_request_id])


# ==================== AI 服务商配置模型 ====================

class AIProvider(Base):
    """AI 服务商配置表（支持配置多个服务商，切换活跃服务商）"""
    __tablename__ = "ai_providers"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # 服务商显示名称（如"通义千问"、"OpenAI"）
    provider_type: Mapped[str] = mapped_column(String(30))  # 服务商类型标识（如 qwen, openai, deepseek, zhipu, moonshot）
    api_key: Mapped[str] = mapped_column(Text, default="")  # API Key（敏感信息，前端脱敏显示）
    base_url: Mapped[str] = mapped_column(String(500), default="")  # API Base URL
    default_model: Mapped[str] = mapped_column(String(100), default="")  # 默认模型（从可用模型中选择）
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 是否为当前活跃服务商（全局唯一一个）
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否启用（可关闭但保留配置）
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIFunctionModelConfig(Base):
    """AI 功能模型配置表 — 为每个 AI 功能单独指定服务商+模型

    未配置的功能自动使用全局活跃服务商（AIProvider.is_active=True）的默认模型。
    管理员可以为不同功能指定不同的模型，实现精细化成本/效果控制。
    """
    __tablename__ = "ai_function_model_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    function_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # 功能标识，对应 ai_functions.py 的 key
    provider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_providers.id"), nullable=True)  # 指定服务商，null 表示跟随全局
    model_name: Mapped[str] = mapped_column(String(100), default="")  # 指定模型名称，空字符串表示跟随服务商默认模型
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 该功能的 AI 能力是否启用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== AI 技能管理模型 ====================

class AISkill(Base):
    """AI 技能表 — 每个 function_key 可有多套提示词实现，激活的那套生效

    设计理念：功能点是固定的（由 ai_functions.py 注册），但同一个功能点可以有多种 prompt 实现。
    管理员可以编辑、新增、删除不同的技能实现，通过 is_active 切换当前生效的版本。
    """
    __tablename__ = "ai_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    function_key: Mapped[str] = mapped_column(String(50), index=True)                 # 对应 AI_FUNCTION_REGISTRY 的 key
    name: Mapped[str] = mapped_column(String(100))                                     # 技能名称（如"默认"、"简洁版"、"专业版"）
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)            # 技能说明
    system_prompt: Mapped[str] = mapped_column(Text, default="")                       # 系统提示词模板，支持 $variable 占位符
    user_prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # 用户提示词模板，为空时由调用方传入
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)             # JSON: {"temperature": 0.7, "max_tokens": 2000, "top_p": 1.0}
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)        # 同一 function_key 仅一个激活
    sort_order: Mapped[int] = mapped_column(Integer, default=0)                        # 排序
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联附件
    attachments: Mapped[List["AISkillAttachment"]] = relationship(
        "AISkillAttachment", back_populates="skill", cascade="all, delete-orphan",
        order_by="AISkillAttachment.sort_order"
    )


class AISkillAttachment(Base):
    """AI 技能附件 — 为技能提供额外的上下文数据（参考文档、示例数据等）

    inject_mode 决定附件内容如何注入到 prompt 中：
    - system_append: 追加到 system prompt 末尾
    - user_prepend: 插入到 user prompt 前面
    - reference: 作为独立参考段落嵌入 system prompt（带标题）
    """
    __tablename__ = "ai_skill_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("ai_skills.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))                 # 附件名称
    file_type: Mapped[str] = mapped_column(String(20), default="text")  # text / markdown / json / csv
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 内联内容
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 大文件路径
    inject_mode: Mapped[str] = mapped_column(String(20), default="system_append")  # system_append / user_prepend / reference
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联
    skill: Mapped["AISkill"] = relationship("AISkill", back_populates="attachments")


class ExternalApp(Base):
    """第三方外部应用配置表 — 全局配置，所有用户可用"""
    __tablename__ = "external_apps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))                          # 应用名称
    url: Mapped[str] = mapped_column(String(500))                           # 应用 URL
    icon_type: Mapped[str] = mapped_column(String(10), default="emoji")     # 图标类型：emoji / image
    icon_emoji: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)   # emoji 字符
    icon_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 图标图片路径
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True) # 简短描述
    open_mode: Mapped[str] = mapped_column(String(20), default="new_tab")   # 打开方式：new_tab / fullscreen
    sort_order: Mapped[int] = mapped_column(Integer, default=0)             # 排序权重（越小越靠前）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)          # 是否激活（控制是否展示给用户）
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
