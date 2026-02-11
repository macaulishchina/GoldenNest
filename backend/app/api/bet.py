"""
小金库 (Golden Nest) - 家庭赌注路由
"""
from datetime import datetime, timedelta
from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import (
    Bet, BetParticipant, BetOption, BetStatus,
    FamilyMember, User, Deposit, Transaction, TransactionType, Family
)
from app.schemas.bet import (
    BetCreate, BetUpdate, BetResponse, BetListResponse,
    BetVoteRequest, BetSettleRequest, BetApproveRequest,
    BetOptionResponse, BetParticipantResponse
)
from sqlalchemy import func as sa_func
from app.api.auth import get_current_user
from app.services.notification import (
    NotificationService, NotificationType, send_bet_notification
)

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


async def auto_transition_bet(bet: Bet, participants: List[BetParticipant], db: AsyncSession) -> None:
    """自动转换赌注状态：截止后自动取消（投票不足）或进入等待结果阶段"""
    if bet.status != BetStatus.ACTIVE:
        return
    if not bet.end_date or bet.end_date > datetime.utcnow():
        return  # 未截止

    voted_count = sum(1 for p in participants if p.selected_option_id is not None)
    if voted_count <= 1:
        # 投票人数不足，自动取消
        bet.status = BetStatus.CANCELLED
        await db.commit()
    else:
        # 投票人数足够，进入等待结果登记阶段
        bet.status = BetStatus.AWAITING_RESULT
        await db.commit()


def build_bet_response(bet: Bet, participants: List[BetParticipant], options: List[BetOption], users_dict: dict) -> BetResponse:
    """构建赌注响应"""
    # 检查是否已过期（截止时间已过）
    is_expired = bet.end_date < datetime.utcnow() if bet.end_date else False

    # 统计已投票人数
    voted_count = sum(1 for p in participants if p.selected_option_id is not None)

    # 检查是否可以结算（已过期且状态为active/awaiting_result）
    can_settle = is_expired and bet.status in (BetStatus.ACTIVE, BetStatus.AWAITING_RESULT)

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
        declared_winning_option_id=bet.declared_winning_option_id,
        approval_request_id=bet.approval_request_id,
        created_at=bet.created_at,
        options=options_response,
        participants=participants_response,
        creator_nickname=users_dict.get(bet.creator_id, "Unknown"),
        is_expired=is_expired,
        can_settle=can_settle,
        voted_count=voted_count
    )


@router.post("/create", response_model=BetResponse)
async def create_bet(
    bet_data: BetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建家庭赌注（直接激活，参与者各自选择选项）"""
    family_id = await get_user_family_id(current_user.id, db)

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

    # 计算截止时间
    now = datetime.utcnow()
    deadline = now + timedelta(hours=bet_data.deadline_hours)

    # 创建赌注（直接激活，无需审批，参与者各自选择选项）
    bet = Bet(
        family_id=family_id,
        creator_id=current_user.id,
        title=bet_data.title,
        description=bet_data.description,
        status=BetStatus.ACTIVE,
        start_date=now,
        end_date=deadline
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
            has_approved=True
        )
        db.add(participant)
        participants.append(participant)

    await db.commit()
    await db.refresh(bet)

    # 获取用户信息
    users_result = await db.execute(
        select(User).where(User.id.in_([current_user.id] + participant_user_ids))
    )
    users = users_result.scalars().all()
    users_dict = {u.id: u.nickname for u in users}

    # 发送企业微信通知
    participants_names = [users_dict.get(uid, "Unknown") for uid in participant_user_ids]
    try:
        logging.info(f"[BET] Sending bet creation notification for bet {bet.id}, family_id={bet.family_id}")
        await send_bet_notification(
            db, NotificationType.BET_CREATED, bet,
            creator_name=current_user.nickname,
            participants_names=participants_names
        )
        logging.info("[BET] Bet creation notification sent successfully")
    except Exception as e:
        logging.error(f"Failed to send bet creation notification: {e}", exc_info=True)

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
        # 自动转换截止的 ACTIVE 赌注
        await auto_transition_bet(bet, participants, db)
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

    # 自动转换截止的 ACTIVE 赌注
    await auto_transition_bet(bet, participants, db)

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

    # 发送投票通知
    try:
        await send_bet_notification(
            db, NotificationType.BET_VOTED, bet,
            voter=current_user, option_text=option.option_text
        )
    except Exception as e:
        logging.error(f"Failed to send bet vote notification: {e}", exc_info=True)

    # 重新获取数据返回
    return await get_bet(bet_id, current_user, db)


@router.post("/{bet_id}/settle", response_model=BetResponse)
async def settle_bet(
    bet_id: int,
    settle_data: BetSettleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """登记赌注结果（仅创建者），提交后需参与者确认"""
    family_id = await get_user_family_id(current_user.id, db)

    # 查询赌注
    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    # 检查权限：仅创建者可以登记结果
    if bet.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅赌局创建者可以登记结果")

    # 检查状态：必须是 AWAITING_RESULT 或 RESULT_PENDING（允许重新提交）
    if bet.status not in (BetStatus.AWAITING_RESULT, BetStatus.RESULT_PENDING):
        # 也允许 ACTIVE 但已截止的赌注（兼容自动转换前的手动操作）
        if bet.status == BetStatus.ACTIVE and bet.end_date < datetime.utcnow():
            # 先自动转换
            participants_result = await db.execute(
                select(BetParticipant).where(BetParticipant.bet_id == bet_id)
            )
            participants = participants_result.scalars().all()
            await auto_transition_bet(bet, participants, db)
            if bet.status != BetStatus.AWAITING_RESULT:
                raise HTTPException(status_code=400, detail="赌注投票人数不足，已自动取消")
        else:
            raise HTTPException(status_code=400, detail="当前状态无法登记结果")

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

    # 设置所有选项的获胜状态
    all_options_result = await db.execute(
        select(BetOption).where(BetOption.bet_id == bet_id)
    )
    all_options = all_options_result.scalars().all()
    for opt in all_options:
        opt.is_winning_option = (opt.id == settle_data.winning_option_id)

    # 记录创建者声明的获胜选项
    bet.declared_winning_option_id = settle_data.winning_option_id

    # 重置所有参与者的 has_approved（允许重新提交时重置）
    participants_result = await db.execute(
        select(BetParticipant).where(BetParticipant.bet_id == bet_id)
    )
    participants = participants_result.scalars().all()
    for p in participants:
        if p.user_id == current_user.id:
            p.has_approved = True  # 创建者自动同意自己的结果
        else:
            p.has_approved = False

    # 更新状态为等待确认
    bet.status = BetStatus.RESULT_PENDING

    await db.commit()

    # 发送结果登记通知
    try:
        winning_opt = await db.execute(
            select(BetOption).where(BetOption.id == settle_data.winning_option_id)
        )
        winning_option = winning_opt.scalar_one_or_none()
        winning_text = winning_option.option_text if winning_option else ""
        await send_bet_notification(
            db, NotificationType.BET_RESULT_DECLARED, bet,
            creator_name=current_user.nickname,
            content=f"创建者 {current_user.nickname} 登记的获胜选项：{winning_text}\n请参与者确认结果"
        )
    except Exception as e:
        logging.error(f"Failed to send bet result declared notification: {e}", exc_info=True)

    # 返回更新后的赌注
    return await get_bet(bet_id, current_user, db)


@router.post("/{bet_id}/approve-result", response_model=BetResponse)
async def approve_bet_result(
    bet_id: int,
    approve_data: BetApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """参与者审批赌注结果"""
    family_id = await get_user_family_id(current_user.id, db)

    # 查询赌注
    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    # 检查状态
    if bet.status != BetStatus.RESULT_PENDING:
        raise HTTPException(status_code=400, detail="当前状态不在结果确认阶段")

    # 查找当前用户的参与者记录
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

    if approve_data.approved:
        # 同意结果
        participant.has_approved = True
        await db.commit()

        # 检查是否所有参与者都已同意
        all_participants_result = await db.execute(
            select(BetParticipant).where(BetParticipant.bet_id == bet_id)
        )
        all_participants = all_participants_result.scalars().all()
        all_approved = all(p.has_approved for p in all_participants)

        if all_approved:
            # 全部同意，自动结算
            winning_option_id = bet.declared_winning_option_id
            winners = []
            losers = []
            for p in all_participants:
                if p.selected_option_id == winning_option_id:
                    p.is_winner = True
                    winners.append(p)
                else:
                    p.is_winner = False
                    losers.append(p)

            bet.status = BetStatus.SETTLED
            bet.settlement_date = datetime.utcnow()

            # 获取参与者昵称用于流水记录和通知
            user_ids = [p.user_id for p in all_participants] + [bet.creator_id]
            users_result = await db.execute(
                select(User).where(User.id.in_(list(set(user_ids))))
            )
            users_dict = {u.id: u.nickname for u in users_result.scalars().all()}
            total_pool = 0.0

            # 股权结算：输家的 stake_amount（%）对应的资金转移给赢家平分
            if losers and winners:
                # 获取家庭总资产
                total_result = await db.execute(
                    select(sa_func.coalesce(sa_func.sum(Deposit.amount), 0)).where(
                        Deposit.family_id == bet.family_id
                    )
                )
                family_total = total_result.scalar() or 0

                if family_total > 0:
                    # 计算每个输家转出的金额
                    total_pool = 0.0
                    for loser in losers:
                        if loser.stake_amount > 0:
                            transfer_amount = family_total * (loser.stake_amount / 100)
                            total_pool += transfer_amount
                            # 输家扣除
                            db.add(Deposit(
                                user_id=loser.user_id,
                                family_id=bet.family_id,
                                amount=-transfer_amount,
                                note=f"赌注结算扣除：{bet.title}",
                                deposit_date=datetime.utcnow()
                            ))

                    # 赢家平分
                    if total_pool > 0 and winners:
                        per_winner = total_pool / len(winners)
                        for winner in winners:
                            db.add(Deposit(
                                user_id=winner.user_id,
                                family_id=bet.family_id,
                                amount=per_winner,
                                note=f"赌注结算获得：{bet.title}",
                                deposit_date=datetime.utcnow()
                            ))

                    # 记录资金流水
                    # 获取当前余额
                    last_tx_result = await db.execute(
                        select(Transaction)
                        .where(Transaction.family_id == bet.family_id)
                        .order_by(Transaction.created_at.desc())
                        .limit(1)
                    )
                    last_tx = last_tx_result.scalar_one_or_none()
                    current_balance = last_tx.balance_after if last_tx else 0

                    # 输家流水
                    for loser in losers:
                        if loser.stake_amount > 0:
                            loss_amount = family_total * (loser.stake_amount / 100)
                            loser_name = users_dict.get(loser.user_id, "Unknown")
                            db.add(Transaction(
                                family_id=bet.family_id,
                                user_id=loser.user_id,
                                transaction_type=TransactionType.BET_LOSE,
                                amount=-loss_amount,
                                balance_after=current_balance,
                                description=f"赌注失败扣除：{bet.title}（{loser_name} 负 {loser.stake_amount}% 股份）",
                                reference_id=bet.id,
                                reference_type="bet_settle"
                            ))

                    # 赢家流水
                    if total_pool > 0 and winners:
                        for winner in winners:
                            winner_name = users_dict.get(winner.user_id, "Unknown")
                            db.add(Transaction(
                                family_id=bet.family_id,
                                user_id=winner.user_id,
                                transaction_type=TransactionType.BET_WIN,
                                amount=per_winner,
                                balance_after=current_balance,
                                description=f"赌注获胜获得：{bet.title}（{winner_name} 获得 ¥{per_winner:,.2f}）",
                                reference_id=bet.id,
                                reference_type="bet_settle"
                            ))

            await db.commit()

            # 发送结算通知
            try:
                winner_names = [users_dict.get(w.user_id, "Unknown") for w in winners]
                loser_names = [users_dict.get(l.user_id, "Unknown") for l in losers]
                content = f"获胜者：{'\u3001'.join(winner_names)}\n失败者：{'\u3001'.join(loser_names)}"
                if total_pool > 0:
                    content += f"\n涉及股权变动：¥{total_pool:,.2f}"
                creator_name = users_dict.get(bet.creator_id, "Unknown")
                await send_bet_notification(
                    db, NotificationType.BET_SETTLED, bet,
                    creator_name=creator_name, content=content
                )
            except Exception as e:
                logging.error(f"Failed to send bet settled notification: {e}", exc_info=True)
    else:
        # 拒绝结果 → 退回给创建者重新登记
        # 重置所有审批状态
        all_participants_result = await db.execute(
            select(BetParticipant).where(BetParticipant.bet_id == bet_id)
        )
        all_participants = all_participants_result.scalars().all()
        for p in all_participants:
            p.has_approved = False

        # 清除已声明的获胜选项
        bet.declared_winning_option_id = None

        # 重置选项获胜状态
        all_options_result = await db.execute(
            select(BetOption).where(BetOption.bet_id == bet_id)
        )
        all_options = all_options_result.scalars().all()
        for opt in all_options:
            opt.is_winning_option = None

        # 退回 AWAITING_RESULT 状态
        bet.status = BetStatus.AWAITING_RESULT
        await db.commit()

    # 返回更新后的赌注
    return await get_bet(bet_id, current_user, db)


@router.post("/{bet_id}/close-voting", response_model=BetResponse)
async def close_voting(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提前截止投票（仅创建者，所有参与者已投票时可用）"""
    family_id = await get_user_family_id(current_user.id, db)

    result = await db.execute(
        select(Bet).where(and_(Bet.id == bet_id, Bet.family_id == family_id))
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="赌注不存在")

    if bet.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅赌局创建者可以提前截止投票")

    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="只有进行中的赌注才能截止投票")

    # 检查所有参与者是否已投票
    participants_result = await db.execute(
        select(BetParticipant).where(BetParticipant.bet_id == bet_id)
    )
    participants = participants_result.scalars().all()
    all_voted = all(p.selected_option_id is not None for p in participants)
    if not all_voted or len(participants) < 2:
        raise HTTPException(status_code=400, detail="尚有参与者未完成投票")

    bet.status = BetStatus.AWAITING_RESULT
    await db.commit()

    # 发送截止投票通知
    try:
        await send_bet_notification(
            db, NotificationType.BET_AWAITING_RESULT, bet,
            creator_name=current_user.nickname,
            content=f"发起者 {current_user.nickname} 已提前截止投票，等待登记结果"
        )
    except Exception as e:
        logging.error(f"Failed to send close voting notification: {e}", exc_info=True)

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
    if bet.status in (BetStatus.SETTLED, BetStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="已结算或已取消的赌注无法取消")

    # 更新状态
    bet.status = BetStatus.CANCELLED
    await db.commit()

    # 发送取消通知
    try:
        await send_bet_notification(
            db, NotificationType.BET_CANCELLED, bet,
            creator_name=current_user.nickname,
            content=f"{current_user.nickname} 已取消赌注"
        )
    except Exception as e:
        logging.error(f"Failed to send bet cancel notification: {e}", exc_info=True)

    # 返回更新后的赌注
    return await get_bet(bet_id, current_user, db)


@router.get("/my-pending/count")
async def get_my_pending_bet_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户待处理的赌注数量（待投票 + 待确认结果 + 待登记结果）"""
    family_id = await get_user_family_id(current_user.id, db)

    # 1. 待投票：状态为 ACTIVE、未过期、未投票
    vote_count_result = await db.execute(
        select(sa_func.count(BetParticipant.id)).where(
            and_(
                BetParticipant.user_id == current_user.id,
                BetParticipant.selected_option_id.is_(None),
                BetParticipant.bet_id.in_(
                    select(Bet.id).where(
                        and_(
                            Bet.family_id == family_id,
                            Bet.status == BetStatus.ACTIVE,
                            Bet.end_date > datetime.utcnow()
                        )
                    )
                )
            )
        )
    )
    vote_count = vote_count_result.scalar() or 0

    # 2. 待确认结果：状态为 RESULT_PENDING，当前用户未确认
    confirm_count_result = await db.execute(
        select(sa_func.count(BetParticipant.id)).where(
            and_(
                BetParticipant.user_id == current_user.id,
                BetParticipant.has_approved == False,
                BetParticipant.bet_id.in_(
                    select(Bet.id).where(
                        and_(
                            Bet.family_id == family_id,
                            Bet.status == BetStatus.RESULT_PENDING
                        )
                    )
                )
            )
        )
    )
    confirm_count = confirm_count_result.scalar() or 0

    # 3. 待登记结果：状态为 AWAITING_RESULT，且当前用户是创建者
    declare_count_result = await db.execute(
        select(sa_func.count(Bet.id)).where(
            and_(
                Bet.family_id == family_id,
                Bet.status == BetStatus.AWAITING_RESULT,
                Bet.creator_id == current_user.id
            )
        )
    )
    declare_count = declare_count_result.scalar() or 0

    count = vote_count + confirm_count + declare_count
    return {"count": count}
