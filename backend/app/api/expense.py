"""
小金库 (Golden Nest) - 支出申请路由
"""
import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import (
    ExpenseRequest, ExpenseApproval, ExpenseStatus,
    FamilyMember, User, Transaction, TransactionType, Deposit
)
from app.schemas.expense import (
    ExpenseRequestCreate, ExpenseApprovalCreate,
    ExpenseRequestResponse, ExpenseApprovalResponse
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


@router.post("/create", response_model=ExpenseRequestResponse)
async def create_expense_request(
    expense_data: ExpenseRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建支出申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 验证扣减比例之和为1
    total_ratio = sum(r.ratio for r in expense_data.deduction_ratios)
    if abs(total_ratio - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="股权扣减比例之和必须为1")
    
    # 转换扣减比例为JSON
    deduction_json = json.dumps([
        {"user_id": r.user_id, "ratio": r.ratio}
        for r in expense_data.deduction_ratios
    ])
    
    expense = ExpenseRequest(
        family_id=family_id,
        requester_id=current_user.id,
        title=expense_data.title,
        amount=expense_data.amount,
        reason=expense_data.reason,
        equity_deduction_ratio=deduction_json
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    
    # 获取家庭所有成员
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family_id)
    )
    all_members = result.scalars().all()
    
    # 获取待审批的成员列表（除了申请人）
    other_members = [m for m in all_members if m.user_id != current_user.id]
    pending_approvers = [m.user_id for m in other_members]
    
    approvals = []
    
    # 单人家庭：自动通过并执行支出
    if len(all_members) == 1:
        # 创建自我审批记录
        auto_approval = ExpenseApproval(
            expense_request_id=expense.id,
            approver_id=current_user.id,
            is_approved=True,
            comment="单人家庭，自动通过"
        )
        db.add(auto_approval)
        await db.flush()
        
        # 更新状态为已通过
        expense.status = ExpenseStatus.APPROVED
        
        # 执行支出逻辑
        deduction_ratios = json.loads(expense.equity_deduction_ratio)
        
        for ratio_info in deduction_ratios:
            user_id = ratio_info["user_id"]
            ratio = ratio_info["ratio"]
            deduction_amount = expense.amount * ratio
            
            # 创建负向存款（相当于撤资）
            deposit = Deposit(
                user_id=user_id,
                family_id=family_id,
                amount=-deduction_amount,
                deposit_date=expense.updated_at,
                note=f"支出扣减: {expense.title}"
            )
            db.add(deposit)
        
        # 获取当前余额
        result = await db.execute(
            select(Transaction)
            .where(Transaction.family_id == family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0
        
        # 创建支出流水
        transaction = Transaction(
            family_id=family_id,
            user_id=expense.requester_id,
            transaction_type=TransactionType.WITHDRAW,
            amount=-expense.amount,
            balance_after=current_balance - expense.amount,
            description=f"大额支出: {expense.title}",
            reference_id=expense.id,
            reference_type="expense"
        )
        db.add(transaction)
        await db.flush()
        
        # 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(db)
            await achievement_service.check_and_unlock(
                current_user.id,
                context={"action": "expense", "expense_amount": expense.amount}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after expense: {e}")
        
        # 构建审批记录响应
        approvals = [
            ExpenseApprovalResponse(
                id=auto_approval.id,
                expense_request_id=auto_approval.expense_request_id,
                approver_id=auto_approval.approver_id,
                approver_nickname=current_user.nickname,
                is_approved=auto_approval.is_approved,
                comment=auto_approval.comment,
                created_at=auto_approval.created_at
            )
        ]
        pending_approvers = []
    
    await db.commit()
    await db.refresh(expense)
    
    return ExpenseRequestResponse(
        id=expense.id,
        family_id=expense.family_id,
        requester_id=expense.requester_id,
        requester_nickname=current_user.nickname,
        title=expense.title,
        amount=expense.amount,
        reason=expense.reason,
        equity_deduction_ratio=expense.equity_deduction_ratio,
        status=expense.status,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        approvals=approvals,
        pending_approvers=pending_approvers
    )


@router.get("/list", response_model=List[ExpenseRequestResponse])
async def list_expense_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取支出申请列表"""
    family_id = await get_user_family_id(current_user.id, db)
    
    result = await db.execute(
        select(ExpenseRequest, User)
        .join(User, ExpenseRequest.requester_id == User.id)
        .where(ExpenseRequest.family_id == family_id)
        .order_by(ExpenseRequest.created_at.desc())
    )
    rows = result.all()
    
    # 获取家庭成员列表
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family_id)
    )
    all_members = result.scalars().all()
    all_member_ids = [m.user_id for m in all_members]
    
    response = []
    for expense, requester in rows:
        # 获取审批记录
        result = await db.execute(
            select(ExpenseApproval, User)
            .join(User, ExpenseApproval.approver_id == User.id)
            .where(ExpenseApproval.expense_request_id == expense.id)
        )
        approval_rows = result.all()
        
        approvals = [
            ExpenseApprovalResponse(
                id=a.id,
                expense_request_id=a.expense_request_id,
                approver_id=a.approver_id,
                approver_nickname=u.nickname,
                is_approved=a.is_approved,
                comment=a.comment,
                created_at=a.created_at
            )
            for a, u in approval_rows
        ]
        
        # 计算待审批成员
        approved_user_ids = [a.approver_id for a, _ in approval_rows]
        pending_approvers = [
            uid for uid in all_member_ids
            if uid != expense.requester_id and uid not in approved_user_ids
        ]
        
        response.append(ExpenseRequestResponse(
            id=expense.id,
            family_id=expense.family_id,
            requester_id=expense.requester_id,
            requester_nickname=requester.nickname,
            title=expense.title,
            amount=expense.amount,
            reason=expense.reason,
            equity_deduction_ratio=expense.equity_deduction_ratio,
            status=expense.status,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
            approvals=approvals,
            pending_approvers=pending_approvers
        ))
    
    return response


@router.post("/{expense_id}/approve", response_model=ExpenseRequestResponse)
async def approve_expense(
    expense_id: int,
    approval_data: ExpenseApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """审批支出申请"""
    family_id = await get_user_family_id(current_user.id, db)
    
    # 获取支出申请
    result = await db.execute(
        select(ExpenseRequest)
        .where(ExpenseRequest.id == expense_id, ExpenseRequest.family_id == family_id)
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="支出申请不存在")
    
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已经处理完毕")
    
    if expense.requester_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能审批自己的申请")
    
    # 检查是否已经审批过
    result = await db.execute(
        select(ExpenseApproval)
        .where(
            ExpenseApproval.expense_request_id == expense_id,
            ExpenseApproval.approver_id == current_user.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="您已经审批过了")
    
    # 创建审批记录
    approval = ExpenseApproval(
        expense_request_id=expense_id,
        approver_id=current_user.id,
        is_approved=approval_data.is_approved,
        comment=approval_data.comment
    )
    db.add(approval)
    await db.flush()
    
    # 检查是否所有人都已审批
    result = await db.execute(
        select(FamilyMember)
        .where(FamilyMember.family_id == family_id, FamilyMember.user_id != expense.requester_id)
    )
    other_members = result.scalars().all()
    
    result = await db.execute(
        select(ExpenseApproval).where(ExpenseApproval.expense_request_id == expense_id)
    )
    all_approvals = result.scalars().all()
    
    # 如果有人拒绝，直接拒绝
    if any(not a.is_approved for a in all_approvals):
        expense.status = ExpenseStatus.REJECTED
    # 如果所有人都同意
    elif len(all_approvals) >= len(other_members):
        if all(a.is_approved for a in all_approvals):
            expense.status = ExpenseStatus.APPROVED
            # 执行支出：创建负向存款记录（按扣减比例）
            deduction_ratios = json.loads(expense.equity_deduction_ratio)
            
            for ratio_info in deduction_ratios:
                user_id = ratio_info["user_id"]
                ratio = ratio_info["ratio"]
                deduction_amount = expense.amount * ratio
                
                # 创建负向存款（相当于撤资）
                deposit = Deposit(
                    user_id=user_id,
                    family_id=family_id,
                    amount=-deduction_amount,
                    deposit_date=expense.updated_at,
                    note=f"支出扣减: {expense.title}"
                )
                db.add(deposit)
            
            # 获取当前余额
            result = await db.execute(
                select(Transaction)
                .where(Transaction.family_id == family_id)
                .order_by(Transaction.created_at.desc())
                .limit(1)
            )
            last_transaction = result.scalar_one_or_none()
            current_balance = last_transaction.balance_after if last_transaction else 0
            
            # 创建支出流水
            transaction = Transaction(
                family_id=family_id,
                user_id=expense.requester_id,
                transaction_type=TransactionType.WITHDRAW,
                amount=-expense.amount,
                balance_after=current_balance - expense.amount,
                description=f"大额支出: {expense.title}",
                reference_id=expense.id,
                reference_type="expense"
            )
            db.add(transaction)
            
            # 检查成就解锁（失败不影响主业务）
            try:
                from app.services.achievement import AchievementService
                achievement_service = AchievementService(db)
                # 申请人的支出成就
                await achievement_service.check_and_unlock(
                    expense.requester_id,
                    context={"action": "expense", "expense_amount": expense.amount}
                )
                # 审批人的审批成就
                await achievement_service.check_and_unlock(
                    current_user.id,
                    context={"action": "review", "is_approved": approval_data.is_approved}
                )
            except Exception as e:
                logging.warning(f"Achievement check failed after expense approval: {e}")
    
    await db.flush()
    
    # 返回更新后的申请信息
    result = await db.execute(
        select(User).where(User.id == expense.requester_id)
    )
    requester = result.scalar_one()
    
    result = await db.execute(
        select(ExpenseApproval, User)
        .join(User, ExpenseApproval.approver_id == User.id)
        .where(ExpenseApproval.expense_request_id == expense_id)
    )
    approval_rows = result.all()
    
    approvals = [
        ExpenseApprovalResponse(
            id=a.id,
            expense_request_id=a.expense_request_id,
            approver_id=a.approver_id,
            approver_nickname=u.nickname,
            is_approved=a.is_approved,
            comment=a.comment,
            created_at=a.created_at
        )
        for a, u in approval_rows
    ]
    
    approved_user_ids = [a.approver_id for a, _ in approval_rows]
    pending_approvers = [
        m.user_id for m in other_members
        if m.user_id not in approved_user_ids
    ]
    
    return ExpenseRequestResponse(
        id=expense.id,
        family_id=expense.family_id,
        requester_id=expense.requester_id,
        requester_nickname=requester.nickname,
        title=expense.title,
        amount=expense.amount,
        reason=expense.reason,
        equity_deduction_ratio=expense.equity_deduction_ratio,
        status=expense.status,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        approvals=approvals,
        pending_approvers=pending_approvers
    )
