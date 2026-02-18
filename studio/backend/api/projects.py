"""
设计院 (Studio) - 项目管理 API
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from studio.backend.core.database import get_db
from studio.backend.models import Project, ProjectStatus, Message, Skill

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio-api/projects", tags=["Projects"])


# ==================== Helpers ====================

def _build_skill_brief(skill_obj) -> Optional['SkillBrief']:
    if not skill_obj:
        return None
    return SkillBrief(
        id=skill_obj.id,
        name=skill_obj.name,
        icon=skill_obj.icon or "",
        stages=skill_obj.stages or [],
        ui_labels=skill_obj.ui_labels or {},
    )


# ==================== Schemas ====================

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    discussion_model: str = Field("gpt-4o")
    implementation_model: str = Field("claude-sonnet-4-20250514")
    skill_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    plan_content: Optional[str] = None
    discussion_model: Optional[str] = None
    implementation_model: Optional[str] = None
    tool_permissions: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class SkillBrief(BaseModel):
    id: int
    name: str
    icon: str
    stages: list
    ui_labels: dict

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    id: int
    title: str
    description: str
    status: ProjectStatus
    github_issue_number: Optional[int]
    github_pr_number: Optional[int]
    branch_name: Optional[str]
    discussion_model: str
    implementation_model: str
    tool_permissions: Optional[List[str]] = None
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    skill_id: Optional[int] = None
    skill: Optional[SkillBrief] = None

    class Config:
        from_attributes = True


class ProjectDetail(ProjectSummary):
    plan_content: str
    plan_version: int
    preview_port: Optional[int]


# ==================== Routes ====================

@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """创建需求项目"""
    # 验证 skill_id (如果提供)
    skill_obj = None
    if data.skill_id:
        result = await db.execute(select(Skill).where(Skill.id == data.skill_id))
        skill_obj = result.scalar_one_or_none()
        if not skill_obj:
            raise HTTPException(status_code=400, detail="指定的技能不存在")
    else:
        # 默认使用第一个启用的内置技能
        result = await db.execute(
            select(Skill).where(Skill.is_enabled.is_(True)).order_by(Skill.sort_order, Skill.id).limit(1)
        )
        skill_obj = result.scalar_one_or_none()

    project = Project(
        title=data.title,
        description=data.description,
        discussion_model=data.discussion_model,
        implementation_model=data.implementation_model,
        status=ProjectStatus.draft,
        skill_id=skill_obj.id if skill_obj else None,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    skill_brief = None
    if skill_obj:
        skill_brief = SkillBrief(
            id=skill_obj.id, name=skill_obj.name, icon=skill_obj.icon or "",
            stages=skill_obj.stages or [], ui_labels=skill_obj.ui_labels or {},
        )

    return ProjectDetail(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        message_count=0,
        skill=skill_brief,
    )


@router.get("", response_model=List[ProjectSummary])
async def list_projects(
    status_filter: Optional[ProjectStatus] = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """项目列表"""
    query = select(Project)
    if not include_archived:
        query = query.where(Project.is_archived.is_(False))
    if status_filter:
        query = query.where(Project.status == status_filter)
    query = query.order_by(Project.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    summaries = []
    for p in projects:
        # 获取消息数量
        msg_count_result = await db.execute(
            select(func.count(Message.id)).where(Message.project_id == p.id)
        )
        msg_count = msg_count_result.scalar() or 0
        skill_brief = _build_skill_brief(p.skill) if p.skill else None
        summaries.append(ProjectSummary(
            **{c.name: getattr(p, c.name) for c in p.__table__.columns},
            message_count=msg_count,
            skill=skill_brief,
        ))
    return summaries


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    msg_count_result = await db.execute(
        select(func.count(Message.id)).where(Message.project_id == project.id)
    )
    msg_count = msg_count_result.scalar() or 0
    skill_brief = _build_skill_brief(project.skill) if project.skill else None

    return ProjectDetail(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        message_count=msg_count,
        skill=skill_brief,
    )


@router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果更新 plan_content, 自增版本号
    if "plan_content" in update_data and update_data["plan_content"] != project.plan_content:
        project.plan_version += 1

    # 归档时间戳维护
    if "is_archived" in update_data:
        archive_value = bool(update_data["is_archived"])
        if archive_value and not project.is_archived:
            project.archived_at = datetime.utcnow()
        elif not archive_value and project.is_archived:
            project.archived_at = None

    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(project)

    msg_count_result = await db.execute(
        select(func.count(Message.id)).where(Message.project_id == project.id)
    )
    msg_count = msg_count_result.scalar() or 0
    # 刷新 skill relationship (skill_id 可能被更新)
    skill_brief = _build_skill_brief(project.skill) if project.skill else None

    return ProjectDetail(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        message_count=msg_count,
        skill=skill_brief,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """删除项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    await db.delete(project)
