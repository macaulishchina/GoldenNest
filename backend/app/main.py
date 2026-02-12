"""
小金库 (Golden Nest) - FastAPI 主入口
"""
import logging

# 配置应用日志（必须在其他模块导入前配置，否则 logging.info 等调用无输出）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
# 降低第三方库日志噪音
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings, UPLOAD_DIR, BASE_DIR
from app.core.database import init_db
from app.core.limiter import limiter
from app.api import auth, family, deposit, equity, investment, transaction, achievement, gift, vote, pet, announcement, report, approval, todo, calendar, asset, ai_config, ai_chat, bet, accounting
from app.services.notification import set_external_base_url, detect_external_url_from_headers
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    print("🏠 小金库数据库初始化完成！")
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"📁 上传目录: {UPLOAD_DIR}")
    
    # 加载活跃 AI 服务商配置到内存
    try:
        from app.core.database import async_session_maker
        async with async_session_maker() as db:
            await ai_config.sync_active_provider_to_config(db)
        # 加载功能模型配置缓存
        from app.services.ai_service import load_function_model_configs
        await load_function_model_configs()
    except Exception as e:
        print(f"⚠️ 加载 AI 服务商配置失败（可能是首次启动）: {e}")
    
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

# 将limiter绑定到app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


# AI 调用元数据中间件 —— 将 AI 模型/功能信息注入响应头
class AIMetadataMiddleware(BaseHTTPMiddleware):
    """
    将当前请求中 AI 调用的元数据写入响应头，
    前端可据此展示"由 xx 模型驱动"的优雅提示。

    响应头：
    - X-AI-Function: 功能标识（如 receipt_ocr）
    - X-AI-Function-Name: 功能名称（如 小票/发票识别）
    - X-AI-Model: 实际使用的模型名
    - X-AI-Source: 配置来源 function/global/env
    """
    async def dispatch(self, request: Request, call_next):
        from app.services.ai_service import ai_call_metadata
        # 每个请求开始时重置
        token = ai_call_metadata.set(None)
        try:
            response = await call_next(request)
            meta = ai_call_metadata.get()
            if meta:
                response.headers["X-AI-Function"] = meta.get("function_key", "")
                response.headers["X-AI-Function-Name"] = meta.get("function_name", "")
                response.headers["X-AI-Model"] = meta.get("model", "")
                response.headers["X-AI-Source"] = meta.get("source", "")
            return response
        finally:
            ai_call_metadata.reset(token)

# 添加中间件（注意顺序：后添加的先执行）
app.add_middleware(ExternalUrlMiddleware)
app.add_middleware(AIMetadataMiddleware)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-AI-Function", "X-AI-Function-Name", "X-AI-Model", "X-AI-Source"],
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
app.include_router(bet.router, prefix="/api/bet", tags=["家庭赌注"])  # 家庭赌注系统
app.include_router(accounting.router, prefix="/api/accounting", tags=["记账系统"])  # 家庭记账系统
app.include_router(ai_config.router, prefix="/api/ai-config", tags=["AI 配置"])  # AI 服务商管理
app.include_router(ai_chat.router, prefix="/api", tags=["AI 助手"])  # AI 通用对话助手

# 挂载静态文件服务（小票图片等）
uploads_root = os.path.join(BASE_DIR, "uploads")
os.makedirs(uploads_root, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_root), name="uploads")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常"""
    import traceback
    
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"}
    )


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "🏠 欢迎来到小金库 Golden Nest！",
        "docs": "/api/docs",
        "version": settings.VERSION
    }
