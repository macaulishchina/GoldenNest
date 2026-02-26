"""
小金库 (Golden Nest) - 记账系统 API
"""
from datetime import datetime
from typing import Optional, List
import base64
import json
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, func, and_, or_, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import UPLOAD_DIR
from app.models.models import (
    User, Family, FamilyMember, AccountingEntry, AccountingCategory,
    AccountingEntrySource, Transaction, TransactionType, AccountingAIReport
)
from app.schemas.accounting import (
    AccountingEntryCreate, AccountingEntryPhotoCreate, AccountingEntryVoiceCreate,
    AccountingEntryImport, AccountingEntryUpdate, AccountingEntryResponse,
    AccountingEntryListResponse, AccountingPhotoOCRResponse, AccountingVoiceTranscriptResponse,
    AccountingBatchExpenseRequest, AccountingStatsResponse, AccountingCategoryStatsResponse,
    DuplicateCheckRequest, DuplicateCheckResponse, DuplicateCheckResult, DuplicateMatch, DuplicateMatchLevel,
    PhotoRecognizeResponse, PhotoRecognizeItem, PhotoCreateRequest,
)
from app.services.ai_accounting import parse_receipt_images, transcribe_voice, categorize_entry, check_duplicate_with_ai, transcribe_audio_file, parse_voice_text, parse_import_file
from app.services.ai_service import ai_service

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

    # 确定来源
    entry_source = AccountingEntrySource.MANUAL
    if hasattr(entry_data, 'source') and entry_data.source:
        try:
            entry_source = AccountingEntrySource(entry_data.source)
        except ValueError:
            pass  # 无效来源，使用默认 MANUAL

    # 创建记账条目
    new_entry = AccountingEntry(
        family_id=family.id,
        user_id=current_user.id,
        consumer_id=entry_data.consumer_id if entry_data.consumer_id != 0 else None,
        amount=entry_data.amount,
        category=category_enum,
        description=entry_data.description,
        entry_date=entry_data.entry_date,
        source=entry_source
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


@router.post("/photo/recognize", response_model=PhotoRecognizeResponse)
async def recognize_photos(
    files: List[UploadFile] = File(..., description="消费凭证图片（支持多张）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传图片并AI识别消费信息（仅识别，不创建记录）"""
    family, _ = await get_user_family(current_user, db)

    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")

    image_b64_list = []
    image_paths = []

    for file in files:
        img_bytes = await file.read()

        # 保存图片到文件
        ext = (file.filename or "").rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        image_paths.append(f"/uploads/receipts/{filename}")

        # 转为base64供AI识别
        img_b64 = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
        image_b64_list.append(img_b64)

    # AI识别
    try:
        items = await parse_receipt_images(image_b64_list)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI识别失败: {str(e)}"
        )

    return PhotoRecognizeResponse(items=items, image_paths=image_paths)


@router.post("/photo/create", response_model=AccountingEntryListResponse)
async def create_entries_from_photos(
    request: PhotoCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """根据确认后的识别结果批量创建记账条目"""
    family, _ = await get_user_family(current_user, db)

    created_entries = []
    # 将图片路径关联到第一条记录（如果有）
    first_image = request.image_paths[0] if request.image_paths else None

    for idx, item in enumerate(request.items):
        if item.amount <= 0:
            continue

        # 验证分类
        try:
            category_enum = AccountingCategory(item.category)
        except ValueError:
            category_enum = AccountingCategory.OTHER

        # 解析日期
        parsed_date = datetime.now()
        if item.entry_date:
            try:
                parsed_date = datetime.fromisoformat(item.entry_date.replace('Z', '+00:00'))
            except ValueError:
                pass

        # 第一条关联图片，其余条不重复关联
        image_data = first_image if idx == 0 and first_image else None

        new_entry = AccountingEntry(
            family_id=family.id,
            user_id=current_user.id,
            consumer_id=current_user.id,
            amount=item.amount,
            category=category_enum,
            description=item.description,
            entry_date=parsed_date,
            source=AccountingEntrySource.PHOTO,
            image_data=image_data,
        )
        db.add(new_entry)
        created_entries.append(new_entry)

    if not created_entries:
        raise HTTPException(status_code=400, detail="没有有效的消费记录可创建")

    await db.flush()

    response_entries = []
    for entry in created_entries:
        await db.refresh(entry)
        response_entries.append(AccountingEntryResponse(
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
            has_image=bool(entry.image_data),
            is_accounted=entry.is_accounted,
            expense_request_id=entry.expense_request_id,
            created_at=entry.created_at,
            user_nickname=current_user.nickname,
        ))

    return AccountingEntryListResponse(
        total=len(response_entries),
        page=1,
        page_size=len(response_entries),
        entries=response_entries,
    )


# ==================== 语音识别 ====================

@router.post("/voice/recognize")
async def voice_recognize(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    语音识别：上传音频文件 → Whisper转录 → AI解析为记账条目
    """
    # 读取音频文件
    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="音频文件为空")
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25MB limit
        raise HTTPException(status_code=400, detail="音频文件过大，请控制在25MB以内")

    filename = file.filename or "audio.webm"

    try:
        # 1. Whisper 转录
        transcript = await transcribe_audio_file(audio_bytes, filename)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"语音转录失败: {str(e)}"
        )

    if not transcript.strip():
        return {"transcript": "", "items": []}

    try:
        # 2. AI 解析文本 → 结构化条目
        items = await parse_voice_text(transcript)
    except Exception as e:
        # 解析失败仍返回转录文本，前端可手动输入
        return {"transcript": transcript, "items": []}

    return {
        "transcript": transcript,
        "items": [item.dict() for item in items],
    }


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

    # 验证金额
    if not voice_result.amount or voice_result.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="未能从语音中识别出有效金额，请手动输入"
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


@router.post("/import/file")
async def import_file_parse(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    上传文件（Excel/CSV/PDF/图片）并解析为记账条目。
    返回解析结果供用户确认后再创建。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 检查文件大小（最大 20MB）
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，请控制在20MB以内")

    # 检查文件类型
    allowed_exts = {"xlsx", "xls", "csv", "pdf", "jpg", "jpeg", "png", "gif", "bmp", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 .{ext}，支持：Excel(.xlsx/.xls)、CSV、PDF、图片(.jpg/.png)"
        )

    try:
        items = await parse_import_file(file_bytes, file.filename)
        return {
            "items": [item.dict() for item in items],
            "count": len(items),
            "filename": file.filename,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)[:200]}")


@router.get("/list", response_model=AccountingEntryListResponse)
async def list_entries(
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    is_accounted: Optional[bool] = None,
    consumer_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取记账条目列表（支持筛选和模糊搜索）"""
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

    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                AccountingEntry.description.ilike(search_pattern),
                cast(AccountingEntry.amount, String).like(search_pattern)
            )
        )

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
            image_data=None,  # 列表不返回图片数据，减少传输
            has_image=bool(entry.image_data),
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
        has_image=bool(entry.image_data),
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
        has_image=bool(entry.image_data),
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
    """批量将记账条目直接转为消费记录（资金流水）"""
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

    # 获取当前余额（仅用于记录，不扣减）
    last_txn_result = await db.execute(
        select(Transaction)
        .where(Transaction.family_id == family.id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    last_transaction = last_txn_result.scalar_one_or_none()
    current_balance = last_transaction.balance_after if last_transaction else 0

    # 构建描述（含时间范围）
    description = batch_data.description or "批量记账入账"
    entry_descs = [f"{e.description}(¥{e.amount})" for e in entries]

    # 计算入账记录覆盖的时间范围
    entry_dates = [e.entry_date for e in entries if e.entry_date]
    if entry_dates:
        min_date = min(entry_dates)
        max_date = max(entry_dates)
        date_range_str = f"【{min_date.strftime('%Y-%m-%d %H:%M')} ~ {max_date.strftime('%Y-%m-%d %H:%M')}】"
    else:
        date_range_str = ""

    full_description = f"{description}{date_range_str}: {', '.join(entry_descs)}"

    # 创建日常消费流水记录（不影响家庭自由资金余额）
    transaction = Transaction(
        family_id=family.id,
        user_id=current_user.id,
        transaction_type=TransactionType.DAILY_EXPENSE,
        amount=-total_amount,
        balance_after=current_balance,  # 余额不变
        description=full_description,
        reference_type="accounting_batch"
    )

    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)

    # 更新记账条目状态
    for entry in entries:
        entry.is_accounted = True

    return {
        "message": "批量入账成功，已记录到资金流水",
        "transaction_id": transaction.id,
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


@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates(
    check_data: DuplicateCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    检查待记账条目是否与已有记录重复

    检测逻辑：
    1. 完全匹配（exact）：时间相差<5分钟 且 金额完全相同 → 自动标记为重复
    2. 很可能重复（likely）：时间相差<1小时 且 金额相同 且 AI相似度>0.8
    3. 可能重复（possible）：时间相差<24小时 且 金额相同 → AI判断
    4. 不重复（unique）：无匹配项
    """
    family, _ = await get_user_family(current_user, db)

    results = []
    exact_count = 0
    likely_count = 0
    possible_count = 0
    unique_count = 0

    for index, entry_data in enumerate(check_data.entries):
        # 查询可能重复的记录（同一家庭，金额相同或接近，时间在24小时内）
        from datetime import timedelta

        # 确保 entry_date 为 naive datetime（数据库存储的是 naive datetime）
        check_date = entry_data.entry_date.replace(tzinfo=None) if entry_data.entry_date.tzinfo else entry_data.entry_date

        time_window_start = check_date - timedelta(hours=24)
        time_window_end = check_date + timedelta(hours=24)

        # 金额允许0.1元的误差
        amount_min = entry_data.amount - 0.1
        amount_max = entry_data.amount + 0.1

        query_result = await db.execute(
            select(AccountingEntry)
            .where(
                and_(
                    AccountingEntry.family_id == family.id,
                    AccountingEntry.entry_date >= time_window_start,
                    AccountingEntry.entry_date <= time_window_end,
                    AccountingEntry.amount >= amount_min,
                    AccountingEntry.amount <= amount_max
                )
            )
            .order_by(AccountingEntry.entry_date.desc())
            .limit(10)  # 最多检查10条可能重复的记录
        )
        existing_entries = query_result.scalars().all()

        if not existing_entries:
            # 没有找到可能重复的记录
            results.append(DuplicateCheckResult(
                index=index,
                entry_data=entry_data,
                is_duplicate=False,
                match_level=DuplicateMatchLevel.UNIQUE,
                duplicates=[]
            ))
            unique_count += 1
            continue

        # 检测重复级别
        duplicates = []
        max_match_level = DuplicateMatchLevel.UNIQUE

        for existing_entry in existing_entries:
            time_diff = abs((check_date - existing_entry.entry_date).total_seconds())
            amount_diff = abs(entry_data.amount - existing_entry.amount)

            match_reasons = []
            similarity_score = 0.0
            match_level = DuplicateMatchLevel.UNIQUE

            # 1. 完全匹配检测（时间<5分钟 且 金额完全相同）
            if time_diff < 300 and amount_diff < 0.01:
                match_level = DuplicateMatchLevel.EXACT
                similarity_score = 1.0
                match_reasons.append("时间和金额完全匹配")

                # 如果描述也相似，提高置信度
                if entry_data.description.lower() == existing_entry.description.lower():
                    match_reasons.append("描述完全相同")
                elif entry_data.description.lower() in existing_entry.description.lower() or \
                     existing_entry.description.lower() in entry_data.description.lower():
                    match_reasons.append("描述包含关系")

            # 2. 很可能重复（时间<1小时 且 金额相同）
            elif time_diff < 3600 and amount_diff < 0.01:
                # 使用AI判断
                ai_similarity, ai_reason = await check_duplicate_with_ai(
                    entry_data.description,
                    entry_data.amount,
                    entry_data.category,
                    existing_entry.description,
                    existing_entry.amount,
                    existing_entry.category.value
                )

                similarity_score = ai_similarity

                if ai_similarity >= 0.8:
                    match_level = DuplicateMatchLevel.LIKELY
                    match_reasons.append(f"时间相近（{int(time_diff/60)}分钟内）")
                    match_reasons.append(f"金额相同（¥{entry_data.amount}）")
                    match_reasons.append(f"AI判断：{ai_reason}")
                elif ai_similarity >= 0.5:
                    match_level = DuplicateMatchLevel.POSSIBLE
                    match_reasons.append(f"时间较近（{int(time_diff/60)}分钟内）")
                    match_reasons.append(f"金额相同")
                    match_reasons.append(f"AI判断：{ai_reason}")

            # 3. 可能重复（时间<24小时 且 金额相同）
            elif time_diff < 86400 and amount_diff < 0.01:
                # 使用AI判断，但相似度要求更高
                ai_similarity, ai_reason = await check_duplicate_with_ai(
                    entry_data.description,
                    entry_data.amount,
                    entry_data.category,
                    existing_entry.description,
                    existing_entry.amount,
                    existing_entry.category.value
                )

                similarity_score = ai_similarity

                if ai_similarity >= 0.7:
                    match_level = DuplicateMatchLevel.POSSIBLE
                    match_reasons.append(f"金额相同（¥{entry_data.amount}）")
                    match_reasons.append(f"时间相差{int(time_diff/3600)}小时")
                    match_reasons.append(f"AI判断：{ai_reason}")

            # 如果匹配，添加到重复列表
            if match_level != DuplicateMatchLevel.UNIQUE:
                # 获取用户昵称
                user_result = await db.execute(
                    select(User).where(User.id == existing_entry.user_id)
                )
                user = user_result.scalar_one_or_none()

                consumer_nickname = None
                if existing_entry.consumer_id:
                    consumer_result = await db.execute(
                        select(User).where(User.id == existing_entry.consumer_id)
                    )
                    consumer = consumer_result.scalar_one_or_none()
                    if consumer:
                        consumer_nickname = consumer.nickname

                entry_response = AccountingEntryResponse(
                    id=existing_entry.id,
                    family_id=existing_entry.family_id,
                    user_id=existing_entry.user_id,
                    consumer_id=existing_entry.consumer_id,
                    amount=existing_entry.amount,
                    category=existing_entry.category.value,
                    description=existing_entry.description,
                    entry_date=existing_entry.entry_date,
                    source=existing_entry.source.value,
                    image_data=existing_entry.image_data,
                    is_accounted=existing_entry.is_accounted,
                    expense_request_id=existing_entry.expense_request_id,
                    created_at=existing_entry.created_at,
                    user_nickname=user.nickname if user else None,
                    consumer_nickname=consumer_nickname
                )

                duplicates.append(DuplicateMatch(
                    existing_entry_id=existing_entry.id,
                    existing_entry=entry_response,
                    match_level=match_level,
                    similarity_score=similarity_score,
                    match_reasons=match_reasons
                ))

                # 更新最高匹配级别
                level_priority = {
                    DuplicateMatchLevel.EXACT: 4,
                    DuplicateMatchLevel.LIKELY: 3,
                    DuplicateMatchLevel.POSSIBLE: 2,
                    DuplicateMatchLevel.UNIQUE: 1
                }
                if level_priority.get(match_level, 0) > level_priority.get(max_match_level, 0):
                    max_match_level = match_level

        # 添加检测结果
        is_duplicate = len(duplicates) > 0
        results.append(DuplicateCheckResult(
            index=index,
            entry_data=entry_data,
            is_duplicate=is_duplicate,
            match_level=max_match_level,
            duplicates=duplicates
        ))

        # 统计计数
        if max_match_level == DuplicateMatchLevel.EXACT:
            exact_count += 1
        elif max_match_level == DuplicateMatchLevel.LIKELY:
            likely_count += 1
        elif max_match_level == DuplicateMatchLevel.POSSIBLE:
            possible_count += 1
        else:
            unique_count += 1

    return DuplicateCheckResponse(
        results=results,
        exact_duplicates_count=exact_count,
        likely_duplicates_count=likely_count,
        possible_duplicates_count=possible_count,
        unique_count=unique_count
    )


# ==================== AI 分析 Schemas ====================

class AIAnalyzeRequest(BaseModel):
    """AI 分析请求"""
    title: str = "家庭消费 AI 分析报告"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    consumer_id: Optional[int] = None   # None = 全部成员
    category: Optional[str] = None      # None = 全部分类
    save_to_history: bool = True


class PersonAnalysis(BaseModel):
    name: str
    user_id: Optional[int] = None
    total: float
    percentage: float
    count: int
    top_categories: List[str]


class AIReportData(BaseModel):
    overall_summary: str
    per_person: List[PersonAnalysis]
    trends: str
    prediction: str
    suggestions: List[dict]  # [{title, detail}]


class AIAnalyzeResponse(BaseModel):
    report_id: Optional[int] = None   # 保存后的 id
    title: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    entry_count: int
    total_amount: float
    report_data: AIReportData
    created_at: datetime


class AIReportSummary(BaseModel):
    id: int
    title: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    entry_count: int
    total_amount: float
    created_by_name: Optional[str] = None
    created_at: datetime


# ==================== AI 分析 Endpoints ====================

MIN_ENTRIES_THRESHOLD = 1   # 最小分析条目数
MAX_ENTRIES_LIMIT = 2000    # 最大分析条目数


@router.post("/ai/analyze", response_model=AIAnalyzeResponse)
async def ai_analyze_accounting(
    req: AIAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 分析记账数据。
    基于当前筛选范围生成消费分析报告，包含：
    - 按人/承担人分摊分析
    - 时间/周期趋势与短期预测
    - 可执行建议与行动项
    可选保存到历史记录。
    """
    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI 服务暂未配置，请联系管理员")

    family, _ = await get_user_family(current_user, db)

    # 构建查询条件
    conditions = [AccountingEntry.family_id == family.id]
    if req.start_date:
        conditions.append(AccountingEntry.entry_date >= req.start_date)
    if req.end_date:
        conditions.append(AccountingEntry.entry_date <= req.end_date)
    if req.consumer_id is not None:
        if req.consumer_id == 0:
            conditions.append(AccountingEntry.consumer_id.is_(None))
        else:
            conditions.append(AccountingEntry.consumer_id == req.consumer_id)
    if req.category:
        try:
            cat_enum = AccountingCategory(req.category)
            conditions.append(AccountingEntry.category == cat_enum)
        except ValueError:
            pass

    # 获取条目
    result = await db.execute(
        select(AccountingEntry)
        .where(and_(*conditions))
        .order_by(AccountingEntry.entry_date)
        .limit(MAX_ENTRIES_LIMIT)
    )
    entries = result.scalars().all()

    if len(entries) < MIN_ENTRIES_THRESHOLD:
        raise HTTPException(
            status_code=400,
            detail=f"数据不足（仅 {len(entries)} 条），建议扩大时间范围后再分析"
        )

    total_amount = sum(e.amount for e in entries)

    # 收集用户信息
    user_ids = set(e.user_id for e in entries) | set(e.consumer_id for e in entries if e.consumer_id)
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u.nickname for u in users_result.scalars().all()}

    # 按消费人分组统计
    person_stats: dict = {}
    for e in entries:
        key = e.consumer_id if e.consumer_id else 0   # 0 = 家庭共同
        if key not in person_stats:
            name = users_map.get(key, "家庭共同")
            person_stats[key] = {"name": name, "user_id": key or None, "total": 0.0, "count": 0, "categories": {}}
        person_stats[key]["total"] += e.amount
        person_stats[key]["count"] += 1
        cat = e.category.value
        person_stats[key]["categories"][cat] = person_stats[key]["categories"].get(cat, 0) + e.amount

    per_person_list = []
    for ps in person_stats.values():
        top_cats = sorted(ps["categories"].items(), key=lambda x: x[1], reverse=True)[:3]
        per_person_list.append(PersonAnalysis(
            name=ps["name"],
            user_id=ps["user_id"],
            total=round(ps["total"], 2),
            percentage=round(ps["total"] / total_amount * 100, 1) if total_amount > 0 else 0,
            count=ps["count"],
            top_categories=[CATEGORY_NAMES.get(c, c) for c, _ in top_cats]
        ))
    per_person_list.sort(key=lambda x: x.total, reverse=True)

    # 构建月度趋势数据
    monthly: dict = {}
    for e in entries:
        ym = e.entry_date.strftime("%Y-%m")
        monthly[ym] = monthly.get(ym, 0) + e.amount
    monthly_sorted = sorted(monthly.items())
    monthly_desc = "\n".join([f"  {ym}: ¥{amt:,.2f}" for ym, amt in monthly_sorted])

    # 按分类统计
    cat_stats: dict = {}
    for e in entries:
        cat = e.category.value
        cat_stats[cat] = cat_stats.get(cat, 0) + e.amount
    cat_desc = "\n".join([
        f"  {CATEGORY_NAMES.get(c, c)}: ¥{amt:,.2f} ({amt/total_amount*100:.1f}%)"
        for c, amt in sorted(cat_stats.items(), key=lambda x: x[1], reverse=True)
    ]) if total_amount > 0 else "暂无数据"

    # 按人摘要
    person_desc = "\n".join([
        f"  {p.name}: ¥{p.total:,.2f} ({p.percentage}%，{p.count}笔，主要: {', '.join(p.top_categories)})"
        for p in per_person_list
    ])

    date_range_str = ""
    if req.start_date and req.end_date:
        date_range_str = f"{req.start_date.strftime('%Y-%m-%d')} 至 {req.end_date.strftime('%Y-%m-%d')}"
    elif req.start_date:
        date_range_str = f"{req.start_date.strftime('%Y-%m-%d')} 至今"
    elif req.end_date:
        date_range_str = f"截至 {req.end_date.strftime('%Y-%m-%d')}"
    else:
        date_range_str = "全部时间"

    system_prompt = """你是一位专业的家庭财务分析师，擅长从消费数据中发现规律并提供可执行建议。

请用中文输出严格的 JSON，格式如下：
{
  "overall_summary": "100-200字的总体消费分析摘要，包含主要发现",
  "trends": "对月度趋势的文字描述（100字左右），说明消费走势、环比变化、异常月份等",
  "prediction": "基于历史趋势对未来3个月消费的短期预测（80字左右），附带置信度说明",
  "suggestions": [
    {"title": "建议标题（10字以内）", "detail": "详细说明，包含原因、预期效果和推荐步骤（50-80字）"},
    {"title": "建议标题", "detail": "详细说明"}
  ]
}

要求：
- suggestions 提供 2-4 条针对主要问题的可执行建议
- 若数据跨度不足3个月，prediction 字段说明"数据跨度不足，无法给出可靠预测"
- 若无法生成有意义建议，提供通用的家庭理财建议模板"""

    user_prompt = f"""请分析以下家庭记账数据：

【基本信息】
- 分析范围：{date_range_str}
- 总金额：¥{total_amount:,.2f}
- 记录条数：{len(entries)} 笔

【按消费人分布】
{person_desc}

【按分类分布】
{cat_desc}

【月度趋势】
{monthly_desc if monthly_desc else "无月度数据"}

请给出综合分析，重点关注消费结构、按人责任、趋势与未来预测，以及可执行建议。"""

    try:
        result_json = await ai_service.chat_json(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            function_key="accounting_analyze",
            prompt_vars={
                "date_range": date_range_str,
                "total_amount": f"{total_amount:,.2f}",
                "entry_count": str(len(entries)),
            },
            max_tokens=2000,
            temperature=0.5
        )
        if not result_json:
            raise ValueError("AI 返回了无效的响应")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")

    report_data = AIReportData(
        overall_summary=result_json.get("overall_summary", "分析完成"),
        per_person=per_person_list,
        trends=result_json.get("trends", ""),
        prediction=result_json.get("prediction", ""),
        suggestions=[
            {"title": s.get("title", ""), "detail": s.get("detail", "")}
            for s in result_json.get("suggestions", [])
            if isinstance(s, dict)
        ]
    )

    now = datetime.utcnow()
    report_id = None

    if req.save_to_history:
        report_obj = AccountingAIReport(
            family_id=family.id,
            created_by=current_user.id,
            title=req.title,
            date_from=req.start_date,
            date_to=req.end_date,
            member_filter=json.dumps([req.consumer_id]) if req.consumer_id is not None else None,
            category_filter=req.category,
            entry_count=len(entries),
            total_amount=total_amount,
            report_data=json.dumps(report_data.model_dump(), ensure_ascii=False),
            created_at=now
        )
        db.add(report_obj)
        await db.flush()
        report_id = report_obj.id

    return AIAnalyzeResponse(
        report_id=report_id,
        title=req.title,
        date_from=req.start_date,
        date_to=req.end_date,
        entry_count=len(entries),
        total_amount=total_amount,
        report_data=report_data,
        created_at=now
    )


@router.get("/ai/reports", response_model=List[AIReportSummary])
async def list_ai_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭历史 AI 分析报告列表"""
    family, _ = await get_user_family(current_user, db)

    result = await db.execute(
        select(AccountingAIReport)
        .where(AccountingAIReport.family_id == family.id)
        .order_by(desc(AccountingAIReport.created_at))
    )
    reports = result.scalars().all()

    user_ids = [r.created_by for r in reports]
    names_map = {}
    if user_ids:
        u_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        names_map = {u.id: u.nickname for u in u_result.scalars().all()}

    return [
        AIReportSummary(
            id=r.id,
            title=r.title,
            date_from=r.date_from,
            date_to=r.date_to,
            entry_count=r.entry_count,
            total_amount=r.total_amount,
            created_by_name=names_map.get(r.created_by),
            created_at=r.created_at
        )
        for r in reports
    ]


@router.get("/ai/reports/{report_id}", response_model=AIAnalyzeResponse)
async def get_ai_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单份历史 AI 分析报告详情"""
    family, _ = await get_user_family(current_user, db)

    result = await db.execute(
        select(AccountingAIReport).where(
            and_(AccountingAIReport.id == report_id, AccountingAIReport.family_id == family.id)
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    report_data_dict = json.loads(report.report_data)
    report_data = AIReportData(**report_data_dict)

    return AIAnalyzeResponse(
        report_id=report.id,
        title=report.title,
        date_from=report.date_from,
        date_to=report.date_to,
        entry_count=report.entry_count,
        total_amount=report.total_amount,
        report_data=report_data,
        created_at=report.created_at
    )


@router.delete("/ai/reports/{report_id}")
async def delete_ai_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除历史 AI 分析报告"""
    family, _ = await get_user_family(current_user, db)

    result = await db.execute(
        select(AccountingAIReport).where(
            and_(AccountingAIReport.id == report_id, AccountingAIReport.family_id == family.id)
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    await db.delete(report)
    return {"message": "报告已删除"}
