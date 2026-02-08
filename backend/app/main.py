"""
小金库 (Golden Nest) - FastAPI 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, family, deposit, equity, investment, transaction, achievement, gift, vote, pet, announcement, report, approval, todo, calendar, asset
from app.services.notification import set_external_base_url, detect_external_url_from_headers


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

# 外网地址检测中间件
class ExternalUrlMiddleware(BaseHTTPMiddleware):
    """
    自动检测外网地址并存储到请求上下文中
    
    支持的请求头：
    - Origin: 浏览器发送的源地址（最可靠）
    - X-Forwarded-Host: 反向代理转发的主机名
    - X-Forwarded-Proto: 反向代理转发的协议
    - Host: 直接访问时的主机名
    """
    
    async def dispatch(self, request: Request, call_next):
        # 从请求头检测外网地址
        external_url = detect_external_url_from_headers(
            host=request.headers.get("host"),
            forwarded_host=request.headers.get("x-forwarded-host"),
            forwarded_proto=request.headers.get("x-forwarded-proto"),
            x_original_host=request.headers.get("x-original-host"),
            origin=request.headers.get("origin"),
        )
        
        if external_url:
            set_external_base_url(external_url)
        
        response = await call_next(request)
        return response


# 添加中间件（注意顺序：后添加的先执行）
app.add_middleware(ExternalUrlMiddleware)

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
app.include_router(asset.router, prefix="/api/asset", tags=["资产登记"])  # 🌟 NEW: 统一资产管理
app.include_router(deposit.router, prefix="/api/deposit", tags=["资金注入"])  # 保留向后兼容
app.include_router(equity.router, prefix="/api/equity", tags=["股权"])
app.include_router(investment.router, prefix="/api/investment", tags=["理财管理"])  # 保留向后兼容
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
