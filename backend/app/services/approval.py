"""
小金库 (Golden Nest) - 通用审批服务
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import (
    ApprovalRequest, ApprovalRecord, ApprovalRequestType, ApprovalRequestStatus,
    FamilyMember, User, Deposit, Investment, InvestmentIncome, InvestmentType,
    Transaction, TransactionType, Family, ExpenseRequest, ExpenseStatus
)
from app.schemas.approval import ApprovalRequestResponse, ApprovalRecordResponse


class ApprovalService:
    """通用审批服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_request(
        self,
        family_id: int,
        requester_id: int,
        request_type: ApprovalRequestType,
        title: str,
        description: str,
        amount: float,
        request_data: Dict[str, Any]
    ) -> ApprovalRequest:
        """创建申请"""
        request = ApprovalRequest(
            family_id=family_id,
            requester_id=requester_id,
            request_type=request_type,
            title=title,
            description=description,
            amount=amount,
            request_data=json.dumps(request_data, default=str)
        )
        self.db.add(request)
        await self.db.flush()
        
        # 检查是否是单人家庭，如果是则自动通过
        member_count = await self._get_family_member_count(family_id)
        if member_count == 1:
            # 单人家庭，自动创建一条自我审批记录并通过
            auto_approval = ApprovalRecord(
                request_id=request.id,
                approver_id=requester_id,
                is_approved=True,
                comment="单人家庭，自动通过"
            )
            self.db.add(auto_approval)
            await self.db.flush()
            
            # 更新状态为已通过
            request.status = ApprovalRequestStatus.APPROVED
            
            # 执行申请
            await self._execute_request(request)
        
        await self.db.refresh(request)
        return request
    
    async def approve_request(
        self,
        request_id: int,
        approver_id: int,
        is_approved: bool,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """审批申请"""
        # 获取申请
        result = await self.db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        if not request:
            raise ValueError("申请不存在")
        
        if request.status != ApprovalRequestStatus.PENDING:
            raise ValueError("该申请已经处理完毕")
        
        # 检查是否是家庭成员
        result = await self.db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == request.family_id,
                FamilyMember.user_id == approver_id
            )
        )
        if not result.scalar_one_or_none():
            raise ValueError("您不是该家庭成员")
        
        # 检查是否已经审批过
        result = await self.db.execute(
            select(ApprovalRecord).where(
                ApprovalRecord.request_id == request_id,
                ApprovalRecord.approver_id == approver_id
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("您已经审批过了")
        
        # 创建审批记录
        approval = ApprovalRecord(
            request_id=request_id,
            approver_id=approver_id,
            is_approved=is_approved,
            comment=comment
        )
        self.db.add(approval)
        await self.db.flush()
        
        # 宠物经验奖励：参与投票 +10 EXP
        try:
            from app.api.pet import grant_pet_exp
            await grant_pet_exp(self.db, request.family_id, "vote", 1, operator_id=approver_id)  # vote 基础经验是10，multiplier=1
        except Exception as e:
            logging.warning(f"Pet EXP grant failed after voting: {e}")
        
        # 检查审批状态
        await self._check_and_update_status(request)
        
        await self.db.refresh(request)
        return request
    
    async def cancel_request(self, request_id: int, user_id: int) -> ApprovalRequest:
        """取消申请"""
        result = await self.db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        if not request:
            raise ValueError("申请不存在")
        
        if request.requester_id != user_id:
            raise ValueError("只有申请人可以取消申请")
        
        if request.status != ApprovalRequestStatus.PENDING:
            raise ValueError("该申请已经处理完毕，无法取消")
        
        request.status = ApprovalRequestStatus.CANCELLED
        await self.db.flush()
        await self.db.refresh(request)
        return request
    
    async def get_request_response(
        self,
        request: ApprovalRequest,
        requester_nickname: str,
        requester_avatar_version: int = 0
    ) -> ApprovalRequestResponse:
        """获取申请响应对象"""
        # 获取审批记录
        result = await self.db.execute(
            select(ApprovalRecord, User)
            .join(User, ApprovalRecord.approver_id == User.id)
            .where(ApprovalRecord.request_id == request.id)
        )
        approval_rows = result.all()
        
        approvals = [
            ApprovalRecordResponse(
                id=a.id,
                request_id=a.request_id,
                approver_id=a.approver_id,
                approver_nickname=u.nickname,
                approver_avatar_version=u.avatar_version or 0,
                is_approved=a.is_approved,
                comment=a.comment,
                created_at=a.created_at
            )
            for a, u in approval_rows
        ]
        
        # 获取所有家庭成员
        result = await self.db.execute(
            select(FamilyMember).where(FamilyMember.family_id == request.family_id)
        )
        all_members = result.scalars().all()
        all_member_ids = [m.user_id for m in all_members]
        
        # 计算待审批成员
        approved_user_ids = [a.approver_id for a, _ in approval_rows]
        
        if len(all_member_ids) == 1:
            # 单人家庭，申请人自己审批
            pending_approvers = [uid for uid in all_member_ids if uid not in approved_user_ids]
        elif request.request_type == ApprovalRequestType.MEMBER_REMOVE:
            # 成员剔除：需要管理员同意，申请人如果是管理员也可以自己审批
            admin_ids = [m.user_id for m in all_members if m.role == "admin"]
            pending_approvers = [
                uid for uid in admin_ids
                if uid not in approved_user_ids
            ]
        else:
            # 其他申请类型：除申请人外的成员需要审批
            pending_approvers = [
                uid for uid in all_member_ids
                if uid != request.requester_id and uid not in approved_user_ids
            ]
        
        approved_count = sum(1 for a, _ in approval_rows if a.is_approved)
        rejected_count = sum(1 for a, _ in approval_rows if not a.is_approved)
        
        return ApprovalRequestResponse(
            id=request.id,
            family_id=request.family_id,
            requester_id=request.requester_id,
            requester_nickname=requester_nickname,
            requester_avatar_version=requester_avatar_version,
            request_type=request.request_type,
            title=request.title,
            description=request.description,
            amount=request.amount,
            request_data=json.loads(request.request_data),
            status=request.status,
            created_at=request.created_at,
            updated_at=request.updated_at,
            executed_at=request.executed_at,
            approvals=approvals,
            pending_approvers=pending_approvers,
            total_members=len(all_member_ids),
            approved_count=approved_count,
            rejected_count=rejected_count
        )
    
    async def _get_family_member_count(self, family_id: int) -> int:
        """获取家庭成员数量"""
        result = await self.db.execute(
            select(FamilyMember).where(FamilyMember.family_id == family_id)
        )
        members = result.scalars().all()
        return len(members)
    
    async def _check_and_update_status(self, request: ApprovalRequest) -> None:
        """检查并更新申请状态"""
        # 成员加入和剔除使用特殊逻辑
        if request.request_type == ApprovalRequestType.MEMBER_JOIN:
            await self._check_member_join_status(request)
            return
        elif request.request_type == ApprovalRequestType.MEMBER_REMOVE:
            await self._check_member_remove_status(request)
            return
        
        # 其他类型使用通用逻辑：全员同意
        # 获取所有审批记录
        result = await self.db.execute(
            select(ApprovalRecord).where(ApprovalRecord.request_id == request.id)
        )
        all_approvals = result.scalars().all()
        
        # 获取需要审批的成员数（申请人除外，除非是单人家庭）
        result = await self.db.execute(
            select(FamilyMember).where(FamilyMember.family_id == request.family_id)
        )
        all_members = result.scalars().all()
        
        if len(all_members) == 1:
            required_approvals = 1  # 单人家庭，自己审批
        else:
            required_approvals = len(all_members) - 1  # 除申请人外的所有人
        
        # 如果有人拒绝，直接拒绝
        if any(not a.is_approved for a in all_approvals):
            request.status = ApprovalRequestStatus.REJECTED
            await self.db.flush()
            return
        
        # 如果所有人都同意
        if len(all_approvals) >= required_approvals:
            if all(a.is_approved for a in all_approvals):
                request.status = ApprovalRequestStatus.APPROVED
                await self._execute_request(request)
    
    async def _check_member_join_status(self, request: ApprovalRequest) -> None:
        """检查成员加入申请状态 - 任一成员同意即可"""
        result = await self.db.execute(
            select(ApprovalRecord).where(ApprovalRecord.request_id == request.id)
        )
        all_approvals = result.scalars().all()
        
        # 任一成员同意即通过
        if any(a.is_approved for a in all_approvals):
            request.status = ApprovalRequestStatus.APPROVED
            await self._execute_request(request)
            return
        
        # 获取家庭成员数
        result = await self.db.execute(
            select(FamilyMember).where(FamilyMember.family_id == request.family_id)
        )
        all_members = result.scalars().all()
        
        # 如果所有成员都拒绝了，则拒绝
        if len(all_approvals) >= len(all_members) and all(not a.is_approved for a in all_approvals):
            request.status = ApprovalRequestStatus.REJECTED
            await self.db.flush()
    
    async def _check_member_remove_status(self, request: ApprovalRequest) -> None:
        """检查成员剔除申请状态 - 需要管理员同意"""
        result = await self.db.execute(
            select(ApprovalRecord).where(ApprovalRecord.request_id == request.id)
        )
        all_approvals = result.scalars().all()
        
        # 获取所有管理员
        result = await self.db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == request.family_id,
                FamilyMember.role == "admin"
            )
        )
        admins = result.scalars().all()
        admin_ids = [a.user_id for a in admins]
        
        # 检查是否有管理员同意
        admin_approved = any(
            a.is_approved and a.approver_id in admin_ids
            for a in all_approvals
        )
        
        if admin_approved:
            request.status = ApprovalRequestStatus.APPROVED
            await self._execute_request(request)
            return
        
        # 如果所有管理员都拒绝了，则拒绝
        admin_approvals = [a for a in all_approvals if a.approver_id in admin_ids]
        if len(admin_approvals) >= len(admin_ids) and all(not a.is_approved for a in admin_approvals):
            request.status = ApprovalRequestStatus.REJECTED
            await self.db.flush()
    
    async def _execute_request(self, request: ApprovalRequest) -> None:
        """执行已通过的申请（带幂等性保护）"""
        # 【幂等性保护】使用行锁重新获取申请记录，防止并发执行
        result = await self.db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.id == request.id)
            .with_for_update()  # 行锁，确保同一时间只有一个事务可以执行
        )
        locked_request = result.scalar_one_or_none()
        
        if not locked_request:
            logging.warning(f"Approval request {request.id} not found during execution")
            return
        
        # 【幂等性保护】检查是否已经执行过
        if locked_request.executed_at is not None:
            logging.info(f"Approval request {request.id} already executed at {locked_request.executed_at}, skipping")
            return
        
        request_data = json.loads(locked_request.request_data)
        
        if locked_request.request_type == ApprovalRequestType.DEPOSIT:
            await self._execute_deposit(locked_request, request_data)
        elif locked_request.request_type == ApprovalRequestType.INVESTMENT_CREATE:
            await self._execute_investment_create(locked_request, request_data)
        elif locked_request.request_type == ApprovalRequestType.INVESTMENT_UPDATE:
            await self._execute_investment_update(locked_request, request_data)
        elif locked_request.request_type == ApprovalRequestType.INVESTMENT_INCOME:
            await self._execute_investment_income(locked_request, request_data)
        elif locked_request.request_type == ApprovalRequestType.MEMBER_JOIN:
            await self._execute_member_join(locked_request, request_data)
        elif locked_request.request_type == ApprovalRequestType.MEMBER_REMOVE:
            await self._execute_member_remove(locked_request, request_data)
        elif locked_request.request_type == ApprovalRequestType.EXPENSE:
            await self._execute_expense(locked_request, request_data)
        
        # 设置执行时间，标记为已执行（幂等性关键标志）
        locked_request.executed_at = datetime.utcnow()
        await self.db.flush()
        
        logging.info(f"Approval request {locked_request.id} executed successfully")
    
    async def _execute_deposit(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行资金注入"""
        # 解析日期
        deposit_date = data.get("deposit_date")
        if isinstance(deposit_date, str):
            deposit_date = datetime.fromisoformat(deposit_date.replace("Z", "+00:00"))
        
        # 创建存款记录
        deposit = Deposit(
            user_id=request.requester_id,
            family_id=request.family_id,
            amount=request.amount,
            deposit_date=deposit_date,
            note=data.get("note")
        )
        self.db.add(deposit)
        await self.db.flush()
        
        # 获取当前余额
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.family_id == request.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0
        
        # 获取用户昵称
        result = await self.db.execute(
            select(User).where(User.id == request.requester_id)
        )
        user = result.scalar_one()
        
        # 创建交易流水
        transaction = Transaction(
            family_id=request.family_id,
            user_id=request.requester_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=request.amount,
            balance_after=current_balance + request.amount,
            description=f"{user.nickname}存入{request.amount}元",
            reference_id=deposit.id,
            reference_type="deposit"
        )
        self.db.add(transaction)
        
        # 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            await achievement_service.check_and_unlock(
                request.requester_id,
                context={"action": "deposit", "deposit_amount": request.amount}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after deposit: {e}")
        
        # 宠物经验奖励：每100元存款 +1 EXP
        try:
            from app.api.pet import grant_pet_exp
            exp_multiplier = max(1, int(request.amount / 100))  # 至少1点经验
            await grant_pet_exp(
                self.db, request.family_id, "deposit", exp_multiplier, 
                operator_id=request.requester_id,
                source_detail=f"存款 ¥{request.amount:.0f}"
            )
        except Exception as e:
            logging.warning(f"Pet EXP grant failed after deposit: {e}")
    
    async def _execute_investment_create(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行创建理财产品"""
        start_date = data.get("start_date")
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        elif start_date is None:
            start_date = datetime.utcnow()  # 默认使用当前时间
        
        end_date = data.get("end_date")
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        logging.info(f"Creating investment: family_id={request.family_id}, name={data.get('name')}")
        
        now = datetime.utcnow()
        investment = Investment(
            family_id=request.family_id,
            name=data.get("name"),
            investment_type=InvestmentType(data.get("investment_type")),
            principal=data.get("principal"),
            expected_rate=data.get("expected_rate"),
            start_date=start_date,
            end_date=end_date,
            note=data.get("note"),
            created_at=now,
            updated_at=now
        )
        self.db.add(investment)
        await self.db.flush()  # 确保投资记录写入数据库
        
        logging.info(f"Investment created: id={investment.id}, family_id={investment.family_id}")
        
        # 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            await achievement_service.check_and_unlock(
                request.requester_id,
                context={"action": "investment_create", "principal": data.get("principal")}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after investment create: {e}")
    
    async def _execute_investment_update(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行更新理财产品"""
        investment_id = data.get("investment_id")
        result = await self.db.execute(
            select(Investment).where(
                Investment.id == investment_id,
                Investment.family_id == request.family_id
            )
        )
        investment = result.scalar_one_or_none()
        if not investment:
            return  # 投资产品不存在，忽略
        
        if data.get("name") is not None:
            investment.name = data["name"]
        if data.get("principal") is not None:
            investment.principal = data["principal"]
        if data.get("expected_rate") is not None:
            investment.expected_rate = data["expected_rate"]
        if data.get("end_date") is not None:
            end_date = data["end_date"]
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            investment.end_date = end_date
        if data.get("is_active") is not None:
            investment.is_active = data["is_active"]
        if data.get("note") is not None:
            investment.note = data["note"]
    
    async def _execute_investment_income(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行登记理财收益"""
        investment_id = data.get("investment_id")
        result = await self.db.execute(
            select(Investment).where(
                Investment.id == investment_id,
                Investment.family_id == request.family_id
            )
        )
        investment = result.scalar_one_or_none()
        if not investment:
            return  # 投资产品不存在，忽略
        
        income_date = data.get("income_date")
        if isinstance(income_date, str):
            income_date = datetime.fromisoformat(income_date.replace("Z", "+00:00"))
        
        # 创建收益记录
        income = InvestmentIncome(
            investment_id=investment_id,
            amount=request.amount,
            income_date=income_date,
            note=data.get("note")
        )
        self.db.add(income)
        await self.db.flush()
        
        # 获取当前余额
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.family_id == request.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0
        
        # 创建交易流水
        transaction = Transaction(
            family_id=request.family_id,
            user_id=None,
            transaction_type=TransactionType.INCOME,
            amount=request.amount,
            balance_after=current_balance + request.amount,
            description=f"理财收益: {investment.name} +{request.amount}元",
            reference_id=income.id,
            reference_type="investment_income"
        )
        self.db.add(transaction)
        
        # 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            await achievement_service.check_and_unlock(
                request.requester_id,
                context={"action": "investment_income", "income_amount": request.amount}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after investment income: {e}")
        
        # 宠物经验奖励：每10元收益 +1 EXP
        try:
            from app.api.pet import grant_pet_exp
            exp_multiplier = max(1, int(request.amount / 10))  # 至少1点经验
            await grant_pet_exp(
                self.db, request.family_id, "investment", exp_multiplier,
                operator_id=request.requester_id,
                source_detail=f"理财收益 {investment.name} +¥{request.amount:.0f}"
            )
        except Exception as e:
            logging.warning(f"Pet EXP grant failed after investment income: {e}")
    
    async def _execute_member_join(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行成员加入"""
        user_id = data.get("user_id")
        
        # 检查用户是否已经是成员
        result = await self.db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == request.family_id,
                FamilyMember.user_id == user_id
            )
        )
        if result.scalar_one_or_none():
            return  # 用户已经是成员，跳过
        
        # 添加成员
        member = FamilyMember(
            user_id=user_id,
            family_id=request.family_id,
            role="member"
        )
        self.db.add(member)
        
        # 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            # 检查新成员的"加入家庭"成就
            await achievement_service.check_and_unlock(
                user_id,
                context={"action": "join_family"}
            )
            # 检查邀请人的"邀请成员"成就
            await achievement_service.check_and_unlock(
                request.requester_id,
                context={"action": "invite_member"}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after member join: {e}")
    
    async def _execute_member_remove(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行成员剔除"""
        user_id = data.get("user_id")
        
        # 查找成员记录
        result = await self.db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == request.family_id,
                FamilyMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return  # 成员不存在，跳过
        
        # 不能剔除管理员
        if member.role == "admin":
            return  # 不能剔除管理员
        
        # 删除成员记录
        await self.db.delete(member)

    async def _execute_expense(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行支出申请"""
        expense_id = data.get("expense_id")
        if not expense_id:
            return

        result = await self.db.execute(
            select(ExpenseRequest).where(
                ExpenseRequest.id == expense_id,
                ExpenseRequest.family_id == request.family_id
            )
        )
        expense = result.scalar_one_or_none()
        if not expense:
            return

        if expense.status != ExpenseStatus.PENDING:
            return

        expense.status = ExpenseStatus.APPROVED
        await self.db.flush()

        # 执行支出逻辑：按扣减比例创建负向存款
        # deduction_ratios 格式为 {"user_id": ratio, ...}
        deduction_ratios = json.loads(expense.equity_deduction_ratio)

        for user_id_str, ratio in deduction_ratios.items():
            user_id = int(user_id_str)
            deduction_amount = expense.amount * ratio

            deposit = Deposit(
                user_id=user_id,
                family_id=request.family_id,
                amount=-deduction_amount,
                deposit_date=datetime.utcnow(),
                note=f"支出扣减: {expense.title}"
            )
            self.db.add(deposit)

        # 获取当前余额
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.family_id == request.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0

        # 创建支出流水
        transaction = Transaction(
            family_id=request.family_id,
            user_id=expense.requester_id,
            transaction_type=TransactionType.WITHDRAW,
            amount=-expense.amount,
            balance_after=current_balance - expense.amount,
            description=f"大额支出: {expense.title}",
            reference_id=expense.id,
            reference_type="expense"
        )
        self.db.add(transaction)

        # 检查成就解锁
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            await achievement_service.check_and_unlock(
                expense.requester_id,
                context={"action": "expense", "expense_amount": expense.amount}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after expense approval: {e}")
