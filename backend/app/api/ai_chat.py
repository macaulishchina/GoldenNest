"""
小金库 (Golden Nest) - AI 聊天助手 API

提供通用的 AI 对话功能，可以回答关于家庭财务的各种问题
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Family, FamilyMember, Deposit, Transaction, Investment, Asset, ExpenseRequest
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


class ChatRequest(BaseModel):
    """AI 对话请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=2000)
    context_type: Optional[str] = Field(None, description="上下文类型: dashboard/transaction/investment/family")


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
    与 AI 助手对话，可以询问关于家庭财务的任何问题
    
    AI 会根据用户的实际数据提供个性化的建议和见解
    """
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置，请联系管理员")
    
    try:
        # 获取用户家庭信息
        family_member_result = await db.execute(
            select(FamilyMember)
            .where(FamilyMember.user_id == current_user.id)
            .limit(1)
        )
        family_member = family_member_result.scalar_one_or_none()
        
        context_data = ""
        
        if family_member:
            family_id = family_member.family_id
            
            # 获取家庭信息
            family_result = await db.execute(
                select(Family).where(Family.id == family_id)
            )
            family = family_result.scalar_one_or_none()
            
            # 获取用户存款总额
            deposits_result = await db.execute(
                select(func.sum(Deposit.amount))
                .where(Deposit.user_id == current_user.id, Deposit.family_id == family_id)
            )
            total_deposits = deposits_result.scalar() or 0
            
            # 获取交易数量
            transactions_result = await db.execute(
                select(func.count(Transaction.id))
                .where(Transaction.family_id == family_id)
            )
            total_transactions = transactions_result.scalar() or 0
            
            # 获取投资数量
            investments_result = await db.execute(
                select(func.count(Investment.id))
                .where(Investment.family_id == family_id)
            )
            total_investments = investments_result.scalar() or 0
            
            # 获取资产数量
            assets_result = await db.execute(
                select(func.count(Asset.id))
                .where(Asset.family_id == family_id)
            )
            total_assets = assets_result.scalar() or 0
            
            # 构建上下文
            context_data = f"""
用户信息：
- 昵称：{current_user.nickname}
- 家庭名称：{family.name if family else '未加入家庭'}
- 累计存款：¥{total_deposits:,.2f}
- 交易记录数：{total_transactions}
- 投资项目数：{total_investments}
- 资产项目数：{total_assets}
"""
        else:
            context_data = f"""
用户信息：
- 昵称：{current_user.nickname}
- 家庭状态：未加入家庭
"""
        
        # 构建系统提示词
        system_prompt = f"""你是小金库（Golden Nest）的智能财务助手，专门帮助用户管理家庭财务。

你的能力：
1. 回答关于家庭财务管理的问题
2. 提供个性化的理财建议
3. 分析用户的财务数据并给出见解
4. 帮助用户理解复杂的财务概念
5. 鼓励良好的储蓄和投资习惯

用户当前数据：
{context_data}

注意事项：
- 回答要简洁明了，一般不超过200字
- 使用友好、鼓励的语气
- 如果涉及具体金额建议，要考虑用户的实际情况
- 不要提供具体的股票、基金推荐
- 当用户数据不足时，给出通用建议
"""
        
        # 调用 AI
        reply = await ai_service.chat(
            user_prompt=request.message,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        # 生成建议问题
        suggestions = []
        if request.context_type == "dashboard":
            suggestions = [
                "分析我的储蓄习惯",
                "如何提高家庭资产增长率",
                "给我一些理财建议"
            ]
        elif request.context_type == "transaction":
            suggestions = [
                "如何减少不必要的开支",
                "我的消费模式健康吗",
                "建议如何分配每月预算"
            ]
        elif request.context_type == "investment":
            suggestions = [
                "如何平衡投资风险",
                "我的资产配置合理吗",
                "什么时候该考虑调整投资组合"
            ]
        
        return ChatResponse(
            reply=reply,
            suggestions=suggestions
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 服务暂时不可用，请稍后再试")
