"""
小金库 (Golden Nest) - 核心配置
"""
from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # 项目基本信息
    PROJECT_NAME: str = "小金库 Golden Nest"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "家庭股份制储蓄管理系统"
    
    # 安全配置
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    ALGORITHM: str = "HS256"
    
    # 加密配置（用于敏感数据加密，如Webhook URL）
    ENCRYPTION_KEY: str = ""  # 必须在.env中配置，使用Fernet密钥格式
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./golden_nest.db"
    
    # 股权计算配置
    EQUITY_ANNUAL_RATE: float = 0.03  # 年化3%的时间加权利率
    SAVINGS_TARGET: float = 2000000.0  # 储蓄目标200万
    
    # AI 视觉解析配置（用于资产凭证图片识别）
    AI_API_KEY: str = ""  # AI API 密钥，在 .env 中配置
    AI_BASE_URL: str = "https://api.openai.com/v1"  # API 基础地址，兼容 OpenAI 格式
    AI_MODEL: str = "gpt-4o-mini"  # 视觉模型名称
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
