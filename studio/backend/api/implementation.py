"""
设计院 (Studio) - 代码实施 API
创建 GitHub Issue → 触发 Copilot Agent → 监控 PR
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio.backend.core.database import get_db
from studio.backend.models import Project, ProjectStatus
from studio.backend.services import github_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio-api/projects", tags=["Implementation"])


class ImplementRequest(BaseModel):
    """发起实施请求"""
    use_copilot_agent: bool = True
    custom_instructions: str = ""


class ImplementationStatus(BaseModel):
    """实施状态"""
    project_id: int
    status: str  # not_started, issue_created, agent_working, pr_created, pr_merged
    github_issue_number: Optional[int]
    github_pr_number: Optional[int]
    branch_name: Optional[str]
    pr_title: Optional[str] = None
    pr_url: Optional[str] = None
    pr_state: Optional[str] = None
    pr_files_changed: int = 0
    pr_diff: Optional[str] = None


@router.post("/{project_id}/implement")
async def start_implementation(
    project_id: int,
    data: ImplementRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发起代码实施:
    1. 将 plan.md 创建为 GitHub Issue
    2. 标记 copilot label → 触发 Copilot Agent
    3. Agent 自动创建分支和 PR
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.plan_content:
        raise HTTPException(status_code=400, detail="请先敲定设计方案 (plan)")

    # 构建 Issue body
    issue_body = f"""## 设计院需求 #{project.id}: {project.title}

### 需求描述
{project.description}

### 实施计划
{project.plan_content}

---
> 🏗️ 此 Issue 由设计院自动创建
> 📋 项目 ID: {project.id}
"""
    if data.custom_instructions:
        issue_body += f"\n### 附加指令\n{data.custom_instructions}\n"

    # 创建 GitHub Issue
    labels = ["studio"]
    assignees = []
    if data.use_copilot_agent:
        labels.append("copilot")
        # Copilot Agent 不需要 assignee, 它通过 label 触发

    try:
        issue = await github_service.create_issue(
            title=f"[设计院] {project.title}",
            body=issue_body,
            labels=labels,
            assignees=assignees,
        )

        project.github_issue_number = issue["number"]
        project.status = ProjectStatus.implementing
        project.updated_at = datetime.utcnow()

        return {
            "success": True,
            "issue_number": issue["number"],
            "issue_url": issue["html_url"],
            "message": "Issue 已创建" + (", Copilot Agent 将自动开始编码" if data.use_copilot_agent else ""),
        }

    except Exception as e:
        logger.exception("创建 GitHub Issue 失败")
        raise HTTPException(status_code=500, detail=f"GitHub API 错误: {str(e)}")


@router.get("/{project_id}/implementation", response_model=ImplementationStatus)
async def get_implementation_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查询实施进度 (轮询 GitHub PR 状态)"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    status_info = ImplementationStatus(
        project_id=project_id,
        status="not_started",
        github_issue_number=project.github_issue_number,
        github_pr_number=project.github_pr_number,
        branch_name=project.branch_name,
    )

    if not project.github_issue_number:
        return status_info

    status_info.status = "issue_created"

    try:
        # 检查是否有关联的 PR
        if project.github_pr_number:
            pr = await github_service.get_pull(project.github_pr_number)
            status_info.pr_title = pr.get("title")
            status_info.pr_url = pr.get("html_url")
            status_info.pr_state = pr.get("state")
            status_info.pr_files_changed = pr.get("changed_files", 0)
            status_info.branch_name = pr.get("head", {}).get("ref")

            if pr.get("merged"):
                status_info.status = "pr_merged"
            elif pr.get("state") == "open":
                status_info.status = "pr_created"
        else:
            # 搜索关联的 PR (Copilot Agent 可能已创建)
            pulls = await github_service.list_pulls(state="open")
            for pr in pulls:
                body = pr.get("body", "") or ""
                title = pr.get("title", "") or ""
                # 检查 PR 是否关联到此 Issue
                if (f"#{project.github_issue_number}" in body or
                    f"#{project.github_issue_number}" in title or
                    project.title in title):
                    project.github_pr_number = pr["number"]
                    project.branch_name = pr.get("head", {}).get("ref")
                    project.status = ProjectStatus.reviewing
                    status_info.status = "pr_created"
                    status_info.github_pr_number = pr["number"]
                    status_info.pr_title = pr.get("title")
                    status_info.pr_url = pr.get("html_url")
                    status_info.pr_state = pr.get("state")
                    status_info.pr_files_changed = pr.get("changed_files", 0)
                    status_info.branch_name = pr.get("head", {}).get("ref")
                    break
            else:
                # 可能 Agent 还在工作
                status_info.status = "agent_working"

    except Exception as e:
        logger.warning(f"查询 GitHub 状态失败: {e}")

    return status_info


@router.get("/{project_id}/pr-diff")
async def get_pr_diff(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取 PR 的 diff 内容"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or not project.github_pr_number:
        raise HTTPException(status_code=404, detail="未找到 PR")

    try:
        diff = await github_service.get_pull_diff(project.github_pr_number)
        files = await github_service.get_pull_files(project.github_pr_number)
        return {
            "diff": diff,
            "files": [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "patch": f.get("patch", ""),
                }
                for f in files
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Diff 失败: {str(e)}")


@router.post("/{project_id}/pr/approve")
async def approve_and_merge_pr(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Review 通过并合并 PR"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or not project.github_pr_number:
        raise HTTPException(status_code=404, detail="未找到 PR")

    try:
        merge_result = await github_service.merge_pull(
            project.github_pr_number,
            merge_method="squash",
            commit_message=f"[设计院] {project.title} (#{project.github_issue_number})",
        )
        project.status = ProjectStatus.deploying
        project.updated_at = datetime.utcnow()

        return {
            "success": True,
            "merged": merge_result.get("merged", False),
            "message": merge_result.get("message", ""),
            "sha": merge_result.get("sha", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合并 PR 失败: {str(e)}")
