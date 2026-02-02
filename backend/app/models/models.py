"""
小金库 (Golden Nest) - 数据库模型
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
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
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 头像URL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    family_memberships: Mapped[List["FamilyMember"]] = relationship(back_populates="user")
    deposits: Mapped[List["Deposit"]] = relationship(back_populates="user")
    expense_requests: Mapped[List["ExpenseRequest"]] = relationship(back_populates="requester", foreign_keys="ExpenseRequest.requester_id")
    expense_approvals: Mapped[List["ExpenseApproval"]] = relationship(back_populates="approver")


# ==================== 家庭模型 ====================

class Family(Base):
    """家庭表"""
    __tablename__ = "families"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))  # 家庭名称
    savings_target: Mapped[float] = mapped_column(Float, default=2000000.0)  # 储蓄目标
    equity_rate: Mapped[float] = mapped_column(Float, default=0.03)  # 时间加权年化利率
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # 邀请码
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
