"""
小金库 (Golden Nest) - 交易流水路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.models import Transaction, TransactionType, FamilyMember, User, InvestmentIncome, Investment
from app.schemas.transaction import TransactionResponse, TransactionSummary, DividendCalculation, MemberDividend
from app.schemas.common import TimeRange, get_time_range_filter
from app.api.auth import get_current_user
from app.services.equity import calculate_family_equity
from app.services.ai_service import ai_service

router = APIRouter()


class TransactionInsightResponse(BaseModel):
    """交易洞察响应"""
    insight: str
    spending_tips: list[str]
    saving_suggestions: list[str]


class TransactionCategorizationRequest(BaseModel):
    """交易分类请求"""
    description: str
    amount: float


class TransactionCategorizationResponse(BaseModel):
    """交易分类响应"""
    category: str
    confidence: str
    suggested_tags: list[str]


async def get_user_family_id(user_id: int, db: AsyncSession) -> int:
    """获取用户的家庭ID"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    return membership.family_id


@router.get("/list", response_model=List[TransactionResponse])
async def list_transactions(
    time_range: TimeRange = Query(TimeRange.MONTH, description="时间范围：day/week/month/year/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取交易流水列表（支持时间范围筛选，默认最近一个月）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 构建查询
    query = select(Transaction).where(Transaction.family_id == family_id)
    
    # 时间范围筛选
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(Transaction.created_at >= start_time)
    
    result = await db.execute(
        query.order_by(Transaction.created_at.desc())
    )
    transactions = result.scalars().all()
    
    # 获取用户信息
    user_ids = [t.user_id for t in transactions if t.user_id]
    users_map = {}
    if user_ids:
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = result.scalars().all()
        users_map = {u.id: u.nickname for u in users}
    
    return [
        TransactionResponse(
            id=t.id,
            family_id=t.family_id,
            user_id=t.user_id,
            user_nickname=users_map.get(t.user_id) if t.user_id else None,
            transaction_type=t.transaction_type,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            reference_id=t.reference_id,
            reference_type=t.reference_type,
            created_at=t.created_at
        )
        for t in transactions
    ]


@router.get("/summary", response_model=TransactionSummary)
async def get_transaction_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取交易汇总"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 统计各类交易
    result = await db.execute(
        select(
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.DEPOSIT),
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.WITHDRAW),
            func.sum(Transaction.amount).filter(Transaction.transaction_type == TransactionType.INCOME),
            func.count(Transaction.id)
        )
        .where(Transaction.family_id == family_id)
    )
    row = result.one()
    
    total_deposits = row[0] or 0
    total_withdrawals = abs(row[1] or 0)
    total_income = row[2] or 0
    transaction_count = row[3] or 0
    
    # 获取当前余额
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0
    
    return TransactionSummary(
        family_id=family_id,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        total_income=total_income,
        current_balance=current_balance,
        transaction_count=transaction_count
    )


@router.get("/dividend", response_model=DividendCalculation)
async def calculate_dividend(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """计算分红"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取股权信息
    equity_summary = await calculate_family_equity(family_id, db)
    
    # 获取所有投资产品及其收益（支持新旧两种模式，排除已删除的）
    result = await db.execute(
        select(Investment).where(
            Investment.family_id == family_id,
            Investment.is_deleted == False
        )
    )
    investments = result.scalars().all()
    
    # 按产品计算收益明细
    breakdown = []
    total_income = 0
    
    for inv in investments:
        # 获取该产品的所有收益记录
        result = await db.execute(
            select(InvestmentIncome).where(
                InvestmentIncome.investment_id == inv.id
            )
        )
        incomes = result.scalars().all()
        
        # 计算该产品的总收益（支持新旧模式）
        inv_total_income = sum(
            inc.calculated_income if inc.calculated_income is not None else inc.amount
            for inc in incomes
        )
        
        if inv_total_income != 0:  # 只添加有收益的产品
            from app.schemas.investment import DividendBreakdown
            breakdown.append(DividendBreakdown(
                investment_id=inv.id,
                investment_name=inv.name,
                total_income=inv_total_income,
                percentage=0  # 占比稍后计算
            ))
            total_income += inv_total_income
    
    # 计算每个产品的收益占比
    if total_income > 0:
        for item in breakdown:
            item.percentage = round(item.total_income / total_income * 100, 2)
    
    # 按股权比例计算分红
    members_dividend = []
    for member in equity_summary.members:
        dividend_amount = total_income * member.equity_ratio
        members_dividend.append(MemberDividend(
            user_id=member.user_id,
            nickname=member.nickname,
            equity_ratio=member.equity_ratio,
            dividend_amount=round(dividend_amount, 2)
        ))
    
    return DividendCalculation(
        family_id=family_id,
        total_income=total_income,
        members=members_dividend,
        breakdown=breakdown
    )


@router.post("/ai/analyze", response_model=TransactionInsightResponse)
async def analyze_transactions_with_ai(
    time_range: TimeRange = Query(TimeRange.MONTH, description="分析时间范围"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 分析交易数据，提供个性化的消费洞察和建议
    """
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置")
    
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取时间范围内的交易
    query = select(Transaction).where(Transaction.family_id == family_id)
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(Transaction.created_at >= start_time)
    
    result = await db.execute(query.order_by(Transaction.created_at.desc()))
    transactions = result.scalars().all()
    
    if not transactions:
        raise HTTPException(status_code=404, detail="暂无交易数据可分析")
    
    # 统计分析数据
    deposit_total = sum(t.amount for t in transactions if t.transaction_type == TransactionType.DEPOSIT)
    withdraw_total = abs(sum(t.amount for t in transactions if t.transaction_type == TransactionType.WITHDRAW))
    income_total = sum(t.amount for t in transactions if t.transaction_type == TransactionType.INCOME)
    
    # 构建交易描述列表（最多20条）
    transaction_desc = "\n".join([
        f"- {t.transaction_type.value}: ¥{t.amount:,.2f} ({t.description or '无描述'})"
        for t in transactions[:20]
    ])
    
    # AI 分析
    system_prompt = """你是一位专业的家庭财务分析师，擅长从交易数据中发现消费模式和提供实用建议。

分析要点：
1. 识别主要消费模式和趋势
2. 发现潜在的过度支出领域
3. 提供3-5条具体可行的节约建议
4. 给出2-3条储蓄增长策略

输出格式要求JSON：
{
  "insight": "150字以内的总体分析",
  "spending_tips": ["建议1", "建议2", "建议3"],
  "saving_suggestions": ["策略1", "策略2"]
}
"""
    
    user_prompt = f"""请分析以下家庭财务数据（时间范围：{time_range.value}）：

统计摘要：
- 总存入：¥{deposit_total:,.2f}
- 总支出：¥{withdraw_total:,.2f}
- 投资收益：¥{income_total:,.2f}
- 交易笔数：{len(transactions)}

最近交易记录：
{transaction_desc}

请给出分析和建议。"""
    
    try:
        result_json = await ai_service.chat_json(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            function_key="transaction_analyze",
            temperature=0.5
        )
        
        if not result_json:
            raise ValueError("AI 返回了无效的响应")
        
        return TransactionInsightResponse(
            insight=result_json.get("insight", "分析结果解析失败"),
            spending_tips=result_json.get("spending_tips", []),
            saving_suggestions=result_json.get("saving_suggestions", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")


@router.post("/ai/categorize", response_model=TransactionCategorizationResponse)
async def categorize_transaction_with_ai(
    request: TransactionCategorizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 智能分类交易，自动识别交易类别和标签
    """
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置")
    
    system_prompt = """你是一个交易分类专家，根据交易描述和金额自动归类。

常见类别：
- 日常消费：食品、日用品、交通
- 餐饮娱乐：外出就餐、娱乐活动
- 购物：服装、电子产品、家居用品
- 教育培训：学费、培训费、书籍
- 医疗保健：医药费、体检、保健品
- 住房相关：房租、物业、水电
- 投资理财：基金、股票、保险
- 其他

输出JSON格式：
{
  "category": "类别名称",
  "confidence": "高/中/低",
  "suggested_tags": ["标签1", "标签2"]
}
"""
    
    user_prompt = f"""请对以下交易进行分类：
描述：{request.description}
金额：¥{request.amount:,.2f}

请分析并返回类别、置信度和建议标签。"""
    
    try:
        result_json = await ai_service.chat_json(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            function_key="transaction_categorize",
            temperature=0.3
        )
        
        if not result_json:
            raise ValueError("AI 返回了无效的响应")
        
        return TransactionCategorizationResponse(
            category=result_json.get("category", "未分类"),
            confidence=result_json.get("confidence", "低"),
            suggested_tags=result_json.get("suggested_tags", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分类失败: {str(e)}")
