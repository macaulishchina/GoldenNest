"""
小金库 (Golden Nest) - AI 基础服务

统一的 AI 调用层，封装 OpenAI 兼容格式的 API 调用。
所有需要 AI 能力的模块都应通过此服务调用，不要直接发起 HTTP 请求。

使用示例：
    from app.services.ai_service import ai_service

    # 纯文本对话
    reply = await ai_service.chat("请用一句话总结这段话...", system_prompt="你是...")

    # 带图片的视觉理解
    reply = await ai_service.chat_with_vision(
        text="请描述这张图片",
        image_base64="data:image/jpeg;base64,...",
        system_prompt="你是一个图片分析助手",
    )

    # 结构化 JSON 输出
    data = await ai_service.chat_json("提取以下文本中的金额和日期...", system_prompt="...")
"""
import json
import logging
import asyncio
import re
from typing import Optional, Dict, Any, List, Union

import httpx

from app.core.config import settings, get_active_ai_config

logger = logging.getLogger(__name__)


def _get_ai_config(key: str) -> str:
    """获取 AI 配置，优先活跃服务商，回退到 .env"""
    val = get_active_ai_config(key)
    if val:
        return val
    return getattr(settings, key, "")


class AIService:
    """
    统一 AI 调用服务（OpenAI 兼容格式）

    特性：
    - 自动从配置中读取活跃服务商信息
    - 支持纯文本对话、视觉理解、JSON 结构化输出
    - 内置 429 限流自动重试
    - 单例模式，共享 HTTP 连接池
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    # -------------------- 配置状态 --------------------

    @property
    def is_configured(self) -> bool:
        """AI 服务是否可用"""
        return bool(
            _get_ai_config("AI_API_KEY")
            and _get_ai_config("AI_BASE_URL")
            and _get_ai_config("AI_MODEL")
        )

    @property
    def current_model(self) -> str:
        return _get_ai_config("AI_MODEL")

    @property
    def current_base_url(self) -> str:
        return _get_ai_config("AI_BASE_URL")

    # -------------------- 公开 API --------------------

    async def chat(
        self,
        user_prompt: str,
        *,
        system_prompt: str = "",
        history: list = None,
        model: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """
        纯文本对话，返回 AI 回复文本。

        Args:
            user_prompt: 用户输入
            system_prompt: 系统提示词（可选）
            history: 历史对话列表 [{"role": "user"/"assistant", "content": "..."}]（可选）
            model: 覆盖默认模型（可选）
            max_tokens: 最大输出 token 数
            temperature: 生成温度
        Returns:
            AI 回复的文本内容
        """
        messages = self._build_messages_with_history(system_prompt, user_prompt, history)
        return await self._call_chat(
            messages=messages,
            model=model,
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
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> str:
        """
        视觉理解：文本 + 图片 → AI 回复。

        Args:
            text: 用户文本提示
            image_base64: Base64 图片（可含 data:image/... 前缀）
            system_prompt: 系统提示词
            model: 覆盖默认模型
        Returns:
            AI 回复的文本内容
        """
        # 确保 data URL 格式
        if not image_base64.startswith("data:"):
            image_base64 = f"data:image/jpeg;base64,{image_base64}"

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": image_base64},
                },
            ],
        })

        return await self._call_chat(
            messages=messages,
            model=model,
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
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """
        对话并期望 JSON 结构化输出，自动提取 & 解析 JSON。

        Returns:
            解析后的 dict，解析失败返回 None
        """
        raw = await self.chat(
            user_prompt,
            system_prompt=system_prompt,
            history=history,
            model=model,
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
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """
        视觉理解并期望 JSON 输出。

        Returns:
            解析后的 dict，解析失败返回 None
        """
        raw = await self.chat_with_vision(
            text,
            image_base64,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self.extract_json(raw)

    # -------------------- 底层调用 --------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def _call_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """
        底层 chat/completions 调用，含重试逻辑。

        Raises:
            ValueError: 配置缺失或 API 调用失败
        """
        if not self.is_configured:
            raise ValueError("AI 服务未配置，请联系管理员配置 AI 服务商")

        ai_model = model or _get_ai_config("AI_MODEL")
        ai_base_url = _get_ai_config("AI_BASE_URL")
        ai_api_key = _get_ai_config("AI_API_KEY")
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

        logger.info(f"AI request → {api_url}, model={ai_model}")

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
                        f"AI rate limited (429), retry after {retry_after}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_after)
                    continue
                logger.error(f"AI HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 429:
                    raise ValueError("AI 服务请求频率超限，请稍后再试")
                raise ValueError(f"AI 服务调用失败: HTTP {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"AI connection error: {e}")
                raise ValueError(f"AI 服务连接失败: {str(e)}")
        else:
            raise ValueError("AI 服务请求频率超限，请稍后再试")

        # 解析响应
        result = response.json()
        if "choices" not in result or not result["choices"]:
            logger.error(f"AI unexpected response: {result}")
            raise ValueError("AI 服务返回了意外的结果")

        content = result["choices"][0]["message"]["content"].strip()
        logger.info(f"AI response ({len(content)} chars): {content[:200]}...")
        return content

    # -------------------- 工具方法 --------------------

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        从 AI 回复中提取 JSON 对象。
        支持直接 JSON、markdown 代码块包裹、以及文本中嵌入 JSON 的情况。
        """
        if not text:
            return None

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
