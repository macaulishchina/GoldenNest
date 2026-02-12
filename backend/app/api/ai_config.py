"""
小金库 (Golden Nest) - AI 服务商配置管理路由
支持多服务商配置、切换活跃服务商、动态获取模型列表
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field

import httpx

from app.core.database import get_db
from app.core.config import set_active_ai_provider, settings
from app.models.models import AIProvider, AIFunctionModelConfig, FamilyMember, User
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 预定义服务商模板 ====================

PROVIDER_TEMPLATES = {
    "qwen": {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-vl-plus",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "zhipu": {
        "name": "智谱AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4v",
    },
    "moonshot": {
        "name": "月之暗面 (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
    },
    "baichuan": {
        "name": "百川智能",
        "base_url": "https://api.baichuan-ai.com/v1",
        "default_model": "Baichuan4",
    },
    "silicon": {
        "name": "硅基流动 (SiliconFlow)",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen2.5-VL-72B-Instruct",
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "default_model": "",
    },
}


# ==================== Schemas ====================

class AIProviderCreate(BaseModel):
    """创建 AI 服务商"""
    name: str = Field(..., max_length=50, description="服务商名称")
    provider_type: str = Field(..., max_length=30, description="服务商类型")
    api_key: str = Field("", description="API Key")
    base_url: str = Field("", max_length=500, description="API Base URL")
    default_model: str = Field("", max_length=100, description="默认模型")


class AIProviderUpdate(BaseModel):
    """更新 AI 服务商"""
    name: Optional[str] = Field(None, max_length=50)
    api_key: Optional[str] = None
    base_url: Optional[str] = Field(None, max_length=500)
    default_model: Optional[str] = Field(None, max_length=100)
    is_enabled: Optional[bool] = None


class AIProviderResponse(BaseModel):
    """AI 服务商响应"""
    id: int
    name: str
    provider_type: str
    api_key_masked: str  # 脱敏显示
    base_url: str
    default_model: str
    is_active: bool
    is_enabled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AIProviderTemplateResponse(BaseModel):
    """服务商模板"""
    provider_type: str
    name: str
    base_url: str
    default_model: str


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    owned_by: Optional[str] = None


# ==================== 管理员权限依赖 ====================

async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """要求当前用户为家庭管理员"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    
    if not membership or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可执行此操作"
        )
    return current_user


# ==================== 工具函数 ====================

def mask_api_key(key: str) -> str:
    """API Key 脱敏显示"""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def provider_to_response(p: AIProvider) -> AIProviderResponse:
    """将数据库模型转为响应"""
    return AIProviderResponse(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        api_key_masked=mask_api_key(p.api_key),
        base_url=p.base_url,
        default_model=p.default_model,
        is_active=p.is_active,
        is_enabled=p.is_enabled,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


async def sync_active_provider_to_config(db: AsyncSession):
    """将活跃服务商同步到内存配置"""
    result = await db.execute(
        select(AIProvider).where(AIProvider.is_active == True, AIProvider.is_enabled == True)
    )
    active = result.scalar_one_or_none()
    if active:
        set_active_ai_provider(
            api_key=active.api_key,
            base_url=active.base_url,
            model=active.default_model
        )
        logger.info(f"活跃 AI 服务商已同步: {active.name} ({active.default_model})")
    else:
        logger.info("无活跃 AI 服务商，使用 .env 配置")


# ==================== API 路由 ====================

@router.get("/templates", response_model=List[AIProviderTemplateResponse])
async def get_provider_templates(
    _: User = Depends(require_admin)
):
    """获取预定义服务商模板列表"""
    return [
        AIProviderTemplateResponse(
            provider_type=key,
            name=val["name"],
            base_url=val["base_url"],
            default_model=val["default_model"],
        )
        for key, val in PROVIDER_TEMPLATES.items()
    ]


@router.get("/providers", response_model=List[AIProviderResponse])
async def list_providers(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取所有已配置的 AI 服务商"""
    result = await db.execute(
        select(AIProvider).order_by(AIProvider.is_active.desc(), AIProvider.created_at.asc())
    )
    providers = result.scalars().all()
    return [provider_to_response(p) for p in providers]


@router.post("/providers", response_model=AIProviderResponse, status_code=201)
async def create_provider(
    data: AIProviderCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """新增 AI 服务商配置"""
    # 检查名称唯一
    existing = await db.execute(
        select(AIProvider).where(AIProvider.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"服务商名称 '{data.name}' 已存在")
    
    provider = AIProvider(
        name=data.name,
        provider_type=data.provider_type,
        api_key=data.api_key,
        base_url=data.base_url,
        default_model=data.default_model,
        is_active=False,
        is_enabled=True,
        created_by=admin.id,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    
    return provider_to_response(provider)


@router.put("/providers/{provider_id}", response_model=AIProviderResponse)
async def update_provider(
    provider_id: int,
    data: AIProviderUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新 AI 服务商配置"""
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    if data.name is not None:
        # 检查名称唯一
        if data.name != provider.name:
            dup = await db.execute(select(AIProvider).where(AIProvider.name == data.name))
            if dup.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"名称 '{data.name}' 已被使用")
        provider.name = data.name
    if data.api_key is not None:
        provider.api_key = data.api_key
    if data.base_url is not None:
        provider.base_url = data.base_url
    if data.default_model is not None:
        provider.default_model = data.default_model
    if data.is_enabled is not None:
        provider.is_enabled = data.is_enabled
        # 如果禁用的是当前活跃服务商，取消活跃
        if not data.is_enabled and provider.is_active:
            provider.is_active = False
    
    await db.commit()
    await db.refresh(provider)
    
    # 如果更新的是活跃服务商，同步内存
    if provider.is_active:
        await sync_active_provider_to_config(db)
    
    return provider_to_response(provider)


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除 AI 服务商配置"""
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    was_active = provider.is_active
    await db.delete(provider)
    await db.commit()
    
    # 如果删除的是活跃服务商，清空内存配置
    if was_active:
        from app.core.config import clear_active_ai_provider
        clear_active_ai_provider()
    
    return {"message": f"已删除服务商: {provider.name}"}


@router.post("/providers/{provider_id}/activate", response_model=AIProviderResponse)
async def activate_provider(
    provider_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """切换活跃 AI 服务商"""
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    if not provider.is_enabled:
        raise HTTPException(status_code=400, detail="该服务商已禁用，请先启用")
    
    if not provider.api_key:
        raise HTTPException(status_code=400, detail="请先配置 API Key")
    
    # 取消所有活跃状态
    await db.execute(
        update(AIProvider).values(is_active=False)
    )
    
    # 设置新的活跃服务商
    provider.is_active = True
    await db.commit()
    await db.refresh(provider)
    
    # 同步到内存
    await sync_active_provider_to_config(db)
    
    return provider_to_response(provider)


@router.post("/providers/{provider_id}/deactivate", response_model=AIProviderResponse)
async def deactivate_provider(
    provider_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """取消活跃服务商（回退到 .env 配置）"""
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    provider.is_active = False
    await db.commit()
    await db.refresh(provider)
    
    # 清空内存缓存，回退到 .env
    from app.core.config import clear_active_ai_provider
    clear_active_ai_provider()
    
    return provider_to_response(provider)


@router.post("/providers/{provider_id}/set-model")
async def set_provider_model(
    provider_id: int,
    data: dict,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """设置服务商的当前使用模型"""
    model = data.get("model", "")
    if not model:
        raise HTTPException(status_code=400, detail="请指定模型 ID")
    
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    provider.default_model = model
    await db.commit()
    
    # 如果是活跃服务商，同步到内存
    if provider.is_active:
        await sync_active_provider_to_config(db)
    
    return {"message": f"已切换模型为: {model}"}


@router.get("/providers/{provider_id}/models", response_model=List[ModelInfo])
async def fetch_provider_models(
    provider_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    从服务商 API 动态获取可用模型列表
    使用 OpenAI 兼容的 /models 接口
    """
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    if not provider.api_key:
        raise HTTPException(status_code=400, detail="请先配置 API Key 才能获取模型列表")
    
    if not provider.base_url:
        raise HTTPException(status_code=400, detail="请先配置 Base URL")
    
    api_url = f"{provider.base_url.rstrip('/')}/models"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                api_url,
                headers={
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"获取模型列表失败: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=502,
            detail=f"获取模型列表失败: HTTP {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"获取模型列表连接失败: {e}")
        raise HTTPException(status_code=502, detail=f"无法连接服务商: {str(e)}")
    
    # 解析 OpenAI 兼容的 /models 响应
    models = []
    raw_models = data.get("data", [])
    if not raw_models and isinstance(data, list):
        raw_models = data
    
    for m in raw_models:
        model_id = m.get("id", "")
        if not model_id:
            continue
        models.append(ModelInfo(
            id=model_id,
            name=model_id,
            owned_by=m.get("owned_by", "")
        ))
    
    # 按 id 排序
    models.sort(key=lambda x: x.id)
    
    return models


@router.get("/status")
async def get_ai_status(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前 AI 服务状态（所有登录用户可查看）"""
    result = await db.execute(
        select(AIProvider).where(AIProvider.is_active == True, AIProvider.is_enabled == True)
    )
    active = result.scalar_one_or_none()
    
    if active:
        return {
            "configured": True,
            "provider_name": active.name,
            "model": active.default_model,
            "source": "database"
        }
    elif settings.AI_API_KEY and settings.AI_BASE_URL:
        return {
            "configured": True,
            "provider_name": "环境变量配置",
            "model": settings.AI_MODEL,
            "source": "env"
        }
    else:
        return {
            "configured": False,
            "provider_name": None,
            "model": None,
            "source": None
        }


# ==================== 功能模型配置 API ====================

class FunctionModelConfigUpdate(BaseModel):
    """更新功能模型配置"""
    provider_id: Optional[int] = Field(None, description="服务商ID，null表示跟随全局")
    model_name: str = Field("", description="模型名称，空表示跟随服务商默认")
    is_enabled: bool = Field(True, description="是否启用该功能的AI能力")


@router.get("/functions/registry")
async def get_function_registry(
    _: User = Depends(get_current_user),
):
    """获取所有 AI 功能注册表（所有登录用户可查看）"""
    from app.core.ai_functions import get_function_registry_for_api
    return get_function_registry_for_api()


@router.get("/functions/configs")
async def list_function_configs(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有功能的当前模型配置"""
    from app.core.ai_functions import AI_FUNCTION_REGISTRY, AI_FUNCTION_GROUPS
    from app.services.ai_service import ai_service

    # 从数据库加载所有已配置的功能
    result = await db.execute(select(AIFunctionModelConfig))
    configs = {c.function_key: c for c in result.scalars().all()}

    # 预加载所有服务商名称
    prov_result = await db.execute(select(AIProvider))
    providers_map = {p.id: p.name for p in prov_result.scalars().all()}

    items = []
    for key, func_def in AI_FUNCTION_REGISTRY.items():
        cfg = configs.get(key)
        resolved = ai_service.get_function_config_info(key)

        # 获取分组信息
        group_info = AI_FUNCTION_GROUPS.get(func_def.group, {})

        item = {
            "key": key,
            "name": func_def.name,
            "description": func_def.description,
            "capability": func_def.capability,
            "group": func_def.group,
            "group_name": group_info.get("name", func_def.group),
            "group_icon": group_info.get("icon", "📦"),
            "group_order": group_info.get("order", 99),
            "default_model": func_def.default_model,
            "alternative_models": func_def.alternative_models,
            # 当前配置
            "config_provider_id": cfg.provider_id if cfg else None,
            "config_provider_name": providers_map.get(cfg.provider_id, None) if cfg and cfg.provider_id else None,
            "config_model_name": cfg.model_name if cfg else "",
            "is_enabled": cfg.is_enabled if cfg else True,
            # 解析后的实际使用
            "resolved_model": resolved.get("model"),
            "source": resolved.get("source"),
            "resolved_configured": resolved.get("configured"),
            "resolved_error": resolved.get("error"),
        }
        items.append(item)

    # 按注册表顺序排列
    group_order = {k: v["order"] for k, v in AI_FUNCTION_GROUPS.items()}
    items.sort(key=lambda x: (group_order.get(x["group"], 99), x["key"]))

    return {"functions": items}


@router.put("/functions/{function_key}/config")
async def update_function_config(
    function_key: str,
    data: FunctionModelConfigUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """设置某个功能的专属模型配置（管理员）"""
    from app.core.ai_functions import AI_FUNCTION_REGISTRY
    from app.services.ai_service import refresh_function_model_cache

    if function_key not in AI_FUNCTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"未知的功能标识: {function_key}")

    # 验证 provider_id
    if data.provider_id is not None:
        prov_result = await db.execute(
            select(AIProvider).where(AIProvider.id == data.provider_id)
        )
        if not prov_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="指定的服务商不存在")

    # 查找或创建配置
    result = await db.execute(
        select(AIFunctionModelConfig).where(AIFunctionModelConfig.function_key == function_key)
    )
    cfg = result.scalar_one_or_none()

    if cfg:
        cfg.provider_id = data.provider_id
        cfg.model_name = data.model_name
        cfg.is_enabled = data.is_enabled
    else:
        cfg = AIFunctionModelConfig(
            function_key=function_key,
            provider_id=data.provider_id,
            model_name=data.model_name,
            is_enabled=data.is_enabled,
        )
        db.add(cfg)

    await db.commit()

    # 刷新内存缓存
    await refresh_function_model_cache()

    func_def = AI_FUNCTION_REGISTRY[function_key]
    return {
        "message": f"已更新「{func_def.name}」的模型配置",
        "function_key": function_key,
        "provider_id": data.provider_id,
        "model_name": data.model_name,
        "is_enabled": data.is_enabled,
    }


@router.delete("/functions/{function_key}/config")
async def reset_function_config(
    function_key: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置功能配置为跟随全局（管理员）"""
    from app.core.ai_functions import AI_FUNCTION_REGISTRY
    from app.services.ai_service import refresh_function_model_cache

    if function_key not in AI_FUNCTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"未知的功能标识: {function_key}")

    result = await db.execute(
        select(AIFunctionModelConfig).where(AIFunctionModelConfig.function_key == function_key)
    )
    cfg = result.scalar_one_or_none()
    if cfg:
        await db.delete(cfg)
        await db.commit()

    await refresh_function_model_cache()

    func_def = AI_FUNCTION_REGISTRY[function_key]
    return {"message": f"已重置「{func_def.name}」为跟随全局配置"}
