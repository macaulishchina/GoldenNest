"""
小金库 (Golden Nest) - 家庭赌注路由
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import (
    Bet, BetParticipant, BetOption, BetStatus,
    FamilyMember, User, ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus
)
from app.schemas.bet import (
    BetCreate, BetUpdate, BetResponse, BetListResponse,
    BetVoteRequest, BetSettleRequest, BetApproveRequest,
    BetOptionResponse, BetParticipantResponse
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


async def check_family_admin(user_id: int, family_id: int, db: AsyncSession) -> bool:
    """检查用户是否为家庭管理员"""
    result = await db.execute(
        select(FamilyMember).where(
            and_(
                FamilyMember.user_id == user_id,
                FamilyMember.family_id == family_id,
                FamilyMember.role == "admin"
            )
        )
    )
    return result.scalar_one_or_none() is not None


def build_bet_response(bet: Bet, participants: List[BetParticipant], options: List[BetOption], users_dict: dict) -> BetResponse:
    """构建赌注响应"""
    # 检查是否已过期
    is_expired = bet.end_date < datetime.utcnow() if bet.end_date else False

    # 检查是否可以结算（已过期且状态为active）
    can_settle = is_expired and bet.status == BetStatus.ACTIVE

    # 构建选项响应
    options_response = [
        BetOptionResponse(
            id=opt.id,
            bet_id=opt.bet_id,
            option_text=opt.option_text,
            is_winning_option=opt.is_winning_option,
            created_at=opt.created_at
        ) for opt in options
    ]

    # 构建参与者响应
    participants_response = []
    for p in participants:
        selected_option_text = None
        if p.selected_option_id:
            selected_opt = next((o for o in options if o.id == p.selected_option_id), None)
            if selected_opt:
                selected_option_text = selected_opt.option_text

        participants_response.append(BetParticipantResponse(
            id=p.id,
            bet_id=p.bet_id,
            user_id=p.user_id,
            selected_option_id=p.selected_option_id,
            stake_amount=p.stake_amount,
            stake_description=p.stake_description,
            is_winner=p.is_winner,
            has_approved=p.has_approved,
            created_at=p.created_at,
            user_nickname=users_dict.get(p.user_id, "Unknown"),
            selected_option_text=selected_option_text
        ))

    return BetResponse(
        id=bet.id,
        family_id=bet.family_id,
        creator_id=bet.creator_id,
        title=bet.title,
        description=bet.description,
        status=bet.status.value,
        start_date=bet.start_date,
        end_date=bet.end_date,
        settlement_date=bet.settlement_date,
        approval_request_id=bet.approval_request_id,
        created_at=bet.created_at,
        options=options_response,
        participants=participants_response,
        creator_nickname=users_dict.get(bet.creator_id, "Unknown"),
        is_expired=is_expired,
        can_settle=can_settle
    )


@router.post("/create", response_model=BetResponse)
async def create_bet(
    bet_data: BetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建家庭赌注（自动创建审批请求）"""
    family_id = await get_user_family_id(current_user.id, db)

    # 验证日期
    if bet_data.start_date >= bet_data.end_date:
        raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")

    # 验证选项数量
    if len(bet_data.options) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个选项")

    # 验证参与者数量
    if len(bet_data.participants) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个参与者")

    # 验证参与者是否都在家庭中
    participant_user_ids = [p.user_id for p in bet_data.participants]
    result = await db.execute(
        select(FamilyMember).where(
            and_(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id.in_(participant_user_ids)
            )
        )
    )
    family_members = result.scalars().all()
    if len(family_members) != len(participant_user_ids):
        raise HTTPException(status_code=400, detail="部分参与者不在家庭中")

    # 创建赌注
    bet = Bet(
        family_id=family_id,
        creator_id=current_user.id,
        title=bet_data.title,
        description=bet_data.description,
        status=BetStatus.PENDING,
        start_date=bet_data.start_date,
        end_date=bet_data.end_date
    )
    db.add(bet)
    await db.flush()  # 获取bet.id

    # 创建选项
    options = []
    for opt_data in bet_data.options:
        option = BetOption(
            bet_id=bet.id,
            option_text=opt_data.option_text
        )
        db.add(option)
        options.append(option)

    await db.flush()  # 获取option ids

    # 创建参与者
    participants = []
    for p_data in bet_data.participants:
        participant = BetParticipant(
            bet_id=bet.id,
            user_id=p_data.user_id,
            stake_amount=p_data.stake_amount,
            stake_description=p_data.stake_description,
            has_approved=(p_data.user_id == current_user.id)  # 创建者自动同意
        )
        db.add(participant)
        participants.append(participant)

    # 创建审批请求（使用通用审批系统）
    approval = ApprovalRequest(
        family_id=family_id,
        requester_id=current_user.id,
        request_type=ApprovalRequestType.EXPENSE,  # 暂时使用EXPENSE类型，实际应该扩展枚举
        status=ApprovalRequestStatus.PENDING,
        request_data={
            "bet_id": bet.id,
            "title": bet_data.title,
            "description": bet_data.description
        }
    )
    db.add(approval)
    await db.flush()

    bet.approval_request_id = approval.id

    await db.commit()
    await db.refresh(bet)

    # 获取用户信息
    users_result = await db.execute(
        select(User).where(User.id.in_([current_user.id] + participant_user_ids))
    )
    users = users_result.scalars().all()
    users_dict = {u.id: u.nickname for u in users}

    return build_bet_response(bet, participants, options, users_dict)


@router.get("/list", response_model=BetListResponse)
async def list_bets(
    status: str = Query(None, description="状态筛选：pending/active/settled/cancelled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭赌注列表"""
    family_id = await get_user_family_id(current_user.id, db)

    # 构建查询
    query = select(Bet).where(Bet.family_id == family_id)

    if status:
        try:
            bet_status = BetStatus(status)
            query = query.where(Bet.status == bet_status)
        except ValueError:
            pass

    # 计算总数
    count_query = select(Bet).where(Bet.family_id == family_id)
    if status:
        try:
            bet_status = BetStatus(status)
            count_query = count_query.where(Bet.status == bet_status)
        except ValueError:
            pass
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # 分页查询
    query = query.order_by(Bet.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    bets = result.scalars().all()

    # 获取所有赌注的参与者和选项
    if bets:
        bet_ids = [b.id for b in bets]

        # 获取参与者
        participants_result = await db.execute(
            select(BetParticipant).where(BetParticipant.bet_id.in_(bet_ids))
        )
        all_participants = participants_result.scalars().all()
        participants_by_bet = {}
        for p in all_participants:
            if p.bet_id not in participants_by_bet:
                participants_by_bet[p.bet_id] = []
            participants_by_bet[p.bet_id].append(p)

        # 获取选项
        options_result = await db.execute(
            select(BetOption).where(BetOption.bet_id.in_(bet_ids))
        )
        all_options = options_result.scalars().all()
        options_by_bet = {}
        for o in all_options:
            if o.bet_id not in options_by_bet:
                options_by_bet[o.bet_id] = []
            options_by_bet[o.bet_id].append(o)

        # 获取所有用户信息
        user_ids = set([b.creator_id for b in bets])
        for participants in participants_by_bet.values():
            user_ids.update([p.user_id for p in participants])

        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = users_result.scalars().all()
        users_dict = {u.id: u.nickname for u in users}
    else:
        participants_by_bet = {}
        options_by_bet = {}
        users_dict = {}

    # 构建响应
    items = []
    for bet in bets:
        participants = participants_by_bet.get(bet.id, [])
        options = options_by_bet.get(bet.id, [])
        items.append(build_bet_response(bet, participants, options, users_dict))

    return BetListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


@router.get("/{bet_id}", response_model=BetResponse)
async def get_bet(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取赌注详情"""
    family_id = await get_user_family_id(current_user.id, db)

    # 查询赌注
    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    # 获取参与者
    participants_result = await db.execute(
        select(BetParticipant).where(BetParticipant.bet_id == bet_id)
    )
    participants = participants_result.scalars().all()

    # 获取选项
    options_result = await db.execute(
        select(BetOption).where(BetOption.bet_id == bet_id)
    )
    options = options_result.scalars().all()

    # 获取用户信息
    user_ids = [bet.creator_id] + [p.user_id for p in participants]
    users_result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = users_result.scalars().all()
    users_dict = {u.id: u.nickname for u in users}

    return build_bet_response(bet, participants, options, users_dict)


@router.post("/{bet_id}/vote", response_model=BetResponse)
async def vote_bet(
    bet_id: int,
    vote_data: BetVoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """投票选择赌注选项"""
    family_id = await get_user_family_id(current_user.id, db)

    # 查询赌注
    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    # 检查状态
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="赌注未激活，无法投票")

    # 检查是否已过期
    if bet.end_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="赌注已过期，无法投票")

    # 查询参与者
    participant_result = await db.execute(
        select(BetParticipant).where(
            and_(
                BetParticipant.bet_id == bet_id,
                BetParticipant.user_id == current_user.id
            )
        )
    )
    participant = participant_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=403, detail="您不是此赌注的参与者")

    # 验证选项
    option_result = await db.execute(
        select(BetOption).where(
            and_(
                BetOption.id == vote_data.option_id,
                BetOption.bet_id == bet_id
            )
        )
    )
    option = option_result.scalar_one_or_none()
    if not option:
        raise HTTPException(status_code=404, detail="选项不存在")

    # 更新投票
    participant.selected_option_id = vote_data.option_id
    await db.commit()

    # 重新获取数据返回
    return await get_bet(bet_id, current_user, db)


@router.post("/{bet_id}/settle", response_model=BetResponse)
async def settle_bet(
    bet_id: int,
    settle_data: BetSettleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """结算赌注（仅管理员）"""
    family_id = await get_user_family_id(current_user.id, db)

    # 检查管理员权限
    is_admin = await check_family_admin(current_user.id, family_id, db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可以结算赌注")

    # 查询赌注
    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    # 检查状态
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="只能结算进行中的赌注")

    # 检查是否已过期
    if bet.end_date > datetime.utcnow():
        raise HTTPException(status_code=400, detail="赌注尚未到期，无法结算")

    # 验证获胜选项
    winning_option_result = await db.execute(
        select(BetOption).where(
            and_(
                BetOption.id == settle_data.winning_option_id,
                BetOption.bet_id == bet_id
            )
        )
    )
    winning_option = winning_option_result.scalar_one_or_none()
    if not winning_option:
        raise HTTPException(status_code=404, detail="获胜选项不存在")

    # 标记获胜选项
    winning_option.is_winning_option = True

    # 标记所有其他选项为非获胜
    other_options_result = await db.execute(
        select(BetOption).where(
            and_(
                BetOption.bet_id == bet_id,
                BetOption.id != settle_data.winning_option_id
            )
        )
    )
    other_options = other_options_result.scalars().all()
    for opt in other_options:
        opt.is_winning_option = False

    # 更新参与者的获胜状态
    participants_result = await db.execute(
        select(BetParticipant).where(BetParticipant.bet_id == bet_id)
    )
    participants = participants_result.scalars().all()

    for participant in participants:
        if participant.selected_option_id == settle_data.winning_option_id:
            participant.is_winner = True
        else:
            participant.is_winner = False

    # 更新赌注状态
    bet.status = BetStatus.SETTLED
    bet.settlement_date = datetime.utcnow()

    # TODO: 实现股份自动调整逻辑
    # 这里应该根据 stake_amount 调整获胜者和失败者的股份
    # 需要集成到 equity 系统中

    await db.commit()

    # 返回更新后的赌注
    return await get_bet(bet_id, current_user, db)


@router.post("/{bet_id}/cancel", response_model=BetResponse)
async def cancel_bet(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取消赌注（仅创建者或管理员）"""
    family_id = await get_user_family_id(current_user.id, db)

    # 查询赌注
    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    # 检查权限（创建者或管理员）
    is_creator = bet.creator_id == current_user.id
    is_admin = await check_family_admin(current_user.id, family_id, db)

    if not (is_creator or is_admin):
        raise HTTPException(status_code=403, detail="仅创建者或管理员可以取消赌注")

    # 检查状态
    if bet.status == BetStatus.SETTLED:
        raise HTTPException(status_code=400, detail="已结算的赌注无法取消")

    # 更新状态
    bet.status = BetStatus.CANCELLED
    await db.commit()

    # 返回更新后的赌注
    return await get_bet(bet_id, current_user, db)
