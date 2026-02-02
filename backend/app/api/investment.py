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


@router.post("/create")
async def create_investment(
    investment_data: InvestmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    [已废弃] 创建理财配置
    
    此接口已废弃，请使用审批接口 POST /api/approval/investment/create
    所有理财配置创建需要经过家庭成员审批后才能执行。
    """
    raise HTTPException(
        status_code=400,
        detail="此接口已废弃。创建理财需要家庭成员审批，请使用 POST /api/approval/investment/create 接口"
    )


@router.get("/list", response_model=List[InvestmentResponse])
async def list_investments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取理财列表"""
    import logging
    family_id = await get_user_family_id(current_user.id, db)
    logging.info(f"Listing investments for user_id={current_user.id}, family_id={family_id}")
    
    result = await db.execute(
        select(Investment)
        .where(Investment.family_id == family_id)
        .order_by(Investment.created_at.desc())
    )
    investments = result.scalars().all()
    logging.info(f"Found {len(investments)} investments for family_id={family_id}")
    
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


@router.put("/{investment_id}")
async def update_investment(
    investment_id: int,
    investment_data: InvestmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    [已废弃] 更新理财配置
    
    此接口已废弃，请使用审批接口 POST /api/approval/investment/update
    所有理财配置更新需要经过家庭成员审批后才能执行。
    """
    raise HTTPException(
        status_code=400,
        detail="此接口已废弃。更新理财需要家庭成员审批，请使用 POST /api/approval/investment/update 接口"
    )


@router.post("/{investment_id}/income")
async def add_investment_income(
    investment_id: int,
    income_data: InvestmentIncomeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    [已废弃] 登记理财收益
    
    此接口已废弃，请使用审批接口 POST /api/approval/investment/income
    所有理财收益登记需要经过家庭成员审批后才能执行。
    """
    raise HTTPException(
        status_code=400,
        detail="此接口已废弃。登记理财收益需要家庭成员审批，请使用 POST /api/approval/investment/income 接口"
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
