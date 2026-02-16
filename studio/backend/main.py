"""
设计院 (Studio) - FastAPI 主入口
独立的后端服务，管理需求讨论、代码实施、部署流水线
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studio.backend.core.database import init_db
from studio.backend.api.projects import router as projects_router
from studio.backend.api.discussion import router as discussion_router
from studio.backend.api.implementation import router as implementation_router
from studio.backend.api.deployment import router as deployment_router
from studio.backend.api.snapshots import router as snapshots_router, system_router
from studio.backend.api.models_api import router as models_router
from studio.backend.api.model_config import router as model_config_router
from studio.backend.api.copilot_auth_api import router as copilot_auth_router
from studio.backend.api.studio_auth import router as studio_auth_router
from studio.backend.api.endpoint_probe import router as endpoint_probe_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    logger.info("🏗️ 设计院启动中...")
    await init_db()
    logger.info("✅ 数据库初始化完成")

    # 种子数据: 自定义模型 + 加载能力覆盖到内存
    from studio.backend.api.model_config import seed_custom_models, load_capability_overrides_to_cache
    from studio.backend.core.database import async_session_maker
    async with async_session_maker() as db:
        await seed_custom_models(db)
    await load_capability_overrides_to_cache()

    # 自动迁移: 为已有的 messages 表添加新列 (无 Alembic, 用 ALTER TABLE)
    await _auto_migrate()

    yield
    logger.info("🏗️ 设计院关闭")


async def _auto_migrate():
    """轻量级自动迁移: 检查并添加缺失的列"""
    import aiosqlite
    from studio.backend.core.config import settings
    db_path = settings.data_path + "/studio.db"
    try:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("PRAGMA table_info(messages)")
            existing = {row[1] for row in await cursor.fetchall()}

            migrations = {
                "thinking_content": "ALTER TABLE messages ADD COLUMN thinking_content TEXT",
                "tool_calls": "ALTER TABLE messages ADD COLUMN tool_calls JSON",
                "parent_message_id": "ALTER TABLE messages ADD COLUMN parent_message_id INTEGER",
            }
            for col, sql in migrations.items():
                if col not in existing:
                    await db.execute(sql)
                    logger.info(f"✅ 自动迁移: 添加 messages.{col}")

            # projects 表迁移
            cursor2 = await db.execute("PRAGMA table_info(projects)")
            proj_cols = {row[1] for row in await cursor2.fetchall()}
            proj_migrations = {
                "ai_muted": "ALTER TABLE projects ADD COLUMN ai_muted BOOLEAN DEFAULT 0",
                "tool_permissions": "ALTER TABLE projects ADD COLUMN tool_permissions JSON DEFAULT '[\"read_source\", \"read_config\", \"search\", \"tree\"]'",
            }
            for col, sql in proj_migrations.items():
                if col not in proj_cols:
                    await db.execute(sql)
                    logger.info(f"✅ 自动迁移: 添加 projects.{col}")

            await db.commit()
    except Exception as e:
        logger.warning(f"⚠️ 自动迁移跳过: {e}")


app = FastAPI(
    title="设计院 (Studio)",
    description="GoldenNest 设计院 - AI 驱动的需求迭代平台",
    version="1.0.0",
    docs_url="/studio-api/docs",
    redoc_url="/studio-api/redoc",
    openapi_url="/studio-api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(projects_router)
app.include_router(discussion_router)
app.include_router(implementation_router)
app.include_router(deployment_router)
app.include_router(snapshots_router)
app.include_router(system_router)
app.include_router(models_router)
app.include_router(model_config_router)
app.include_router(copilot_auth_router)
app.include_router(studio_auth_router)
app.include_router(endpoint_probe_router)


@app.get("/studio-api/health")
async def health_check():
    """设计院健康检查"""
    return {"status": "ok", "service": "studio"}
