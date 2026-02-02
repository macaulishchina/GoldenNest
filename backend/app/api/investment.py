"""
小金库 (Golden Nest) - 理财管理路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.models import Investment, InvestmentIncome, FamilyMember, User, Transaction, TransactionType
from app.schemas.investment import (
    InvestmentCreate, InvestmentUpdate, InvestmentResponse,
    InvestmentIncomeCreate, InvestmentIncomeResponse, InvestmentSummary
)
from app.api.auth import get_current_user

router = APIRouter()


async def get_user_family_id(user_id: int, db: AsyncSession) -> int:
    """获取用户的家庭ID"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    return membership.family_id


@router.post("/create", response_model=InvestmentResponse)
async def create_investment(
    investment_data: InvestmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建理财配置"""
    family_id = await get_user_family_id(current_user.id, db)
    
    investment = Investment(
        family_id=family_id,
        name=investment_data.name,
        investment_type=investment_data.investment_type,
        principal=investment_data.principal,
        expected_rate=investment_data.expected_rate,
        start_date=investment_data.start_date,
        end_date=investment_data.end_date,
        note=investment_data.note
    )
    db.add(investment)
    await db.flush()
    await db.refresh(investment)
    
    return InvestmentResponse(
        id=investment.id,
        family_id=investment.family_id,
        name=investment.name,
        investment_type=investment.investment_type,
        principal=investment.principal,
        expected_rate=investment.expected_rate,
        start_date=investment.start_date,
        end_date=investment.end_date,
        is_active=investment.is_active,
        note=investment.note,
        created_at=investment.created_at,
        total_income=0,
        income_records=[]
    )


@router.get("/list", response_model=List[InvestmentResponse])
async def list_investments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取理财列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Investment)
        .where(Investment.family_id == family_id)
        .order_by(Investment.created_at.desc())
    )
    investments = result.scalars().all()
    
    response = []
    for inv in investments:
        # 计算累计收益
        result = await db.execute(
            select(func.sum(InvestmentIncome.amount))
            .where(InvestmentIncome.investment_id == inv.id)
        )
        total_income = result.scalar() or 0
        
        # 获取收益记录
        result = await db.execute(
            select(InvestmentIncome)
            .where(InvestmentIncome.investment_id == inv.id)
            .order_by(InvestmentIncome.income_date.desc())
        )
        income_records = result.scalars().all()
        
        response.append(InvestmentResponse(
            id=inv.id,
            family_id=inv.family_id,
            name=inv.name,
            investment_type=inv.investment_type,
            principal=inv.principal,
            expected_rate=inv.expected_rate,
            start_date=inv.start_date,
            end_date=inv.end_date,
            is_active=inv.is_active,
            note=inv.note,
            created_at=inv.created_at,
            total_income=total_income,
            income_records=[
                InvestmentIncomeResponse(
                    id=ir.id,
                    investment_id=ir.investment_id,
                    amount=ir.amount,
                    income_date=ir.income_date,
                    note=ir.note,
                    created_at=ir.created_at
                ) for ir in income_records
            ]
        ))
    
    return response


@router.put("/{investment_id}", response_model=InvestmentResponse)
async def update_investment(
    investment_id: int,
    investment_data: InvestmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新理财配置"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Investment)
        .where(Investment.id == investment_id, Investment.family_id == family_id)
    )
    investment = result.scalar_one_or_none()
    if not investment:
        raise HTTPException(status_code=404, detail="理财产品不存在")
    
    if investment_data.name is not None:
        investment.name = investment_data.name
    if investment_data.principal is not None:
        investment.principal = investment_data.principal
    if investment_data.expected_rate is not None:
        investment.expected_rate = investment_data.expected_rate
    if investment_data.end_date is not None:
        investment.end_date = investment_data.end_date
    if investment_data.is_active is not None:
        investment.is_active = investment_data.is_active
    if investment_data.note is not None:
        investment.note = investment_data.note
    
    await db.flush()
    
    # 计算累计收益
    result = await db.execute(
        select(func.sum(InvestmentIncome.amount))
        .where(InvestmentIncome.investment_id == investment.id)
    )
    total_income = result.scalar() or 0
    
    return InvestmentResponse(
        id=investment.id,
        family_id=investment.family_id,
        name=investment.name,
        investment_type=investment.investment_type,
        principal=investment.principal,
        expected_rate=investment.expected_rate,
        start_date=investment.start_date,
        end_date=investment.end_date,
        is_active=investment.is_active,
        note=investment.note,
        created_at=investment.created_at,
        total_income=total_income,
        income_records=[]
    )


@router.post("/{investment_id}/income", response_model=InvestmentIncomeResponse)
async def add_investment_income(
    investment_id: int,
    income_data: InvestmentIncomeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """登记理财收益"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Investment)
        .where(Investment.id == investment_id, Investment.family_id == family_id)
    )
    investment = result.scalar_one_or_none()
    if not investment:
        raise HTTPException(status_code=404, detail="理财产品不存在")
    
    # 创建收益记录
    income = InvestmentIncome(
        investment_id=investment_id,
        amount=income_data.amount,
        income_date=income_data.income_date,
        note=income_data.note
    )
    db.add(income)
    await db.flush()
    
    # 获取当前余额
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0
    
    # 创建交易流水
    transaction = Transaction(
        family_id=family_id,
        user_id=None,
        transaction_type=TransactionType.INCOME,
        amount=income_data.amount,
        balance_after=current_balance + income_data.amount,
        description=f"理财收益: {investment.name} +{income_data.amount}元",
        reference_id=income.id,
        reference_type="investment_income"
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(income)
    
    return InvestmentIncomeResponse(
        id=income.id,
        investment_id=income.investment_id,
        amount=income.amount,
        income_date=income.income_date,
        note=income.note,
        created_at=income.created_at
    )


@router.get("/summary", response_model=InvestmentSummary)
async def get_investment_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取理财汇总"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取所有理财
    result = await db.execute(
        select(Investment).where(Investment.family_id == family_id)
    )
    investments = result.scalars().all()
    
    total_principal = sum(inv.principal for inv in investments if inv.is_active)
    active_count = sum(1 for inv in investments if inv.is_active)
    
    # 计算总收益
    result = await db.execute(
        select(func.sum(InvestmentIncome.amount))
        .join(Investment, InvestmentIncome.investment_id == Investment.id)
        .where(Investment.family_id == family_id)
    )
    total_income = result.scalar() or 0
    
    return InvestmentSummary(
        family_id=family_id,
        total_principal=total_principal,
        total_income=total_income,
        active_count=active_count,
        investments=[]  # 简化返回，完整列表用 /list 接口
    )
