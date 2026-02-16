"""
设计院 (Studio) - AI 模型管理 API

从 GitHub Models API 动态获取可用模型列表，带本地缓存。
你的 GitHub PAT (Copilot Pro+) 决定了你能用哪些模型。

GitHub Models API 端点:
  GET https://models.inference.ai.azure.com/models
  Authorization: Bearer <GITHUB_TOKEN>
"""
import asyncio
import logging
import re
import time
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from studio.backend.core.config import settings
from studio.backend.core.model_capabilities import capability_cache
from studio.backend.models import ModelCapabilityOverride
from studio.backend.services.copilot_auth import copilot_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio-api/models", tags=["AI Models"])


# ==================== 模型定义 ====================

class ModelInfo(BaseModel):
    """模型信息 (从 GitHub Models API 映射)"""
    id: str = Field(description="模型 ID，用于 API 调用 (Copilot 模型以 'copilot:' 前缀)")
    name: str = Field(description="模型显示名称")
    publisher: str = Field("", description="发布者/厂商 (如 OpenAI, Anthropic)")
    registry: str = Field("", description="注册源 (如 azure-openai, github)")
    description: str = ""
    summary: str = ""
    category: str = Field("discussion", description="discussion / implementation / both")
    max_input_tokens: int = 0
    max_output_tokens: int = 4096
    supports_vision: bool = False
    supports_tools: bool = False
    supports_json_output: bool = False
    is_reasoning: bool = Field(False, description="推理模型需要 max_completion_tokens 替代 max_tokens")
    api_backend: str = Field("models", description="API 后端: models (GitHub Models) / copilot (Copilot API)")
    pricing_tier: str = Field("free", description="定价: free(免费) / premium(消耗高级请求)")
    premium_multiplier: float = Field(0, description="付费用户每次消耗高级请求数 (0=免费, 1=1次, 0.33=⅓次)")
    free_multiplier: Optional[float] = Field(None, description="免费用户每次消耗高级请求数 (None=需订阅, 1=可用)")
    is_deprecated: bool = Field(False, description="是否即将弃用")
    pricing_note: str = Field("", description="定价/弃用说明")
    task: str = Field("", description="模型任务类型 (chat-completion, etc)")
    is_custom: bool = Field(False, description="是否来自 DB 补充模型 (用于全局开关过滤)")
    # 原始数据保留
    raw_capabilities: Dict[str, Any] = Field(default_factory=dict)


# ==================== 模型缓存 ====================

class ModelCache:
    """模型列表缓存，避免每次请求都调 GitHub API"""

    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds  # 默认缓存 10 分钟
        self._models: List[ModelInfo] = []
        self._last_fetch: float = 0
        self._lock = asyncio.Lock()
        self._fetch_error: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return time.time() - self._last_fetch > self.ttl

    @property
    def models(self) -> List[ModelInfo]:
        return self._models

    @property
    def last_error(self) -> Optional[str]:
        return self._fetch_error

    async def get_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """获取模型列表，过期则自动刷新"""
        if not force_refresh and not self.is_expired and self._models:
            return self._models

        async with self._lock:
            # 双检锁 — 其他协程可能已刷新
            if not force_refresh and not self.is_expired and self._models:
                return self._models

            try:
                self._models = await _fetch_github_models()
                self._last_fetch = time.time()
                self._fetch_error = None
                logger.info(f"✅ 从 GitHub Models API 获取到 {len(self._models)} 个模型")
            except Exception as e:
                self._fetch_error = str(e)
                logger.error(f"❌ 获取 GitHub 模型列表失败: {e}")
                # 如果有旧缓存就继续用，不置空
                if not self._models:
                    raise

        return self._models


# 全局单例
_model_cache = ModelCache(ttl_seconds=600)  # 缓存 10 分钟, 手动刷新按钮触发 force_refresh


# ==================== GitHub Models API 调用 ====================

# 已知的强代码实现能力的模型关键字 (用于自动分类)
_STRONG_CODE_KEYWORDS = {
    "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    "o1", "o1-mini", "o3", "o3-mini", "o4-mini",
    "claude-sonnet-4", "claude-3.5-sonnet", "claude-3-opus",
    "deepseek-chat", "deepseek-v3", "deepseek-r1",
    "codestral",
    "mistral-large",
}

# model_family → 显示名映射
_FAMILY_DISPLAY = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "meta": "Meta",
    "mistralai": "Mistral AI",
    "mistral-ai": "Mistral AI",
    "deepseek": "DeepSeek",
    "google": "Google",
    "microsoft": "Microsoft",
    "cohere": "Cohere",
    "ai21 labs": "AI21 Labs",
    "xai": "xAI",
}

# tags → 能力映射
_VISION_TAGS = {"multimodal", "vision", "image"}
_TOOLS_TAGS = {"agents", "tools", "function-calling"}
_REASONING_TAGS = {"reasoning"}

# 已知的推理模型 (需要 max_completion_tokens 替代 max_tokens, 不支持 system prompt)
_REASONING_MODEL_PATTERNS = {"o1", "o3", "o3-mini", "o4-mini"}


# ==================== 定价信息 ====================

# Copilot API 模型定价倍率表 (基于 GitHub Copilot 官方定价)
# 两列: paid = 付费用户倍率 (0=计划内免费, >0=消耗高级请求)
#        free = 免费用户倍率 (1=可用消耗1次高级请求, None=需订阅)
# 来源: https://docs.github.com/en/copilot/concepts/billing/copilot-requests#model-multipliers
# 最后更新: 2026-02-16 (可通过设置页「刷新定价」按钮从官方文档同步)
_COPILOT_PREMIUM_COST: Dict[str, Dict[str, Any]] = {
    # OpenAI — 免费包含模型 (paid plans)
    "gpt-4o": {"paid": 0, "free": 1},
    "gpt-4o-mini": {"paid": 0, "free": 1},
    "gpt-4": {"paid": 0, "free": 1},
    "gpt-4.1": {"paid": 0, "free": 1},
    "gpt-5-mini": {"paid": 0, "free": 1},
    "raptor-mini": {"paid": 0, "free": 1},
    # OpenAI — 高级模型
    "gpt-4.1-mini": {"paid": 0.25, "free": 1},
    "gpt-4.1-nano": {"paid": 0, "free": 1},
    "gpt-5": {"paid": 1.0, "free": None},
    "gpt-5-codex": {"paid": 1.0, "free": None},
    "gpt-5.1": {"paid": 1.0, "free": None},
    "gpt-5.1-codex": {"paid": 1.0, "free": None},
    "gpt-5.1-codex-max": {"paid": 1.0, "free": None},
    "gpt-5.1-codex-mini": {"paid": 0.33, "free": 1},
    "gpt-5.2": {"paid": 1.0, "free": None},
    "gpt-5.2-codex": {"paid": 1.0, "free": None},
    "gpt-5.3-codex": {"paid": 1.0, "free": None},
    "o1": {"paid": 1.0, "free": None},
    "o1-mini": {"paid": 0.5, "free": 1},
    "o3": {"paid": 1.0, "free": None},
    "o3-mini": {"paid": 0.33, "free": 1},
    "o4-mini": {"paid": 0.33, "free": 1},
    # Anthropic
    "claude-sonnet-4": {"paid": 1.0, "free": 1},
    "claude-sonnet-4-20250514": {"paid": 1.0, "free": 1},
    "claude-sonnet-4.5": {"paid": 1.0, "free": None},
    "claude-opus-41": {"paid": 10.0, "free": None},
    "claude-opus-4.5": {"paid": 3.0, "free": None},
    "claude-opus-4.6": {"paid": 3.0, "free": None},
    "claude-opus-4.6-fast": {"paid": 9.0, "free": None},
    "claude-haiku-4.5": {"paid": 0.33, "free": 1},
    "claude-3.5-sonnet": {"paid": 0, "free": 1},
    "claude-3.7-sonnet": {"paid": 1.0, "free": 1},
    # Google
    "gemini-2.0-flash": {"paid": 0.25, "free": 1},
    "gemini-2.5-pro": {"paid": 1.0, "free": None},
    "gemini-3-flash-preview": {"paid": 0.33, "free": 1},
    "gemini-3-pro-preview": {"paid": 1.0, "free": None},
    # xAI
    "grok-3": {"paid": 1.0, "free": None},
    "grok-code-fast-1": {"paid": 0.25, "free": 1},
}

# 已知即将弃用 / 已有更新版本的模型
_DEPRECATED_MODELS: Dict[str, str] = {
    "claude-3.5-sonnet": "建议升级到 Claude Sonnet 4",
}


def _classify_model(model_name: str, task: str, supports_tools: bool) -> str:
    """根据模型名称和能力自动分类: discussion / implementation / both"""
    name_lower = model_name.lower()

    # 非 chat 类 → 不参与
    if task and "chat" not in task and "completion" not in task:
        return "discussion"

    # 已知强代码模型 → both
    for keyword in _STRONG_CODE_KEYWORDS:
        if keyword in name_lower:
            return "both"

    # 支持 tool calling / agents 标签的通常也能写代码
    if supports_tools:
        return "both"

    return "discussion"


def _parse_model(raw: Dict[str, Any], api_backend: str = "models") -> ModelInfo:
    """
    将 GitHub Models API 返回的原始数据解析为 ModelInfo

    api_backend: "models" (GitHub Models API) 或 "copilot" (Copilot API)

    GitHub Models API 响应字段:
      id:             azureml://registries/.../gpt-4o/versions/2 (长路径)
      name:           gpt-4o (短名称, 用于 chat API 调用!)
      friendly_name:  OpenAI GPT-4o (显示名)
      model_family:   openai (厂商)
      model_registry: azure-openai
      task:           chat-completion
      tags:           ["multipurpose", "multilingual", "multimodal"]
      description:    ...
      summary:        ...
    """
    # 关键: name 才是 chat/completions API 用的 model 参数
    model_name = raw.get("name") or raw.get("id", "unknown")
    friendly_name = raw.get("friendly_name") or model_name
    model_family = (raw.get("model_family") or "").lower()
    registry = raw.get("model_registry") or raw.get("registry", "")
    description = raw.get("description") or ""
    summary = raw.get("summary") or ""
    task = raw.get("task") or ""
    tags = set(t.lower() for t in (raw.get("tags") or []))

    # 通过 tags 检测能力
    supports_vision = bool(tags & _VISION_TAGS)
    supports_tools = bool(tags & _TOOLS_TAGS)

    # 额外: 基于模型名的 vision 推断 (描述中明确说支持 image)
    if not supports_vision:
        desc_lower = (description + summary).lower()
        if "image" in desc_lower and "input" in desc_lower:
            supports_vision = True

    # 推理模型检测
    is_reasoning = bool(tags & _REASONING_TAGS)
    # 更精确：已知推理模型
    name_lower = model_name.lower()
    for pattern in _REASONING_MODEL_PATTERNS:
        if name_lower == pattern or name_lower.startswith(pattern + "-"):
            is_reasoning = True
            break

    # publisher 显示名
    publisher = _FAMILY_DISPLAY.get(model_family, raw.get("publisher", model_family))

    # 分类
    category = _classify_model(model_name, task, supports_tools)

    # Copilot API 模型 ID 添加前缀
    model_id = f"copilot:{model_name}" if api_backend == "copilot" else model_name
    # 显示名不添加后端标识 (前端的分组标题已有 ☁️)
    display_name = friendly_name

    # 定价信息
    # 定价信息 (两列: paid=付费用户倍率, free=免费用户倍率)
    free_multiplier: Optional[float] = None
    if api_backend == "copilot":
        pricing_tier = "premium"
        # 精确匹配 → 前缀匹配 (处理带日期后缀的模型如 gpt-4o-2024-08-06)
        pricing_entry = _COPILOT_PREMIUM_COST.get(model_name, None)
        if pricing_entry is None:
            # 尝试前缀匹配 (去掉日期后缀)
            for known_name, entry in _COPILOT_PREMIUM_COST.items():
                if model_name.startswith(known_name):
                    pricing_entry = entry
                    break
        if pricing_entry:
            premium_multiplier = pricing_entry["paid"]
            free_multiplier = pricing_entry.get("free")
        else:
            premium_multiplier = 1.0  # 未知模型默认 1x (可能不准)
            free_multiplier = None
        if premium_multiplier == 0:
            pricing_tier = "free"
            pricing_note = "x0"
        else:
            pricing_note = f"x{premium_multiplier:g}"
    else:
        # GitHub Models API 模型始终免费
        pricing_tier = "free"
        premium_multiplier = 0.0
        free_multiplier = None  # GitHub Models API 不区分
        pricing_note = "x0"

    model_is_deprecated = model_name in _DEPRECATED_MODELS
    if model_is_deprecated:
        pricing_note += f" | {_DEPRECATED_MODELS[model_name]}"

    # Token 限制: 优先从 API 原始数据学习, 否则查能力缓存
    capability_cache.learn_from_api(model_id, raw)
    cap_input, cap_output = capability_cache.get_context_window(model_id)

    return ModelInfo(
        id=model_id,             # copilot:gpt-4o 或 gpt-4o
        name=display_name,       # 显示名
        publisher=publisher,
        registry=registry,
        description=description,
        summary=summary,
        category=category,
        max_input_tokens=cap_input,
        max_output_tokens=cap_output,
        supports_vision=supports_vision,
        supports_tools=supports_tools,
        supports_json_output=False,  # API 未返回此字段
        is_reasoning=is_reasoning,
        api_backend=api_backend,
        pricing_tier=pricing_tier,
        premium_multiplier=premium_multiplier,
        free_multiplier=free_multiplier,
        is_deprecated=model_is_deprecated,
        pricing_note=pricing_note,
        task=task,
        raw_capabilities={"tags": list(tags)},
    )


# ==================== Copilot 动态模型发现 ====================
# 旧硬编码模型列表已迁移到数据库 (custom_models 表)
# 种子数据见 studio/backend/api/model_config.py
# 用户可通过设置页面增删改补充模型

def _guess_family(model_name: str) -> str:
    """根据模型名称猜测 model_family"""
    n = model_name.lower()
    if "claude" in n or "anthropic" in n:
        return "anthropic"
    if "gpt" in n or n.startswith("o1") or n.startswith("o3") or n.startswith("o4"):
        return "openai"
    if "gemini" in n or "google" in n:
        return "google"
    if "grok" in n or "xai" in n:
        return "xai"
    if "deepseek" in n:
        return "deepseek"
    if "mistral" in n or "codestral" in n:
        return "mistral"
    if "llama" in n or "meta" in n:
        return "meta"
    return "unknown"


def _guess_tags(model_name: str) -> list:
    """根据模型名称猜测 tags"""
    n = model_name.lower()
    tags = []
    if any(k in n for k in ("opus", "pro", "sonnet-4", "gpt-4o", "o3", "grok-3")):
        tags.append("multimodal")
    if any(k in n for k in ("o1", "o3", "o4", "3.7", "reasoning", "think")):
        tags.append("reasoning")
    if "flash" in n or "mini" in n or "haiku" in n:
        tags.append("fast")
    tags.append("agents")
    return tags


async def _fetch_copilot_api_models() -> List[Dict[str, Any]]:
    """
    尝试从 Copilot API 动态获取可用模型列表。
    VS Code Copilot 使用 GET https://api.githubcopilot.com/models 获取模型。
    返回原始模型信息列表，失败返回空列表。
    """
    if not copilot_auth.is_authenticated:
        return []

    try:
        session_token = await copilot_auth.ensure_session()
        headers = {
            "Authorization": f"Bearer {session_token}",
            "Accept": "application/json",
            "editor-version": "vscode/1.96.0",
            "editor-plugin-version": "copilot-chat/0.24.0",
            "copilot-integration-id": "vscode-chat",
            "user-agent": "GoldenNest-Studio/1.0",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.githubcopilot.com/models",
                headers=headers,
            )

            if resp.status_code == 200:
                data = resp.json()
                # 兼容多种返回格式
                if isinstance(data, list):
                    raw_list = data
                elif isinstance(data, dict):
                    raw_list = data.get("data") or data.get("models") or data.get("value") or []
                else:
                    raw_list = []

                logger.info(f"Copilot API /models 返回 {len(raw_list)} 个模型")
                return raw_list
            else:
                logger.warning(f"Copilot /models 返回 {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"获取 Copilot 模型列表失败: {e}")

    return []


async def _fetch_github_models() -> List[ModelInfo]:
    """
    获取可用模型列表:
    1. 从 GitHub Models API 动态获取 (backend="models")
    2. 合并 DB 中的 backend="models" 补充模型 (去重)
    3. 如果 Copilot 已授权:
       a. 先尝试 Copilot API 动态获取 (优先)
       b. 失败时回退到 DB 中的 backend="copilot" 模型
    4. 应用 DB 能力覆盖
    """
    token = settings.github_token
    if not token:
        raise RuntimeError("未配置 GITHUB_TOKEN，无法获取模型列表")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    models: List[ModelInfo] = []
    seen_names: set = set()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{settings.github_models_endpoint}/models",
            headers=headers,
        )

        if resp.status_code == 200:
            data = resp.json()
            raw_list = data if isinstance(data, list) else (
                data.get("data") or data.get("models") or data.get("value") or []
            )

            for raw in raw_list:
                try:
                    model = _parse_model(raw)
                    # 只保留 chat 相关模型
                    if model.task and "chat" not in model.task and "completion" not in model.task:
                        continue
                    models.append(model)
                    seen_names.add(model.id.lower())
                except Exception as e:
                    logger.warning(f"解析模型数据失败: {e}, raw={raw.get('name', 'unknown')}")
                    continue

            logger.info(f"GitHub Models API 返回 {len(raw_list)} 个原始模型, 解析出 {len(models)} 个 chat 模型")
        else:
            error_text = resp.text[:500]
            logger.warning(f"GitHub Models API 返回 {resp.status_code}: {error_text}")

    # 从 DB 加载补充模型 (替代原硬编码 _COPILOT_PRO_EXTRA_MODELS)
    db_extra_models = await _load_db_custom_models("models")
    extra_count = 0
    for extra_raw in db_extra_models:
        if extra_raw["name"].lower() not in seen_names:
            try:
                model = _parse_model(extra_raw, api_backend="models")
                model.is_custom = True
                models.append(model)
                seen_names.add(model.id.lower())
                extra_count += 1
            except Exception as e:
                logger.warning(f"解析 DB 补充模型失败: {e}")

    if extra_count:
        logger.info(f"从 DB 补充了 {extra_count} 个 models 后端模型")

    # 添加 Copilot API 专属模型 (如果已授权)
    if copilot_auth.is_authenticated:
        copilot_count = 0
        copilot_seen = set()

        # 先尝试从 Copilot API 动态获取模型列表
        dynamic_models = await _fetch_copilot_api_models()
        _SKIP_PATTERNS = {"embedding", "text-embedding", "oswe-"}
        if dynamic_models:
            for cp_raw in dynamic_models:
                cp_name = (cp_raw.get("id") or cp_raw.get("name") or "").strip()
                if not cp_name:
                    continue
                cp_lower = cp_name.lower()
                if any(pat in cp_lower for pat in _SKIP_PATTERNS):
                    continue
                copilot_id = f"copilot:{cp_lower}"
                if copilot_id in copilot_seen:
                    continue

                # 从 Copilot API 的 capabilities 字段提取丰富能力信息
                caps = cp_raw.get("capabilities", {})
                caps_supports = caps.get("supports", {})
                caps_limits = caps.get("limits", {})

                # 构建 tags: 先用 API 能力数据，再用猜测兜底
                api_tags = set()
                if caps_supports.get("vision"):
                    api_tags.add("multimodal")
                if caps_supports.get("tool_calls"):
                    api_tags.add("agents")
                if caps_supports.get("adaptive_thinking"):
                    api_tags.add("reasoning")
                merged_tags = list(api_tags) if api_tags else _guess_tags(cp_name)

                parsed_raw = {
                    "name": cp_name,
                    "friendly_name": cp_raw.get("name") or cp_raw.get("friendly_name") or cp_name,
                    "model_family": caps.get("family") or cp_raw.get("vendor") or _guess_family(cp_name),
                    "task": caps.get("type", "chat") + "-completion",
                    "tags": merged_tags,
                    "summary": cp_raw.get("summary") or cp_raw.get("description") or "",
                    # 传递 API 原始能力数据，供 learn_from_api 使用
                    "max_input_tokens": caps_limits.get("max_prompt_tokens") or caps_limits.get("max_context_window_tokens") or 0,
                    "max_output_tokens": caps_limits.get("max_output_tokens") or 0,
                }
                try:
                    model = _parse_model(parsed_raw, api_backend="copilot")
                    models.append(model)
                    copilot_seen.add(copilot_id)
                    copilot_count += 1
                except Exception as e:
                    logger.warning(f"解析 Copilot 动态模型失败: {e}")
            logger.info(f"Copilot API 动态发现 {copilot_count} 个模型")
        else:
            # 动态获取失败，回退到 DB 中的 copilot 模型 (替代原硬编码列表)
            db_copilot_models = await _load_db_custom_models("copilot")
            for cp_raw in db_copilot_models:
                cp_name = cp_raw["name"].lower()
                copilot_id = f"copilot:{cp_name}"
                if copilot_id not in copilot_seen:
                    try:
                        model = _parse_model(cp_raw, api_backend="copilot")
                        model.is_custom = True
                        models.append(model)
                        copilot_seen.add(copilot_id)
                        copilot_count += 1
                    except Exception as e:
                        logger.warning(f"解析 DB Copilot 模型失败: {e}")
            logger.info(f"回退使用 DB 配置，{copilot_count} 个 Copilot 模型")

        if copilot_count:
            logger.info(f"添加了 {copilot_count} 个 Copilot API 专属模型")
    else:
        logger.info("Copilot 未授权，跳过 Copilot 专属模型")

    # 应用 DB 能力覆盖 (supports_vision, supports_tools, is_reasoning)
    await _apply_db_capability_overrides(models)

    # 按 publisher 排序，常用模型靠前
    publisher_order = {"OpenAI": 0, "Anthropic": 1, "Google": 2, "DeepSeek": 3, "Mistral AI": 4, "Meta": 5, "xAI": 6, "AI21 Labs": 7}
    models.sort(key=lambda m: (publisher_order.get(m.publisher, 99), m.api_backend, m.name))

    return models


async def _load_db_custom_models(api_backend: str) -> list:
    """从 DB 加载指定后端的自定义模型 (返回与 _parse_model 兼容的 dict 列表)"""
    from studio.backend.core.database import async_session_maker
    try:
        async with async_session_maker() as db:
            from studio.backend.api.model_config import get_custom_models_from_db
            return await get_custom_models_from_db(db, api_backend=api_backend)
    except Exception as e:
        logger.warning(f"从 DB 加载 {api_backend} 自定义模型失败: {e}")
        return []


async def _apply_db_capability_overrides(models: List[ModelInfo]):
    """应用 DB 中的能力覆盖到模型列表 (boolean 能力: vision, tools, reasoning)"""
    from studio.backend.core.database import async_session_maker
    try:
        async with async_session_maker() as db:
            from studio.backend.api.model_config import get_capability_overrides_map
            overrides = await get_capability_overrides_map(db)
            if not overrides:
                return

            for m in models:
                clean = m.id.removeprefix("copilot:").lower()
                ov = overrides.get(clean)
                if not ov:
                    continue
                if ov.supports_vision is not None:
                    m.supports_vision = ov.supports_vision
                if ov.supports_tools is not None:
                    m.supports_tools = ov.supports_tools
                if ov.is_reasoning is not None:
                    m.is_reasoning = ov.is_reasoning
                # token 限制已通过 capability_cache 的 DB override 层处理
                # 这里同步更新 ModelInfo 的显示值
                if ov.max_input_tokens is not None:
                    m.max_input_tokens = ov.max_input_tokens
                if ov.max_output_tokens is not None:
                    m.max_output_tokens = ov.max_output_tokens

            logger.debug(f"应用了 {len(overrides)} 条 DB 能力覆盖")
    except Exception as e:
        logger.warning(f"应用 DB 能力覆盖失败: {e}")


# ==================== Routes ====================

@router.get("", response_model=List[ModelInfo])
async def list_models(
    category: Optional[str] = Query(None, description="筛选: discussion / implementation / both"),
    vision_only: bool = Query(False, description="只返回支持图片的模型"),
    api_backend: Optional[str] = Query(None, description="筛选 API 后端: models / copilot"),
    refresh: bool = Query(False, description="强制刷新缓存"),
    custom_models: bool = Query(True, description="是否包含补充模型 (全局开关)"),
):
    """
    获取可用的 AI 模型列表

    模型列表从 GitHub Models API 动态获取，使用你的 GITHUB_TOKEN 鉴权。
    如果已完成 Copilot OAuth 授权，还会包含 Copilot 专属模型（Claude, Gemini 等）。
    Copilot 模型的 id 以 "copilot:" 前缀标识，用 ☁️ 图标在前端展示。

    缓存 10 分钟，可通过 refresh=true 强制刷新。
    """
    try:
        models = await _model_cache.get_models(force_refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"获取模型列表失败: {str(e)}")

    # 筛选
    result = models
    if not custom_models:
        result = [m for m in result if not m.is_custom]
    if category:
        result = [m for m in result if m.category in (category, "both")]
    if vision_only:
        result = [m for m in result if m.supports_vision]
    if api_backend:
        result = [m for m in result if m.api_backend == api_backend]

    return result


@router.get("/cache-status")
async def get_cache_status():
    """获取模型缓存状态"""
    return {
        "cached_count": len(_model_cache.models),
        "is_expired": _model_cache.is_expired,
        "last_error": _model_cache.last_error,
        "ttl_seconds": _model_cache.ttl,
        "seconds_since_fetch": int(time.time() - _model_cache._last_fetch) if _model_cache._last_fetch else None,
        "copilot_authenticated": copilot_auth.is_authenticated,
    }


@router.post("/refresh")
async def refresh_models():
    """强制刷新模型缓存"""
    try:
        models = await _model_cache.get_models(force_refresh=True)
        return {"success": True, "count": len(models)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"刷新失败: {str(e)}")


@router.get("/capabilities/all")
async def get_all_capabilities():
    """获取所有已知模型的能力数据 (含 API 学习 + 硬编码)"""
    known = capability_cache.get_all_known()
    result = {}
    for model_name, (max_input, max_output) in known.items():
        result[model_name] = {
            "max_input_tokens": max_input,
            "max_output_tokens": max_output,
        }
    return result


class CapabilityUpdate(BaseModel):
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None


@router.patch("/capabilities/{model_id:path}")
async def update_model_capability(model_id: str, data: CapabilityUpdate):
    """手动更新模型能力数据 (前端设置页面调用, 同时持久化到 DB)"""
    current_in, current_out = capability_cache.get_context_window(model_id)
    clean = model_id.removeprefix("copilot:").lower()
    new_in = data.max_input_tokens or current_in
    new_out = data.max_output_tokens or current_out
    capability_cache._learned[clean] = (new_in, new_out)

    # 也持久化到 DB
    try:
        from studio.backend.core.database import async_session_maker
        from sqlalchemy import select
        async with async_session_maker() as db:
            result = await db.execute(
                select(ModelCapabilityOverride).where(ModelCapabilityOverride.model_name == clean)
            )
            override = result.scalar_one_or_none()
            if override:
                if data.max_input_tokens is not None:
                    override.max_input_tokens = data.max_input_tokens
                if data.max_output_tokens is not None:
                    override.max_output_tokens = data.max_output_tokens
            else:
                override = ModelCapabilityOverride(
                    model_name=clean,
                    max_input_tokens=data.max_input_tokens,
                    max_output_tokens=data.max_output_tokens,
                )
                db.add(override)
            await db.commit()
            capability_cache.set_db_override(clean, max_input=override.max_input_tokens, max_output=override.max_output_tokens)
    except Exception as e:
        logger.warning(f"持久化能力覆盖失败: {e}")

    return {
        "ok": True,
        "model": model_id,
        "max_input_tokens": new_in,
        "max_output_tokens": new_out,
    }


@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """获取模型详情"""
    try:
        models = await _model_cache.get_models()
    except Exception:
        raise HTTPException(status_code=503, detail="模型列表不可用")

    for m in models:
        if m.id == model_id:
            return m
    raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在或不在你的可用范围内")


# ==================== 定价刷新 ====================

_PRICING_DOC_URL = "https://docs.github.com/en/copilot/concepts/billing/copilot-requests"


async def _scrape_github_pricing() -> Dict[str, Dict[str, Any]]:
    """
    从 GitHub 官方文档抓取模型定价倍率表。
    页面包含一个 HTML table，列: Model | Multiplier for paid plans | Multiplier for Copilot Free
    返回 {model_name_lower: {"paid": float, "free": float|None}}
    """
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(_PRICING_DOC_URL, headers={
            "Accept": "text/html",
            "User-Agent": "GoldenNest-Studio/1.0",
        })
        if resp.status_code != 200:
            raise RuntimeError(f"获取文档失败: HTTP {resp.status_code}")
        html = resp.text

    # 解析 HTML 中 "Model multipliers" section 的 table
    parsed: Dict[str, Dict[str, Any]] = {}

    # 找到 model-multipliers 部分
    anchor = html.find('id="model-multipliers"')
    if anchor == -1:
        raise RuntimeError("页面中未找到 #model-multipliers 锚点")

    table_section = html[anchor:]
    # 找第一个 <table>
    table_start = table_section.find("<table")
    if table_start == -1:
        raise RuntimeError("未找到定价表格")

    table_end = table_section.find("</table>", table_start)
    table_html = table_section[table_start:table_end]

    # 解析行: <tr><th scope="row">Model</th><td>Paid multiplier</td><td>Free multiplier</td></tr>
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
    cell_pattern = re.compile(r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", re.DOTALL)

    for row_match in row_pattern.finditer(table_html):
        row_html = row_match.group(1)
        cells = cell_pattern.findall(row_html)
        if len(cells) < 2:
            continue

        model_name_raw = re.sub(r"<[^>]+>", "", cells[0]).strip()
        paid_raw = re.sub(r"<[^>]+>", "", cells[1]).strip().lower()

        # 跳过表头行
        if not model_name_raw or model_name_raw.lower() == "model":
            continue

        # 解析付费倍率 (左列: Multiplier for paid plans)
        paid_mult = None
        if "not applicable" not in paid_raw:
            num_match = re.match(r"([\d.]+)", paid_raw)
            if num_match:
                paid_mult = float(num_match.group(1))

        if paid_mult is None:
            continue  # 无法解析付费倍率，跳过

        # 解析免费倍率 (右列: Multiplier for Copilot Free)
        free_mult = None
        if len(cells) >= 3:
            free_raw = re.sub(r"<[^>]+>", "", cells[2]).strip().lower()
            if "not applicable" not in free_raw:
                num_match_f = re.match(r"([\d.]+)", free_raw)
                if num_match_f:
                    free_mult = float(num_match_f.group(1))

        # 标准化模型名（转小写，去掉括号注释但保留核心名）
        clean_name = _normalize_model_name(model_name_raw)
        if clean_name:
            parsed[clean_name] = {"paid": paid_mult, "free": free_mult}

    if not parsed:
        raise RuntimeError("解析定价表失败: 未提取到任何模型数据")

    return parsed


def _normalize_model_name(display_name: str) -> str:
    """
    将 GitHub 文档中的模型显示名标准化为 API 模型 ID。

    如: "Claude Opus 4.6 (fast mode) (preview)" → "claude-opus-4.6-fast"
         "GPT-5.1-Codex-Mini" → "gpt-5.1-codex-mini"
         "Gemini 3 Flash" → "gemini-3-flash-preview" (尝试映射)
    """
    name = display_name.strip()

    # 提取快速模式标记
    is_fast = "(fast mode)" in name.lower() or "(fast)" in name.lower()
    # 去掉括号注释
    name = re.sub(r'\(.*?\)', '', name).strip()

    # 标准化: 空格 → 连字符, 小写
    name = re.sub(r'\s+', '-', name).strip('-').lower()

    if is_fast:
        name += "-fast"

    # 特殊映射 (文档显示名 → API ID)
    _DOC_TO_API = {
        "grok-code-fast-1": "grok-code-fast-1",
        "raptor-mini": "raptor-mini",
        "gemini-3-flash": "gemini-3-flash-preview",
        "gemini-3-pro": "gemini-3-pro-preview",
        "gemini-2.5-pro": "gemini-2.5-pro",
        "claude-opus-4.6-fast": "claude-opus-4.6-fast",
    }
    return _DOC_TO_API.get(name, name)


def _format_pricing_change(old_entry: Dict, new_entry: Dict) -> str:
    """格式化定价变更说明"""
    parts = []
    if old_entry["paid"] != new_entry["paid"]:
        parts.append(f"付费: x{old_entry['paid']:g}→x{new_entry['paid']:g}")
    old_free = old_entry.get("free")
    new_free = new_entry.get("free")
    if old_free != new_free:
        old_f = f"x{old_free:g}" if old_free is not None else "需订阅"
        new_f = f"x{new_free:g}" if new_free is not None else "需订阅"
        parts.append(f"免费: {old_f}→{new_f}")
    return ", ".join(parts) if parts else "数据变更"


@router.post("/pricing/refresh")
async def refresh_pricing():
    """
    从 GitHub 官方文档抓取最新的模型定价倍率表，与当前硬编码表对比。
    返回差异列表 (含付费/免费两列)，供前端二次确认后应用。
    """
    global _COPILOT_PREMIUM_COST

    try:
        scraped = await _scrape_github_pricing()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"抓取官方定价失败: {e}")

    # 对比差异 (两列比较)
    changes: List[Dict[str, Any]] = []
    all_models = set(list(_COPILOT_PREMIUM_COST.keys()) + list(scraped.keys()))

    for model in sorted(all_models):
        old_entry = _COPILOT_PREMIUM_COST.get(model)
        new_entry = scraped.get(model)

        if old_entry is not None and new_entry is not None:
            if old_entry != new_entry:
                changes.append({
                    "model": model,
                    "type": "changed",
                    "old_paid": old_entry["paid"],
                    "new_paid": new_entry["paid"],
                    "old_free": old_entry.get("free"),
                    "new_free": new_entry.get("free"),
                    "note": _format_pricing_change(old_entry, new_entry),
                })
        elif old_entry is not None and new_entry is None:
            changes.append({
                "model": model,
                "type": "removed",
                "old_paid": old_entry["paid"],
                "new_paid": None,
                "old_free": old_entry.get("free"),
                "new_free": None,
                "note": "文档中未列出 (可能已下线)",
            })
        elif new_entry is not None and old_entry is None:
            free_note = f"免费x{new_entry['free']:g}" if new_entry.get("free") is not None else "需订阅"
            changes.append({
                "model": model,
                "type": "added",
                "old_paid": None,
                "new_paid": new_entry["paid"],
                "old_free": None,
                "new_free": new_entry.get("free"),
                "note": f"新模型: 付费x{new_entry['paid']:g}, {free_note}",
            })

    return {
        "has_changes": len(changes) > 0,
        "changes": changes,
        "scraped_count": len(scraped),
        "current_count": len(_COPILOT_PREMIUM_COST),
        "scraped": scraped,  # 完整新表，用于应用
    }


class PricingApplyRequest(BaseModel):
    scraped: Dict[str, Any]  # Dict[str, {"paid": float, "free": float|None}]


@router.post("/pricing/apply")
async def apply_pricing(data: PricingApplyRequest):
    """
    应用新的定价表 (运行时替换内存中的 _COPILOT_PREMIUM_COST)。
    注意: 这只影响运行时，重启后会恢复为代码中的硬编码值。
    同时触发模型缓存刷新以使新定价生效。
    """
    global _COPILOT_PREMIUM_COST
    old_count = len(_COPILOT_PREMIUM_COST)

    # 兼容处理: 新格式 {"paid": x, "free": y} 或旧格式 float
    new_pricing: Dict[str, Dict[str, Any]] = {}
    for model, entry in data.scraped.items():
        if isinstance(entry, dict):
            new_pricing[model] = entry
        else:
            new_pricing[model] = {"paid": float(entry), "free": None}

    _COPILOT_PREMIUM_COST = new_pricing
    # 刷新模型缓存使新定价生效
    try:
        await _model_cache.get_models(force_refresh=True)
    except Exception:
        pass

    return {
        "ok": True,
        "old_count": old_count,
        "new_count": len(_COPILOT_PREMIUM_COST),
        "message": "定价表已更新 (运行时生效，重启后恢复为代码默认值)",
    }


@router.get("/pricing/current")
async def get_current_pricing():
    """获取当前使用的定价表 (两列: paid + free)"""
    return {
        "pricing": _COPILOT_PREMIUM_COST,
        "count": len(_COPILOT_PREMIUM_COST),
        "source": "hardcoded + runtime overrides",
    }
