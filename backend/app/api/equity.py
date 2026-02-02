"""
小金库 (Golden Nest) - 股权路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import FamilyMember, User
from app.schemas.equity import EquitySummary
from app.api.auth import get_current_user
from app.services.equity import calculate_family_equity

router = APIRouter()


@router.get("/summary", response_model=EquitySummary)
async def get_equity_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取股权汇总信息"""
    # 获取用户的家庭
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="您还没有加入任何家庭")
    
    # 计算股权
    equity_summary = await calculate_family_equity(membership.family_id, db)
    
    return equity_summary
