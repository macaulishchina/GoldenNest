"""
小金库 (Golden Nest) - 记账系统 API
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    User, Family, FamilyMember, AccountingEntry, AccountingCategory,
    AccountingEntrySource, ExpenseRequest, ExpenseStatus
)
from app.schemas.accounting import (
    AccountingEntryCreate, AccountingEntryPhotoCreate, AccountingEntryVoiceCreate,
    AccountingEntryImport, AccountingEntryUpdate, AccountingEntryResponse,
    AccountingEntryListResponse, AccountingPhotoOCRResponse, AccountingVoiceTranscriptResponse,
    AccountingBatchExpenseRequest, AccountingStatsResponse, AccountingCategoryStatsResponse
)
from app.services.ai_accounting import parse_receipt_image, transcribe_voice, categorize_entry

router = APIRouter()

# 分类名称映射
CATEGORY_NAMES = {
    "food": "餐饮",
    "transport": "交通",
    "shopping": "购物",
    "entertainment": "娱乐",
    "healthcare": "医疗",
    "education": "教育",
    "housing": "住房",
    "utilities": "水电煤",
    "other": "其他"
}


async def get_user_family(current_user: User, db: AsyncSession) -> tuple[Family, FamilyMember]:
    """获取用户的家庭信息"""
    result = await db.execute(
        select(FamilyMember)
        .options(selectinload(FamilyMember.family))
        .where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您还未加入任何家庭"
        )

    return membership.family, membership


@router.post("/entry", response_model=AccountingEntryResponse)
async def create_entry(
    entry_data: AccountingEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动创建记账条目"""
    family, _ = await get_user_family(current_user, db)

    # 验证分类
    try:
        category_enum = AccountingCategory(entry_data.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的分类: {entry_data.category}"
        )

    # 验证消费人（如果指定）
    if entry_data.consumer_id:
        consumer_result = await db.execute(
            select(FamilyMember).where(
                and_(
                    FamilyMember.user_id == entry_data.consumer_id,
                    FamilyMember.family_id == family.id
                )
            )
        )
        if not consumer_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定的消费人不是家庭成员"
            )

    # 创建记账条目
    new_entry = AccountingEntry(
        family_id=family.id,
        user_id=current_user.id,
        consumer_id=entry_data.consumer_id,
        amount=entry_data.amount,
        category=category_enum,
        description=entry_data.description,
        entry_date=entry_data.entry_date,
        source=AccountingEntrySource.MANUAL
    )

    db.add(new_entry)
    await db.flush()
    await db.refresh(new_entry)

    # 构造响应
    response = AccountingEntryResponse(
        id=new_entry.id,
        family_id=new_entry.family_id,
        user_id=new_entry.user_id,
        consumer_id=new_entry.consumer_id,
        amount=new_entry.amount,
        category=new_entry.category.value,
        description=new_entry.description,
        entry_date=new_entry.entry_date,
        source=new_entry.source.value,
        is_accounted=new_entry.is_accounted,
        expense_request_id=new_entry.expense_request_id,
        created_at=new_entry.created_at,
        user_nickname=current_user.nickname
    )

    # 获取消费人昵称
    if new_entry.consumer_id:
        consumer_result = await db.execute(
            select(User).where(User.id == new_entry.consumer_id)
        )
        consumer = consumer_result.scalar_one_or_none()
        if consumer:
            response.consumer_nickname = consumer.nickname

    return response


@router.post("/photo", response_model=AccountingEntryResponse)
async def create_entry_from_photo(
    photo_data: AccountingEntryPhotoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """拍照识别创建记账条目"""
    family, _ = await get_user_family(current_user, db)

    # AI识别小票信息
    try:
        ocr_result = await parse_receipt_image(photo_data.image_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR识别失败: {str(e)}"
        )

    # 验证分类
    try:
        category_enum = AccountingCategory(ocr_result.category)
    except ValueError:
        category_enum = AccountingCategory.OTHER

    # 创建记账条目
    new_entry = AccountingEntry(
        family_id=family.id,
        user_id=current_user.id,
        consumer_id=None,  # 拍照识别默认为空（家庭共同消费）
        amount=ocr_result.amount,
        category=category_enum,
        description=ocr_result.description,
        entry_date=photo_data.entry_date or datetime.now(),
        source=AccountingEntrySource.PHOTO,
        image_data=photo_data.image_data
    )

    db.add(new_entry)
    await db.flush()
    await db.refresh(new_entry)

    return AccountingEntryResponse(
        id=new_entry.id,
        family_id=new_entry.family_id,
        user_id=new_entry.user_id,
        consumer_id=new_entry.consumer_id,
        amount=new_entry.amount,
        category=new_entry.category.value,
        description=new_entry.description,
        entry_date=new_entry.entry_date,
        source=new_entry.source.value,
        image_data=new_entry.image_data,
        is_accounted=new_entry.is_accounted,
        expense_request_id=new_entry.expense_request_id,
        created_at=new_entry.created_at,
        user_nickname=current_user.nickname
    )


@router.post("/voice", response_model=AccountingEntryResponse)
async def create_entry_from_voice(
    voice_data: AccountingEntryVoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """语音输入创建记账条目"""
    family, _ = await get_user_family(current_user, db)

    # AI转录语音
    try:
        voice_result = await transcribe_voice(voice_data.audio_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语音识别失败: {str(e)}"
        )

    # 验证分类
    try:
        category_enum = AccountingCategory(voice_result.category)
    except ValueError:
        category_enum = AccountingCategory.OTHER

    # 创建记账条目
    new_entry = AccountingEntry(
        family_id=family.id,
        user_id=current_user.id,
        consumer_id=None,  # 语音识别默认为空（家庭共同消费）
        amount=voice_result.amount,
        category=category_enum,
        description=voice_result.description,
        entry_date=voice_data.entry_date or datetime.now(),
        source=AccountingEntrySource.VOICE
    )

    db.add(new_entry)
    await db.flush()
    await db.refresh(new_entry)

    return AccountingEntryResponse(
        id=new_entry.id,
        family_id=new_entry.family_id,
        user_id=new_entry.user_id,
        consumer_id=new_entry.consumer_id,
        amount=new_entry.amount,
        category=new_entry.category.value,
        description=new_entry.description,
        entry_date=new_entry.entry_date,
        source=new_entry.source.value,
        is_accounted=new_entry.is_accounted,
        expense_request_id=new_entry.expense_request_id,
        created_at=new_entry.created_at,
        user_nickname=current_user.nickname
    )


@router.post("/import", response_model=AccountingEntryListResponse)
async def import_entries(
    import_data: AccountingEntryImport,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量导入记账条目"""
    family, _ = await get_user_family(current_user, db)

    created_entries = []

    for entry_data in import_data.entries:
        # 验证分类
        try:
            category_enum = AccountingCategory(entry_data.category)
        except ValueError:
            continue  # 跳过无效分类的条目

        # 验证消费人（如果指定）
        if entry_data.consumer_id:
            consumer_result = await db.execute(
                select(FamilyMember).where(
                    and_(
                        FamilyMember.user_id == entry_data.consumer_id,
                        FamilyMember.family_id == family.id
                    )
                )
            )
            if not consumer_result.scalar_one_or_none():
                continue  # 跳过无效消费人的条目

        # 创建记账条目
        new_entry = AccountingEntry(
            family_id=family.id,
            user_id=current_user.id,
            consumer_id=entry_data.consumer_id,
            amount=entry_data.amount,
            category=category_enum,
            description=entry_data.description,
            entry_date=entry_data.entry_date,
            source=AccountingEntrySource.IMPORT
        )

        db.add(new_entry)
        created_entries.append(new_entry)

    await db.flush()

    # 构造响应
    response_entries = []
    for entry in created_entries:
        await db.refresh(entry)

        entry_response = AccountingEntryResponse(
            id=entry.id,
            family_id=entry.family_id,
            user_id=entry.user_id,
            consumer_id=entry.consumer_id,
            amount=entry.amount,
            category=entry.category.value,
            description=entry.description,
            entry_date=entry.entry_date,
            source=entry.source.value,
            is_accounted=entry.is_accounted,
            expense_request_id=entry.expense_request_id,
            created_at=entry.created_at,
            user_nickname=current_user.nickname
        )

        # 获取消费人昵称
        if entry.consumer_id:
            consumer_result = await db.execute(
                select(User).where(User.id == entry.consumer_id)
            )
            consumer = consumer_result.scalar_one_or_none()
            if consumer:
                entry_response.consumer_nickname = consumer.nickname

        response_entries.append(entry_response)

    return AccountingEntryListResponse(
        total=len(response_entries),
        page=1,
        page_size=len(response_entries),
        entries=response_entries
    )


@router.get("/list", response_model=AccountingEntryListResponse)
async def list_entries(
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    is_accounted: Optional[bool] = None,
    consumer_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取记账条目列表（支持筛选）"""
    family, _ = await get_user_family(current_user, db)

    # 构建查询条件
    conditions = [AccountingEntry.family_id == family.id]

    if category:
        try:
            category_enum = AccountingCategory(category)
            conditions.append(AccountingEntry.category == category_enum)
        except ValueError:
            pass

    if is_accounted is not None:
        conditions.append(AccountingEntry.is_accounted == is_accounted)

    if consumer_id is not None:
        if consumer_id == 0:
            # 0表示查询家庭共同消费（consumer_id为空）
            conditions.append(AccountingEntry.consumer_id.is_(None))
        else:
            conditions.append(AccountingEntry.consumer_id == consumer_id)

    if start_date:
        conditions.append(AccountingEntry.entry_date >= start_date)

    if end_date:
        conditions.append(AccountingEntry.entry_date <= end_date)

    # 查询总数
    count_result = await db.execute(
        select(func.count(AccountingEntry.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    # 查询列表
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AccountingEntry)
        .where(and_(*conditions))
        .order_by(desc(AccountingEntry.entry_date), desc(AccountingEntry.created_at))
        .limit(page_size)
        .offset(offset)
    )
    entries = result.scalars().all()

    # 构造响应
    response_entries = []
    for entry in entries:
        # 获取记账人昵称
        user_result = await db.execute(
            select(User).where(User.id == entry.user_id)
        )
        user = user_result.scalar_one_or_none()

        entry_response = AccountingEntryResponse(
            id=entry.id,
            family_id=entry.family_id,
            user_id=entry.user_id,
            consumer_id=entry.consumer_id,
            amount=entry.amount,
            category=entry.category.value,
            description=entry.description,
            entry_date=entry.entry_date,
            source=entry.source.value,
            image_data=entry.image_data,
            is_accounted=entry.is_accounted,
            expense_request_id=entry.expense_request_id,
            created_at=entry.created_at,
            user_nickname=user.nickname if user else None
        )

        # 获取消费人昵称
        if entry.consumer_id:
            consumer_result = await db.execute(
                select(User).where(User.id == entry.consumer_id)
            )
            consumer = consumer_result.scalar_one_or_none()
            if consumer:
                entry_response.consumer_nickname = consumer.nickname

        response_entries.append(entry_response)

    return AccountingEntryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        entries=response_entries
    )


@router.get("/{entry_id}", response_model=AccountingEntryResponse)
async def get_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个记账条目详情"""
    family, _ = await get_user_family(current_user, db)

    result = await db.execute(
        select(AccountingEntry).where(
            and_(
                AccountingEntry.id == entry_id,
                AccountingEntry.family_id == family.id
            )
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记账条目不存在"
        )

    # 获取记账人昵称
    user_result = await db.execute(
        select(User).where(User.id == entry.user_id)
    )
    user = user_result.scalar_one_or_none()

    response = AccountingEntryResponse(
        id=entry.id,
        family_id=entry.family_id,
        user_id=entry.user_id,
        consumer_id=entry.consumer_id,
        amount=entry.amount,
        category=entry.category.value,
        description=entry.description,
        entry_date=entry.entry_date,
        source=entry.source.value,
        image_data=entry.image_data,
        is_accounted=entry.is_accounted,
        expense_request_id=entry.expense_request_id,
        created_at=entry.created_at,
        user_nickname=user.nickname if user else None
    )

    # 获取消费人昵称
    if entry.consumer_id:
        consumer_result = await db.execute(
            select(User).where(User.id == entry.consumer_id)
        )
        consumer = consumer_result.scalar_one_or_none()
        if consumer:
            response.consumer_nickname = consumer.nickname

    return response


@router.put("/{entry_id}", response_model=AccountingEntryResponse)
async def update_entry(
    entry_id: int,
    update_data: AccountingEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新记账条目"""
    family, _ = await get_user_family(current_user, db)

    result = await db.execute(
        select(AccountingEntry).where(
            and_(
                AccountingEntry.id == entry_id,
                AccountingEntry.family_id == family.id
            )
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记账条目不存在"
        )

    # 已入账的条目不允许修改
    if entry.is_accounted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已入账的条目不能修改"
        )

    # 更新字段
    if update_data.amount is not None:
        entry.amount = update_data.amount

    if update_data.category is not None:
        try:
            category_enum = AccountingCategory(update_data.category)
            entry.category = category_enum
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的分类: {update_data.category}"
            )

    if update_data.description is not None:
        entry.description = update_data.description

    if update_data.entry_date is not None:
        entry.entry_date = update_data.entry_date

    if update_data.consumer_id is not None:
        # 验证消费人
        if update_data.consumer_id > 0:
            consumer_result = await db.execute(
                select(FamilyMember).where(
                    and_(
                        FamilyMember.user_id == update_data.consumer_id,
                        FamilyMember.family_id == family.id
                    )
                )
            )
            if not consumer_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定的消费人不是家庭成员"
                )
            entry.consumer_id = update_data.consumer_id
        else:
            entry.consumer_id = None

    await db.flush()
    await db.refresh(entry)

    # 获取昵称
    user_result = await db.execute(
        select(User).where(User.id == entry.user_id)
    )
    user = user_result.scalar_one_or_none()

    response = AccountingEntryResponse(
        id=entry.id,
        family_id=entry.family_id,
        user_id=entry.user_id,
        consumer_id=entry.consumer_id,
        amount=entry.amount,
        category=entry.category.value,
        description=entry.description,
        entry_date=entry.entry_date,
        source=entry.source.value,
        image_data=entry.image_data,
        is_accounted=entry.is_accounted,
        expense_request_id=entry.expense_request_id,
        created_at=entry.created_at,
        user_nickname=user.nickname if user else None
    )

    if entry.consumer_id:
        consumer_result = await db.execute(
            select(User).where(User.id == entry.consumer_id)
        )
        consumer = consumer_result.scalar_one_or_none()
        if consumer:
            response.consumer_nickname = consumer.nickname

    return response


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除记账条目"""
    family, _ = await get_user_family(current_user, db)

    result = await db.execute(
        select(AccountingEntry).where(
            and_(
                AccountingEntry.id == entry_id,
                AccountingEntry.family_id == family.id
            )
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记账条目不存在"
        )

    # 已入账的条目不允许删除
    if entry.is_accounted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已入账的条目不能删除"
        )

    await db.delete(entry)

    return {"message": "删除成功"}


@router.post("/batch-expense")
async def batch_create_expense(
    batch_data: AccountingBatchExpenseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量将记账条目转为支出申请"""
    family, membership = await get_user_family(current_user, db)

    # 查询所有待转换的条目
    result = await db.execute(
        select(AccountingEntry).where(
            and_(
                AccountingEntry.id.in_(batch_data.entry_ids),
                AccountingEntry.family_id == family.id,
                AccountingEntry.is_accounted == False
            )
        )
    )
    entries = result.scalars().all()

    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有找到可转换的记账条目"
        )

    # 计算总金额
    total_amount = sum(entry.amount for entry in entries)

    # 创建支出申请
    description = batch_data.description or "批量记账入账"
    expense_request = ExpenseRequest(
        family_id=family.id,
        requester_id=current_user.id,
        title=batch_data.title,
        description=description,
        amount=total_amount,
        status=ExpenseStatus.PENDING
    )

    db.add(expense_request)
    await db.flush()
    await db.refresh(expense_request)

    # 更新记账条目状态
    for entry in entries:
        entry.is_accounted = True
        entry.expense_request_id = expense_request.id

    return {
        "message": "批量入账成功",
        "expense_request_id": expense_request.id,
        "total_amount": total_amount,
        "entry_count": len(entries)
    }


@router.get("/stats/summary", response_model=AccountingStatsResponse)
async def get_accounting_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取记账统计信息"""
    family, _ = await get_user_family(current_user, db)

    # 构建查询条件
    conditions = [AccountingEntry.family_id == family.id]

    if start_date:
        conditions.append(AccountingEntry.entry_date >= start_date)

    if end_date:
        conditions.append(AccountingEntry.entry_date <= end_date)

    # 查询总计
    total_result = await db.execute(
        select(
            func.sum(AccountingEntry.amount),
            func.count(AccountingEntry.id)
        ).where(and_(*conditions))
    )
    total_row = total_result.one()
    total_amount = float(total_row[0] or 0)
    total_count = total_row[1] or 0

    # 查询已入账
    accounted_conditions = conditions + [AccountingEntry.is_accounted == True]
    accounted_result = await db.execute(
        select(
            func.sum(AccountingEntry.amount),
            func.count(AccountingEntry.id)
        ).where(and_(*accounted_conditions))
    )
    accounted_row = accounted_result.one()
    accounted_amount = float(accounted_row[0] or 0)
    accounted_count = accounted_row[1] or 0

    # 未入账
    unaccounted_amount = total_amount - accounted_amount
    unaccounted_count = total_count - accounted_count

    # 分类统计
    category_result = await db.execute(
        select(
            AccountingEntry.category,
            func.sum(AccountingEntry.amount),
            func.count(AccountingEntry.id)
        )
        .where(and_(*conditions))
        .group_by(AccountingEntry.category)
    )

    category_stats = []
    for row in category_result:
        category = row[0]
        category_amount = float(row[1])
        category_count = row[2]
        percentage = (category_amount / total_amount * 100) if total_amount > 0 else 0

        category_stats.append(AccountingCategoryStatsResponse(
            category=category.value,
            category_name=CATEGORY_NAMES.get(category.value, category.value),
            total_amount=category_amount,
            count=category_count,
            percentage=round(percentage, 2)
        ))

    # 按金额排序
    category_stats.sort(key=lambda x: x.total_amount, reverse=True)

    return AccountingStatsResponse(
        total_amount=total_amount,
        total_count=total_count,
        accounted_amount=accounted_amount,
        accounted_count=accounted_count,
        unaccounted_amount=unaccounted_amount,
        unaccounted_count=unaccounted_count,
        category_stats=category_stats
    )
