"""
设计院 (Studio) - AI 对话服务

支持双 API 后端:
  1. GitHub Models API (models.inference.ai.azure.com) - 用 PAT 直接调用
  2. GitHub Copilot API (api.githubcopilot.com) - 用 OAuth 授权, 支持所有 Copilot 模型 (含 Claude)

模型 ID 以 "copilot:" 前缀区分后端:
  - "gpt-4o"          → GitHub Models API
  - "copilot:gpt-4o"  → Copilot API

SSE 事件协议 (chat_stream yield 结构化 dict):
  {"type": "content",    "content": "..."}            - 文本内容
  {"type": "thinking",   "content": "..."}            - 推理过程 (reasoning models)
  {"type": "tool_call",  "tool_call": {...}}          - AI 请求调用工具
  {"type": "tool_result", "tool_call_id": "...", ...} - 工具执行结果
  {"type": "tool_error", "tool_call_id": "...", ...}  - 工具执行失败
  {"type": "usage",      "usage": {...}}              - token 使用统计
  {"type": "error",      "error": "..."}              - 错误信息
"""
import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable, Awaitable, Set

import httpx

from studio.backend.core.config import settings
from studio.backend.core.model_capabilities import capability_cache
from studio.backend.core.token_utils import estimate_tokens, estimate_messages_tokens, truncate_text
from studio.backend.services.copilot_auth import copilot_auth, COPILOT_CHAT_URL

logger = logging.getLogger(__name__)

# ==================== Copilot 计费会话管理 ====================
# VS Code 的 Copilot 计费机制:
#   - 每条用户消息生成一个新的 x-request-id
#   - 该消息内的工具调用轮次复用同一个 x-request-id
#   - GitHub 后端通过 x-request-id 将同一轮对话的多次 API 调用归集为一次 premium request
#   - vscode-sessionid 和 vscode-machineid 用于计费上下文关联
#
# 正确实现: 每次调用 chat_stream() 生成新 request_id，
# 该次调用内所有工具轮次复用同一个 ID。

# 应用实例级 session ID (启动时生成一次, 稳定用于计费关联)
_STUDIO_SESSION_ID = str(uuid.uuid4()) + str(int(time.time() * 1000))
_STUDIO_MACHINE_ID = hashlib.sha256(
    f"{os.uname().nodename}-{settings.data_path}-studio".encode()
).hexdigest()


def new_request_id() -> str:
    """每次用户消息生成新的 request_id

    工具调用轮次内复用同一个 ID (chat_stream 内部处理)。
    这样 GitHub 后端将同一个 request_id 的多次 API 调用归集为一次 premium request。
    """
    rid = str(uuid.uuid4())
    logger.info(f"新消息 request_id: {rid[:8]}...")
    return rid

def _parse_error_metadata(status_code: int, error_text: str, model: str) -> Dict[str, Any]:
    """从 API 错误响应中提取结构化元数据 (供前端展示和模型能力学习)"""
    meta: Dict[str, Any] = {"status_code": status_code, "model": model}

    lower = error_text.lower()

    # 速率限制
    if status_code == 429 or "rate limit" in lower:
        meta["error_type"] = "rate_limit"
        m = re.search(r'Rate limit of (\d+) per (\d+)s', error_text, re.I)
        if m:
            meta["rate_limit"] = f"{m.group(1)} per {m.group(2)}s"
            meta["rate_limit_count"] = int(m.group(1))
            meta["rate_limit_seconds"] = int(m.group(2))
        m = re.search(r'(\d+) per (\d+) (second|minute|hour)', error_text, re.I)
        if m and "rate_limit" not in meta:
            unit_map = {"second": 1, "minute": 60, "hour": 3600}
            secs = int(m.group(2)) * unit_map.get(m.group(3).lower(), 1)
            meta["rate_limit"] = f"{m.group(1)} per {secs}s"
            meta["rate_limit_count"] = int(m.group(1))
            meta["rate_limit_seconds"] = secs
        m = re.search(r'wait\s+(\d+)\s*seconds?', error_text, re.I)
        if m:
            meta["wait_seconds"] = int(m.group(1))

    # 上下文/token 超限
    elif "context length" in lower or "too large" in lower or "max_tokens" in lower:
        meta["error_type"] = "context_overflow"
        m = re.search(r'maximum context length.*?(\d{3,})', error_text, re.I)
        if m:
            meta["max_context_tokens"] = int(m.group(1))
        m = re.search(r'Max size:\s*(\d+)\s*tokens', error_text, re.I)
        if m:
            meta["max_context_tokens"] = int(m.group(1))
        m = re.search(r'requested\s+(\d+)\s*tokens', error_text, re.I)
        if m:
            meta["requested_tokens"] = int(m.group(1))

    # 认证错误
    elif status_code in (401, 403):
        meta["error_type"] = "auth_error"

    else:
        meta["error_type"] = "unknown"

    return meta


# GitHub Models API 端点
GITHUB_MODELS_URL = settings.github_models_endpoint

# Copilot API 前缀标识
COPILOT_PREFIX = "copilot:"

# 推理模型需要特殊参数处理 (max_completion_tokens 替代 max_tokens, 不支持 system 消息)
_REASONING_MODEL_PREFIXES = ("o1", "o3", "o4")


def _is_reasoning_model(model: str) -> bool:
    """检测是否为推理模型"""
    name = model.lower().removeprefix(COPILOT_PREFIX.lower())
    for prefix in _REASONING_MODEL_PREFIXES:
        if name == prefix or name.startswith(prefix + "-"):
            return True
    return False


def _is_copilot_model(model: str) -> bool:
    """检测是否使用 Copilot API 后端"""
    return model.startswith(COPILOT_PREFIX)


def _get_actual_model_name(model: str) -> str:
    """提取实际模型名 (去掉 copilot: 前缀)"""
    if model.startswith(COPILOT_PREFIX):
        return model[len(COPILOT_PREFIX):]
    return model


async def _get_copilot_headers(request_id: str = "") -> Dict[str, str]:
    """获取 Copilot API 请求头

    Args:
        request_id: 计费归集 ID。
                    同一个 request_id 下的所有 API 调用 (包括工具调用轮次)
                    会被 GitHub 后端归集为一次 premium request。
                    每条用户消息应使用新的 request_id (new_request_id())。
    """
    session_token = await copilot_auth.ensure_session()
    return {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json",
        "editor-version": "vscode/1.96.0",
        "editor-plugin-version": "copilot-chat/0.24.0",
        "copilot-integration-id": "vscode-chat",
        "openai-intent": "conversation-panel",
        "user-agent": "GoldenNest-Studio/1.0",
        # 计费归集头 — 同一 request_id 的工具调用轮次合并计费
        "x-request-id": request_id or str(uuid.uuid4()),
        "vscode-sessionid": _STUDIO_SESSION_ID,
        "vscode-machineid": _STUDIO_MACHINE_ID,
    }


def _get_models_headers() -> Dict[str, str]:
    """获取 GitHub Models API 请求头"""
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Content-Type": "application/json",
    }


def _build_api_messages(
    messages: List[Dict[str, Any]],
    system_prompt: str,
    is_reasoning: bool,
) -> List[Dict[str, Any]]:
    """构建 API 消息列表"""
    api_messages = []

    if system_prompt:
        if is_reasoning:
            api_messages.append({
                "role": "user",
                "content": f"[System Instructions]\n{system_prompt}",
            })
        else:
            api_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")
        images = msg.get("images", [])

        # Tool role messages (tool execution results)
        if role == "tool":
            api_messages.append({
                "role": "tool",
                "tool_call_id": msg.get("tool_call_id", ""),
                "content": msg.get("content", ""),
            })
            continue

        # Assistant messages with tool_calls
        if role == "assistant" and "tool_calls" in msg:
            entry: Dict[str, Any] = {"role": "assistant"}
            if content:
                entry["content"] = content
            else:
                entry["content"] = None
            entry["tool_calls"] = msg["tool_calls"]
            api_messages.append(entry)
            continue

        if images and role == "user":
            content_parts = []
            if content:
                content_parts.append({"type": "text", "text": content})
            for img in images:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['mime_type']};base64,{img['base64']}"
                    },
                })
            api_messages.append({"role": role, "content": content_parts})
        else:
            api_messages.append({"role": role, "content": content})

    return api_messages


# 工具调用最大循环次数 (防止无限 tool-call 循环)
# 同一 request_id 下的工具轮次应归集为一次 premium request
MAX_TOOL_ROUNDS = 15

# Tool call 执行回调类型
ToolExecutor = Callable[[str, Dict[str, Any]], Awaitable[str]]


async def chat_stream(
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o",
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_executor: Optional[ToolExecutor] = None,
    request_id: str = "",
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式 AI 对话 (SSE) — 结构化输出, 支持 Tool Calling

    yield 字典类型:
      {"type": "content",    "content": "..."}                                    - 文本内容增量
      {"type": "thinking",   "content": "..."}                                    - 思考过程增量
      {"type": "tool_call",  "tool_call": {"id":"..","name":"..","arguments":{..}}} - AI 请求调用工具
      {"type": "tool_result","tool_call_id":"..","name":"..","result":"..","duration_ms":N} - 工具结果
      {"type": "tool_error", "tool_call_id":"..","name":"..","error":".."}         - 工具错误
      {"type": "usage",      "usage": {...}}                                      - token 使用统计
      {"type": "error",      "error": "..."}                                      - 错误信息
    """
    use_copilot = _is_copilot_model(model)
    actual_model = _get_actual_model_name(model)
    is_reasoning = _is_reasoning_model(actual_model)

    # 推理模型不支持 tools, 强制禁用
    if is_reasoning and tools:
        logger.info(f"推理模型 {actual_model} 不支持 tools, 跳过工具注入")
        tools = None

    # 验证认证
    if use_copilot:
        if not copilot_auth.is_authenticated:
            yield {"type": "error", "error": "❌ 未授权 Copilot，请在设置页面完成 OAuth 授权"}
            return
    else:
        if not settings.github_token:
            yield {"type": "error", "error": "❌ 未配置 GITHUB_TOKEN，无法调用 AI 服务"}
            return

    # 工具调用循环 — 模型可能多次调用工具
    current_messages = list(messages)  # 可追加 tool results
    total_tool_rounds = 0
    all_tool_calls_collected: List[Dict[str, Any]] = []  # 收集所有轮次的 tool calls

    while True:
        # 构建消息
        api_messages = _build_api_messages(current_messages, system_prompt, is_reasoning)

        # 获取请求头和 URL
        if use_copilot:
            try:
                headers = await _get_copilot_headers(request_id=request_id)
            except Exception as e:
                yield {"type": "error", "error": f"❌ Copilot 认证失败: {str(e)}"}
                return
            base_url = COPILOT_CHAT_URL
            logger.info(f"Using Copilot API for model: {actual_model} (request_id: {request_id[:8]}...)" if request_id else f"Using Copilot API for model: {actual_model}")
        else:
            headers = _get_models_headers()
            base_url = GITHUB_MODELS_URL
            logger.info(f"Using GitHub Models API for model: {actual_model}")

        # 构建 payload
        if is_reasoning:
            payload: Dict[str, Any] = {
                "model": actual_model,
                "messages": api_messages,
                "max_completion_tokens": max_tokens,
            }
            logger.info(f"Using reasoning model params for {actual_model}")
        else:
            payload = {
                "model": actual_model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }

        # 注入 tools
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                if is_reasoning:
                    # 推理模型不支持流式
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code != 200:
                        error_text = response.text
                        logger.error(f"AI API error {response.status_code}: {error_text}")
                        capability_cache.learn_from_error(model, error_text)
                        error_meta = _parse_error_metadata(response.status_code, error_text, model)
                        yield {"type": "error", "error": f"❌ AI 服务错误 ({response.status_code}): {error_text}", "error_meta": error_meta}
                        return

                    result = response.json()
                    choice = result.get("choices", [{}])[0]
                    message_data = choice.get("message", {})

                    # 思考过程
                    thinking = message_data.get("reasoning_content") or message_data.get("thinking") or ""
                    if thinking:
                        yield {"type": "thinking", "content": thinking}

                    # 主要内容
                    content = message_data.get("content", "")
                    if content:
                        yield {"type": "content", "content": content}

                    # token 使用统计
                    usage = result.get("usage")
                    if usage:
                        yield {"type": "usage", "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                            "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
                        }}
                    # 推理模型不走循环
                    return

                else:
                    # 普通模型使用流式
                    async with client.stream(
                        "POST",
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            error_text = error_body.decode()
                            logger.error(f"AI API error {response.status_code}: {error_text}")
                            capability_cache.learn_from_error(model, error_text)
                            error_meta = _parse_error_metadata(response.status_code, error_text, model)
                            yield {"type": "error", "error": f"❌ AI 服务错误 ({response.status_code}): {error_text}", "error_meta": error_meta}
                            return

                        usage_data = None
                        # tool_calls 累积器 (流式中分片到达)
                        pending_tool_calls: Dict[int, Dict[str, Any]] = {}
                        response_has_content = False

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})

                                    # 思考过程 (流式, Claude 等模型)
                                    thinking_delta = delta.get("reasoning_content") or delta.get("thinking") or ""
                                    if thinking_delta:
                                        yield {"type": "thinking", "content": thinking_delta}

                                    # 主要内容
                                    if "content" in delta and delta["content"]:
                                        yield {"type": "content", "content": delta["content"]}
                                        response_has_content = True

                                    # Tool calls 增量累积
                                    if "tool_calls" in delta:
                                        for tc_delta in delta["tool_calls"]:
                                            idx = tc_delta.get("index", 0)
                                            if idx not in pending_tool_calls:
                                                pending_tool_calls[idx] = {
                                                    "id": tc_delta.get("id", ""),
                                                    "name": "",
                                                    "arguments": "",
                                                }
                                            tc = pending_tool_calls[idx]
                                            if tc_delta.get("id"):
                                                tc["id"] = tc_delta["id"]
                                            func = tc_delta.get("function", {})
                                            if func.get("name"):
                                                tc["name"] = func["name"]
                                            if func.get("arguments"):
                                                tc["arguments"] += func["arguments"]

                                    # 流式 usage
                                    chunk_usage = chunk.get("usage")
                                    if chunk_usage:
                                        usage_data = chunk_usage

                                except Exception:
                                    continue

                        # 发送 usage (不管是否有 tool calls)
                        if usage_data:
                            yield {"type": "usage", "usage": {
                                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                                "completion_tokens": usage_data.get("completion_tokens", 0),
                                "total_tokens": usage_data.get("total_tokens", 0),
                                "tool_rounds": total_tool_rounds,
                            }}

                        # 检查是否有 tool calls 需要执行
                        if pending_tool_calls and tool_executor:
                            total_tool_rounds += 1
                            if total_tool_rounds > max_tool_rounds:
                                yield {"type": "content", "content": "\n\n⚠️ 工具调用已达上限 ({}轮)，停止继续调用。".format(max_tool_rounds)}
                                return

                            # 解析并执行 tool calls
                            sorted_tcs = sorted(pending_tool_calls.items())
                            tool_results_messages = []

                            # 先追加 assistant 的 tool_calls 消息 (OpenAI 协议要求)
                            assistant_tool_calls = []
                            for _, tc in sorted_tcs:
                                assistant_tool_calls.append({
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tc["name"],
                                        "arguments": tc["arguments"],
                                    },
                                })
                            current_messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": assistant_tool_calls,
                            })

                            for _, tc in sorted_tcs:
                                try:
                                    arguments = json.loads(tc["arguments"]) if tc["arguments"] else {}
                                except json.JSONDecodeError:
                                    arguments = {"_raw": tc["arguments"]}

                                # yield tool_call 事件
                                yield {
                                    "type": "tool_call",
                                    "tool_call": {
                                        "id": tc["id"],
                                        "name": tc["name"],
                                        "arguments": arguments,
                                    },
                                }

                                # 执行工具
                                start_time = time.monotonic()
                                try:
                                    result_text = await tool_executor(tc["name"], arguments)
                                    duration_ms = int((time.monotonic() - start_time) * 1000)

                                    # 截断工具结果以适配小上下文模型
                                    max_input, _ = capability_cache.get_context_window(model)
                                    current_tokens = estimate_messages_tokens(current_messages)
                                    result_tokens = estimate_tokens(result_text)
                                    # 给模型回复和其他 tool calls 留出空间
                                    remaining_budget = max_input - current_tokens - max_tokens - 200
                                    if result_tokens > remaining_budget and remaining_budget > 500:
                                        result_text = truncate_text(result_text, remaining_budget)
                                        result_text += f"\n\n[… 内容已截断以适配模型上下文窗口 ({remaining_budget} tokens), 请用 start_line/end_line 指定范围精确读取]"
                                        logger.info(f"工具结果截断: {result_tokens} -> {remaining_budget} tokens (model={model}, budget={max_input})")
                                    elif remaining_budget <= 500:
                                        # 上下文已经极度紧张, 只保留摘要
                                        result_text = truncate_text(result_text, 500)
                                        result_text += "\n\n[⚠️ 上下文空间不足, 内容已大幅截断. 建议: 用 start_line/end_line 指定小范围, 或切换到更大上下文的模型]"
                                        logger.warning(f"上下文极度紧张, 工具结果强制截断到 500 tokens (model={model})")

                                    yield {
                                        "type": "tool_result",
                                        "tool_call_id": tc["id"],
                                        "name": tc["name"],
                                        "result": result_text,
                                        "duration_ms": duration_ms,
                                    }

                                    # 记录完整的 tool call 信息
                                    all_tool_calls_collected.append({
                                        "id": tc["id"],
                                        "name": tc["name"],
                                        "arguments": arguments,
                                        "result": result_text,
                                        "duration_ms": duration_ms,
                                    })

                                    tool_results_messages.append({
                                        "role": "tool",
                                        "tool_call_id": tc["id"],
                                        "content": result_text,
                                    })

                                except Exception as e:
                                    duration_ms = int((time.monotonic() - start_time) * 1000)
                                    error_msg = f"工具执行失败: {str(e)}"
                                    yield {
                                        "type": "tool_error",
                                        "tool_call_id": tc["id"],
                                        "name": tc["name"],
                                        "error": error_msg,
                                    }
                                    all_tool_calls_collected.append({
                                        "id": tc["id"],
                                        "name": tc["name"],
                                        "arguments": arguments,
                                        "result": f"ERROR: {error_msg}",
                                        "duration_ms": duration_ms,
                                    })
                                    tool_results_messages.append({
                                        "role": "tool",
                                        "tool_call_id": tc["id"],
                                        "content": error_msg,
                                    })

                            # 追加 tool results 到消息列表, 继续循环
                            current_messages.extend(tool_results_messages)
                            continue  # 回到 while 循环, 重新调用模型

                        else:
                            # 无 tool calls, 正常结束
                            return

        except httpx.TimeoutException:
            yield {"type": "error", "error": "❌ AI 服务响应超时，请重试"}
            return
        except Exception as e:
            logger.exception("AI chat stream error")
            yield {"type": "error", "error": f"❌ AI 服务异常: {str(e)}"}
            return


async def chat_complete(
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o",
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """同步 AI 对话 (非流式, 用于生成 plan 等) — 只返回 content 文本"""
    result = []
    async for event in chat_stream(messages, model, system_prompt, temperature, max_tokens):
        if isinstance(event, dict):
            if event.get("type") == "content":
                result.append(event["content"])
            elif event.get("type") == "error":
                result.append(event["error"])
        else:
            result.append(str(event))
    return "".join(result)


def encode_image_to_base64(file_bytes: bytes) -> str:
    """将图片字节编码为 base64"""
    return base64.b64encode(file_bytes).decode("utf-8")


def get_mime_type(filename: str) -> str:
    """根据文件名获取 MIME 类型"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "image/png"
