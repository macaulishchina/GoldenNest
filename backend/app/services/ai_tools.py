"""
小金库 (Golden Nest) - AI 工具调用服务

定义一组 readonly 的数据查询函数，供 AI 根据用户对话内容动态决定调用。
采用两阶段方案：
  Phase 1: AI 分析用户意图，输出需要调用的工具列表 (JSON)
  Phase 2: 后端执行查询，将结果喂给 AI 生成最终回复

兼容任何 OpenAI 格式的模型（无需原生 function calling 支持）。
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.models import (
    User, Family, FamilyMember, Deposit, Transaction, Investment,
    InvestmentIncome, InvestmentPosition, PositionOperationType,
    Asset, TransactionType
)

logger = logging.getLogger(__name__)

# ==================== 工具注册表 ====================

TOOL_DEFINITIONS: List[Dict[str, str]] = [
    {
        "name": "get_my_deposits",
        "description": "查询当前用户的个人累计存款总额",
    },
    {
        "name": "get_family_deposits",
        "description": "查询家庭累计存款总额",
    },
    {
        "name": "get_recent_deposits",
        "description": "查询最近的存款记录（谁在什么时候存了多少钱）",
    },
    {
        "name": "get_balance",
        "description": "查询家庭当前活期余额",
    },
    {
        "name": "get_recent_transactions",
        "description": "查询最近的交易流水（收入、支出、存入、投资等）",
    },
    {
        "name": "get_monthly_summary",
        "description": "查询本月的收支汇总（本月存入、支出、投资收益等）",
    },
    {
        "name": "get_investments",
        "description": "查询家庭当前的投资/理财产品详情（名称、类型、本金、收益等）",
    },
    {
        "name": "get_family_members",
        "description": "查询家庭成员列表",
    },
    {
        "name": "get_family_info",
        "description": "查询家庭基本信息（名称等）",
    },
]

# 工具名称列表（用于 prompt）
TOOL_LIST_TEXT = "\n".join(
    f"  - {t['name']}: {t['description']}" for t in TOOL_DEFINITIONS
)


# ==================== Phase 1: 意图分析 Prompt ====================

def build_tool_selection_prompt(user_message: str, available_context: str = "") -> str:
    """
    构建让 AI 判断需要调用哪些工具的 system prompt。
    AI 应返回 JSON: {"tools": ["tool_name1", "tool_name2", ...], "needs_data": true/false}
    """
    return f"""你是一个智能助手的工具选择器。用户即将向财务助手提问，你需要判断回答这个问题需要查询哪些数据。

可用的查询工具：
{TOOL_LIST_TEXT}

请分析用户的问题，判断需要调用哪些工具来获取数据。

规则：
1. 如果用户的问题不涉及任何具体数据查询（如闲聊、问候、一般性理财知识），返回空工具列表
2. 只选择真正需要的工具，不要多选
3. 如果问题涉及多个方面的数据，可以选择多个工具

{available_context}

请严格按以下 JSON 格式返回（不要返回其他内容）：
{{"tools": ["工具名1", "工具名2"], "needs_data": true}}
或
{{"tools": [], "needs_data": false}}"""


# ==================== Phase 2: 工具执行 ====================

async def execute_tool(
    tool_name: str,
    db: AsyncSession,
    user: User,
    family_id: int,
) -> str:
    """执行单个工具查询，返回格式化的文本结果"""
    try:
        handler = _TOOL_HANDLERS.get(tool_name)
        if not handler:
            return f"[工具 {tool_name} 不存在]"
        return await handler(db, user, family_id)
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
        return f"[查询 {tool_name} 时出错]"


async def execute_tools(
    tool_names: List[str],
    db: AsyncSession,
    user: User,
    family_id: int,
) -> str:
    """批量执行工具查询，返回汇总结果文本"""
    if not tool_names:
        return ""

    results = []
    for name in tool_names:
        result = await execute_tool(name, db, user, family_id)
        results.append(f"【{name}】\n{result}")

    return "\n\n".join(results)


# ==================== 各工具的具体实现 ====================

async def _get_my_deposits(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(func.sum(Deposit.amount))
        .where(Deposit.user_id == user.id, Deposit.family_id == family_id)
    )
    total = result.scalar() or 0

    # 存款笔数
    count_result = await db.execute(
        select(func.count(Deposit.id))
        .where(Deposit.user_id == user.id, Deposit.family_id == family_id)
    )
    count = count_result.scalar() or 0

    return f"用户 {user.nickname} 的个人累计存款：¥{total:,.2f}（共 {count} 笔）"


async def _get_family_deposits(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(func.sum(Deposit.amount))
        .where(Deposit.family_id == family_id)
    )
    total = result.scalar() or 0

    # 各成员存款
    members_result = await db.execute(
        select(User.nickname, func.sum(Deposit.amount))
        .join(User, Deposit.user_id == User.id)
        .where(Deposit.family_id == family_id)
        .group_by(User.nickname)
    )
    members = members_result.all()
    member_detail = "\n".join(
        f"  · {name}: ¥{amount:,.2f}" for name, amount in members
    ) or "  暂无记录"

    return f"家庭累计存款总额：¥{total:,.2f}\n各成员存款：\n{member_detail}"


async def _get_recent_deposits(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(Deposit, User)
        .join(User, Deposit.user_id == User.id)
        .where(Deposit.family_id == family_id)
        .order_by(Deposit.deposit_date.desc())
        .limit(10)
    )
    deposits = result.all()
    if not deposits:
        return "暂无存款记录"

    lines = [
        f"  · {d.deposit_date.strftime('%Y-%m-%d')} {u.nickname} 存入 ¥{d.amount:,.2f}"
        + (f"（{d.note}）" if d.note else "")
        for d, u in deposits
    ]
    return "最近存款记录：\n" + "\n".join(lines)


async def _get_balance(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_tx = result.scalar_one_or_none()
    balance = last_tx.balance_after if last_tx else 0
    return f"当前活期余额：¥{balance:,.2f}"


async def _get_recent_transactions(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(15)
    )
    transactions = result.scalars().all()
    if not transactions:
        return "暂无交易记录"

    lines = [
        f"  · {t.created_at.strftime('%Y-%m-%d')} [{t.transaction_type.value}] "
        f"¥{t.amount:+,.2f} → 余额 ¥{t.balance_after:,.2f} | {t.description}"
        for t in transactions
    ]
    return "最近交易流水：\n" + "\n".join(lines)


async def _get_monthly_summary(db: AsyncSession, user: User, family_id: int) -> str:
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.DEPOSIT),
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.WITHDRAW),
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.INCOME),
            func.count(Transaction.id),
        )
        .where(Transaction.family_id == family_id, Transaction.created_at >= month_start)
    )
    row = result.one()
    deposits = row[0] or 0
    withdrawals = abs(row[1] or 0)
    income = row[2] or 0
    count = row[3] or 0

    now = datetime.now()
    return (
        f"本月（{now.year}年{now.month}月）收支汇总：\n"
        f"  · 总交易笔数：{count} 笔\n"
        f"  · 本月存入：¥{deposits:,.2f}\n"
        f"  · 本月支出：¥{withdrawals:,.2f}\n"
        f"  · 本月投资收益：¥{income:,.2f}\n"
        f"  · 净流入：¥{deposits + income - withdrawals:,.2f}"
    )


async def _get_investments(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(Investment)
        .where(Investment.family_id == family_id, Investment.is_deleted == False)
    )
    investments = result.scalars().all()
    active = [inv for inv in investments if inv.is_active]

    if not active:
        return "当前没有在投的理财产品"

    lines = []
    total_principal = 0
    total_income = 0
    for inv in active:
        # 计算持仓本金
        pos_result = await db.execute(
            select(InvestmentPosition)
            .where(InvestmentPosition.investment_id == inv.id)
        )
        positions = pos_result.scalars().all()
        principal = sum(
            p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
            else -p.amount
            for p in positions
        )
        total_principal += principal

        # 计算累计收益
        income_result = await db.execute(
            select(func.sum(InvestmentIncome.calculated_income))
            .where(InvestmentIncome.investment_id == inv.id)
        )
        inv_income = income_result.scalar() or 0
        total_income += inv_income

        lines.append(
            f"  · {inv.name}（{inv.investment_type.value}）"
            f"| 本金 ¥{principal:,.2f} | 累计收益 ¥{inv_income:,.2f}"
            + (f" | {inv.bank_name}" if inv.bank_name else "")
        )

    return (
        f"在投资产 {len(active)} 个 | 总本金 ¥{total_principal:,.2f} | 总收益 ¥{total_income:,.2f}\n"
        + "\n".join(lines)
    )


async def _get_family_members(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(
        select(User, FamilyMember)
        .join(FamilyMember, User.id == FamilyMember.user_id)
        .where(FamilyMember.family_id == family_id)
    )
    members = result.all()
    if not members:
        return "暂无家庭成员信息"

    lines = [f"  · {u.nickname}（{fm.role}）" for u, fm in members]
    return f"家庭成员（共 {len(members)} 人）：\n" + "\n".join(lines)


async def _get_family_info(db: AsyncSession, user: User, family_id: int) -> str:
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()
    if not family:
        return "未找到家庭信息"
    return f"家庭名称：{family.name}"


# ==================== 工具处理器映射 ====================

_TOOL_HANDLERS = {
    "get_my_deposits": _get_my_deposits,
    "get_family_deposits": _get_family_deposits,
    "get_recent_deposits": _get_recent_deposits,
    "get_balance": _get_balance,
    "get_recent_transactions": _get_recent_transactions,
    "get_monthly_summary": _get_monthly_summary,
    "get_investments": _get_investments,
    "get_family_members": _get_family_members,
    "get_family_info": _get_family_info,
}
