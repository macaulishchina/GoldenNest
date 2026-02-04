"""
股权赠与 API 路由
"""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, FamilyMember, EquityGift, EquityGiftStatus, Deposit
from app.schemas.gift import (
    GiftCreate,
    GiftResponse,
    GiftAcceptReject,
    GiftListResponse,
    GiftStats,
)

router = APIRouter(prefix="/api/gift", tags=["股权赠与"])


async def get_user_equity(db: AsyncSession, user_id: int, family_id: int) -> float:
    """计算用户在家庭中的股权比例"""
    # 获取该用户的总存款
    user_result = await db.execute(
        select(func.coalesce(func.sum(Deposit.amount), 0))
        .where(and_(Deposit.user_id == user_id, Deposit.family_id == family_id))
    )
    user_total = user_result.scalar() or 0
    
    # 获取家庭总存款
    family_result = await db.execute(
        select(func.coalesce(func.sum(Deposit.amount), 0))
        .where(Deposit.family_id == family_id)
    )
    family_total = family_result.scalar() or 0
    
    if family_total == 0:
        return 0
    
    return user_total / family_total


async def build_gift_response(db: AsyncSession, gift: EquityGift) -> GiftResponse:
    """构建赠与响应对象"""
    # 获取发送者信息
    from_user_result = await db.execute(
        select(User).where(User.id == gift.from_user_id)
    )
    from_user = from_user_result.scalar_one()
    
    # 获取接收者信息
    to_user_result = await db.execute(
        select(User).where(User.id == gift.to_user_id)
    )
    to_user = to_user_result.scalar_one()
    
    return GiftResponse(
        id=gift.id,
        family_id=gift.family_id,
        from_user_id=gift.from_user_id,
        from_user_nickname=from_user.nickname,
        from_avatar_version=from_user.avatar_version or 0,
        to_user_id=gift.to_user_id,
        to_user_nickname=to_user.nickname,
        to_avatar_version=to_user.avatar_version or 0,
        amount=gift.amount,
        message=gift.message,
        status=gift.status.value,
        created_at=gift.created_at,
        responded_at=gift.responded_at,
    )


@router.post("/send", response_model=GiftResponse)
async def send_gift(
    gift_data: GiftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送股权赠与
    
    - 只能赠与给同一家庭的成员
    - 赠与比例不能超过自己的股权比例
    """
    # 检查用户是否属于某个家庭
    member_result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = member_result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(status_code=400, detail="您还没有加入家庭")
    
    family_id = membership.family_id
    
    # 检查接收者是否是同一家庭成员
    to_member_result = await db.execute(
        select(FamilyMember).where(
            and_(
                FamilyMember.user_id == gift_data.to_user_id,
                FamilyMember.family_id == family_id
            )
        )
    )
    to_membership = to_member_result.scalar_one_or_none()
    
    if not to_membership:
        raise HTTPException(status_code=400, detail="接收者不是您的家庭成员")
    
    if gift_data.to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己赠送股权")
    
    # 检查用户的股权比例是否足够
    user_equity = await get_user_equity(db, current_user.id, family_id)
    
    if gift_data.amount > user_equity:
        raise HTTPException(
            status_code=400, 
            detail=f"您的股权比例为 {user_equity*100:.2f}%，无法赠送 {gift_data.amount*100:.2f}%"
        )
    
    # 检查是否有未处理的赠与给同一用户
    pending_result = await db.execute(
        select(EquityGift).where(
            and_(
                EquityGift.from_user_id == current_user.id,
                EquityGift.to_user_id == gift_data.to_user_id,
                EquityGift.status == EquityGiftStatus.PENDING
            )
        )
    )
    pending_gift = pending_result.scalar_one_or_none()
    
    if pending_gift:
        raise HTTPException(status_code=400, detail="您已有一个待处理的赠与请求给该用户")
    
    # 创建赠与记录
    new_gift = EquityGift(
        family_id=family_id,
        from_user_id=current_user.id,
        to_user_id=gift_data.to_user_id,
        amount=gift_data.amount,
        message=gift_data.message,
        status=EquityGiftStatus.PENDING,
    )
    
    db.add(new_gift)
    await db.commit()
    await db.refresh(new_gift)
    
    return await build_gift_response(db, new_gift)


@router.get("/list", response_model=GiftListResponse)
async def list_gifts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的赠与列表（发送和接收的）"""
    # 获取我发送的赠与
    sent_result = await db.execute(
        select(EquityGift)
        .where(EquityGift.from_user_id == current_user.id)
        .order_by(EquityGift.created_at.desc())
    )
    sent_gifts = sent_result.scalars().all()
    
    # 获取我收到的赠与
    received_result = await db.execute(
        select(EquityGift)
        .where(EquityGift.to_user_id == current_user.id)
        .order_by(EquityGift.created_at.desc())
    )
    received_gifts = received_result.scalars().all()
    
    # 统计待处理数量
    pending_count = sum(1 for g in received_gifts if g.status == EquityGiftStatus.PENDING)
    
    # 构建响应
    sent_responses = [await build_gift_response(db, g) for g in sent_gifts]
    received_responses = [await build_gift_response(db, g) for g in received_gifts]
    
    return GiftListResponse(
        sent=sent_responses,
        received=received_responses,
        pending_count=pending_count,
    )


@router.post("/{gift_id}/respond", response_model=GiftResponse)
async def respond_to_gift(
    gift_id: int,
    response_data: GiftAcceptReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    接受或拒绝股权赠与
    
    - 只能处理发给自己的赠与
    - 接受后会执行股权转移（通过存款记录调整）
    """
    # 获取赠与记录
    gift_result = await db.execute(
        select(EquityGift).where(EquityGift.id == gift_id)
    )
    gift = gift_result.scalar_one_or_none()
    
    if not gift:
        raise HTTPException(status_code=404, detail="赠与记录不存在")
    
    if gift.to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权处理此赠与")
    
    if gift.status != EquityGiftStatus.PENDING:
        raise HTTPException(status_code=400, detail="此赠与已被处理")
    
    if response_data.accept:
        # 接受赠与 - 执行股权转移
        # 计算需要转移的金额（基于家庭总存款）
        family_total_result = await db.execute(
            select(func.coalesce(func.sum(Deposit.amount), 0))
            .where(Deposit.family_id == gift.family_id)
        )
        family_total = family_total_result.scalar() or 0
        
        transfer_amount = family_total * gift.amount
        
        if transfer_amount > 0:
            # 从赠送者扣除存款记录
            deduct_deposit = Deposit(
                user_id=gift.from_user_id,
                family_id=gift.family_id,
                amount=-transfer_amount,
                note=f"股权赠与给 {current_user.nickname}",
                deposit_date=datetime.utcnow(),
            )
            db.add(deduct_deposit)
            
            # 给接收者增加存款记录
            add_deposit = Deposit(
                user_id=current_user.id,
                family_id=gift.family_id,
                amount=transfer_amount,
                note=f"收到来自赠与的股权",
                deposit_date=datetime.utcnow(),
            )
            db.add(add_deposit)
        
        gift.status = EquityGiftStatus.ACCEPTED
        
        # 宠物经验奖励：赠送股权 +30 EXP（赠送者获得）
        try:
            from app.api.pet import grant_pet_exp
            await grant_pet_exp(
                db, gift.family_id, "gift", 1, 
                operator_id=gift.from_user_id,
                source_detail=f"赠送股权 {gift.amount*100:.1f}%"
            )  # gift 基础经验是30，multiplier=1
        except Exception as e:
            logging.warning(f"Pet EXP grant failed after gift accepted: {e}")
    else:
        gift.status = EquityGiftStatus.REJECTED
    
    gift.responded_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(gift)
    
    return await build_gift_response(db, gift)


@router.delete("/{gift_id}")
async def cancel_gift(
    gift_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取消待处理的赠与（只能由发送者取消）
    """
    # 获取赠与记录
    gift_result = await db.execute(
        select(EquityGift).where(EquityGift.id == gift_id)
    )
    gift = gift_result.scalar_one_or_none()
    
    if not gift:
        raise HTTPException(status_code=404, detail="赠与记录不存在")
    
    if gift.from_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您只能取消自己发送的赠与")
    
    if gift.status != EquityGiftStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能取消待处理的赠与")
    
    await db.delete(gift)
    await db.commit()
    
    return {"message": "赠与已取消"}


@router.get("/stats", response_model=GiftStats)
async def get_gift_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取赠与统计"""
    # 发送统计
    sent_result = await db.execute(
        select(
            func.count(EquityGift.id),
            func.coalesce(func.sum(EquityGift.amount), 0)
        )
        .where(
            and_(
                EquityGift.from_user_id == current_user.id,
                EquityGift.status == EquityGiftStatus.ACCEPTED
            )
        )
    )
    sent_row = sent_result.first()
    total_sent = sent_row[0] if sent_row else 0
    total_sent_amount = float(sent_row[1]) if sent_row else 0
    
    # 接收统计
    received_result = await db.execute(
        select(
            func.count(EquityGift.id),
            func.coalesce(func.sum(EquityGift.amount), 0)
        )
        .where(
            and_(
                EquityGift.to_user_id == current_user.id,
                EquityGift.status == EquityGiftStatus.ACCEPTED
            )
        )
    )
    received_row = received_result.first()
    total_received = received_row[0] if received_row else 0
    total_received_amount = float(received_row[1]) if received_row else 0
    
    return GiftStats(
        total_sent=total_sent,
        total_received=total_received,
        total_sent_amount=total_sent_amount,
        total_received_amount=total_received_amount,
    )


@router.get("/pending-count")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待处理的赠与数量（用于显示红点提示）"""
    result = await db.execute(
        select(func.count(EquityGift.id))
        .where(
            and_(
                EquityGift.to_user_id == current_user.id,
                EquityGift.status == EquityGiftStatus.PENDING
            )
        )
    )
    count = result.scalar() or 0
    
    return {"pending_count": count}
