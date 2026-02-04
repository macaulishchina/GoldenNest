"""
小金库 (Golden Nest) - FastAPI 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, family, deposit, equity, investment, transaction, achievement, gift, vote, pet, announcement, report, approval, todo, calendar


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    print("🏠 小金库数据库初始化完成！")
    yield
    # 关闭时清理资源
    print("👋 小金库服务关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(family.router, prefix="/api/family", tags=["家庭管理"])
app.include_router(deposit.router, prefix="/api/deposit", tags=["资金注入"])
app.include_router(equity.router, prefix="/api/equity", tags=["股权"])
app.include_router(investment.router, prefix="/api/investment", tags=["理财管理"])
# expense router 已迁移至 approval 通用审批系统
app.include_router(transaction.router, prefix="/api/transaction", tags=["资金流水"])
app.include_router(achievement.router)  # 成就系统（路由已内置prefix）
app.include_router(gift.router)  # 股权赠与（路由已内置prefix）
app.include_router(vote.router, prefix="/api", tags=["股东大会投票"])  # 投票系统
app.include_router(pet.router, prefix="/api", tags=["宠物养成"])  # 宠物系统
app.include_router(announcement.router, prefix="/api", tags=["家庭公告"])  # 公告板
app.include_router(report.router, prefix="/api", tags=["年度报告"])  # 年度报告
app.include_router(approval.router, prefix="/api/approval", tags=["通用审批"])  # 通用审批系统
app.include_router(todo.router, prefix="/api", tags=["家庭清单"])  # 家庭 Todo 清单
app.include_router(calendar.router, prefix="/api", tags=["共享日历"])  # 共享日历


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "🏠 欢迎来到小金库 Golden Nest！",
        "docs": "/api/docs",
        "version": settings.VERSION
    }
