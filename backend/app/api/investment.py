"""
小金库 (Golden Nest) - 理财管理路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import (
    Investment, InvestmentIncome, InvestmentPosition, PositionOperationType,
    FamilyMember, User, Transaction, TransactionType
)
from app.schemas.investment import (
    InvestmentCreate, InvestmentUpdate, InvestmentResponse,
    InvestmentIncomeCreate, InvestmentIncomeResponse, InvestmentPositionResponse,
    InvestmentSummary
)
from app.schemas.common import TimeRange, get_time_range_filter
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
    time_range: TimeRange = Query(TimeRange.MONTH, description="时间范围：day/week/month/year/all"),
    include_deleted: bool = Query(False, description="是否包含已删除的投资"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取理财列表（支持时间范围筛选，默认最近一个月）"""
    import logging
    family_id = await get_user_family_id(current_user.id, db)
    logging.info(f"Listing investments for user_id={current_user.id}, family_id={family_id}")
    
    # 构建查询
    query = select(Investment).where(Investment.family_id == family_id)
    
    # 过滤已删除的投资
    if not include_deleted:
        query = query.where(Investment.is_deleted == False)
    
    # 时间范围筛选
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(Investment.created_at >= start_time)
    
    # 使用selectinload预加载关联数据，避免N+1查询
    result = await db.execute(
        query.options(
            selectinload(Investment.positions),
            selectinload(Investment.income_records)
        ).order_by(Investment.created_at.desc())
    )
    investments = result.scalars().all()
    logging.info(f"Found {len(investments)} investments for family_id={family_id}")
    
    response = []
    for inv in investments:
        # 直接使用预加载的关联数据（不再需要额外查询）
        positions = inv.positions
        positions.sort(key=lambda p: p.operation_date, reverse=True)
        
        # 计算当前持仓本金
        current_principal = sum(
            p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
            else -p.amount
            for p in positions
        )
        
        # 直接使用预加载的收益记录（不再需要额外查询）
        income_records = inv.income_records
        income_records.sort(key=lambda ir: ir.income_date, reverse=True)
        
        # 计算总收益（支持新旧两种模式）
        total_return = sum(
            ir.calculated_income if ir.calculated_income is not None else ir.amount
            for ir in income_records
        )
        
        # 计算ROI
        roi = (total_return / inv.principal * 100) if inv.principal > 0 else 0
        
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
            is_deleted=inv.is_deleted,
            deleted_at=inv.deleted_at,
            note=inv.note,
            created_at=inv.created_at,
            total_income=total_return,  # Deprecated but kept for compatibility
            current_principal=current_principal,
            total_return=total_return,
            roi=roi,
            income_records=[
                InvestmentIncomeResponse(
                    id=ir.id,
                    investment_id=ir.investment_id,
                    amount=ir.amount,
                    current_value=ir.current_value,
                    calculated_income=ir.calculated_income,
                    income_date=ir.income_date,
                    note=ir.note,
                    created_at=ir.created_at
                ) for ir in income_records
            ],
            positions=[
                InvestmentPositionResponse(
                    id=p.id,
                    investment_id=p.investment_id,
                    operation_type=p.operation_type,
                    amount=p.amount,
                    operation_date=p.operation_date,
                    note=p.note,
                    transaction_id=p.transaction_id,
                    deposit_id=p.deposit_id,
                    approval_request_id=p.approval_request_id,
                    created_at=p.created_at
                ) for p in positions
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
    
    # 获取所有未删除的理财
    result = await db.execute(
        select(Investment).where(
            Investment.family_id == family_id,
            Investment.is_deleted == False
        )
    )
    investments = result.scalars().all()
    
    # 计算总本金（使用持仓记录）
    total_principal = 0
    for inv in investments:
        if inv.is_active:
            result = await db.execute(
                select(InvestmentPosition).where(
                    InvestmentPosition.investment_id == inv.id
                )
            )
            positions = result.scalars().all()
            current_principal = sum(
                p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
                else -p.amount
                for p in positions
            )
            total_principal += current_principal
    
    active_count = sum(1 for inv in investments if inv.is_active)
    
    # 计算总收益（支持新旧两种模式）
    result = await db.execute(
        select(InvestmentIncome)
        .join(Investment, InvestmentIncome.investment_id == Investment.id)
        .where(
            Investment.family_id == family_id,
            Investment.is_deleted == False
        )
    )
    incomes = result.scalars().all()
    total_income = sum(
        inc.calculated_income if inc.calculated_income is not None else inc.amount
        for inc in incomes
    )
    
    return InvestmentSummary(
        family_id=family_id,
        total_principal=total_principal,
        total_income=total_income,
        active_count=active_count,
        investments=[]  # 简化返回，完整列表用 /list 接口
    )
