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
from studio.backend.api.provider_api import router as provider_router, seed_providers
from studio.backend.api.skills import router as skills_router

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

    # 自动迁移: 先于数据加载, 确保新列已存在
    await _auto_migrate()

    # 种子数据: 自定义模型 + 加载能力覆盖到内存
    from studio.backend.api.model_config import seed_custom_models, load_capability_overrides_to_cache
    from studio.backend.api.models_api import load_pricing_overrides_from_db
    from studio.backend.core.database import async_session_maker
    async with async_session_maker() as db:
        await seed_custom_models(db)
    await load_capability_overrides_to_cache()
    await load_pricing_overrides_from_db()

    # 种子数据: AI 服务提供商
    await seed_providers()

    # 种子数据: 内置技能
    from studio.backend.api.skills import seed_skills
    await seed_skills()

    # 一次性迁移: 为 skill_id=NULL 的旧项目设置默认技能
    await _migrate_null_skill_projects()

    # 一次性迁移: 为旧项目的 tool_permissions 添加 ask_user
    await _migrate_ask_user_permission()

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
                "is_archived": "ALTER TABLE projects ADD COLUMN is_archived BOOLEAN DEFAULT 0",
                "archived_at": "ALTER TABLE projects ADD COLUMN archived_at DATETIME",
            }
            for col, sql in proj_migrations.items():
                if col not in proj_cols:
                    await db.execute(sql)
                    logger.info(f"✅ 自动迁移: 添加 projects.{col}")

            # projects.skill_id 迁移
            proj_skill_migrations = {
                "skill_id": "ALTER TABLE projects ADD COLUMN skill_id INTEGER REFERENCES skills(id)",
            }
            for col, sql in proj_skill_migrations.items():
                if col not in proj_cols:
                    await db.execute(sql)
                    logger.info(f"✅ 自动迁移: 添加 projects.{col}")

            # ai_providers 表迁移 (新表通过 init_db 创建, 此处处理列变动)
            try:
                cursor3 = await db.execute("PRAGMA table_info(ai_providers)")
                prov_cols = {row[1] for row in await cursor3.fetchall()}
                prov_migrations = {}
                for col, sql in prov_migrations.items():
                    if col not in prov_cols:
                        await db.execute(sql)
                        logger.info(f"✅ 自动迁移: 添加 ai_providers.{col}")
            except Exception:
                pass  # 表尚未创建, 跳过

            # model_capability_overrides 表迁移: 添加定价列
            try:
                cursor4 = await db.execute("PRAGMA table_info(model_capability_overrides)")
                cap_cols = {row[1] for row in await cursor4.fetchall()}
                cap_migrations = {
                    "premium_paid": "ALTER TABLE model_capability_overrides ADD COLUMN premium_paid FLOAT",
                    "premium_free": "ALTER TABLE model_capability_overrides ADD COLUMN premium_free FLOAT",
                }
                for col, sql in cap_migrations.items():
                    if col not in cap_cols:
                        await db.execute(sql)
                        logger.info(f"✅ 自动迁移: 添加 model_capability_overrides.{col}")
            except Exception:
                pass

            await db.commit()
    except Exception as e:
        logger.warning(f"⚠️ 自动迁移跳过: {e}")


async def _migrate_null_skill_projects():
    """一次性迁移: 为 skill_id=NULL 的旧项目设置为第一个内置技能"""
    from studio.backend.core.database import async_session_maker
    from sqlalchemy import text
    try:
        async with async_session_maker() as db:
            # 找第一个内置且启用的技能
            row = (await db.execute(
                text("SELECT id FROM skills WHERE is_builtin = 1 AND is_enabled = 1 ORDER BY sort_order, id LIMIT 1")
            )).first()
            if not row:
                return
            default_id = row[0]
            result = await db.execute(
                text("UPDATE projects SET skill_id = :sid WHERE skill_id IS NULL"),
                {"sid": default_id},
            )
            if result.rowcount > 0:
                await db.commit()
                logger.info(f"✅ 迁移 {result.rowcount} 个旧项目 → 默认技能 id={default_id}")
            else:
                await db.commit()
    except Exception as e:
        logger.warning(f"⚠️ 旧项目技能迁移跳过: {e}")


app = FastAPI(
    title="设计院 (Studio)",
    description="GoldenNest 设计院 - AI 驱动的需求迭代平台",
    version="1.0.0",
    docs_url="/studio-api/docs",
    redoc_url="/studio-api/redoc",
    openapi_url="/studio-api/openapi.json",
    lifespan=lifespan,
)


async def _migrate_ask_user_permission():
    """一次性迁移: 为旧项目的 tool_permissions 添加 ask_user（默认开启）"""
    from studio.backend.core.database import async_session_maker
    from sqlalchemy import text
    import json
    try:
        async with async_session_maker() as db:
            rows = (await db.execute(
                text("SELECT id, tool_permissions FROM projects")
            )).fetchall()
            count = 0
            for row in rows:
                pid, raw = row
                perms = json.loads(raw) if isinstance(raw, str) else (raw or [])
                if "ask_user" not in perms:
                    perms.insert(0, "ask_user")
                    await db.execute(
                        text("UPDATE projects SET tool_permissions = :val WHERE id = :pid"),
                        {"val": json.dumps(perms), "pid": pid},
                    )
                    count += 1
            if count > 0:
                await db.commit()
                logger.info(f"✅ 迁移 {count} 个旧项目: tool_permissions 添加 ask_user")
            else:
                await db.commit()
    except Exception as e:
        logger.warning(f"⚠️ ask_user 权限迁移跳过: {e}")

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
app.include_router(provider_router)
app.include_router(skills_router)


@app.get("/studio-api/health")
async def health_check():
    """设计院健康检查"""
    return {"status": "ok", "service": "studio"}
