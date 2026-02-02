"""
年度财务报告 API - 年末自动生成财务总结
"""
from datetime import datetime, date
from typing import Optional, List
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import (
    User, FamilyMember, Family, Deposit, Transaction, 
    Investment, InvestmentIncome, AnnualReport, TransactionType
)

router = APIRouter(prefix="/report", tags=["report"])


# ==================== Helper ====================

async def get_user_family_id(user_id: int, db: AsyncSession) -> int:
    """获取用户所属家庭ID"""
    result = await db.execute(
        select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
    )
    family_id = result.scalar_one_or_none()
    if not family_id:
        raise HTTPException(status_code=400, detail="您还没有加入家庭")
    return family_id


async def calculate_equity_at_date(db: AsyncSession, family_id: int, target_date: date) -> dict:
    """计算指定日期的股权分布"""
    # 获取家庭成员
    result = await db.execute(
        select(FamilyMember, User)
        .join(User, FamilyMember.user_id == User.id)
        .where(FamilyMember.family_id == family_id)
    )
    members = result.fetchall()
    
    # 获取截至该日期的所有存款
    result = await db.execute(
        select(Deposit.user_id, func.sum(Deposit.amount))
        .where(
            Deposit.family_id == family_id,
            Deposit.deposit_date <= datetime.combine(target_date, datetime.max.time())
        )
        .group_by(Deposit.user_id)
    )
    deposits_by_user = {row[0]: row[1] for row in result.fetchall()}
    
    total_deposits = sum(deposits_by_user.values()) if deposits_by_user else 0
    
    equity_data = {}
    for member, user in members:
        user_deposits = deposits_by_user.get(user.id, 0)
        equity_ratio = (user_deposits / total_deposits * 100) if total_deposits > 0 else 0
        equity_data[str(user.id)] = {
            "name": user.nickname,
            "deposits": user_deposits,
            "equity_ratio": round(equity_ratio, 2)
        }
    
    return equity_data


async def generate_annual_report_data(db: AsyncSession, family_id: int, year: int) -> dict:
    """生成年度报告数据"""
    start_of_year = datetime(year, 1, 1)
    end_of_year = datetime(year, 12, 31, 23, 59, 59)
    start_of_prev_year = datetime(year - 1, 12, 31, 23, 59, 59)
    
    # 1. 年度总存款
    result = await db.execute(
        select(func.sum(Deposit.amount)).where(
            Deposit.family_id == family_id,
            Deposit.deposit_date >= start_of_year,
            Deposit.deposit_date <= end_of_year
        )
    )
    total_deposits = result.scalar() or 0
    
    # 2. 年度总支出（从交易记录获取）
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.family_id == family_id,
            Transaction.transaction_type == TransactionType.WITHDRAW,
            Transaction.created_at >= start_of_year,
            Transaction.created_at <= end_of_year
        )
    )
    total_withdrawals = abs(result.scalar() or 0)
    
    # 3. 年度理财收益
    result = await db.execute(
        select(func.sum(InvestmentIncome.amount))
        .join(Investment, InvestmentIncome.investment_id == Investment.id)
        .where(
            Investment.family_id == family_id,
            InvestmentIncome.income_date >= start_of_year,
            InvestmentIncome.income_date <= end_of_year
        )
    )
    total_income = result.scalar() or 0
    
    # 4. 年初余额（上年末最后一笔交易的balance_after）
    result = await db.execute(
        select(Transaction.balance_after)
        .where(
            Transaction.family_id == family_id,
            Transaction.created_at <= start_of_prev_year
        )
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    start_balance = result.scalar() or 0
    
    # 5. 年末余额
    result = await db.execute(
        select(Transaction.balance_after)
        .where(
            Transaction.family_id == family_id,
            Transaction.created_at <= end_of_year
        )
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    end_balance = result.scalar() or 0
    
    # 6. 净资产变化
    net_change = end_balance - start_balance
    
    # 7. 月度数据
    monthly_data = []
    for month in range(1, 13):
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)
        
        # 月度存款
        result = await db.execute(
            select(func.sum(Deposit.amount)).where(
                Deposit.family_id == family_id,
                Deposit.deposit_date >= month_start,
                Deposit.deposit_date < month_end
            )
        )
        month_deposits = result.scalar() or 0
        
        # 月度支出
        result = await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.family_id == family_id,
                Transaction.transaction_type == TransactionType.WITHDRAW,
                Transaction.created_at >= month_start,
                Transaction.created_at < month_end
            )
        )
        month_withdrawals = abs(result.scalar() or 0)
        
        # 月度收益
        result = await db.execute(
            select(func.sum(InvestmentIncome.amount))
            .join(Investment, InvestmentIncome.investment_id == Investment.id)
            .where(
                Investment.family_id == family_id,
                InvestmentIncome.income_date >= month_start,
                InvestmentIncome.income_date < month_end
            )
        )
        month_income = result.scalar() or 0
        
        monthly_data.append({
            "month": month,
            "deposits": month_deposits,
            "withdrawals": month_withdrawals,
            "income": month_income,
            "net": month_deposits - month_withdrawals + month_income
        })
    
    # 8. 股权变化（年初 vs 年末）
    equity_start = await calculate_equity_at_date(db, family_id, date(year, 1, 1))
    equity_end = await calculate_equity_at_date(db, family_id, date(year, 12, 31))
    
    equity_changes = {}
    all_user_ids = set(equity_start.keys()) | set(equity_end.keys())
    for user_id in all_user_ids:
        start_data = equity_start.get(user_id, {"name": "未知", "equity_ratio": 0})
        end_data = equity_end.get(user_id, {"name": start_data.get("name", "未知"), "equity_ratio": 0})
        
        equity_changes[user_id] = {
            "name": end_data.get("name", start_data.get("name", "未知")),
            "start_ratio": start_data.get("equity_ratio", 0),
            "end_ratio": end_data.get("equity_ratio", 0),
            "change": round(end_data.get("equity_ratio", 0) - start_data.get("equity_ratio", 0), 2)
        }
    
    # 9. 年度亮点
    highlights = []
    
    # 最大单笔存款
    result = await db.execute(
        select(Deposit, User)
        .join(User, Deposit.user_id == User.id)
        .where(
            Deposit.family_id == family_id,
            Deposit.deposit_date >= start_of_year,
            Deposit.deposit_date <= end_of_year
        )
        .order_by(Deposit.amount.desc())
        .limit(1)
    )
    max_deposit = result.first()
    if max_deposit:
        deposit, user = max_deposit
        highlights.append({
            "type": "max_deposit",
            "title": "最大单笔存款",
            "value": deposit.amount,
            "description": f"{user.nickname} 在 {deposit.deposit_date.strftime('%m月%d日')} 存入 ¥{deposit.amount:,.2f}"
        })
    
    # 最佳理财收益月
    best_month = max(monthly_data, key=lambda x: x["income"]) if monthly_data else None
    if best_month and best_month["income"] > 0:
        highlights.append({
            "type": "best_income_month",
            "title": "最佳收益月份",
            "value": best_month["income"],
            "description": f"{best_month['month']}月理财收益 ¥{best_month['income']:,.2f}"
        })
    
    # 年度储蓄率
    if total_deposits > 0:
        savings_rate = ((total_deposits - total_withdrawals) / total_deposits) * 100
        highlights.append({
            "type": "savings_rate",
            "title": "年度储蓄率",
            "value": round(savings_rate, 1),
            "description": f"全年储蓄率 {savings_rate:.1f}%"
        })
    
    # 资产增长率
    if start_balance > 0:
        growth_rate = ((end_balance - start_balance) / start_balance) * 100
        highlights.append({
            "type": "growth_rate",
            "title": "资产增长率",
            "value": round(growth_rate, 1),
            "description": f"全年资产增长 {growth_rate:.1f}%"
        })
    
    return {
        "year": year,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "total_income": total_income,
        "net_change": net_change,
        "start_balance": start_balance,
        "end_balance": end_balance,
        "equity_changes": equity_changes,
        "monthly_data": monthly_data,
        "highlights": highlights
    }


# ==================== API ====================

@router.get("/annual/{year}", response_model=dict)
async def get_annual_report(
    year: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取指定年度的财务报告"""
    family_id = await get_user_family_id(current_user.id, db)
    
    current_year = datetime.now().year
    if year > current_year:
        raise HTTPException(status_code=400, detail="无法生成未来年份的报告")
    if year < 2020:
        raise HTTPException(status_code=400, detail="年份不能早于2020年")
    
    # 检查是否已有缓存的报告
    result = await db.execute(
        select(AnnualReport).where(
            AnnualReport.family_id == family_id,
            AnnualReport.year == year
        )
    )
    cached_report = result.scalar_one_or_none()
    
    # 如果是当前年份，总是重新生成；如果是历史年份且有缓存，使用缓存
    if cached_report and year < current_year:
        return {
            "year": cached_report.year,
            "total_deposits": cached_report.total_deposits,
            "total_withdrawals": cached_report.total_withdrawals,
            "total_income": cached_report.total_income,
            "net_change": cached_report.net_change,
            "start_balance": cached_report.start_balance,
            "end_balance": cached_report.end_balance,
            "equity_changes": json.loads(cached_report.equity_changes),
            "monthly_data": json.loads(cached_report.monthly_data),
            "highlights": json.loads(cached_report.highlights),
            "is_cached": True,
            "generated_at": cached_report.created_at.isoformat()
        }
    
    # 生成新报告
    report_data = await generate_annual_report_data(db, family_id, year)
    
    # 如果是历史年份，缓存报告
    if year < current_year:
        if cached_report:
            # 更新现有缓存
            cached_report.total_deposits = report_data["total_deposits"]
            cached_report.total_withdrawals = report_data["total_withdrawals"]
            cached_report.total_income = report_data["total_income"]
            cached_report.net_change = report_data["net_change"]
            cached_report.start_balance = report_data["start_balance"]
            cached_report.end_balance = report_data["end_balance"]
            cached_report.equity_changes = json.dumps(report_data["equity_changes"], ensure_ascii=False)
            cached_report.monthly_data = json.dumps(report_data["monthly_data"], ensure_ascii=False)
            cached_report.highlights = json.dumps(report_data["highlights"], ensure_ascii=False)
        else:
            # 创建新缓存
            new_report = AnnualReport(
                family_id=family_id,
                year=year,
                total_deposits=report_data["total_deposits"],
                total_withdrawals=report_data["total_withdrawals"],
                total_income=report_data["total_income"],
                net_change=report_data["net_change"],
                start_balance=report_data["start_balance"],
                end_balance=report_data["end_balance"],
                equity_changes=json.dumps(report_data["equity_changes"], ensure_ascii=False),
                monthly_data=json.dumps(report_data["monthly_data"], ensure_ascii=False),
                highlights=json.dumps(report_data["highlights"], ensure_ascii=False)
            )
            db.add(new_report)
        
        await db.commit()
    
    report_data["is_cached"] = False
    report_data["generated_at"] = datetime.now().isoformat()
    
    return report_data


@router.get("/years", response_model=dict)
async def get_available_years(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用的报告年份列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取家庭最早的存款/交易记录年份
    result = await db.execute(
        select(func.min(Deposit.deposit_date)).where(Deposit.family_id == family_id)
    )
    earliest_deposit = result.scalar()
    
    result = await db.execute(
        select(func.min(Transaction.created_at)).where(Transaction.family_id == family_id)
    )
    earliest_transaction = result.scalar()
    
    earliest_date = None
    if earliest_deposit and earliest_transaction:
        earliest_date = min(earliest_deposit, earliest_transaction)
    elif earliest_deposit:
        earliest_date = earliest_deposit
    elif earliest_transaction:
        earliest_date = earliest_transaction
    
    current_year = datetime.now().year
    
    if not earliest_date:
        return {"years": [current_year]}
    
    start_year = earliest_date.year
    years = list(range(start_year, current_year + 1))
    years.reverse()  # 最新年份在前
    
    return {"years": years}


@router.get("/summary", response_model=dict)
async def get_quick_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取快速财务摘要（用于仪表盘）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # 当月数据
    month_start = datetime(current_year, current_month, 1)
    if current_month == 12:
        month_end = datetime(current_year + 1, 1, 1)
    else:
        month_end = datetime(current_year, current_month + 1, 1)
    
    # 当月存款
    result = await db.execute(
        select(func.sum(Deposit.amount)).where(
            Deposit.family_id == family_id,
            Deposit.deposit_date >= month_start,
            Deposit.deposit_date < month_end
        )
    )
    month_deposits = result.scalar() or 0
    
    # 当月支出
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.family_id == family_id,
            Transaction.transaction_type == TransactionType.WITHDRAW,
            Transaction.created_at >= month_start,
            Transaction.created_at < month_end
        )
    )
    month_withdrawals = abs(result.scalar() or 0)
    
    # 当月收益
    result = await db.execute(
        select(func.sum(InvestmentIncome.amount))
        .join(Investment, InvestmentIncome.investment_id == Investment.id)
        .where(
            Investment.family_id == family_id,
            InvestmentIncome.income_date >= month_start,
            InvestmentIncome.income_date < month_end
        )
    )
    month_income = result.scalar() or 0
    
    # 当前余额
    result = await db.execute(
        select(Transaction.balance_after)
        .where(Transaction.family_id == family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    current_balance = result.scalar() or 0
    
    # 年度累计
    year_start = datetime(current_year, 1, 1)
    result = await db.execute(
        select(func.sum(Deposit.amount)).where(
            Deposit.family_id == family_id,
            Deposit.deposit_date >= year_start
        )
    )
    year_deposits = result.scalar() or 0
    
    result = await db.execute(
        select(func.sum(InvestmentIncome.amount))
        .join(Investment, InvestmentIncome.investment_id == Investment.id)
        .where(
            Investment.family_id == family_id,
            InvestmentIncome.income_date >= year_start
        )
    )
    year_income = result.scalar() or 0
    
    return {
        "current_balance": current_balance,
        "month": {
            "deposits": month_deposits,
            "withdrawals": month_withdrawals,
            "income": month_income,
            "net": month_deposits - month_withdrawals + month_income
        },
        "year": {
            "deposits": year_deposits,
            "income": year_income
        },
        "as_of": now.isoformat()
    }


@router.get("/compare/{year1}/{year2}", response_model=dict)
async def compare_years(
    year1: int,
    year2: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """对比两个年度的财务数据"""
    family_id = await get_user_family_id(current_user.id, db)
    
    report1 = await generate_annual_report_data(db, family_id, year1)
    report2 = await generate_annual_report_data(db, family_id, year2)
    
    def calc_change(new, old):
        if old == 0:
            return 100 if new > 0 else 0
        return round(((new - old) / abs(old)) * 100, 1)
    
    return {
        "year1": year1,
        "year2": year2,
        "comparison": {
            "deposits": {
                "year1": report1["total_deposits"],
                "year2": report2["total_deposits"],
                "change": calc_change(report2["total_deposits"], report1["total_deposits"])
            },
            "withdrawals": {
                "year1": report1["total_withdrawals"],
                "year2": report2["total_withdrawals"],
                "change": calc_change(report2["total_withdrawals"], report1["total_withdrawals"])
            },
            "income": {
                "year1": report1["total_income"],
                "year2": report2["total_income"],
                "change": calc_change(report2["total_income"], report1["total_income"])
            },
            "net_change": {
                "year1": report1["net_change"],
                "year2": report2["net_change"],
                "change": calc_change(report2["net_change"], report1["net_change"])
            },
            "end_balance": {
                "year1": report1["end_balance"],
                "year2": report2["end_balance"],
                "change": calc_change(report2["end_balance"], report1["end_balance"])
            }
        }
    }
