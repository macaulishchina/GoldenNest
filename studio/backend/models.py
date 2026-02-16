"""
设计院 (Studio) - 数据模型
独立的 ORM 模型，与主项目完全隔离
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from studio.backend.core.database import Base


# ======================== Enums ========================

class ProjectStatus(str, enum.Enum):
    draft = "draft"
    discussing = "discussing"
    planned = "planned"
    implementing = "implementing"
    reviewing = "reviewing"
    deploying = "deploying"
    deployed = "deployed"
    rolled_back = "rolled_back"
    closed = "closed"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageType(str, enum.Enum):
    chat = "chat"
    plan_draft = "plan_draft"
    plan_final = "plan_final"
    code_review = "code_review"
    image = "image"


class DeployType(str, enum.Enum):
    preview = "preview"
    merge_deploy = "merge_deploy"
    direct_deploy = "direct_deploy"
    rollback = "rollback"


class DeployStatus(str, enum.Enum):
    pending = "pending"
    building = "building"
    deploying = "deploying"
    healthy = "healthy"
    failed = "failed"
    rolled_back = "rolled_back"


# ======================== Models ========================

class Project(Base):
    """需求项目"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.draft, nullable=False)

    # 设计稿
    plan_content = Column(Text, default="")
    plan_version = Column(Integer, default=0)

    # GitHub 集成
    github_issue_number = Column(Integer, nullable=True)
    github_pr_number = Column(Integer, nullable=True)
    branch_name = Column(String(200), nullable=True)

    # 预览
    preview_port = Column(Integer, nullable=True)

    # AI 模型配置
    discussion_model = Column(String(100), default="gpt-4o")
    implementation_model = Column(String(100), default="claude-sonnet-4-20250514")  # DEPRECATED: 不再使用

    # AI 禁言 (群聊模式: 禁言时 AI 不自动回复)
    ai_muted = Column(Boolean, default=False)

    # 工具权限 (讨论阶段 AI 可用的代码查看工具)
    # ⚠️ 默认关闭 — 每轮工具调用消耗额外 1 次 premium request
    tool_permissions = Column(JSON, default=lambda: [])

    # 元信息
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    messages = relationship("Message", back_populates="project", cascade="all, delete-orphan",
                            order_by="Message.created_at")
    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan",
                               order_by="Deployment.started_at.desc()")


class Message(Base):
    """讨论消息"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    sender_name = Column(String(100), default="")
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.chat)

    # 附件 (图片等)
    attachments = Column(JSON, default=list)  # [{"type":"image","url":"...","name":"..."}]

    # AI 元数据
    model_used = Column(String(100), nullable=True)
    token_usage = Column(JSON, nullable=True)  # {"prompt_tokens":x, "completion_tokens":y, "total_tokens":z}

    # 思考过程 (reasoning models)
    thinking_content = Column(Text, nullable=True)

    # 工具调用记录
    tool_calls = Column(JSON, nullable=True)  # [{"id":"...", "name":"...", "arguments":{...}, "result":"..."}]

    # 消息关系 (重试/编辑 → 指向原消息)
    parent_message_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="messages")


class Snapshot(Base):
    """代码快照"""
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    git_commit = Column(String(40), nullable=False)
    git_tag = Column(String(100), nullable=False)
    docker_image_tags = Column(JSON, default=dict)  # {"frontend":"tag","backend":"tag"}
    db_backup_path = Column(String(500), default="")
    description = Column(String(500), default="")
    is_healthy = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Deployment(Base):
    """部署记录"""
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    snapshot_before_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    snapshot_after_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    deploy_type = Column(Enum(DeployType), nullable=False)
    status = Column(Enum(DeployStatus), default=DeployStatus.pending)
    logs = Column(Text, default="")
    error_message = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="deployments")
    snapshot_before = relationship("Snapshot", foreign_keys=[snapshot_before_id])
    snapshot_after = relationship("Snapshot", foreign_keys=[snapshot_after_id])


class CustomModel(Base):
    """
    自定义/补充模型配置

    替代硬编码的 _COPILOT_PRO_EXTRA_MODELS 和 _COPILOT_EXCLUSIVE_MODELS，
    用户可通过设置页面增删改，系统首次启动时从内置种子数据初始化。
    """
    __tablename__ = "custom_models"
    __table_args__ = (
        UniqueConstraint("name", "api_backend", name="uq_custom_model_name_backend"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)              # 模型名 (API 调用用, 如 o1, claude-opus-4-20250514)
    friendly_name = Column(String(200), default="")         # 显示名
    model_family = Column(String(100), default="")          # openai, anthropic, google, ...
    task = Column(String(100), default="chat-completion")   # 任务类型
    tags = Column(JSON, default=list)                       # ["reasoning", "agents", "multimodal"]
    summary = Column(String(500), default="")               # 简介
    api_backend = Column(String(50), default="models")      # "models" = GitHub Models API, "copilot" = Copilot API
    enabled = Column(Boolean, default=True)
    is_seed = Column(Boolean, default=True)                 # True = 内置种子数据, False = 用户自建
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelCapabilityOverride(Base):
    """
    模型能力手动覆盖 (持久化到数据库)

    覆盖优先级最高: DB override > runtime learned > 硬编码静态 > 默认值
    model_name 已归一化 (小写、去掉 copilot: 前缀)
    """
    __tablename__ = "model_capability_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(200), nullable=False, unique=True)  # 归一化名 (小写, 无 copilot: 前缀)
    max_input_tokens = Column(Integer, nullable=True)
    max_output_tokens = Column(Integer, nullable=True)
    supports_vision = Column(Boolean, nullable=True)        # null = 自动检测, true/false = 手动覆盖
    supports_tools = Column(Boolean, nullable=True)
    is_reasoning = Column(Boolean, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
