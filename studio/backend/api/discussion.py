"""
设计院 (Studio) - AI 讨论 API
支持多轮对话、图片上传、流式输出、Tool Calling、Plan 生成

SSE 事件协议:
  {"type": "content",     "content": "..."}          - 文本内容增量
  {"type": "thinking",    "content": "..."}          - 推理思考过程
  {"type": "tool_call",   "tool_call": {...}}        - AI 请求调用工具
  {"type": "tool_result", "tool_call_id": "...", ...}- 工具执行结果
  {"type": "tool_error",  "tool_call_id": "...", ...}- 工具执行失败
  {"type": "usage",       "usage": {...}}            - token 使用统计
  {"type": "context",     "context": {...}}          - 上下文管理信息
  {"type": "done",        "message_id": N}           - 完成
  {"type": "error",       "error": "..."}            - 错误
"""
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio.backend.core.config import settings
from studio.backend.core.database import get_db
from studio.backend.core.model_capabilities import capability_cache
from studio.backend.core.security import get_studio_user, get_optional_studio_user
from studio.backend.models import Project, Message, MessageRole, MessageType, ProjectStatus
from studio.backend.services import ai_service, context_service
from studio.backend.services.ai_service import new_request_id
from studio.backend.services.context_manager import prepare_context, build_usage_summary, summarize_context_if_needed, _generate_summary
from studio.backend.services.tool_registry import get_tool_definitions, execute_tool, DEFAULT_PERMISSIONS
from studio.backend.core.token_utils import estimate_tokens, truncate_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio-api/projects", tags=["Discussion"])


async def _check_model_supports_tools(model: str) -> bool:
    """检查模型是否支持 tool calling (查询模型缓存)"""
    try:
        from studio.backend.api.models_api import _model_cache
        models = await _model_cache.get_models()
        for m in models:
            if m.id == model:
                return m.supports_tools
    except Exception:
        pass
    # 缓存不可用时保守地允许 (避免阻断正常流程)
    return True


# ==================== Schemas ====================

class MessageOut(BaseModel):
    id: int
    role: MessageRole
    sender_name: str
    content: str
    message_type: MessageType
    attachments: list = []
    model_used: Optional[str] = None
    token_usage: Optional[dict] = None
    thinking_content: Optional[str] = None
    tool_calls: Optional[list] = None
    parent_message_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DiscussRequest(BaseModel):
    message: str = Field("", max_length=10000)
    sender_name: str = Field("user", max_length=100)
    # 图片通过单独的上传接口处理, 这里传已上传的 attachment 引用
    attachments: List[dict] = Field(default_factory=list)
    regenerate: bool = Field(False, description="重新生成: 不保存用户消息, 直接用历史生成 AI 回复")
    max_tool_rounds: int = Field(15, ge=0, le=100, description="工具调用轮次上限 (前端根据免费/付费模型配置)")


# AI 正在流式输出的项目集 (用于阻止并发发送)
_streaming_projects: set = set()


# ==================== AI 禁言控制 ====================

@router.post("/{project_id}/ai-mute")
async def toggle_ai_mute(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_studio_user),
):
    """切换 AI 禁言状态"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    project.ai_muted = not project.ai_muted
    await db.commit()
    status = "muted" if project.ai_muted else "unmuted"
    logger.info(f"AI {'禁言' if project.ai_muted else '解除禁言'} by {user['nickname']}")
    return {"ai_muted": project.ai_muted, "status": status}


@router.get("/{project_id}/ai-mute")
async def get_ai_mute_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取 AI 禁言状态"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"ai_muted": project.ai_muted}


@router.get("/{project_id}/streaming-status")
async def get_streaming_status(project_id: int):
    """获取 AI 是否正在生成"""
    return {"streaming": project_id in _streaming_projects}


# ==================== 图片上传 ====================

@router.post("/{project_id}/upload-image")
async def upload_image(
    project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    上传讨论用的图片
    返回图片 URL 和 base64, 供后续讨论消息引用
    """
    # 验证项目存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证文件类型
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file.content_type}")

    # 限制大小 10MB
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片不能超过 10MB")

    # 保存文件
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(settings.uploads_path, str(project_id))
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # 生成 base64 (用于 AI 调用)
    base64_data = ai_service.encode_image_to_base64(content)
    mime_type = file.content_type

    return {
        "filename": filename,
        "url": f"/studio-uploads/{project_id}/{filename}",
        "base64": base64_data,
        "mime_type": mime_type,
        "size": len(content),
    }


# ==================== 讨论对话 ====================

@router.post("/{project_id}/discuss")
async def discuss(
    project_id: int,
    data: DiscussRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_studio_user),
):
    """
    发送讨论消息，AI 流式返回
    响应格式: Server-Sent Events (SSE)

    群聊逻辑:
      - 用户消息保存真实 sender_name (来自认证)
      - AI 正在输出时, 用户可以发消息但不触发新 AI 回复 (消息入库)
      - AI 禁言模式: 只保存消息, 不触发 AI
      - 解除禁言后, AI 获取上次回复到现在的所有新消息, 一并作为输入
    """
    # 获取项目
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 更新项目状态
    if project.status == ProjectStatus.draft:
        project.status = ProjectStatus.discussing

    # 确定发送者名称 (优先使用认证用户)
    sender = data.sender_name
    if user:
        sender = user.get("nickname", user.get("username", sender))

    # 保存用户消息 (regenerate 模式跳过)
    if not data.regenerate:
        user_msg = Message(
            project_id=project_id,
            role=MessageRole.user,
            sender_name=sender,
            content=data.message,
            message_type=MessageType.image if data.attachments else MessageType.chat,
            attachments=data.attachments,
        )
        db.add(user_msg)

    # ⚠️ 提前 commit: 释放 SQLite 写锁, 否则 event_stream 中保存 AI 回复会死锁
    await db.commit()

    # 检查 AI 是否正在流式输出 → 消息已保存, 但不触发新 AI 回复
    if project_id in _streaming_projects:
        return {"status": "queued", "message": "AI 正在输出中, 消息已保存, 稍后一并回复"}

    # 检查 AI 禁言模式 → 仅保存消息, 不触发 AI
    if project.ai_muted and not data.regenerate:
        return {"status": "muted", "message": "AI 已禁言, 消息已保存"}

    # 获取历史消息
    msg_result = await db.execute(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at)
    )
    history_msgs = msg_result.scalars().all()

    # 构建 AI 消息列表
    ai_messages = []
    for msg in history_msgs:
        # 跳过 plan_final 消息 — 已通过系统提示词注入，避免重复占用上下文
        if msg.message_type == MessageType.plan_final:
            continue
        entry = {"role": msg.role.value, "content": msg.content}
        # 处理图片附件
        if msg.attachments:
            images = []
            for att in msg.attachments:
                if att.get("type") == "image" and att.get("base64"):
                    images.append({
                        "base64": att["base64"],
                        "mime_type": att.get("mime_type", "image/png"),
                    })
            if images:
                entry["images"] = images
        ai_messages.append(entry)

    model = project.discussion_model or "gpt-4o"

    # 构建系统 prompt (项目上下文) — 自适应压缩
    max_input = capability_cache.get_max_input(model)
    # system prompt 预算: 上下文窗口的 15%, 至少 2000 tokens
    system_budget = max(int(max_input * 0.15), 2000)

    # 构建额外上下文: 需求 + 当前设计稿 (标签名来自 skill)
    skill = project.skill
    _labels = (skill.ui_labels if skill and skill.ui_labels else None) or {}
    _pn = _labels.get("project_noun", "需求")
    _on = _labels.get("output_noun", "设计稿")
    extra_parts = [f"\n## 当前{_pn}\n标题: {project.title}\n描述: {project.description}"]
    plan_summary = ""
    if project.plan_content and project.plan_content.strip():
        plan_summary = project.plan_content.strip()
        extra_parts.append(
            f"\n## 当前{_on} (v{project.plan_version})\n"
            f"以下是当前最新的{_on}，用户可能正在同步编辑它。"
            f"请结合{_on}内容和讨论进行回复。\n\n{plan_summary}"
        )

    # 提前计算工具权限 (build_project_context 需要知道 ask_user 是否开启)
    raw_perms = getattr(project, 'tool_permissions', None)
    tool_permissions = set(raw_perms) if raw_perms else set()

    system_prompt, system_sections = context_service.build_project_context(
        skill=skill,
        extra_context="\n".join(extra_parts),
        budget_tokens=system_budget,
        return_sections=True,
        tool_permissions=tool_permissions,
    )

    # 上下文自动总结: 使用率 > 90% 时触发
    ai_messages, summary_text = await summarize_context_if_needed(
        messages=ai_messages,
        system_prompt=system_prompt,
        model=model,
    )

    # 如果触发了总结, 保存总结消息到 DB (带重试)
    if summary_text:
        from studio.backend.core.database import async_session_maker
        for attempt in range(3):
            try:
                async with async_session_maker() as save_db:
                    summary_db_msg = Message(
                        project_id=project_id,
                        role=MessageRole.system,
                        sender_name="Context Summary",
                        content=f"[对话历史总结]\n\n{summary_text}",
                        message_type=MessageType.chat,
                        model_used=model,
                    )
                    save_db.add(summary_db_msg)
                    await save_db.commit()
                break
            except Exception as save_err:
                logger.warning(f"保存上下文总结失败 (尝试 {attempt+1}/3): {save_err}")
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(0.5)

    # 获取工具定义 (根据项目权限 + 模型能力)
    # 检查模型是否支持 tool calling — 不支持则跳过工具注入
    model_supports_tools = await _check_model_supports_tools(model)
    if not model_supports_tools:
        tool_permissions = set()  # 清空权限, 不注入代码工具
        logger.info(f"模型 {model} 不支持 tool calling, 已跳过工具注入")
        tool_defs = []
    else:
        tool_defs = get_tool_definitions(tool_permissions)

    managed_messages, usage_info = prepare_context(
        messages=ai_messages,
        system_prompt=system_prompt,
        model=model,
        tool_definitions=tool_defs,
    )

    # 创建 tool_executor 闭包
    workspace_path = settings.workspace_path

    async def _tool_executor(name: str, arguments: dict) -> str:
        return await execute_tool(name, arguments, workspace_path, tool_permissions)

    # 流式响应
    async def event_stream():
        _streaming_projects.add(project_id)
        full_response = []
        thinking_parts = []
        token_usage = None
        collected_tool_calls = []
        collected_errors = []  # 收集错误信息用于持久化
        current_managed_messages = managed_messages
        current_usage_info = usage_info
        is_truncated = False  # 跟踪是否被截断
        try:
            # 发送上下文管理信息
            context_summary = build_usage_summary(current_usage_info, system_sections=system_sections, history_messages=current_managed_messages)
            yield f"data: {json.dumps({'type': 'context', 'context': context_summary}, ensure_ascii=False)}\n\n"

            # 通知前端如果触发了上下文总结
            if summary_text:
                yield f"data: {json.dumps({'type': 'summary', 'summary': summary_text}, ensure_ascii=False)}\n\n"

            # 自动重试循环 (上下文超限时压缩后重试一次)
            for _attempt in range(2):
                overflow_retry = False

                async for event in ai_service.chat_stream(
                    messages=current_managed_messages,
                    model=model,
                    system_prompt=system_prompt,
                    tools=tool_defs if tool_defs else None,
                    tool_executor=_tool_executor,
                    request_id=new_request_id(),
                    max_tool_rounds=data.max_tool_rounds,
                ):
                    if not isinstance(event, dict):
                        continue
                    event_type = event.get("type", "")

                    if event_type == "content":
                        full_response.append(event["content"])
                        yield f"data: {json.dumps({'type': 'content', 'content': event['content']}, ensure_ascii=False)}\n\n"

                    elif event_type == "thinking":
                        thinking_parts.append(event["content"])
                        yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']}, ensure_ascii=False)}\n\n"

                    elif event_type == "tool_call_start":
                        yield f"data: {json.dumps({'type': 'tool_call_start', 'tool_call': event['tool_call']}, ensure_ascii=False)}\n\n"

                    elif event_type == "tool_call":
                        yield f"data: {json.dumps({'type': 'tool_call', 'tool_call': event['tool_call']}, ensure_ascii=False)}\n\n"

                    elif event_type == "tool_result":
                        collected_tool_calls.append({
                            "id": event["tool_call_id"],
                            "name": event["name"],
                            "arguments": event.get("arguments", {}),
                            "result": event["result"],
                            "duration_ms": event.get("duration_ms", 0),
                        })
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool_call_id': event['tool_call_id'], 'name': event['name'], 'result': event['result'], 'duration_ms': event.get('duration_ms', 0)}, ensure_ascii=False)}\n\n"

                    elif event_type == "tool_error":
                        collected_tool_calls.append({
                            "id": event["tool_call_id"],
                            "name": event["name"],
                            "arguments": {},
                            "result": f"ERROR: {event['error']}",
                            "duration_ms": 0,
                        })
                        yield f"data: {json.dumps({'type': 'tool_error', 'tool_call_id': event['tool_call_id'], 'name': event['name'], 'error': event['error']}, ensure_ascii=False)}\n\n"

                    elif event_type == "usage":
                        token_usage = event["usage"]
                        yield f"data: {json.dumps({'type': 'usage', 'usage': token_usage}, ensure_ascii=False)}\n\n"

                    elif event_type == "truncated":
                        is_truncated = True
                        yield f"data: {json.dumps({'type': 'truncated'}, ensure_ascii=False)}\n\n"

                    elif event_type == "ask_user_pending":
                        yield f"data: {json.dumps({'type': 'ask_user_pending'}, ensure_ascii=False)}\n\n"

                    elif event_type == "error":
                        error_meta = event.get('error_meta', {})
                        # 上下文超限 + 无已生成内容 + 首次尝试 → 自动压缩重试
                        if (error_meta.get('error_type') == 'context_overflow'
                                and not full_response and _attempt == 0):
                            logger.info("上下文超限，自动压缩后重试...")
                            compress_notice = json.dumps({'type': 'content', 'content': '\n\n⏳ 上下文超限，正在自动压缩后重试...\n\n'}, ensure_ascii=False)
                            yield f"data: {compress_notice}\n\n"
                            # 强制总结
                            try:
                                min_keep = min(len(ai_messages), 4)
                                to_summarize_part = ai_messages[:-min_keep] if min_keep < len(ai_messages) else []
                                recent_part = ai_messages[-min_keep:]
                                if to_summarize_part:
                                    compress_summary = await _generate_summary(to_summarize_part, model)
                                    if compress_summary:
                                        compressed = [{"role": "system", "content": f"[对话历史总结]\n\n{compress_summary}"}] + recent_part
                                        current_managed_messages, current_usage_info = prepare_context(
                                            messages=compressed, system_prompt=system_prompt,
                                            model=model, tool_definitions=tool_defs,
                                        )
                                        context_summary = build_usage_summary(current_usage_info, system_sections=system_sections, history_messages=current_managed_messages)
                                        yield f"data: {json.dumps({'type': 'context', 'context': context_summary}, ensure_ascii=False)}\n\n"
                                        # 保存总结到 DB
                                        from studio.backend.core.database import async_session_maker
                                        try:
                                            async with async_session_maker() as save_db:
                                                summary_db_msg = Message(
                                                    project_id=project_id, role=MessageRole.system,
                                                    sender_name="Context Summary",
                                                    content=f"[对话历史总结]\n\n{compress_summary}",
                                                    message_type=MessageType.chat, model_used=model,
                                                )
                                                save_db.add(summary_db_msg)
                                                await save_db.commit()
                                        except Exception as se:
                                            logger.warning(f"保存压缩总结失败: {se}")
                                        overflow_retry = True
                                        full_response.clear()
                                        break  # 退出内层循环，重试
                            except Exception as ce:
                                logger.warning(f"自动压缩失败: {ce}")
                            if not overflow_retry:
                                # 压缩失败，正常报错
                                collected_errors.append(event['error'])
                                error_data: dict = {'type': 'error', 'error': event['error']}
                                if event.get('error_meta'):
                                    error_data['error_meta'] = event['error_meta']
                                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                        else:
                            collected_errors.append(event['error'])
                            error_data: dict = {'type': 'error', 'error': event['error']}
                            if event.get('error_meta'):
                                error_data['error_meta'] = event['error_meta']
                                # 同步更新后端能力缓存
                                from studio.backend.core.model_capabilities import capability_cache
                                capability_cache.learn_from_error(model, event['error'])
                            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

                if not overflow_retry:
                    break  # 正常结束，退出重试循环

            # 保存 AI 回复 (带重试)
            ai_content = "".join(full_response)
            # 如果没有内容但有错误，将错误保存为消息内容 (使刷新后可见)
            if not ai_content and collected_errors:
                error_text = collected_errors[-1]  # 使用最后一个错误
                brief = error_text[:300] + '...' if len(error_text) > 300 else error_text
                ai_content = f"**⚠️ AI 服务错误**\n\n❌ {brief}"
            thinking_content = "".join(thinking_parts) if thinking_parts else None
            ai_msg_id = None

            from studio.backend.core.database import async_session_maker
            for attempt in range(3):
                try:
                    async with async_session_maker() as save_db:
                        ai_msg = Message(
                            project_id=project_id,
                            role=MessageRole.assistant,
                            sender_name=model,
                            content=ai_content,
                            message_type=MessageType.chat,
                            model_used=model,
                            token_usage=token_usage,
                            thinking_content=thinking_content,
                            tool_calls=collected_tool_calls if collected_tool_calls else None,
                        )
                        save_db.add(ai_msg)
                        await save_db.commit()
                        ai_msg_id = ai_msg.id
                    break
                except Exception as save_err:
                    logger.warning(f"保存 AI 回复失败 (尝试 {attempt+1}/3): {save_err}")
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(0.5)

            # 无论保存是否成功都发送 done (前端需要将内容持久化到消息列表)
            yield f"data: {json.dumps({'type': 'done', 'message_id': ai_msg_id or -1}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("AI 讨论异常")
            error_str = str(e)
            yield f"data: {json.dumps({'type': 'error', 'error': error_str}, ensure_ascii=False)}\n\n"
            # 保存异常错误到数据库 (如果没有已保存的内容)
            if not full_response:
                brief = error_str[:300] + '...' if len(error_str) > 300 else error_str
                error_content = f"**⚠️ AI 服务错误**\n\n❌ {brief}"
                try:
                    from studio.backend.core.database import async_session_maker
                    async with async_session_maker() as save_db:
                        err_msg = Message(
                            project_id=project_id,
                            role=MessageRole.assistant,
                            sender_name=model,
                            content=error_content,
                            message_type=MessageType.chat,
                            model_used=model,
                        )
                        save_db.add(err_msg)
                        await save_db.commit()
                        yield f"data: {json.dumps({'type': 'done', 'message_id': err_msg.id}, ensure_ascii=False)}\n\n"
                except Exception as save_err:
                    logger.warning(f"保存错误消息失败: {save_err}")
        finally:
            _streaming_projects.discard(project_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 消息历史 ====================

@router.get("/{project_id}/messages", response_model=List[MessageOut])
async def get_messages(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取项目讨论历史"""
    result = await db.execute(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


# ==================== 消息操作 ====================

@router.delete("/{project_id}/messages/{message_id}")
async def delete_message(
    project_id: int,
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除单条消息"""
    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.project_id == project_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    await db.delete(msg)
    await db.commit()
    return {"ok": True}


@router.post("/{project_id}/summarize-context")
async def manual_summarize_context(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_studio_user),
):
    """
    手动触发上下文总结: 将旧消息压缩为一条总结，保留最近消息
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    model = project.discussion_model or "gpt-4o"

    msg_result = await db.execute(
        select(Message).where(Message.project_id == project_id).order_by(Message.created_at)
    )
    history_msgs = list(msg_result.scalars().all())
    if len(history_msgs) < 4:
        raise HTTPException(status_code=400, detail="消息太少，无需总结")

    # 保留最近 4 条，其余进行总结
    min_keep = min(len(history_msgs), 4)
    to_summarize_msgs = [{"role": msg.role.value, "content": msg.content} for msg in history_msgs[:-min_keep]]
    keep_msgs = history_msgs[-min_keep:]

    if not to_summarize_msgs:
        raise HTTPException(status_code=400, detail="消息太少，无需总结")

    summary_text = await _generate_summary(to_summarize_msgs, model)
    if not summary_text:
        raise HTTPException(status_code=500, detail="总结生成失败，请重试")

    # 删除被总结的旧消息
    keep_ids = {m.id for m in keep_msgs}
    for msg in history_msgs:
        if msg.id not in keep_ids:
            await db.delete(msg)

    # 插入总结消息
    summary_msg = Message(
        project_id=project_id,
        role=MessageRole.system,
        sender_name="Context Summary",
        content=f"[对话历史总结]\n\n{summary_text}",
        message_type=MessageType.chat,
        model_used=model,
    )
    db.add(summary_msg)
    await db.commit()

    # 返回最新消息列表
    msg_result = await db.execute(
        select(Message).where(Message.project_id == project_id).order_by(Message.created_at)
    )
    new_msgs = msg_result.scalars().all()

    return {
        "ok": True,
        "summarized_count": len(to_summarize_msgs),
        "remaining_count": len(list(new_msgs)),
        "summary": summary_text,
    }


@router.delete("/{project_id}/clear-context")
async def clear_context(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_studio_user),
):
    """
    清空项目所有讨论消息
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    from sqlalchemy import delete as sql_delete
    del_result = await db.execute(
        sql_delete(Message).where(Message.project_id == project_id)
    )
    await db.commit()

    return {"ok": True, "deleted_count": del_result.rowcount}


@router.delete("/{project_id}/messages/{message_id}/and-after")
async def delete_message_and_after(
    project_id: int,
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除指定消息及其之后的所有消息 (用于重试)"""
    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.project_id == project_id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="消息不存在")

    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(Message).where(
            Message.project_id == project_id,
            Message.created_at >= target.created_at,
        )
    )
    await db.commit()
    return {"ok": True}


# ==================== 敲定 Plan ====================

@router.post("/{project_id}/finalize-plan")
async def finalize_plan(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    基于讨论历史生成并敲定 plan.md
    流式返回 plan 内容
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取讨论历史
    msg_result = await db.execute(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    if not messages:
        raise HTTPException(status_code=400, detail="还没有讨论内容")

    model = project.discussion_model or "gpt-4o"

    # 构建讨论摘要 (自适应截断，防止超出模型上下文)
    discussion_text = "\n".join(
        f"[{msg.sender_name}]: {msg.content}" for msg in messages
    )
    max_input = capability_cache.get_max_input(model)
    # 给 system prompt + plan prompt + 输出预留空间
    discussion_budget = max(max_input - 12000, max_input // 2)
    if estimate_tokens(discussion_text) > discussion_budget:
        logger.info(f"敲定 plan: 讨论内容 ({estimate_tokens(discussion_text)} tokens) 超出预算 ({discussion_budget}), 截断")
        discussion_text = truncate_text(discussion_text, discussion_budget)

    # 构建生成 plan 的 prompt — 自适应压缩
    max_input = capability_cache.get_max_input(model)
    system_budget = max(int(max_input * 0.15), 2000)
    system_prompt = context_service.build_project_context(skill=project.skill, budget_tokens=system_budget, tool_permissions=set())
    plan_prompt = context_service.build_plan_generation_prompt(discussion_text, skill=project.skill)

    async def event_stream():
        full_plan = []
        try:
            async for event in ai_service.chat_stream(
                messages=[{"role": "user", "content": plan_prompt}],
                model=model,
                system_prompt=system_prompt,
                max_tokens=8192,
                request_id=new_request_id(),
            ):
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "content":
                    full_plan.append(event["content"])
                    yield f"data: {json.dumps({'type': 'content', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event.get("type") == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event.get("type") == "error":
                    yield f"data: {json.dumps({'type': 'error', 'error': event['error']}, ensure_ascii=False)}\n\n"

            plan_content = "".join(full_plan)

            # 保存 plan
            from studio.backend.core.database import async_session_maker
            async with async_session_maker() as save_db:
                res = await save_db.execute(select(Project).where(Project.id == project_id))
                proj = res.scalar_one()
                proj.plan_content = plan_content
                proj.plan_version += 1
                proj.status = ProjectStatus.planned
                proj.updated_at = datetime.utcnow()

                # 同时保存 plan.md 文件
                plan_path = os.path.join(settings.plans_path, f"project-{project_id}-v{proj.plan_version}.md")
                with open(plan_path, "w", encoding="utf-8") as f:
                    f.write(plan_content)

                # 保存 plan 生成消息
                plan_msg = Message(
                    project_id=project_id,
                    role=MessageRole.assistant,
                    sender_name=f"Plan Generator ({model})",
                    content=plan_content,
                    message_type=MessageType.plan_final,
                    model_used=model,
                )
                save_db.add(plan_msg)
                await save_db.commit()

            yield f"data: {json.dumps({'type': 'done', 'plan_version': proj.plan_version}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("Plan 生成异常")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== Plan 版本管理 ====================

@router.get("/{project_id}/plan-versions")
async def get_plan_versions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取项目的 Plan 版本列表"""
    import glob

    # 验证项目存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    pattern = os.path.join(settings.plans_path, f"project-{project_id}-v*.md")
    files = glob.glob(pattern)
    versions = []
    for f in sorted(files):
        name = os.path.basename(f)
        v_str = name.replace(f"project-{project_id}-v", "").replace(".md", "")
        try:
            v_num = int(v_str)
            stat = os.stat(f)
            versions.append({
                "version": v_num,
                "filename": name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_current": v_num == project.plan_version,
            })
        except (ValueError, OSError):
            pass

    versions.sort(key=lambda x: x["version"], reverse=True)
    return versions


@router.get("/{project_id}/plan-versions/{version}")
async def get_plan_version(
    project_id: int,
    version: int,
):
    """获取指定版本的 Plan 内容"""
    path = os.path.join(settings.plans_path, f"project-{project_id}-v{version}.md")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="版本不存在")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"version": version, "content": content}


# ==================== 切换模型时上下文检查 ====================

class ContextCheckRequest(BaseModel):
    model: str = Field(..., description="目标模型 ID")

@router.post("/{project_id}/context-check")
async def check_context_on_model_switch(
    project_id: int,
    data: ContextCheckRequest,
    user=Depends(get_optional_studio_user),
    db: AsyncSession = Depends(get_db),
):
    """
    切换模型时检查上下文使用情况，必要时触发自动总结压缩。
    返回新模型下的上下文使用率信息。
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    model = data.model

    # 获取历史消息
    msg_result = await db.execute(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at)
    )
    history_msgs = msg_result.scalars().all()

    if not history_msgs:
        # 无消息，直接返回空使用率
        max_input = capability_cache.get_max_input(model)
        return {
            "context": build_usage_summary({"max_input": max_input, "total_tokens": 0,
                                             "system_tokens": 0, "tools_tokens": 0,
                                             "history_tokens": 0, "messages_kept": 0,
                                             "messages_dropped": 0, "messages_total": 0}),
            "summarized": False,
        }

    # 构建 AI 消息列表
    ai_messages = []
    for msg in history_msgs:
        # 跳过 plan_final 消息 — 已通过系统提示词注入
        if msg.message_type == MessageType.plan_final:
            continue
        entry = {"role": msg.role.value, "content": msg.content}
        if msg.attachments:
            images = []
            for att in msg.attachments:
                if att.get("type") == "image" and att.get("base64"):
                    images.append({"base64": att["base64"], "mime_type": att.get("mime_type", "image/png")})
            if images:
                entry["images"] = images
        ai_messages.append(entry)

    # 构建 system prompt
    max_input = capability_cache.get_max_input(model)
    system_budget = max(int(max_input * 0.15), 2000)
    _chk_labels = (project.skill.ui_labels if project.skill and project.skill.ui_labels else None) or {}
    _chk_pn = _chk_labels.get("project_noun", "需求")
    _chk_on = _chk_labels.get("output_noun", "设计稿")
    extra_parts = [f"\n## 当前{_chk_pn}\n标题: {project.title}\n描述: {project.description}"]
    if project.plan_content and project.plan_content.strip():
        extra_parts.append(f"\n## 当前{_chk_on} (v{project.plan_version})\n{project.plan_content.strip()}")
    chk_raw_perms = getattr(project, 'tool_permissions', None)
    chk_tool_permissions = set(chk_raw_perms) if chk_raw_perms else set()
    system_prompt, check_system_sections = context_service.build_project_context(
        skill=project.skill,
        extra_context="\n".join(extra_parts),
        budget_tokens=system_budget,
        return_sections=True,
        tool_permissions=chk_tool_permissions,
    )

    # 检查是否需要总结 — 超限时自动总结并保存到 DB
    compressed_messages, summary_text = await summarize_context_if_needed(
        messages=ai_messages,
        system_prompt=system_prompt,
        model=model,
    )
    # 如果触发了总结, 保存到 DB (用户切到小窗口模型时自动压缩)
    if summary_text:
        try:
            summary_db_msg = Message(
                project_id=project_id,
                role=MessageRole.system,
                sender_name="Context Summary",
                content=f"[对话历史总结]\n\n{summary_text}",
                message_type=MessageType.chat,
                model_used=model,
            )
            db.add(summary_db_msg)
            await db.commit()
        except Exception as se:
            logger.warning(f"保存模型切换总结失败: {se}")

    # 计算新模型下的上下文使用率
    tool_defs = []
    model_supports_tools = await _check_model_supports_tools(model)
    if model_supports_tools:
        raw_perms = getattr(project, 'tool_permissions', None)
        tool_permissions = set(raw_perms) if raw_perms else set()
        tool_defs = get_tool_definitions(tool_permissions)

    _, usage_info = prepare_context(
        messages=compressed_messages,
        system_prompt=system_prompt,
        model=model,
        tool_definitions=tool_defs,
    )

    context_summary = build_usage_summary(usage_info, system_sections=check_system_sections, history_messages=compressed_messages)

    return {
        "context": context_summary,
        "summarized": summary_text is not None,
        "summary_text": summary_text,
    }
