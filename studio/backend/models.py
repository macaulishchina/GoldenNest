"""
设计院 (Studio) - 数据模型
独立的 ORM 模型，与主项目完全隔离
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, Enum, ForeignKey, JSON,
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


class AiTaskStatus(str, enum.Enum):
    """AI 后台任务状态"""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AiTaskType(str, enum.Enum):
    """AI 任务类型"""
    discuss = "discuss"
    finalize_plan = "finalize_plan"
    auto_review = "auto_review"


# ======================== Models ========================

class Skill(Base):
    """AI 技能定义 — 数据驱动的工作流配置"""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(10), default="🎯")
    description = Column(Text, default="")
    is_builtin = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)

    # AI 对话配置
    role_prompt = Column(Text, nullable=False, default="")
    strategy_prompt = Column(Text, nullable=False, default="")
    tool_strategy_prompt = Column(Text, default="")
    finalization_prompt = Column(Text, default="")
    output_generation_prompt = Column(Text, default="")

    # 阶段流程配置 [{"key": "draft", "label": "草稿", "status": "draft"}, ...]
    stages = Column(JSON, nullable=False, default=list)

    # UI 文案配置 {"project_noun": "需求", "create_title": "...", ...}
    ui_labels = Column(JSON, default=lambda: {})

    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    """需求项目"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.draft, nullable=False)

    # 项目类型 (定义生命周期, 取代旧的 skill_id 1:1 模式)
    project_type = Column(String(50), default="requirement")  # requirement, bug, ...

    # 设计稿
    plan_content = Column(Text, default="")
    plan_version = Column(Integer, default=0)

    # 审查报告 (审查阶段产出)
    review_content = Column(Text, default="")
    review_version = Column(Integer, default=0)

    # GitHub 集成
    github_issue_number = Column(Integer, nullable=True)
    github_pr_number = Column(Integer, nullable=True)
    branch_name = Column(String(200), nullable=True)

    # 工作区管理
    workspace_dir = Column(String(500), nullable=True)  # 项目独立工作区路径 (审查/迭代)
    iteration_count = Column(Integer, default=0)  # 迭代次数

    # 预览
    preview_port = Column(Integer, nullable=True)

    # AI 模型配置
    discussion_model = Column(String(100), default="gpt-4o")
    implementation_model = Column(String(100), default="claude-sonnet-4-20250514")  # DEPRECATED: 不再使用

    # AI 禁言 (群聊模式: 禁言时 AI 不自动回复)
    ai_muted = Column(Boolean, default=False)

    # 技能关联 (DEPRECATED: 用 project_type 代替, 保留用于迁移兼容)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=True)

    # 归档
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)

    # 工具权限 (讨论阶段 AI 可用的代码查看工具)
    # 默认全开 (除 execute_command 需显式授权)
    tool_permissions = Column(JSON, default=lambda: [
        "ask_user", "read_source", "read_config", "search", "tree", "execute_readonly_command"
    ])

    # 元信息
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    skill = relationship("Skill", lazy="joined")  # DEPRECATED: 保留向后兼容
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
    premium_paid = Column(Float, nullable=True)              # Copilot 付费用户定价倍率 (null = 用硬编码)
    premium_free = Column(Float, nullable=True)              # Copilot 免费用户定价倍率 (null = 用硬编码, -1 = 需订阅)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIProvider(Base):
    """
    AI 服务提供商配置

    支持三种类型:
    - github_models: GitHub Models API (内置, 用 GITHUB_TOKEN)
    - copilot: GitHub Copilot API (内置, 用 OAuth Device Flow)
    - openai_compatible: 第三方 OpenAI 兼容 API (用用户提供的 API Key)

    内置提供商 (is_builtin=True) 不可删除、不可改 base_url。
    预设提供商 (is_preset=True) 默认禁用, 用户填入 API Key 后启用。
    """
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), nullable=False, unique=True)       # 唯一标识 (如 "deepseek", "qwen")
    name = Column(String(100), nullable=False)                   # 显示名 (如 "DeepSeek")
    provider_type = Column(String(50), nullable=False)           # github_models / copilot / openai_compatible
    base_url = Column(String(500), default="")                   # API base URL
    api_key = Column(String(500), default="")                    # API Key (明文存储, GET 时脱敏)
    enabled = Column(Boolean, default=False)                     # 是否启用
    is_builtin = Column(Boolean, default=False)                  # 内置 (不可删除)
    is_preset = Column(Boolean, default=False)                   # 预设第三方 (不可删 base_url)
    icon = Column(String(20), default="🔌")                     # Emoji 图标
    description = Column(String(500), default="")                # 说明
    default_models = Column(JSON, default=list)                  # 预设模型列表 [{name, friendly_name, ...}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AiTask(Base):
    """
    AI 后台任务 — 持久化 AI 执行状态

    核心设计: AI 的发言（包括工具调用）作为后台任务执行，不依赖前端连接。
    前端通过订阅任务事件流获取实时进度，断开后可重连继续获取。
    """
    __tablename__ = "ai_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_type = Column(String(50), nullable=False, default="discuss")  # discuss / finalize_plan / auto_review
    status = Column(String(20), nullable=False, default="pending")     # pending / running / completed / failed / cancelled

    # 输入
    model = Column(String(100), default="")
    sender_name = Column(String(100), default="")
    input_message = Column(Text, default="")
    input_attachments = Column(JSON, default=list)
    max_tool_rounds = Column(Integer, default=15)
    regenerate = Column(Boolean, default=False)

    # 累积输出 (用于持久化 + 重连恢复)
    output_content = Column(Text, default="")
    thinking_content = Column(Text, default="")
    tool_calls_data = Column(JSON, default=list)
    token_usage = Column(JSON, nullable=True)
    error_message = Column(Text, default="")

    # 结果
    result_message_id = Column(Integer, nullable=True)  # 最终保存的 Message 的 ID

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project")