"""
小金库 (Golden Nest) - 资产登记路由
统一的资产管理接口（活期、定期、基金、股票等）
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.core.database import get_db
from app.models.models import Asset, AssetType, CurrencyType, FamilyMember, User
from app.api.auth import get_current_user
from app.services.asset_helper import get_cash_balance, get_asset_summary, get_user_assets
from app.services.exchange_rate import exchange_rate_service
from app.services.image_parser import image_parser_service

logger = logging.getLogger(__name__)

router = APIRouter()


class AssetInfoUpdate(BaseModel):
    """更新资产非金额信息（不需要审批）"""
    name: Optional[str] = None
    end_date: Optional[str] = None
    bank_name: Optional[str] = None
    note: Optional[str] = None


async def get_user_family_id(user_id: int, db: AsyncSession) -> int:
    """获取用户的家庭ID"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="您还没有加入家庭")
    return member.family_id


@router.get("/cash-balance")
async def get_cash_balance_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取家庭自由资金余额
    """
    family_id = await get_user_family_id(current_user.id, db)
    balance = await get_cash_balance(db, family_id)
    return {
        "family_id": family_id,
        "balance": balance,
        "currency": "CNY"
    }


@router.get("/summary")
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取资产汇总信息
    """
    family_id = await get_user_family_id(current_user.id, db)
    summary = await get_asset_summary(db, family_id)
    return summary


@router.get("/list")
async def list_assets(
    asset_type: Optional[AssetType] = None,
    currency: Optional[CurrencyType] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取投资型资产列表（不包括活期）
    
    Args:
        asset_type: 资产类型筛选(time_deposit/fund/stock/bond/other)
        currency: 币种筛选(CNY/USD/HKD/JPY/EUR等)
        user_id: 用户ID筛选(查看指定用户的资产)
    """
    family_id = await get_user_family_id(current_user.id, db)
    
    # 构建查询条件（排除CASH类型）
    conditions = [
        Asset.family_id == family_id,
        Asset.investment_type != AssetType.CASH,  # 排除活期
        Asset.is_active == True,
        Asset.is_deleted == False
    ]
    
    if asset_type:
        conditions.append(Asset.investment_type == asset_type)
    
    if currency:
        conditions.append(Asset.currency == currency)
    
    if user_id:
        conditions.append(Asset.user_id == user_id)
    
    # 执行查询
    result = await db.execute(
        select(Asset)
        .where(and_(*conditions))
        .order_by(Asset.created_at.desc())
    )
    assets = result.scalars().all()
    
    # 格式化返回
    return [{
        "id": asset.id,
        "name": asset.name,
        "asset_type": asset.investment_type.value,
        "currency": asset.currency.value,
        "principal": asset.principal,  # CNY
        "foreign_amount": asset.foreign_amount,
        "exchange_rate": asset.exchange_rate,
        "start_date": asset.start_date.isoformat(),
        "end_date": asset.end_date.isoformat() if asset.end_date else None,
        "bank_name": asset.bank_name,
        "deduct_from_cash": asset.deduct_from_cash,
        "user_id": asset.user_id,
        "note": asset.note,
        "created_at": asset.created_at.isoformat()
    } for asset in assets]


@router.get("/exchange-rate/{currency}")
async def get_exchange_rate(
    currency: CurrencyType,
    current_user: User = Depends(get_current_user)
):
    """
    获取实时汇率（外币 → CNY）
    
    Args:
        currency: 货币类型(USD/HKD/JPY/EUR等)
    
    Returns:
        {
            "currency": "USD",
            "rate": 7.20,
            "formatted": "$1 = ¥7.20"
        }
    """
    if currency == CurrencyType.CNY:
        return {
            "currency": "CNY",
            "rate": 1.0,
            "formatted": "¥1 = ¥1"
        }
    
    try:
        rate = await exchange_rate_service.get_rate_to_cny(currency)
        foreign_symbol = exchange_rate_service.format_foreign_amount(1, currency)
        
        return {
            "currency": currency.value,
            "rate": rate,
            "formatted": f"{foreign_symbol} = ¥{rate:.4f}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取汇率失败: {str(e)}")


class ImageParseRequest(BaseModel):
    """图片解析请求"""
    image: str  # Base64 编码的图片


@router.post("/parse-image")
async def parse_asset_image(
    req: ImageParseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    解析资产凭证图片，提取资产信息并返回结构化数据。
    
    通过 AI 视觉模型分析上传的图片（银行存款凭证、基金确认截图等），
    自动识别产品名称、金额、日期、银行等信息。
    
    Request Body:
        image: Base64 编码的图片（支持 data:image/xxx;base64,... 格式）
    
    Returns:
        {
            "success": true,
            "data": {
                "name": "产品名称",
                "asset_type": "time_deposit/fund/stock/bond/other",
                "currency": "CNY/USD/...",
                "amount": 10000.00,
                "start_date": "2025-01-01",
                "end_date": "2026-01-01",
                "bank_name": "招商银行",
                "note": "年化3.5%"
            }
        }
    """
    if not image_parser_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI 图片解析服务未配置，请联系管理员在 .env 中设置 AI_API_KEY"
        )
    
    try:
        result = await image_parser_service.parse_image(req.image)
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "data": {}
            }
        
        logger.info(f"Image parsed successfully for user {current_user.id}: {result}")
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Image parsing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图片解析失败: {str(e)}")


@router.get("/my-assets")
async def get_my_assets(
    asset_type: str = None,
    currency: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取家庭的投资资产列表
    """
    family_id = await get_user_family_id(current_user.id, db)
    assets = await get_user_assets(db, current_user.id, family_id, asset_type=asset_type, currency=currency)
    
    return {
        "assets": [{
            "id": asset.id,
            "name": asset.name,
            "investment_type": asset.investment_type.value,
            "currency": asset.currency.value if asset.currency else "CNY",
            "principal": asset.principal,
            "foreign_amount": asset.foreign_amount,
            "exchange_rate": asset.exchange_rate,
            "start_date": asset.start_date.isoformat() if asset.start_date else None,
            "end_date": asset.end_date.isoformat() if asset.end_date else None,
            "bank_name": asset.bank_name,
            "deduct_from_cash": asset.deduct_from_cash,
            "is_active": asset.is_active,
            "note": asset.note,
            "created_at": asset.created_at.isoformat()
        } for asset in assets]
    }


@router.patch("/{asset_id}/info")
async def update_asset_info(
    asset_id: int,
    data: AssetInfoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新资产非金额信息（名称、到期日、银行、备注等），不需要审批，直接生效。
    """
    from datetime import datetime as dt
    family_id = await get_user_family_id(current_user.id, db)
    result = await db.execute(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.family_id == family_id,
            Asset.is_deleted == False
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    updated_fields = []
    if data.name is not None and data.name.strip():
        asset.name = data.name.strip()
        updated_fields.append("名称")
    if data.end_date is not None:
        if data.end_date == '':
            asset.end_date = None
            updated_fields.append("到期日")
        else:
            asset.end_date = dt.fromisoformat(data.end_date.replace('Z', '+00:00'))
            updated_fields.append("到期日")
    if data.bank_name is not None:
        asset.bank_name = data.bank_name.strip() if data.bank_name.strip() else None
        updated_fields.append("银行/机构")
    if data.note is not None:
        asset.note = data.note.strip() if data.note.strip() else None
        updated_fields.append("备注")
    
    if not updated_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    
    await db.commit()
    return {"message": f"已更新：{', '.join(updated_fields)}", "id": asset_id}
