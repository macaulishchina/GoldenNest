"""
小金库 (Golden Nest) - AI 聊天助手 API

提供通用的 AI 对话功能，AI 可根据对话内容动态决定是否查询财务数据。
采用两阶段 Tool-Calling 模式：
  Phase 1: AI 分析用户意图，判断需要调用哪些数据查询工具
  Phase 2: 执行查询，将结果注入上下文后生成最终回复
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, FamilyMember
from app.services.ai_service import ai_service
from app.services.ai_tools import (
    build_tool_selection_prompt, execute_tools, TOOL_LIST_TEXT,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


class ChatMessage(BaseModel):
    """对话历史消息"""
    role: str = Field(..., description="角色: user/assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """AI 对话请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=2000)
    context_type: Optional[str] = Field(None, description="上下文类型: dashboard/transaction/investment/family")
    history: List[ChatMessage] = Field(default_factory=list, description="对话历史")


class ChatResponse(BaseModel):
    """AI 对话响应"""
    reply: str
    suggestions: list[str] = []


@router.post("", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    与 AI 助手对话。
    AI 会根据对话内容自主判断是否需要查询数据，按需调用查询接口。
    """
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置，请联系管理员")

    try:
        # 获取用户家庭 ID
        fm_result = await db.execute(
            select(FamilyMember)
            .where(FamilyMember.user_id == current_user.id)
            .limit(1)
        )
        family_member = fm_result.scalar_one_or_none()
        family_id = family_member.family_id if family_member else None

        # 构建历史对话
        history = [{"role": h.role, "content": h.content} for h in request.history[-20:]]

        # ===== Phase 1: AI 判断需要调用哪些工具 =====
        tool_data = ""
        if family_id:
            tool_prompt = build_tool_selection_prompt(request.message)
            # 把最近几轮对话也给工具选择器看，便于理解上下文
            recent_history = history[-6:] if history else None
            tool_decision = await ai_service.chat_json(
                user_prompt=f"用户的问题是：{request.message}",
                system_prompt=tool_prompt,
                history=recent_history,
                temperature=0.1,
            )

            logger.info(f"AI tool decision: {tool_decision}")

            if tool_decision and tool_decision.get("needs_data") and tool_decision.get("tools"):
                selected_tools = tool_decision["tools"]
                # 过滤非法工具名
                valid_tools = [t for t in selected_tools if isinstance(t, str)][:5]

                if valid_tools:
                    # ===== Phase 2: 执行查询 =====
                    tool_data = await execute_tools(valid_tools, db, current_user, family_id)
                    logger.info(f"Tools executed: {valid_tools}, data length: {len(tool_data)}")

        # ===== Phase 3: 带数据生成最终回复 =====
        data_section = ""
        if tool_data:
            data_section = f"""

以下是根据用户问题实时查询到的数据，请基于这些数据准确回答：
{tool_data}
"""

        system_prompt = f"""你是小金库（Golden Nest）的智能财务助手，专门帮助用户管理家庭财务。
用户昵称：{current_user.nickname}

你的能力：
1. 基于实时查询的数据，准确回答用户关于余额、存款、交易、投资的具体问题
2. 提供个性化的理财建议和财务分析
3. 帮助用户理解复杂的财务概念
4. 鼓励良好的储蓄和投资习惯
{data_section}
注意事项：
- 当有查询数据时，直接引用数据准确回答，不要编造数字
- 当没有查询数据且用户问的是具体数字时，告诉用户你可以帮他查询，让他再问一次具体问题
- 回答要简洁明了，一般不超过200字
- 使用友好、鼓励的语气
- 不要提供具体的股票、基金推荐
"""

        reply = await ai_service.chat(
            user_prompt=request.message,
            system_prompt=system_prompt,
            history=history,
            temperature=0.7,
        )

        # 生成建议问题
        suggestions = _get_suggestions(request.context_type)

        return ChatResponse(reply=reply, suggestions=suggestions)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 服务暂时不可用，请稍后再试")


def _get_suggestions(context_type: Optional[str]) -> List[str]:
    """根据上下文类型返回建议问题"""
    mapping = {
        "dashboard": ["我存了多少钱", "分析我的储蓄习惯", "给我一些理财建议"],
        "transaction": ["最近有哪些交易", "本月收支情况如何", "建议如何分配每月预算"],
        "investment": ["我有哪些投资", "我的资产配置合理吗", "投资收益怎么样"],
    }
    return mapping.get(context_type, [])
