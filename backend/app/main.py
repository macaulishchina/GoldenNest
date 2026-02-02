"""
小金库 (Golden Nest) - FastAPI 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, family, deposit, equity, investment, expense, transaction


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
app.include_router(expense.router, prefix="/api/expense", tags=["支出申请"])
app.include_router(transaction.router, prefix="/api/transaction", tags=["资金流水"])


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
