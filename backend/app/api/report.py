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
            "member_id": user.id,
            "name": user.nickname,
            "deposits": user_deposits,
            "equity_ratio": round(equity_ratio, 2),
            "avatar_version": user.avatar_version or 0
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
    
    # 转换 equity_changes 为前端期望的数组格式
    equity_start_list = []
    equity_end_list = []
    for user_id, data in equity_changes.items():
        # 从 equity_end 获取 avatar_version（因为它是当前最新的数据）
        avatar_version = equity_end.get(user_id, {}).get("avatar_version", 0)
        equity_start_list.append({
            "member_id": int(user_id),
            "name": data["name"],
            "percentage": data["start_ratio"],
            "avatar_version": avatar_version
        })
        equity_end_list.append({
            "member_id": int(user_id),
            "name": data["name"],
            "percentage": data["end_ratio"],
            "avatar_version": avatar_version
        })
    
    # 转换 monthly_data 为前端期望的格式
    monthly_data_formatted = []
    for m in monthly_data:
        monthly_data_formatted.append({
            "month": m["month"],
            "income": m["deposits"] + m["income"],  # 收入 = 存款 + 理财收益
            "expense": m["withdrawals"],
            "net": m["net"]
        })
    
    # 转换 highlights 为前端期望的对象格式
    highlights_obj = {}
    for h in highlights:
        if h["type"] == "max_deposit":
            highlights_obj["biggest_deposit"] = {
                "amount": h["value"],
                "member": h["description"].split(" 在 ")[0] if " 在 " in h["description"] else "",
                "date": None  # 日期需要从描述解析或添加到原数据
            }
        elif h["type"] == "best_income_month":
            highlights_obj["best_month"] = {
                "month": int(h["description"].split("月")[0]) if "月" in h["description"] else 1,
                "net": h["value"]
            }
        elif h["type"] == "savings_rate":
            highlights_obj["savings_rate"] = h["value"]
        elif h["type"] == "growth_rate":
            highlights_obj["growth_rate"] = h["value"]
    
    # 添加理财收益到亮点
    if total_income > 0:
        highlights_obj["investment_return"] = total_income
    
    # 查找最佳存款人
    if max_deposit:
        # 获取各成员的总存款
        member_deposits = await db.execute(
            select(User.nickname, func.sum(Deposit.amount).label('total'))
            .join(Deposit, User.id == Deposit.user_id)
            .where(
                Deposit.family_id == family_id,
                Deposit.deposit_date >= start_of_year,
                Deposit.deposit_date <= end_of_year
            )
            .group_by(User.id, User.nickname)
            .order_by(func.sum(Deposit.amount).desc())
            .limit(1)
        )
        top_depositor = member_deposits.first()
        if top_depositor:
            highlights_obj["most_deposits_member"] = {
                "name": top_depositor[0],
                "total": top_depositor[1]
            }
    
    # 10. 计算建议分红（基于年末持股比例分配投资收益）
    dividend_suggestion = {
        "total_investment_income": total_income,  # 可分配的投资收益总额
        "distribution": [],  # 各成员的分红明细
        "has_dividend": total_income > 0  # 是否有可分配收益
    }
    
    if total_income > 0:
        for eq in equity_end_list:
            # 按年末持股比例计算每人应得分红
            member_dividend = round(total_income * eq["percentage"] / 100, 2)
            dividend_suggestion["distribution"].append({
                "member_id": eq["member_id"],
                "name": eq["name"],
                "equity_percentage": eq["percentage"],
                "dividend_amount": member_dividend,
                "avatar_version": eq.get("avatar_version", 0)
            })
    
    return {
        "year": year,
        "summary": {
            "total_income": total_deposits + total_income,  # 总收入 = 存款 + 理财收益
            "total_expense": total_withdrawals,
            "net_change": net_change,
            "start_balance": start_balance,
            "end_balance": end_balance
        },
        "monthly_data": monthly_data_formatted,
        "equity_start": equity_start_list,
        "equity_end": equity_end_list,
        "highlights": highlights_obj,
        "dividend_suggestion": dividend_suggestion,  # 建议分红
        # 也保留原始数据，方便以后使用
        "raw": {
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_income": total_income,
            "equity_changes": equity_changes
        }
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
    
    # 生成新报告（暂时禁用缓存，因为数据格式已更改）
    report_data = await generate_annual_report_data(db, family_id, year)
    
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
    
    # 从 raw 字段获取原始数据
    raw1 = report1.get("raw", {})
    raw2 = report2.get("raw", {})
    summary1 = report1.get("summary", {})
    summary2 = report2.get("summary", {})
    
    return {
        "year1": year1,
        "year2": year2,
        "comparison": {
            "deposits": {
                "year1": raw1.get("total_deposits", 0),
                "year2": raw2.get("total_deposits", 0),
                "change": calc_change(raw2.get("total_deposits", 0), raw1.get("total_deposits", 0))
            },
            "withdrawals": {
                "year1": raw1.get("total_withdrawals", 0),
                "year2": raw2.get("total_withdrawals", 0),
                "change": calc_change(raw2.get("total_withdrawals", 0), raw1.get("total_withdrawals", 0))
            },
            "income": {
                "year1": raw1.get("total_income", 0),
                "year2": raw2.get("total_income", 0),
                "change": calc_change(raw2.get("total_income", 0), raw1.get("total_income", 0))
            },
            "net_change": {
                "year1": summary1.get("net_change", 0),
                "year2": summary2.get("net_change", 0),
                "change": calc_change(summary2.get("net_change", 0), summary1.get("net_change", 0))
            },
            "end_balance": {
                "year1": summary1.get("end_balance", 0),
                "year2": summary2.get("end_balance", 0),
                "change": calc_change(summary2.get("end_balance", 0), summary1.get("end_balance", 0))
            }
        }
    }
