"""
股东大会投票 API - 全员同意才能通过
"""
from datetime import datetime, timedelta
from typing import List, Optional
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.limiter import limiter
from app.api.auth import get_current_user
from app.models.models import (
    User, FamilyMember, Family, Proposal, Vote, ProposalStatus,
    Dividend, DividendType, DividendStatus, Transaction, TransactionType
)
from app.schemas.common import TimeRange, get_time_range_filter

router = APIRouter(prefix="/vote", tags=["vote"])


# ==================== Schema ====================

class ProposalCreate(BaseModel):
    title: str
    description: str
    options: List[str]  # 选项列表，至少2个
    deadline_days: int = 7  # 投票期限（天）

class DividendProposalCreate(BaseModel):
    """分红提案创建"""
    dividend_type: str  # "profit" 或 "cash"
    amount: float  # 分红金额
    deadline_days: int = 7  # 投票期限（天）

class VoteCreate(BaseModel):
    option_index: int  # 选择的选项索引

class ProposalResponse(BaseModel):
    id: int
    title: str
    description: str
    options: List[str]
    status: str
    deadline: datetime
    created_at: datetime
    creator_name: str
    total_members: int
    voted_count: int
    my_vote: Optional[int]
    votes_detail: List[dict]  # 每个选项的投票情况

class VoteResponse(BaseModel):
    success: bool
    message: str
    proposal_status: str


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


async def get_user_equity(db: AsyncSession, user_id: int, family_id: int) -> float:
    """获取用户股权比例（简化版，实际应调用equity服务）"""
    from app.models.models import Deposit
    
    # 获取家庭总存款和用户存款
    result = await db.execute(
        select(func.sum(Deposit.amount)).where(Deposit.family_id == family_id)
    )
    total = result.scalar() or 0
    
    result = await db.execute(
        select(func.sum(Deposit.amount)).where(
            Deposit.family_id == family_id,
            Deposit.user_id == user_id
        )
    )
    user_total = result.scalar() or 0
    
    if total == 0:
        return 0
    return user_total / total


async def check_proposal_result(db: AsyncSession, proposal: Proposal, family_id: int):
    """检查提案结果 - 全员同意才通过"""
    # 获取家庭成员数
    result = await db.execute(
        select(func.count(FamilyMember.id)).where(FamilyMember.family_id == family_id)
    )
    total_members = result.scalar() or 0
    
    # 获取已投票数
    result = await db.execute(
        select(func.count(Vote.id)).where(Vote.proposal_id == proposal.id)
    )
    voted_count = result.scalar() or 0
    
    # 如果所有人都投票了
    if voted_count >= total_members:
        # 检查是否全员选择同一选项（第一个选项通常是"同意"）
        result = await db.execute(
            select(Vote.option_index, func.count(Vote.id))
            .where(Vote.proposal_id == proposal.id)
            .group_by(Vote.option_index)
        )
        vote_counts = {row[0]: row[1] for row in result.fetchall()}
        
        # 全员同意（选项0）才通过
        if vote_counts.get(0, 0) == total_members:
            proposal.status = ProposalStatus.PASSED
            proposal.closed_at = datetime.utcnow()
            
            # 🌟 检查是否是分红提案，如果是则触发分红分配
            await handle_dividend_approval(db, proposal)
            
            # 发送投票通过通知
            await send_vote_result_notification(db, proposal, passed=True)
        else:
            proposal.status = ProposalStatus.REJECTED
            proposal.closed_at = datetime.utcnow()
            
            # 🌟 如果是分红提案被拒绝，更新分红状态
            await handle_dividend_rejection(db, proposal)
            
            # 发送投票未通过通知
            await send_vote_result_notification(db, proposal, passed=False)
        
        await db.commit()


async def handle_dividend_approval(db: AsyncSession, proposal: Proposal):
    """处理分红提案通过"""
    from app.services.dividend import (
        get_dividend_by_proposal,
        create_dividend_claims,
        clear_dividend_pool
    )
    
    # 查找关联的分红记录
    dividend = await get_dividend_by_proposal(proposal.id, db)
    if not dividend:
        return  # 不是分红提案
    
    # 更新分红状态
    dividend.status = DividendStatus.APPROVED
    dividend.approved_at = datetime.utcnow()
    await db.commit()
    
    # 先清空分红资金池（在分配前清空，避免资金重复计算）
    # 注意：资金已在创建提案时冻结，这里不需要再次扣除
    await clear_dividend_pool(
        dividend.family_id,
        dividend.type,
        dividend.total_amount,
        db,
        already_frozen=True  # 资金已冻结
    )
    
    # 创建个人分红审核
    await create_dividend_claims(dividend.id, db)


async def handle_dividend_rejection(db: AsyncSession, proposal: Proposal):
    """处理分红提案被拒绝"""
    from app.services.dividend import get_dividend_by_proposal
    
    dividend = await get_dividend_by_proposal(proposal.id, db)
    if not dividend:
        return  # 不是分红提案
    
    # 更新分红状态为已拒绝
    dividend.status = DividendStatus.REJECTED
    
    # 解冻资金
    await unfreeze_dividend_amount(db, dividend)
    
    await db.commit()


async def freeze_dividend_amount(db: AsyncSession, dividend: Dividend) -> None:
    """冻结分红金额"""
    # 获取当前余额
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == dividend.family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0
    
    # 创建冻结交易记录
    freeze_transaction = Transaction(
        family_id=dividend.family_id,
        user_id=None,
        transaction_type=TransactionType.FREEZE,
        amount=-dividend.total_amount,  # 负数表示扣除
        balance_after=current_balance - dividend.total_amount,
        description=f"冻结分红资金：{dividend.total_amount:.2f}元",
        reference_id=dividend.id,
        reference_type="dividend"
    )
    db.add(freeze_transaction)
    logging.info(f"💰 Frozen {dividend.total_amount} for dividend {dividend.id}")


async def unfreeze_dividend_amount(db: AsyncSession, dividend: Dividend) -> None:
    """解冻分红金额（投票未通过时）"""
    # 获取当前余额
    result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == dividend.family_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0
    
    # 创建解冻交易记录
    unfreeze_transaction = Transaction(
        family_id=dividend.family_id,
        user_id=None,
        transaction_type=TransactionType.UNFREEZE,
        amount=dividend.total_amount,  # 正数表示归还
        balance_after=current_balance + dividend.total_amount,
        description=f"解冻分红资金（投票未通过）：{dividend.total_amount:.2f}元",
        reference_id=dividend.id,
        reference_type="dividend"
    )
    db.add(unfreeze_transaction)
    logging.info(f"💰 Unfrozen {dividend.total_amount} for dividend {dividend.id}")


async def send_vote_result_notification(db: AsyncSession, proposal: Proposal, passed: bool):
    """发送投票结果通知"""
    from app.services.notification import NotificationService
    from app.services.dividend import get_dividend_by_proposal
    
    # 获取家庭和创建者信息
    result = await db.execute(select(Family).where(Family.id == proposal.family_id))
    family = result.scalar_one_or_none()
    
    result = await db.execute(select(User).where(User.id == proposal.creator_id))
    creator = result.scalar_one_or_none()
    
    if not family or not creator:
        logging.warning(f"Cannot send vote result: family={family}, creator={creator}")
        return
    
    # 如果是分红提案，获取分红金额
    amount = None
    dividend = await get_dividend_by_proposal(proposal.id, db)
    if dividend:
        amount = dividend.total_amount
    
    # 发送通知
    try:
        service = NotificationService(db)
        await service.notify_vote_result(
            proposal=proposal,
            passed=passed,
            creator=creator,
            family=family,
            amount=amount
        )
        result_text = "通过" if passed else "未通过"
        logging.info(f"✅ Vote result notification sent: {proposal.id} - {result_text}")
    except Exception as e:
        logging.error(f"❌ Failed to send vote result notification: {e}", exc_info=True)


# ==================== API ====================

@router.post("/proposals", response_model=dict)
@limiter.limit("20/day")
async def create_proposal(
    request: Request,
    data: ProposalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新提案"""
    family_id = await get_user_family_id(current_user.id, db)
    
    if len(data.options) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个选项")
    
    proposal = Proposal(
        family_id=family_id,
        creator_id=current_user.id,
        title=data.title,
        description=data.description,
        options=json.dumps(data.options, ensure_ascii=False),
        deadline=datetime.utcnow() + timedelta(days=data.deadline_days),
        status=ProposalStatus.VOTING
    )
    
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    
    # 发送新提案创建通知
    from app.services.notification import NotificationService
    
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()
    if family:
        try:
            service = NotificationService(db)
            await service.notify_vote_proposal_created(
                proposal=proposal,
                creator=current_user,
                family=family
            )
            logging.info(f"✅ Proposal {proposal.id} notification sent successfully")
        except Exception as e:
            logging.error(f"❌ Failed to send proposal notification: {e}", exc_info=True)
    
    return {
        "success": True,
        "message": "提案创建成功",
        "proposal_id": proposal.id
    }


@router.get("/proposals", response_model=List[dict])
async def list_proposals(
    status: Optional[str] = None,
    time_range: TimeRange = Query(TimeRange.MONTH, description="时间范围：day/week/month/year/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取提案列表（支持时间范围筛选，默认最近一个月）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 先检查过期提案
    await check_expired_proposals(db, family_id)
    
    query = select(Proposal).where(Proposal.family_id == family_id)
    if status:
        query = query.where(Proposal.status == status)
    
    # 时间范围筛选
    start_time = get_time_range_filter(time_range)
    if start_time:
        query = query.where(Proposal.created_at >= start_time)
    
    query = query.order_by(Proposal.created_at.desc())
    
    result = await db.execute(query)
    proposals = result.scalars().all()
    
    # 获取家庭成员数
    result = await db.execute(
        select(func.count(FamilyMember.id)).where(FamilyMember.family_id == family_id)
    )
    total_members = result.scalar() or 0
    
    response = []
    for p in proposals:
        # 获取创建者信息
        result = await db.execute(select(User).where(User.id == p.creator_id))
        creator = result.scalar_one_or_none()
        
        # 获取投票统计
        result = await db.execute(
            select(func.count(Vote.id)).where(Vote.proposal_id == p.id)
        )
        voted_count = result.scalar() or 0
        
        # 获取当前用户的投票
        result = await db.execute(
            select(Vote.option_index).where(
                Vote.proposal_id == p.id,
                Vote.user_id == current_user.id
            )
        )
        my_vote = result.scalar_one_or_none()
        
        # 获取每个选项的投票统计（用于已完成提案显示结果）
        result = await db.execute(
            select(Vote.option_index, func.count(Vote.id), func.sum(Vote.weight))
            .where(Vote.proposal_id == p.id)
            .group_by(Vote.option_index)
        )
        vote_stats = {row[0]: {"count": row[1], "weight": row[2] or 0} for row in result.fetchall()}
        
        options = json.loads(p.options)
        votes_summary = []
        for i, opt in enumerate(options):
            stat = vote_stats.get(i, {"count": 0, "weight": 0})
            votes_summary.append({
                "option": opt,
                "count": stat["count"],
                "weight_percent": round(stat["weight"] * 100, 1) if stat["weight"] else 0
            })
        
        response.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "options": options,
            "status": p.status.value if hasattr(p.status, 'value') else p.status,
            "deadline": p.deadline.isoformat(),
            "created_at": p.created_at.isoformat(),
            "creator_id": creator.id if creator else None,
            "creator_name": creator.nickname if creator else "未知",
            "creator_avatar_version": creator.avatar_version or 0 if creator else 0,
            "total_members": total_members,
            "voted_count": voted_count,
            "my_vote": my_vote,
            "votes_summary": votes_summary
        })
    
    return response


@router.get("/proposals/{proposal_id}", response_model=dict)
async def get_proposal_detail(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取提案详情"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.family_id == family_id
        )
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="提案不存在")
    
    # 获取创建者
    result = await db.execute(select(User).where(User.id == proposal.creator_id))
    creator = result.scalar_one_or_none()
    
    # 获取家庭成员数
    result = await db.execute(
        select(func.count(FamilyMember.id)).where(FamilyMember.family_id == family_id)
    )
    total_members = result.scalar() or 0
    
    # 获取所有投票详情
    result = await db.execute(
        select(Vote, User).join(User, Vote.user_id == User.id)
        .where(Vote.proposal_id == proposal_id)
    )
    votes = result.fetchall()
    
    options = json.loads(proposal.options)
    votes_detail = []
    for i, option in enumerate(options):
        option_votes = [v for v, u in votes if v.option_index == i]
        voters = [{"user_id": u.id, "name": u.nickname, "weight": v.weight, "avatar_version": u.avatar_version or 0} for v, u in votes if v.option_index == i]
        votes_detail.append({
            "option": option,
            "count": len(option_votes),
            "voters": voters
        })
    
    # 当前用户的投票
    my_vote = next((v.option_index for v, u in votes if v.user_id == current_user.id), None)
    
    # 计算每个选项的权重百分比
    total_weight = sum(v.weight for v, u in votes) if votes else 0
    for detail in votes_detail:
        detail_weight = sum(voter["weight"] for voter in detail["voters"]) if detail["voters"] else 0
        detail["weight_percent"] = round(detail_weight * 100, 1) if detail_weight else 0
    
    return {
        "id": proposal.id,
        "title": proposal.title,
        "description": proposal.description,
        "options": options,
        "status": proposal.status.value if hasattr(proposal.status, 'value') else proposal.status,
        "deadline": proposal.deadline.isoformat(),
        "created_at": proposal.created_at.isoformat(),
        "closed_at": proposal.closed_at.isoformat() if proposal.closed_at else None,
        "creator_id": creator.id if creator else None,
        "creator_name": creator.nickname if creator else "未知",
        "creator_avatar_version": creator.avatar_version or 0 if creator else 0,
        "total_members": total_members,
        "voted_count": len(votes),
        "my_vote": my_vote,
        "votes_detail": votes_detail
    }


@router.post("/proposals/{proposal_id}/vote", response_model=VoteResponse)
@limiter.limit("50/hour")
async def cast_vote(
    request: Request,
    proposal_id: int,
    data: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """投票"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取提案
    result = await db.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.family_id == family_id
        )
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="提案不存在")
    
    if proposal.status != ProposalStatus.VOTING:
        raise HTTPException(status_code=400, detail="该提案已结束投票")
    
    if proposal.deadline < datetime.utcnow():
        raise HTTPException(status_code=400, detail="投票已截止")
    
    options = json.loads(proposal.options)
    if data.option_index < 0 or data.option_index >= len(options):
        raise HTTPException(status_code=400, detail="无效的选项")
    
    # 检查是否已投票
    result = await db.execute(
        select(Vote).where(
            Vote.proposal_id == proposal_id,
            Vote.user_id == current_user.id
        )
    )
    existing_vote = result.scalar_one_or_none()
    
    if existing_vote:
        raise HTTPException(status_code=400, detail="您已经投过票了")
    
    # 获取用户股权作为权重
    weight = await get_user_equity(db, current_user.id, family_id)
    
    # 创建投票记录
    vote = Vote(
        proposal_id=proposal_id,
        user_id=current_user.id,
        option_index=data.option_index,
        weight=weight
    )
    db.add(vote)
    await db.commit()
    
    # 🔕 投票通知已禁用：成员投票不需要通知其他人
    # 发送投票通知
    # from app.services.notification import NotificationService
    
    # result = await db.execute(select(Family).where(Family.id == family_id))
    # family = result.scalar_one_or_none()
    # if family:
    #     try:
    #         service = NotificationService(db)
    #         await service.notify_vote_cast(
    #             proposal=proposal,
    #             voter=current_user,
    #             vote_option=options[data.option_index],
    #             family=family
    #         )
    #         logging.info(f"✅ Vote cast notification sent for proposal {proposal_id}")
    #     except Exception as e:
    #         logging.error(f"❌ Failed to send vote cast notification: {e}", exc_info=True)
    
    # 检查是否所有人都投票了
    await check_proposal_result(db, proposal, family_id)
    
    # 重新获取状态
    await db.refresh(proposal)
    
    return VoteResponse(
        success=True,
        message=f"投票成功，您选择了「{options[data.option_index]}」",
        proposal_status=proposal.status.value if hasattr(proposal.status, 'value') else proposal.status
    )


async def check_expired_proposals(db: AsyncSession, family_id: int):
    """检查并更新过期提案"""
    result = await db.execute(
        select(Proposal).where(
            Proposal.family_id == family_id,
            Proposal.status == ProposalStatus.VOTING,
            Proposal.deadline < datetime.utcnow()
        )
    )
    expired = result.scalars().all()
    
    for p in expired:
        p.status = ProposalStatus.EXPIRED
        p.closed_at = datetime.utcnow()
    
    if expired:
        await db.commit()


@router.get("/stats", response_model=dict)
async def get_vote_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取投票统计（用于成就系统）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 用户投票总数
    result = await db.execute(
        select(func.count(Vote.id))
        .join(Proposal, Vote.proposal_id == Proposal.id)
        .where(
            Vote.user_id == current_user.id,
            Proposal.family_id == family_id
        )
    )
    total_votes = result.scalar() or 0
    
    # 用户发起的提案数
    result = await db.execute(
        select(func.count(Proposal.id)).where(
            Proposal.creator_id == current_user.id,
            Proposal.family_id == family_id
        )
    )
    total_proposals = result.scalar() or 0
    
    # 用户发起的已通过提案数
    result = await db.execute(
        select(func.count(Proposal.id)).where(
            Proposal.creator_id == current_user.id,
            Proposal.family_id == family_id,
            Proposal.status == ProposalStatus.PASSED
        )
    )
    passed_proposals = result.scalar() or 0
    
    return {
        "total_votes": total_votes,
        "total_proposals": total_proposals,
        "passed_proposals": passed_proposals
    }


@router.get("/pending-count", response_model=dict)
async def get_pending_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取待投票提案数量（用于显示红点）"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取投票中的提案
    result = await db.execute(
        select(Proposal.id)
        .where(
            Proposal.family_id == family_id,
            Proposal.status == ProposalStatus.VOTING,
            Proposal.deadline >= datetime.utcnow()
        )
    )
    voting_proposal_ids = [row[0] for row in result.fetchall()]
    
    if not voting_proposal_ids:
        return {"pending_count": 0}
    
    # 检查哪些提案用户还没有投票
    result = await db.execute(
        select(Vote.proposal_id)
        .where(
            Vote.proposal_id.in_(voting_proposal_ids),
            Vote.user_id == current_user.id
        )
    )
    voted_proposal_ids = {row[0] for row in result.fetchall()}
    
    # 计算未投票数量
    pending_count = len(voting_proposal_ids) - len(voted_proposal_ids)
    
    return {"pending_count": pending_count}


# ==================== 分红投票 ====================

@router.get("/dividend-pool", response_model=dict)
async def get_dividend_pool(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用于分红的资金池（只支持自由资金分红）"""
    from app.services.dividend import calculate_dividend_pool
    
    family_id = await get_user_family_id(current_user.id, db)
    
    cash_pool = await calculate_dividend_pool(family_id, DividendType.CASH, db)
    
    return {
        "profit_pool": 0,  # 已废弃，保留兼容
        "cash_pool": round(cash_pool, 2)
    }


@router.post("/proposals/dividend", response_model=dict)
@limiter.limit("10/day")
async def create_dividend_proposal(
    request: Request,
    data: DividendProposalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建分红提案（只支持自由资金分红）"""
    from app.services.dividend import calculate_dividend_pool
    
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证分红类型，只支持cash
    if data.dividend_type != "cash":
        raise HTTPException(status_code=400, detail="现在只支持自由资金分红")
    
    try:
        dividend_type = DividendType(data.dividend_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的分红类型")
    
    # 检查可用资金
    available_amount = await calculate_dividend_pool(family_id, dividend_type, db)
    if data.amount > available_amount:
        raise HTTPException(
            status_code=400,
            detail=f"分红金额超出可用资金（可用：{available_amount:.2f}元）"
        )
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="分红金额必须大于0")
    
    # 创建投票提案
    type_name = "家庭自由资金"  # 只支持自由资金分红
    proposal = Proposal(
        family_id=family_id,
        creator_id=current_user.id,
        title=f"分红提案 - {type_name}",
        description=f"提议将 {data.amount:.2f} 元{type_name}进行分红，按股权比例分配。",
        options=json.dumps(["同意", "不同意"], ensure_ascii=False),
        deadline=datetime.utcnow() + timedelta(days=data.deadline_days),
        status=ProposalStatus.VOTING
    )
    db.add(proposal)
    await db.flush()
    
    # 创建分红记录（状态为VOTING）
    dividend = Dividend(
        family_id=family_id,
        type=dividend_type,
        total_amount=data.amount,
        proposal_id=proposal.id,
        status=DividendStatus.VOTING,
        created_by=current_user.id
    )
    db.add(dividend)
    await db.flush()
    
    # 冻结分红金额
    await freeze_dividend_amount(db, dividend)
    
    await db.commit()
    await db.refresh(proposal)
    
    # 发送分红提案创建通知
    from app.services.notification import NotificationService
    
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()
    if family:
        try:
            service = NotificationService(db)
            await service.notify_vote_proposal_created(
                proposal=proposal,
                creator=current_user,
                family=family
            )
            logging.info(f"✅ Dividend proposal {proposal.id} notification sent successfully")
        except Exception as e:
            logging.error(f"❌ Failed to send dividend proposal notification: {e}", exc_info=True)
    
    return {
        "success": True,
        "message": "分红提案创建成功",
        "proposal_id": proposal.id,
        "dividend_id": dividend.id
    }
