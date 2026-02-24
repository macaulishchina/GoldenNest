"""
小金库 (Golden Nest) - AI 技能管理 API

管理 AI 功能点的提示词技能配置。每个 function_key 可有多套技能实现，
通过激活/停用切换当前生效的版本。
"""
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, FamilyMember, AISkill, AISkillAttachment
from app.core.ai_functions import AI_FUNCTION_REGISTRY
from app.services.ai_service import refresh_skill_cache, resolve_skill, _skill_cache, _skill_cache_loaded, load_skill_cache

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Schemas ====================

class AISkillCreate(BaseModel):
    function_key: str = Field(..., description="功能标识 (如 receipt_ocr)")
    name: str = Field(..., description="技能名称", max_length=100)
    description: Optional[str] = Field(None, description="技能说明")
    system_prompt: str = Field("", description="系统提示词模板（$variable 占位符）")
    user_prompt_template: Optional[str] = Field(None, description="用户提示词模板")
    parameters: Optional[dict] = Field(None, description="参数: {temperature, max_tokens, top_p}")
    is_active: bool = Field(False, description="是否激活")


class AISkillUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    parameters: Optional[dict] = None


class AISkillAttachmentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    file_type: str = Field("text", description="text/markdown/json/csv")
    content: str = Field(..., description="附件内容")
    inject_mode: str = Field("system_append", description="注入方式: system_append/user_prepend/reference")
    sort_order: int = Field(0)


class SkillPreviewRequest(BaseModel):
    prompt_vars: dict = Field(default_factory=dict, description="模板变量示例值")


# ==================== 管理员权限依赖 ====================

async def _require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")
    return current_user


# ==================== API Endpoints ====================

@router.get("")
async def list_skills(
    function_key: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """列出所有技能（可按 function_key 过滤）"""
    query = select(AISkill).options(selectinload(AISkill.attachments))
    if function_key:
        query = query.where(AISkill.function_key == function_key)
    query = query.order_by(AISkill.function_key, AISkill.sort_order, AISkill.id)

    result = await db.execute(query)
    skills = result.scalars().all()

    items = []
    for s in skills:
        fn_def = AI_FUNCTION_REGISTRY.get(s.function_key)
        params = {}
        if s.parameters:
            try:
                params = json.loads(s.parameters)
            except (json.JSONDecodeError, TypeError):
                pass

        items.append({
            "id": s.id,
            "function_key": s.function_key,
            "function_name": fn_def.name if fn_def else s.function_key,
            "function_group": fn_def.group if fn_def else "unknown",
            "name": s.name,
            "description": s.description,
            "system_prompt": s.system_prompt,
            "user_prompt_template": s.user_prompt_template,
            "parameters": params,
            "is_active": s.is_active,
            "sort_order": s.sort_order,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "attachments": [
                {
                    "id": att.id,
                    "name": att.name,
                    "file_type": att.file_type,
                    "content": att.content,
                    "inject_mode": att.inject_mode,
                    "sort_order": att.sort_order,
                }
                for att in s.attachments
            ],
        })

    return items


@router.get("/summary")
async def get_skills_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取技能概要（每个 function_key 有几套技能、哪套激活）"""
    result = await db.execute(
        select(AISkill).order_by(AISkill.function_key, AISkill.sort_order)
    )
    skills = result.scalars().all()

    # 按 function_key 分组
    summary = {}
    for s in skills:
        if s.function_key not in summary:
            fn_def = AI_FUNCTION_REGISTRY.get(s.function_key)
            summary[s.function_key] = {
                "function_key": s.function_key,
                "function_name": fn_def.name if fn_def else s.function_key,
                "function_group": fn_def.group if fn_def else "unknown",
                "total_skills": 0,
                "active_skill_id": None,
                "active_skill_name": None,
            }
        summary[s.function_key]["total_skills"] += 1
        if s.is_active:
            summary[s.function_key]["active_skill_id"] = s.id
            summary[s.function_key]["active_skill_name"] = s.name

    return list(summary.values())


@router.post("")
async def create_skill(
    data: AISkillCreate,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """创建新技能"""
    if data.function_key not in AI_FUNCTION_REGISTRY:
        raise HTTPException(status_code=400, detail=f"无效的功能标识: {data.function_key}")

    # 如果要激活，先停用同 function_key 的其他技能
    if data.is_active:
        await db.execute(
            update(AISkill)
            .where(AISkill.function_key == data.function_key, AISkill.is_active == True)
            .values(is_active=False)
        )

    params_json = json.dumps(data.parameters) if data.parameters else None
    skill = AISkill(
        function_key=data.function_key,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        user_prompt_template=data.user_prompt_template,
        parameters=params_json,
        is_active=data.is_active,
        created_by=admin.id,
    )
    db.add(skill)
    await db.flush()

    await refresh_skill_cache()
    return {"id": skill.id, "message": "技能创建成功"}


@router.put("/{skill_id}")
async def update_skill(
    skill_id: int,
    data: AISkillUpdate,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新技能内容"""
    result = await db.execute(select(AISkill).where(AISkill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    if data.name is not None:
        skill.name = data.name
    if data.description is not None:
        skill.description = data.description
    if data.system_prompt is not None:
        skill.system_prompt = data.system_prompt
    if data.user_prompt_template is not None:
        skill.user_prompt_template = data.user_prompt_template if data.user_prompt_template else None
    if data.parameters is not None:
        skill.parameters = json.dumps(data.parameters)

    await refresh_skill_cache()
    return {"message": "技能更新成功"}


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: int,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除技能"""
    result = await db.execute(select(AISkill).where(AISkill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    if skill.is_active:
        raise HTTPException(status_code=400, detail="不能删除当前激活的技能，请先激活其他技能")

    await db.delete(skill)
    await refresh_skill_cache()
    return {"message": "技能已删除"}


@router.post("/{skill_id}/activate")
async def activate_skill(
    skill_id: int,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """激活技能（同 function_key 下仅一个激活）"""
    result = await db.execute(select(AISkill).where(AISkill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    # 停用同 function_key 的其他技能
    await db.execute(
        update(AISkill)
        .where(AISkill.function_key == skill.function_key, AISkill.is_active == True)
        .values(is_active=False)
    )

    skill.is_active = True
    await refresh_skill_cache()
    return {"message": f"已激活技能「{skill.name}」"}


@router.post("/{skill_id}/deactivate")
async def deactivate_skill(
    skill_id: int,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """停用技能"""
    result = await db.execute(select(AISkill).where(AISkill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    skill.is_active = False
    await refresh_skill_cache()
    return {"message": f"已停用技能「{skill.name}」"}


@router.post("/{skill_id}/duplicate")
async def duplicate_skill(
    skill_id: int,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """复制技能"""
    result = await db.execute(
        select(AISkill).where(AISkill.id == skill_id).options(selectinload(AISkill.attachments))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    new_skill = AISkill(
        function_key=skill.function_key,
        name=f"{skill.name} (副本)",
        description=skill.description,
        system_prompt=skill.system_prompt,
        user_prompt_template=skill.user_prompt_template,
        parameters=skill.parameters,
        is_active=False,  # 副本默认不激活
        created_by=admin.id,
    )
    db.add(new_skill)
    await db.flush()

    # 复制附件
    for att in skill.attachments:
        new_att = AISkillAttachment(
            skill_id=new_skill.id,
            name=att.name,
            file_type=att.file_type,
            content=att.content,
            file_path=att.file_path,
            inject_mode=att.inject_mode,
            sort_order=att.sort_order,
        )
        db.add(new_att)

    return {"id": new_skill.id, "message": "技能复制成功"}


@router.post("/{skill_id}/preview")
async def preview_skill(
    skill_id: int,
    data: SkillPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """预览技能渲染效果（传入示例变量值）"""
    result = await db.execute(
        select(AISkill).where(AISkill.id == skill_id).options(selectinload(AISkill.attachments))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    from string import Template as StrTemplate

    safe_vars = data.prompt_vars or {}

    system_prompt = StrTemplate(skill.system_prompt or "").safe_substitute(safe_vars)
    user_prompt = None
    if skill.user_prompt_template:
        user_prompt = StrTemplate(skill.user_prompt_template).safe_substitute(safe_vars)

    # 注入附件
    for att in skill.attachments:
        content = att.content
        if not content:
            continue
        if att.inject_mode == "system_append":
            system_prompt += f"\n\n{content}"
        elif att.inject_mode == "user_prepend" and user_prompt:
            user_prompt = f"{content}\n\n{user_prompt}"
        elif att.inject_mode == "reference":
            system_prompt += f"\n\n--- 参考资料：{att.name} ---\n{content}\n--- 参考资料结束 ---"

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "parameters": json.loads(skill.parameters) if skill.parameters else {},
    }


# ==================== 附件管理 ====================

@router.post("/{skill_id}/attachments")
async def add_attachment(
    skill_id: int,
    data: AISkillAttachmentCreate,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """为技能添加附件"""
    result = await db.execute(select(AISkill).where(AISkill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    if data.inject_mode not in ("system_append", "user_prepend", "reference"):
        raise HTTPException(status_code=400, detail="无效的注入方式")

    att = AISkillAttachment(
        skill_id=skill_id,
        name=data.name,
        file_type=data.file_type,
        content=data.content,
        inject_mode=data.inject_mode,
        sort_order=data.sort_order,
    )
    db.add(att)
    await db.flush()

    if skill.is_active:
        await refresh_skill_cache()

    return {"id": att.id, "message": "附件添加成功"}


@router.put("/attachments/{attachment_id}")
async def update_attachment(
    attachment_id: int,
    data: AISkillAttachmentCreate,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新附件"""
    result = await db.execute(select(AISkillAttachment).where(AISkillAttachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    att.name = data.name
    att.file_type = data.file_type
    att.content = data.content
    att.inject_mode = data.inject_mode
    att.sort_order = data.sort_order

    # 检查关联的技能是否激活
    skill_result = await db.execute(select(AISkill).where(AISkill.id == att.skill_id))
    skill = skill_result.scalar_one_or_none()
    if skill and skill.is_active:
        await refresh_skill_cache()

    return {"message": "附件更新成功"}


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除附件"""
    result = await db.execute(select(AISkillAttachment).where(AISkillAttachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    skill_id = att.skill_id
    await db.delete(att)

    # 检查关联的技能是否激活
    skill_result = await db.execute(select(AISkill).where(AISkill.id == skill_id))
    skill = skill_result.scalar_one_or_none()
    if skill and skill.is_active:
        await refresh_skill_cache()

    return {"message": "附件已删除"}
