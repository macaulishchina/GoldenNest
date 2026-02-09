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
    InvestmentPosition, PositionOperationType,
    Transaction, TransactionType, Family, ExpenseRequest, ExpenseStatus
)
from app.schemas.approval import ApprovalRequestResponse, ApprovalRecordResponse
from app.services.calendar import calendar_service
from app.services.notification import NotificationService, NotificationType, send_approval_notification


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
            await self.db.flush()
            
            # 【关键修复】先提交事务，再执行业务逻辑
            # 这样可以避免长时间事务阻塞其他查询
            await self.db.commit()
            
            # 重新获取request对象（commit后session失效）
            result = await self.db.execute(
                select(ApprovalRequest).where(ApprovalRequest.id == request.id)
            )
            request = result.scalar_one_or_none()
            if request:
                # 在新的事务中执行申请
                await self._execute_request(request)
                await self.db.commit()
        
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
        
        # 获取目标用户信息（如果有）
        target_user_id = request.target_user_id
        target_user_nickname = None
        target_user_avatar_version = None
        if target_user_id:
            result = await self.db.execute(
                select(User).where(User.id == target_user_id)
            )
            target_user = result.scalar_one_or_none()
            if target_user:
                target_user_nickname = target_user.nickname
                target_user_avatar_version = target_user.avatar_version or 0
        
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
        elif request.request_type == ApprovalRequestType.DIVIDEND_CLAIM:
            # 分红领取：只有目标用户需要审批
            pending_approvers = [target_user_id] if target_user_id and target_user_id not in approved_user_ids else []
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
            target_user_id=target_user_id,
            target_user_nickname=target_user_nickname,
            target_user_avatar_version=target_user_avatar_version,
            request_type=request.request_type,
            title=request.title,
            description=request.description,
            amount=request.amount,
            request_data=json.loads(request.request_data),
            status=request.status,
            created_at=request.created_at,
            updated_at=request.updated_at,
            executed_at=request.executed_at,
            execution_failed=request.execution_failed,
            failure_reason=request.failure_reason,
            approvals=approvals,
            pending_approvers=pending_approvers,
            total_members=len(all_member_ids),
            approved_count=approved_count,
            rejected_count=rejected_count
        )
    
    async def get_request_response_with_preloaded_data(
        self,
        request: ApprovalRequest,
        requester_nickname: str,
        requester_avatar_version: int = 0,
        approval_rows: list = None,
        target_user = None,
        all_members: list = None
    ) -> ApprovalRequestResponse:
        """获取申请响应对象（使用预加载的数据，避免N+1查询）"""
        if approval_rows is None:
            approval_rows = []
        if all_members is None:
            all_members = []
            
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
        
        # 使用预加载的目标用户信息
        target_user_id = request.target_user_id
        target_user_nickname = None
        target_user_avatar_version = None
        if target_user:
            target_user_nickname = target_user.nickname
            target_user_avatar_version = target_user.avatar_version or 0
        
        # 使用预加载的家庭成员
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
        elif request.request_type == ApprovalRequestType.DIVIDEND_CLAIM:
            # 分红领取：只有目标用户需要审批
            pending_approvers = [target_user_id] if target_user_id and target_user_id not in approved_user_ids else []
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
            target_user_id=target_user_id,
            target_user_nickname=target_user_nickname,
            target_user_avatar_version=target_user_avatar_version,
            request_type=request.request_type,
            title=request.title,
            description=request.description,
            amount=request.amount,
            request_data=json.loads(request.request_data),
            status=request.status,
            created_at=request.created_at,
            updated_at=request.updated_at,
            executed_at=request.executed_at,
            execution_failed=request.execution_failed,
            failure_reason=request.failure_reason,
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
        """执行已通过的申请（带幂等性保护和回滚支持）"""
        # 【幂等性保护】重新获取申请记录，检查是否已执行
        # 不使用行锁，避免阻塞其他查询
        result = await self.db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.id == request.id)
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
        
        # 创建savepoint用于回滚部分事务
        async with self.db.begin_nested():
            try:
                if locked_request.request_type == ApprovalRequestType.ASSET_CREATE:
                    await self._execute_asset_create(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.DEPOSIT:
                    await self._execute_deposit(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.INVESTMENT_CREATE:
                    await self._execute_investment_create(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.INVESTMENT_UPDATE:
                    await self._execute_investment_update(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.INVESTMENT_INCOME:
                    await self._execute_investment_income(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.INVESTMENT_INCREASE:
                    await self._execute_investment_increase(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.INVESTMENT_DECREASE:
                    await self._execute_investment_decrease(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.INVESTMENT_DELETE:
                    await self._execute_investment_delete(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.MEMBER_JOIN:
                    await self._execute_member_join(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.MEMBER_REMOVE:
                    await self._execute_member_remove(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.EXPENSE:
                    await self._execute_expense(locked_request, request_data)
                elif locked_request.request_type == ApprovalRequestType.DIVIDEND_CLAIM:
                    await self._execute_dividend_claim(locked_request, request_data)
                
                # 执行成功，savepoint会自动提交
                locked_request.executed_at = datetime.utcnow()
                locked_request.execution_failed = False
                locked_request.failure_reason = None
                logging.info(f"Approval request {locked_request.id} executed successfully")
                
            except ValueError as e:
                # 捕获业务逻辑异常（如余额不足、持仓不足等）
                # savepoint会自动回滚，不会保存任何业务数据
                error_msg = str(e)
                locked_request.executed_at = datetime.utcnow()
                locked_request.execution_failed = True
                locked_request.failure_reason = error_msg
                logging.warning(f"Approval request {locked_request.id} execution failed: {error_msg}")
                
            except Exception as e:
                # 捕获其他未预期的异常
                # savepoint会自动回滚
                error_msg = f"执行失败: {str(e)}"
                locked_request.executed_at = datetime.utcnow()
                locked_request.execution_failed = True
                locked_request.failure_reason = error_msg
                logging.error(f"Approval request {locked_request.id} execution error: {error_msg}", exc_info=True)
        
        # 在savepoint外部flush，确保执行状态被保存
        await self.db.flush()
    
    async def _execute_asset_create(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """
        执行资产登记（投资型资产）
        注意：活期资产(CASH)应通过 Deposit 接口创建，此处仅处理投资型资产
        支持多币种和汇率自动计算
        """
        from app.models.models import Asset, AssetType, CurrencyType, AssetPosition, PositionOperationType, Deposit, Transaction, TransactionType, User
        from app.services.exchange_rate import exchange_rate_service
        from app.services.asset_helper import get_cash_balance
        
        # 解析数据
        user_id = data.get("user_id")
        name = data.get("name")
        asset_type = AssetType(data.get("asset_type"))
        
        # 活期资产不应通过此接口创建
        if asset_type == AssetType.CASH:
            raise ValueError("活期资产应通过资金注入接口创建，不能在此登记")
        
        currency = CurrencyType(data.get("currency", "CNY"))
        expected_rate = data.get("expected_rate", 0.0)
        deduct_from_cash = data.get("deduct_from_cash", False)
        bank_name = data.get("bank_name")
        note = data.get("note")
        
        # 解析日期
        start_date = data.get("start_date")
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        
        end_date = data.get("end_date")
        if end_date and isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        # 计算CNY本金
        if currency == CurrencyType.CNY:
            principal_cny = data.get("amount")
            foreign_amount = None
            exchange_rate = 1.0
        else:
            # 外币：获取实时汇率
            foreign_amount = data.get("foreign_amount")
            exchange_rate = await exchange_rate_service.get_rate_to_cny(currency)
            principal_cny = foreign_amount * exchange_rate
            logging.info(f"Exchange rate for {currency.value}: 1 = ¥{exchange_rate}, {foreign_amount} = ¥{principal_cny}")
        
        # 处理活期余额变化
        cash_change = 0.0
        create_deposit_record = False
        
        if deduct_from_cash:
            # 从活期转入其他资产：减少活期余额
            current_cash = await get_cash_balance(self.db, request.family_id)
            if current_cash < principal_cny:
                raise ValueError(f"活期余额不足：需要¥{principal_cny:.2f}，当前仅有¥{current_cash:.2f}")
            cash_change = -principal_cny
            create_deposit_record = False  # 内部转换，不计入股权
        else:
            # 外部资金直接买入：不影响活期
            cash_change = 0.0
            create_deposit_record = True  # 外部注资，计入股权
        
        # 创建资产记录
        asset = Asset(
            family_id=request.family_id,
            user_id=user_id,
            name=name,
            investment_type=asset_type,
            currency=currency,
            foreign_amount=foreign_amount,
            exchange_rate=exchange_rate if currency != CurrencyType.CNY else None,
            principal=principal_cny,
            expected_rate=expected_rate,
            start_date=start_date,
            end_date=end_date,
            bank_name=bank_name,
            deduct_from_cash=deduct_from_cash,
            is_active=True,
            note=note
        )
        self.db.add(asset)
        await self.db.flush()
        
        logging.info(f"Asset created: id={asset.id}, type={asset_type.value}, currency={currency.value}, principal_cny={principal_cny}")
        
        # 创建 持仓记录
        position = AssetPosition(
            investment_id=asset.id,
            operation_type=PositionOperationType.CREATE,
            foreign_amount=foreign_amount,
            exchange_rate=exchange_rate if currency != CurrencyType.CNY else None,
            amount=principal_cny,
            principal_before=0,
            principal_after=principal_cny,
            operation_date=start_date
        )
        self.db.add(position)
        await self.db.flush()
        
        # 更新Transaction（仅在有活期变化时）
        if cash_change != 0:
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
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one()
            
            # 创建交易流水
            asset_type_names = {
                "cash": "活期现金",
                "time_deposit": "定期存款",
                "fund": "基金",
                "stock": "股票",
                "bond": "债券",
                "other": "其他"
            }
            asset_type_name = asset_type_names.get(asset_type.value, asset_type.value)
            
            if cash_change > 0:
                desc = f"{user.nickname}注入{asset_type_name} {name}"
            else:
                desc = f"{user.nickname}从活期转入{asset_type_name} {name}"
            
            transaction = Transaction(
                family_id=request.family_id,
                user_id=user_id,
                transaction_type=TransactionType.DEPOSIT if cash_change > 0 else TransactionType.WITHDRAW,
                amount=abs(cash_change),
                balance_after=current_balance + cash_change,
                description=desc,
                reference_id=asset.id,
                reference_type="asset_create"
            )
            self.db.add(transaction)
            await self.db.flush()
            
            # 关联交易ID到持仓记录
            position.transaction_id = transaction.id
        
        # 创建Deposit记录（用于股权计算）
        if create_deposit_record:
            deposit = Deposit(
                user_id=user_id,
                family_id=request.family_id,
                amount=principal_cny,
                deposit_date=start_date,
                note=f"资产登记: {name}"
            )
            self.db.add(deposit)
            await self.db.flush()
            
            # 关联存款ID到持仓记录
            position.deposit_id = deposit.id
            
            logging.info(f"Deposit record created for asset {asset.id}: user_id={user_id}, amount={principal_cny}")
        
        # 检查成就解锁（仅当创建Deposit记录时，即外部注资）
        if create_deposit_record:
            try:
                from app.services.achievement import AchievementService
                achievement_service = AchievementService(self.db)
                await achievement_service.check_and_unlock(
                    user_id,
                    context={"action": "deposit", "deposit_amount": principal_cny}
                )
            except Exception as e:
                logging.warning(f"Achievement check failed after asset create: {e}")
            
            # 宠物经验奖励
            try:
                from app.api.pet import grant_pet_exp
                exp_multiplier = max(1, int(principal_cny / 100))
                await grant_pet_exp(
                    self.db, request.family_id, "deposit", exp_multiplier,
                    operator_id=user_id,
                    source_detail=f"资产登记 {name}"
                )
            except Exception as e:
                logging.warning(f"Pet EXP grant failed after asset create: {e}")
    
    async def _execute_deposit(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行资金注入（注入家庭自由资金/活期）"""
        # 解析日期
        deposit_date = data.get("deposit_date")
        if isinstance(deposit_date, str):
            deposit_date = datetime.fromisoformat(deposit_date.replace("Z", "+00:00"))
        
        # 获取用户昵称
        result = await self.db.execute(
            select(User).where(User.id == request.requester_id)
        )
        user = result.scalar_one()
        
        # 1. 创建存款记录（用于股权计算）
        deposit = Deposit(
            user_id=request.requester_id,
            family_id=request.family_id,
            amount=request.amount,
            deposit_date=deposit_date,
            note=data.get("note")
        )
        self.db.add(deposit)
        await self.db.flush()
        
        # 2. 获取当前活期余额（Transaction.balance_after）
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.family_id == request.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0
        
        # 3. 创建交易流水（更新家庭活期余额）
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
        await self.db.flush()
        
        # 4. 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            await achievement_service.check_and_unlock(
                request.requester_id,
                context={"action": "deposit", "deposit_amount": request.amount}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after deposit: {e}")
        
        # 5. 宠物经验奖励：每100元存款 +1 EXP
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
        
        principal = data.get("principal")
        
        # 获取当前余额
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.family_id == request.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0
        
        # 检查余额是否足够
        if current_balance < principal:
            logging.error(f"Insufficient balance for investment create: current={current_balance}, required={principal}")
            raise ValueError(f"余额不足，当前余额: {current_balance}，需要: {principal}")
        
        logging.info(f"Creating investment: family_id={request.family_id}, name={data.get('name')}")
        
        now = datetime.utcnow()
        investment = Investment(
            family_id=request.family_id,
            name=data.get("name"),
            investment_type=InvestmentType(data.get("investment_type")),
            principal=principal,
            expected_rate=data.get("expected_rate"),
            start_date=start_date,
            end_date=end_date,
            note=data.get("note"),
            created_at=now,
            updated_at=now
        )
        self.db.add(investment)
        await self.db.flush()
        
        logging.info(f"Investment created: id={investment.id}, family_id={investment.family_id}")
        
        # 创建持仓记录
        position = InvestmentPosition(
            investment_id=investment.id,
            operation_type=PositionOperationType.CREATE,
            amount=principal,
            operation_date=start_date,
            note=f"创建投资: {investment.name}",
            approval_request_id=request.id,
            created_at=now
        )
        self.db.add(position)
        await self.db.flush()
        
        # 创建交易流水（从余额扣款）
        transaction = Transaction(
            family_id=request.family_id,
            user_id=request.requester_id,
            transaction_type=TransactionType.WITHDRAW,
            amount=-principal,
            balance_after=current_balance - principal,
            description=f"创建投资: {investment.name}",
            reference_id=investment.id,
            reference_type="investment_create"
        )
        self.db.add(transaction)
        await self.db.flush()
        
        # 关联交易ID到持仓记录
        position.transaction_id = transaction.id
        
        # 创建存款记录（记录权益贡献）
        deposit = Deposit(
            user_id=request.requester_id,
            family_id=request.family_id,
            amount=principal,
            deposit_date=start_date,
            note=f"投资本金: {investment.name}"
        )
        self.db.add(deposit)
        await self.db.flush()
        
        # 关联存款ID到持仓记录
        position.deposit_id = deposit.id
        
        logging.info(f"Position, Transaction, and Deposit created for investment {investment.id}")
        
        # 创建日历提醒（如果有到期日）
        try:
            if investment.end_date:
                await calendar_service.create_investment_reminder(
                    db=self.db,
                    family_id=request.family_id,
                    investment=investment,
                    created_by=request.requester_id
                )
                logging.info(f"Calendar reminder created for investment {investment.id}")
        except Exception as e:
            logging.warning(f"Calendar reminder creation failed after investment create: {e}")
        
        # 检查成就解锁（失败不影响主业务）
        try:
            from app.services.achievement import AchievementService
            achievement_service = AchievementService(self.db)
            await achievement_service.check_and_unlock(
                request.requester_id,
                context={"action": "investment_create", "principal": principal}
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
        
        # 更新日历提醒
        try:
            await calendar_service.update_investment_reminder(
                db=self.db,
                family_id=request.family_id,
                investment=investment,
                created_by=request.requester_id
            )
            logging.info(f"Calendar reminder updated for investment {investment.id}")
        except Exception as e:
            logging.warning(f"Calendar reminder update failed after investment update: {e}")
    
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
        
        # 判断是新模式（提供current_value）还是老模式（提供amount）
        current_value = data.get("current_value")
        amount = data.get("amount")
        
        if current_value is not None:
            # 新模式：记录当前价值，自动计算收益
            # 1. 计算当前持仓本金
            positions_result = await self.db.execute(
                select(InvestmentPosition).where(
                    InvestmentPosition.investment_id == investment_id
                )
            )
            positions = positions_result.scalars().all()
            current_principal = sum(
                p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
                else -p.amount
                for p in positions
            )
            
            # 2. 计算历史总收益
            incomes_result = await self.db.execute(
                select(InvestmentIncome).where(
                    InvestmentIncome.investment_id == investment_id
                )
            )
            incomes = incomes_result.scalars().all()
            historical_income = sum(
                inc.calculated_income if inc.calculated_income is not None else inc.amount
                for inc in incomes
            )
            
            # 3. 计算本次收益
            calculated_income = current_value - current_principal - historical_income
            
            # 创建收益记录（新模式）
            income = InvestmentIncome(
                investment_id=investment_id,
                amount=calculated_income,  # 存储计算出的收益
                current_value=current_value,
                calculated_income=calculated_income,
                income_date=income_date,
                note=data.get("note")
            )
            income_amount = calculated_income
        else:
            # 老模式：直接记录收益金额
            income = InvestmentIncome(
                investment_id=investment_id,
                amount=amount,
                income_date=income_date,
                note=data.get("note")
            )
            income_amount = amount
        
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
        
        # 创建交易流水（理财收益不影响家庭自由资金余额，仅作记录）
        transaction = Transaction(
            family_id=request.family_id,
            user_id=None,
            transaction_type=TransactionType.INCOME,
            amount=income_amount,
            balance_after=current_balance,  # 余额不变，收益留在理财产品中
            description=f"理财收益: {investment.name} +{income_amount}元",
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
                context={"action": "investment_income", "income_amount": income_amount}
            )
        except Exception as e:
            logging.warning(f"Achievement check failed after investment income: {e}")
        
        # 宠物经验奖励：每10元收益 +1 EXP
        try:
            from app.api.pet import grant_pet_exp
            exp_multiplier = max(1, int(income_amount / 10))  # 至少1点经验
            await grant_pet_exp(
                self.db, request.family_id, "investment", exp_multiplier,
                operator_id=request.requester_id,
                source_detail=f"理财收益 {investment.name} +¥{income_amount:.0f}"
            )
        except Exception as e:
            logging.warning(f"Pet EXP grant failed after investment income: {e}")
    
    async def _execute_investment_increase(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行投资增持"""
        investment_id = data.get("investment_id")
        result = await self.db.execute(
            select(Investment).where(
                Investment.id == investment_id,
                Investment.family_id == request.family_id,
                Investment.is_deleted == False
            )
        )
        investment = result.scalar_one_or_none()
        if not investment:
            logging.warning(f"Investment {investment_id} not found or deleted")
            return
        
        operation_date = data.get("operation_date")
        if isinstance(operation_date, str):
            operation_date = datetime.fromisoformat(operation_date.replace("Z", "+00:00"))
        
        amount = data.get("amount")
        
        # 获取当前余额
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.family_id == request.family_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        last_transaction = result.scalar_one_or_none()
        current_balance = last_transaction.balance_after if last_transaction else 0
        
        # 检查余额是否足够
        if current_balance < amount:
            logging.error(f"Insufficient balance for investment increase: current={current_balance}, required={amount}")
            raise ValueError(f"余额不足，当前余额: {current_balance}，需要: {amount}")
        
        now = datetime.utcnow()
        
        # 创建持仓记录
        position = InvestmentPosition(
            investment_id=investment_id,
            operation_type=PositionOperationType.INCREASE,
            amount=amount,
            operation_date=operation_date,
            note=data.get("note") or f"增持投资: {investment.name}",
            approval_request_id=request.id,
            created_at=now
        )
        self.db.add(position)
        await self.db.flush()
        
        # 创建交易流水（从余额扣款）
        transaction = Transaction(
            family_id=request.family_id,
            user_id=request.requester_id,
            transaction_type=TransactionType.WITHDRAW,
            amount=-amount,
            balance_after=current_balance - amount,
            description=f"投资增持: {investment.name}",
            reference_id=investment_id,
            reference_type="investment_increase"
        )
        self.db.add(transaction)
        await self.db.flush()
        position.transaction_id = transaction.id
        
        # 创建存款记录（增加权益贡献）
        deposit = Deposit(
            user_id=request.requester_id,
            family_id=request.family_id,
            amount=amount,
            deposit_date=operation_date,
            note=f"投资增持: {investment.name}"
        )
        self.db.add(deposit)
        await self.db.flush()
        position.deposit_id = deposit.id
        
        logging.info(f"Investment increase executed: investment_id={investment_id}, amount={amount}")
    
    async def _execute_investment_decrease(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行投资减持"""
        investment_id = data.get("investment_id")
        result = await self.db.execute(
            select(Investment).where(
                Investment.id == investment_id,
                Investment.family_id == request.family_id,
                Investment.is_deleted == False
            )
        )
        investment = result.scalar_one_or_none()
        if not investment:
            logging.warning(f"Investment {investment_id} not found or deleted")
            return
        
        operation_date = data.get("operation_date")
        if isinstance(operation_date, str):
            operation_date = datetime.fromisoformat(operation_date.replace("Z", "+00:00"))
        
        amount = data.get("amount")
        
        # 计算当前持仓本金
        positions_result = await self.db.execute(
            select(InvestmentPosition).where(
                InvestmentPosition.investment_id == investment_id
            )
        )
        positions = positions_result.scalars().all()
        current_principal = sum(
            p.amount if p.operation_type in [PositionOperationType.CREATE, PositionOperationType.INCREASE]
            else -p.amount
            for p in positions
        )
        
        # 检查减持金额是否超过持仓
        if amount > current_principal:
            logging.error(f"Decrease amount exceeds position: amount={amount}, current_principal={current_principal}")
            raise ValueError(f"减持金额超过当前持仓，当前持仓: {current_principal}，减持金额: {amount}")
        
        now = datetime.utcnow()
        
        # 创建持仓记录
        position = InvestmentPosition(
            investment_id=investment_id,
            operation_type=PositionOperationType.DECREASE,
            amount=amount,
            operation_date=operation_date,
            note=data.get("note") or f"减持投资: {investment.name}",
            approval_request_id=request.id,
            created_at=now
        )
        self.db.add(position)
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
        
        # 创建交易流水（返还到余额）
        transaction = Transaction(
            family_id=request.family_id,
            user_id=request.requester_id,
            transaction_type=TransactionType.INCOME,
            amount=amount,
            balance_after=current_balance + amount,
            description=f"投资减持: {investment.name}",
            reference_id=investment_id,
            reference_type="investment_decrease"
        )
        self.db.add(transaction)
        await self.db.flush()
        position.transaction_id = transaction.id
        
        # 创建负数存款记录（减少权益贡献）
        deposit = Deposit(
            user_id=request.requester_id,
            family_id=request.family_id,
            amount=-amount,
            deposit_date=operation_date,
            note=f"投资减持: {investment.name}"
        )
        self.db.add(deposit)
        await self.db.flush()
        position.deposit_id = deposit.id
        
        logging.info(f"Investment decrease executed: investment_id={investment_id}, amount={amount}")
    
    async def _execute_investment_delete(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """执行删除投资产品（软删除）"""
        investment_id = data.get("investment_id")
        result = await self.db.execute(
            select(Investment).where(
                Investment.id == investment_id,
                Investment.family_id == request.family_id
            )
        )
        investment = result.scalar_one_or_none()
        if not investment:
            logging.warning(f"Investment {investment_id} not found")
            return
        
        # 软删除
        investment.is_deleted = True
        investment.deleted_at = datetime.utcnow()
        
        logging.info(f"Investment soft deleted: id={investment_id}, name={investment.name}")
    
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
    
    async def _execute_dividend_claim(self, request: ApprovalRequest, data: Dict[str, Any]) -> None:
        """
        执行分红领取处理
        处理用户对分红的选择（再投或提现）
        """
        from app.services.dividend import process_dividend_claim
        
        claim_id = data.get("claim_id")
        reinvest = data.get("reinvest", False)  # 默认提现
        
        if not claim_id:
            raise ValueError("缺少分红领取记录ID")
        
        # 调用分红服务处理
        await process_dividend_claim(
            claim_id=claim_id,
            reinvest=reinvest,
            user_id=request.target_user_id or request.requester_id,
            db=self.db
        )
