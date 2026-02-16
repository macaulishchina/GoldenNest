"""
设计院 (Studio) - 快照服务
管理代码快照、数据库备份和回滚操作
"""
import asyncio
import logging
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio.backend.core.config import settings
from studio.backend.models import Snapshot

logger = logging.getLogger(__name__)


async def _run_cmd(cmd: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
    """运行 shell 命令"""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd or settings.workspace_path,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def create_snapshot(
    db: AsyncSession,
    description: str = "",
    project_id: Optional[int] = None,
) -> Snapshot:
    """
    创建代码快照:
    1. git tag
    2. 数据库备份
    3. Docker 镜像标记
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    tag_name = f"snapshot-{timestamp}"

    # 1. 获取当前 commit
    rc, stdout, stderr = await _run_cmd("git rev-parse HEAD")
    commit_hash = stdout.strip() if rc == 0 else "unknown"

    # 2. 创建 git tag
    await _run_cmd(f'git tag -a {tag_name} -m "Snapshot: {description or tag_name}"')

    # 3. 备份数据库
    db_src = os.path.join(settings.workspace_path, "data", "golden_nest.db")
    db_backup_filename = f"golden_nest-{timestamp}.db"
    db_backup_path = os.path.join(settings.db_backups_path, db_backup_filename)
    if os.path.exists(db_src):
        shutil.copy2(db_src, db_backup_path)
        logger.info(f"数据库备份: {db_backup_path}")
    else:
        db_backup_path = ""
        logger.warning("主项目数据库文件不存在, 跳过备份")

    # 4. 标记 Docker 镜像
    docker_tags = {}
    for service in ["frontend", "backend"]:
        image_name = f"goldennest-{service}"
        tag_cmd = f"docker tag {image_name}:latest {image_name}:{tag_name} 2>/dev/null || true"
        await _run_cmd(tag_cmd)
        docker_tags[service] = tag_name

    # 5. 保存快照记录
    snapshot = Snapshot(
        project_id=project_id,
        git_commit=commit_hash,
        git_tag=tag_name,
        docker_image_tags=docker_tags,
        db_backup_path=db_backup_path,
        description=description,
        is_healthy=True,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)

    logger.info(f"快照已创建: {tag_name} (commit: {commit_hash[:8]})")
    return snapshot


async def rollback_to_snapshot(
    db: AsyncSession,
    snapshot_id: int,
    restore_db: bool = False,
) -> Dict[str, Any]:
    """
    回滚到指定快照:
    1. git checkout tag
    2. 可选: 恢复数据库
    3. 重建并重启主项目容器
    """
    result = await db.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return {"success": False, "error": "快照不存在"}

    logs = []

    try:
        # 1. Git checkout
        tag = snapshot.git_tag
        rc, stdout, stderr = await _run_cmd(f"git checkout {tag}")
        logs.append(f"git checkout {tag}: {'OK' if rc == 0 else stderr}")

        # 2. 可选恢复数据库
        if restore_db and snapshot.db_backup_path and os.path.exists(snapshot.db_backup_path):
            db_target = os.path.join(settings.workspace_path, "data", "golden_nest.db")
            shutil.copy2(snapshot.db_backup_path, db_target)
            logs.append(f"数据库已恢复: {snapshot.db_backup_path}")

        # 3. 尝试用已标记的镜像直接启动（更快）
        image_tags = snapshot.docker_image_tags or {}
        if image_tags:
            for service, tag_val in image_tags.items():
                image_name = f"goldennest-{service}"
                retag_cmd = f"docker tag {image_name}:{tag_val} {image_name}:latest 2>/dev/null"
                rc, _, _ = await _run_cmd(retag_cmd)
                if rc == 0:
                    logs.append(f"镜像回退 {image_name}:{tag_val} → latest: OK")

            # 重启容器
            rc, stdout, stderr = await _run_cmd(
                "docker compose up -d frontend backend",
                cwd=settings.workspace_path,
            )
            logs.append(f"容器重启: {'OK' if rc == 0 else stderr}")
        else:
            # 没有镜像标记, 重新构建
            rc, stdout, stderr = await _run_cmd(
                "docker compose up -d --build frontend backend",
                cwd=settings.workspace_path,
            )
            logs.append(f"容器重建: {'OK' if rc == 0 else stderr}")

        # 4. 健康检查
        healthy = await _health_check()
        logs.append(f"健康检查: {'通过 ✅' if healthy else '失败 ❌'}")

        return {
            "success": healthy,
            "snapshot": tag,
            "logs": logs,
        }

    except Exception as e:
        logger.exception("回滚失败")
        logs.append(f"异常: {str(e)}")
        return {"success": False, "error": str(e), "logs": logs}


async def _health_check() -> bool:
    """检查主项目是否健康"""
    for attempt in range(settings.health_check_retries):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 检查后端
                resp = await client.get("http://backend:8000/api/health")
                if resp.status_code != 200:
                    logger.warning(f"后端健康检查失败 (尝试 {attempt + 1})")
                    await asyncio.sleep(settings.health_check_interval)
                    continue

                # 检查前端
                resp = await client.get("http://frontend:80")
                if resp.status_code != 200:
                    logger.warning(f"前端健康检查失败 (尝试 {attempt + 1})")
                    await asyncio.sleep(settings.health_check_interval)
                    continue

                return True
        except Exception as e:
            logger.warning(f"健康检查异常 (尝试 {attempt + 1}): {e}")
            await asyncio.sleep(settings.health_check_interval)

    return False


# 需要导入 httpx (在函数体中使用)
import httpx  # noqa: E402
