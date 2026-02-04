"""
股东大会投票 API - 全员同意才能通过
"""
from datetime import datetime, timedelta
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import (
    User, FamilyMember, Proposal, Vote, ProposalStatus
)

router = APIRouter(prefix="/vote", tags=["vote"])


# ==================== Schema ====================

class ProposalCreate(BaseModel):
    title: str
    description: str
    options: List[str]  # 选项列表，至少2个
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
        else:
            proposal.status = ProposalStatus.REJECTED
            proposal.closed_at = datetime.utcnow()
        
        await db.commit()


# ==================== API ====================

@router.post("/proposals", response_model=dict)
async def create_proposal(
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
    
    return {
        "success": True,
        "message": "提案创建成功",
        "proposal_id": proposal.id
    }


@router.get("/proposals", response_model=List[dict])
async def list_proposals(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取提案列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 先检查过期提案
    await check_expired_proposals(db, family_id)
    
    query = select(Proposal).where(Proposal.family_id == family_id)
    if status:
        query = query.where(Proposal.status == status)
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
async def cast_vote(
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
