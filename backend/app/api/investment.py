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
        
        # 计算平均年化收益率
        annualized_return = 0
        holding_days = 0
        if positions:
            # 获取首次购买日期（最早的持仓记录）
            first_position = min(positions, key=lambda p: p.operation_date)
            # 获取最新登记日期（最近的收益记录或最近的持仓操作）
            latest_date = inv.start_date
            if income_records:
                latest_income = max(income_records, key=lambda ir: ir.income_date)
                latest_date = max(latest_date, latest_income.income_date)
            if positions:
                latest_position = max(positions, key=lambda p: p.operation_date)
                latest_date = max(latest_date, latest_position.operation_date)
            
            # 计算持有天数
            holding_days = (latest_date - first_position.operation_date).days
            
            # 计算平均年化收益率：(总收益 / 当前本金) / (持有天数 / 365) * 100%
            if holding_days > 0 and current_principal > 0:
                holding_years = holding_days / 365.0
                annualized_return = (total_return / current_principal / holding_years) * 100
        
        response.append(InvestmentResponse(
            id=inv.id,
            family_id=inv.family_id,
            name=inv.name,
            investment_type=inv.investment_type,
            principal=inv.principal,
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
            annualized_return=annualized_return,
            holding_days=holding_days,
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
    
    # 计算综合平均年化收益率（加权平均）
    average_annualized_return = 0
    if total_principal > 0:
        weighted_return_sum = 0
        total_weight = 0
        
        for inv in investments:
            if not inv.is_active:
                continue
                
            # 获取持仓记录
            result_pos = await db.execute(
                select(InvestmentPosition).where(
                    InvestmentPosition.investment_id == inv.id
                )
            )
            positions = result_pos.scalars().all()
            
            if not positions:
                continue
            
            # 计算当前本金
            current_principal = sum(
                p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
                else -p.amount
                for p in positions
            )
            
            if current_principal <= 0:
                continue
            
            # 获取该产品的收益记录
            result_inc = await db.execute(
                select(InvestmentIncome).where(
                    InvestmentIncome.investment_id == inv.id
                )
            )
            product_incomes = result_inc.scalars().all()
            product_total_income = sum(
                inc.calculated_income if inc.calculated_income is not None else inc.amount
                for inc in product_incomes
            )
            
            # 获取首次购买日期和最新登记日期
            first_position = min(positions, key=lambda p: p.operation_date)
            latest_date = inv.start_date
            
            if product_incomes:
                latest_income = max(product_incomes, key=lambda ir: ir.income_date)
                latest_date = max(latest_date, latest_income.income_date)
            
            latest_position = max(positions, key=lambda p: p.operation_date)
            latest_date = max(latest_date, latest_position.operation_date)
            
            # 计算持有天数和年化收益率
            holding_days = (latest_date - first_position.operation_date).days
            if holding_days > 0:
                holding_years = holding_days / 365.0
                product_annualized = (product_total_income / current_principal / holding_years) * 100
                
                # 按本金加权
                weighted_return_sum += product_annualized * current_principal
                total_weight += current_principal
        
        if total_weight > 0:
            average_annualized_return = weighted_return_sum / total_weight
    
    return InvestmentSummary(
        family_id=family_id,
        total_principal=total_principal,
        total_income=total_income,
        active_count=active_count,
        average_annualized_return=average_annualized_return,
        investments=[]  # 简化返回，完整列表用 /list 接口
    )


@router.get("/{investment_id}/history")
async def get_investment_history(
    investment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取投资的操作历史"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取投资产品
    result = await db.execute(
        select(Investment).where(
            Investment.id == investment_id,
            Investment.family_id == family_id
        )
    )
    investment = result.scalar_one_or_none()
    if not investment:
        raise HTTPException(status_code=404, detail="投资产品不存在")
    
    # 获取所有的持仓操作记录
    result = await db.execute(
        select(InvestmentPosition)
        .where(InvestmentPosition.investment_id == investment_id)
        .order_by(InvestmentPosition.created_at.desc())
    )
    positions = result.scalars().all()
    
    # 获取相关的收益记录
    result = await db.execute(
        select(InvestmentIncome)
        .where(InvestmentIncome.investment_id == investment_id)
        .order_by(InvestmentIncome.income_date.desc())
    )
    incomes = result.scalars().all()
    
    # 构造操作历史列表
    history = []
    
    # 添加持仓操作
    for position in positions:
        history.append({
            "type": "position",
            "operation_type": position.operation_type.value,
            "amount": position.amount,
            "principal_before": position.principal_before,
            "principal_after": position.principal_after,
            "date": position.operation_date.isoformat() if position.operation_date else position.created_at.isoformat(),
            "note": position.note,
            "timestamp": position.created_at.isoformat()
        })
    
    # 添加收益记录
    for income in incomes:
        history.append({
            "type": "income",
            "amount": income.calculated_income or income.amount,  # 优先使用计算的收益，否则用amount
            "current_value": income.current_value,
            "date": income.income_date.isoformat(),
            "note": income.note,
            "timestamp": income.created_at.isoformat()
        })
    
    # 按时间戳倒序排列
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # 计算当前持仓
    current_principal = sum(
        pos.amount if pos.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
        else -pos.amount
        for pos in positions
    )
    
    return {
        "investment": {
            "id": investment.id,
            "name": investment.name,
            "investment_type": investment.investment_type.value,
            "principal": investment.principal,
            "current_principal": current_principal,
            "start_date": investment.start_date.isoformat() if investment.start_date else None,
            "end_date": investment.end_date.isoformat() if investment.end_date else None,
            "is_active": investment.is_active
        },
        "history": history
    }
