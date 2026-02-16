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
from studio.backend.models import Project, ProjectStatus, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio-api/projects", tags=["Projects"])


# ==================== Schemas ====================

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    discussion_model: str = Field("gpt-4o")
    implementation_model: str = Field("claude-sonnet-4-20250514")


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    plan_content: Optional[str] = None
    discussion_model: Optional[str] = None
    implementation_model: Optional[str] = None
    tool_permissions: Optional[List[str]] = None


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
    created_by: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

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
    project = Project(
        title=data.title,
        description=data.description,
        discussion_model=data.discussion_model,
        implementation_model=data.implementation_model,
        status=ProjectStatus.draft,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    return ProjectDetail(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        message_count=0,
    )


@router.get("", response_model=List[ProjectSummary])
async def list_projects(
    status_filter: Optional[ProjectStatus] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """项目列表"""
    query = select(Project)
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
        summaries.append(ProjectSummary(
            **{c.name: getattr(p, c.name) for c in p.__table__.columns},
            message_count=msg_count,
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

    return ProjectDetail(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        message_count=msg_count,
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

    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(project)

    msg_count_result = await db.execute(
        select(func.count(Message.id)).where(Message.project_id == project.id)
    )
    msg_count = msg_count_result.scalar() or 0

    return ProjectDetail(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        message_count=msg_count,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """删除项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    await db.delete(project)
