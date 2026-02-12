"""
小金库 (Golden Nest) - AI 基础服务

统一的 AI 调用层，封装 OpenAI 兼容格式的 API 调用。
所有需要 AI 能力的模块都应通过此服务调用，不要直接发起 HTTP 请求。

核心特性：
- 支持按功能（function_key）使用不同服务商+模型
- 未配置的功能自动回退到全局活跃服务商
- 内置错误状态报告，方便前端感知
- 429 限流自动重试
- 单例模式，共享 HTTP 连接池

使用示例：
    from app.services.ai_service import ai_service

    # 指定功能的调用（自动选择该功能配置的模型）
    reply = await ai_service.chat("分析...", function_key="transaction_analyze")

    # 不指定 function_key 则使用全局默认
    reply = await ai_service.chat("你好", system_prompt="你是助手")
"""
import json
import logging
import asyncio
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings, get_active_ai_config

logger = logging.getLogger(__name__)


# ==================== 功能模型配置缓存 ====================

@dataclass
class ResolvedAIConfig:
    """解析后的 AI 配置（某功能最终使用的服务商+模型）"""
    api_key: str
    base_url: str
    model: str
    source: str  # "function" | "global" | "env"


# 内存缓存: function_key -> {provider_id, model_name, is_enabled, api_key, base_url}
_function_model_cache: Dict[str, Dict[str, Any]] = {}
_cache_loaded = False


async def load_function_model_configs():
    """从数据库加载所有功能模型配置到内存缓存"""
    global _function_model_cache, _cache_loaded
    try:
        from app.core.database import async_session_maker
        from sqlalchemy import select
        from app.models.models import AIFunctionModelConfig, AIProvider

        async with async_session_maker() as db:
            result = await db.execute(select(AIFunctionModelConfig))
            configs = result.scalars().all()

            cache: Dict[str, Dict[str, Any]] = {}
            for cfg in configs:
                entry: Dict[str, Any] = {
                    "provider_id": cfg.provider_id,
                    "model_name": cfg.model_name,
                    "is_enabled": cfg.is_enabled,
                }

                # 如果指定了 provider_id，预加载该服务商的连接信息
                if cfg.provider_id:
                    provider_result = await db.execute(
                        select(AIProvider).where(
                            AIProvider.id == cfg.provider_id,
                            AIProvider.is_enabled == True
                        )
                    )
                    provider = provider_result.scalar_one_or_none()
                    if provider:
                        entry["api_key"] = provider.api_key
                        entry["base_url"] = provider.base_url
                        # 如果没指定 model_name，使用服务商默认模型
                        if not cfg.model_name:
                            entry["model_name"] = provider.default_model

                cache[cfg.function_key] = entry

            _function_model_cache = cache
            _cache_loaded = True
            logger.info(f"已加载 {len(cache)} 条功能模型配置到缓存")
    except Exception as e:
        logger.warning(f"加载功能模型配置失败: {e}")
        _cache_loaded = True  # 标记已尝试加载，避免重复


async def refresh_function_model_cache():
    """刷新缓存（配置变更后调用）"""
    await load_function_model_configs()


def _get_ai_config(key: str) -> str:
    """获取 AI 配置，优先活跃服务商，回退到 .env"""
    val = get_active_ai_config(key)
    if val:
        return val
    return getattr(settings, key, "")


def _resolve_config_for_function(function_key: str = "") -> ResolvedAIConfig:
    """
    为指定功能解析最终使用的 AI 配置。

    优先级：
    1. 功能专属配置（如果 function_key 在缓存中且指定了 provider_id）
    2. 功能专属模型名（使用全局服务商 + 专属模型）
    3. 全局活跃服务商
    4. .env 配置
    """
    # 尝试从缓存查找该功能的专属配置
    if function_key and function_key in _function_model_cache:
        fc = _function_model_cache[function_key]

        # 功能被禁用
        if not fc.get("is_enabled", True):
            raise ValueError(f"AI 功能 [{function_key}] 已被管理员禁用")

        # 有专属服务商
        if fc.get("api_key") and fc.get("base_url"):
            return ResolvedAIConfig(
                api_key=fc["api_key"],
                base_url=fc["base_url"],
                model=fc.get("model_name", "") or _get_ai_config("AI_MODEL"),
                source="function",
            )

        # 只指定了模型名，使用全局服务商 + 专属模型
        if fc.get("model_name"):
            return ResolvedAIConfig(
                api_key=_get_ai_config("AI_API_KEY"),
                base_url=_get_ai_config("AI_BASE_URL"),
                model=fc["model_name"],
                source="function",
            )

    # 回退到全局配置
    api_key = _get_ai_config("AI_API_KEY")
    base_url = _get_ai_config("AI_BASE_URL")
    model = _get_ai_config("AI_MODEL")
    source = "global" if get_active_ai_config("AI_API_KEY") else "env"

    return ResolvedAIConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        source=source,
    )


class AIService:
    """
    统一 AI 调用服务（OpenAI 兼容格式）

    特性：
    - 支持按功能（function_key）使用不同服务商+模型
    - 自动从配置中读取活跃服务商信息
    - 支持纯文本对话、视觉理解、JSON 结构化输出
    - 内置 429 限流自动重试 + 错误状态报告
    - 单例模式，共享 HTTP 连接池
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    # -------------------- 配置状态 --------------------

    @property
    def is_configured(self) -> bool:
        """AI 服务是否可用（全局）"""
        return bool(
            _get_ai_config("AI_API_KEY")
            and _get_ai_config("AI_BASE_URL")
            and _get_ai_config("AI_MODEL")
        )

    def is_function_configured(self, function_key: str) -> bool:
        """指定功能的 AI 是否可用"""
        try:
            cfg = _resolve_config_for_function(function_key)
            return bool(cfg.api_key and cfg.base_url and cfg.model)
        except ValueError:
            return False

    @property
    def current_model(self) -> str:
        return _get_ai_config("AI_MODEL")

    @property
    def current_base_url(self) -> str:
        return _get_ai_config("AI_BASE_URL")

    def get_function_config_info(self, function_key: str) -> Dict[str, Any]:
        """获取功能的配置详情（供 API 返回错误状态用）"""
        try:
            cfg = _resolve_config_for_function(function_key)
            return {
                "function_key": function_key,
                "configured": bool(cfg.api_key and cfg.base_url and cfg.model),
                "model": cfg.model,
                "source": cfg.source,
                "error": None,
            }
        except ValueError as e:
            return {
                "function_key": function_key,
                "configured": False,
                "model": None,
                "source": None,
                "error": str(e),
            }

    # -------------------- 公开 API --------------------

    async def chat(
        self,
        user_prompt: str,
        *,
        system_prompt: str = "",
        history: list = None,
        model: str = "",
        function_key: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """
        纯文本对话，返回 AI 回复文本。

        Args:
            user_prompt: 用户输入
            system_prompt: 系统提示词（可选）
            history: 历史对话列表（可选）
            model: 强制覆盖模型（可选，优先级最高）
            function_key: 功能标识（可选，用于按功能选择模型）
            max_tokens: 最大输出 token 数
            temperature: 生成温度
        """
        messages = self._build_messages_with_history(system_prompt, user_prompt, history)
        return await self._call_chat(
            messages=messages,
            model=model,
            function_key=function_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def chat_with_vision(
        self,
        text: str,
        image_base64: str,
        *,
        system_prompt: str = "",
        model: str = "",
        function_key: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> str:
        """视觉理解：文本 + 图片 → AI 回复。"""
        if not image_base64.startswith("data:"):
            image_base64 = f"data:image/jpeg;base64,{image_base64}"

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_base64}},
            ],
        })

        return await self._call_chat(
            messages=messages,
            model=model,
            function_key=function_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def chat_json(
        self,
        user_prompt: str,
        *,
        system_prompt: str = "",
        history: list = None,
        model: str = "",
        function_key: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """对话并期望 JSON 结构化输出。"""
        raw = await self.chat(
            user_prompt,
            system_prompt=system_prompt,
            history=history,
            model=model,
            function_key=function_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self.extract_json(raw)

    async def chat_vision_json(
        self,
        text: str,
        image_base64: str,
        *,
        system_prompt: str = "",
        model: str = "",
        function_key: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """视觉理解并期望 JSON 输出。"""
        raw = await self.chat_with_vision(
            text,
            image_base64,
            system_prompt=system_prompt,
            model=model,
            function_key=function_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self.extract_json(raw)

    # -------------------- 底层调用 --------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def _call_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str = "",
        function_key: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """
        底层 chat/completions 调用，含重试逻辑和按功能模型解析。

        优先级：model参数 > function_key配置 > 全局配置 > .env

        Raises:
            ValueError: 配置缺失或 API 调用失败
        """
        # 确保缓存已加载
        if not _cache_loaded:
            await load_function_model_configs()

        # 解析配置
        cfg = _resolve_config_for_function(function_key)

        # model 参数最高优先级
        ai_model = model or cfg.model
        ai_base_url = cfg.base_url
        ai_api_key = cfg.api_key

        if not ai_api_key or not ai_base_url or not ai_model:
            raise ValueError("AI 服务未配置，请联系管理员配置 AI 服务商")

        api_url = f"{ai_base_url.rstrip('/')}/chat/completions"

        request_body = {
            "model": ai_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {ai_api_key}",
            "Content-Type": "application/json",
        }

        fk_tag = f"[{function_key}] " if function_key else ""
        logger.info(f"{fk_tag}AI request → {api_url}, model={ai_model}, source={cfg.source}")

        # 429 自动重试
        max_retries = 2
        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(api_url, json=request_body, headers=headers)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < max_retries:
                    retry_after = min(int(e.response.headers.get("retry-after", "5")), 30)
                    logger.warning(
                        f"{fk_tag}AI rate limited (429), retry after {retry_after}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_after)
                    continue
                logger.error(f"{fk_tag}AI HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 429:
                    raise ValueError("AI 服务请求频率超限，请稍后再试")
                raise ValueError(
                    f"AI 服务调用失败: HTTP {e.response.status_code}"
                    + (f" (功能: {function_key}, 模型: {ai_model})" if function_key else "")
                )
            except httpx.RequestError as e:
                logger.error(f"{fk_tag}AI connection error: {e}")
                raise ValueError(f"AI 服务连接失败: {str(e)}")
        else:
            raise ValueError("AI 服务请求频率超限，请稍后再试")

        # 解析响应
        result = response.json()
        if "choices" not in result or not result["choices"]:
            logger.error(f"{fk_tag}AI unexpected response: {result}")
            raise ValueError("AI 服务返回了意外的结果")

        content = result["choices"][0]["message"]["content"].strip()
        logger.info(f"{fk_tag}AI response ({len(content)} chars): {content[:200]}...")
        return content

    # -------------------- 工具方法 --------------------

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """从 AI 回复中提取 JSON 对象。"""
        if not text:
            return None

        # 去除 <think>...</think> 标签
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

        # 1. 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. markdown 代码块
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 从文本中找 { ... }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def build_messages(
        system_prompt: str, user_prompt: str
    ) -> List[Dict[str, str]]:
        """构建标准 messages 列表（公开工具方法）"""
        return AIService._build_messages(system_prompt, user_prompt)

    @staticmethod
    def _build_messages(
        system_prompt: str, user_prompt: str
    ) -> List[Dict[str, str]]:
        msgs: List[Dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_prompt})
        return msgs

    @staticmethod
    def _build_messages_with_history(
        system_prompt: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """构建带历史对话的 messages 列表"""
        msgs: List[Dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        if history:
            for h in history:
                if h.get("role") in ("user", "assistant") and h.get("content"):
                    msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": user_prompt})
        return msgs

    async def close(self):
        """关闭 HTTP 连接池"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ======================== 全局单例 ========================
ai_service = AIService()
