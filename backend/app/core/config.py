"""
小金库 (Golden Nest) - 核心配置

配置优先级（从高到低）：
1. 数据库动态配置（管理员通过系统设置页面配置的活跃 AI 服务商）
2. .env 文件配置（默认 AI 服务商配置）
3. 代码中的默认值
"""
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
import secrets


# 活跃 AI 服务商配置缓存（由数据库加载，运行时可切换）
_active_ai_provider: Dict[str, str] = {}


def set_active_ai_provider(api_key: str, base_url: str, model: str):
    """设置当前活跃的 AI 服务商配置"""
    _active_ai_provider["AI_API_KEY"] = api_key
    _active_ai_provider["AI_BASE_URL"] = base_url
    _active_ai_provider["AI_MODEL"] = model


def get_active_ai_config(key: str) -> Optional[str]:
    """获取活跃 AI 服务商的配置项"""
    return _active_ai_provider.get(key) or None


def clear_active_ai_provider():
    """清空活跃 AI 服务商缓存"""
    _active_ai_provider.clear()


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
    
    # AI 能力配置（兼容 OpenAI 格式，支持通义千问/DeepSeek/OpenAI 等）
    # 默认值为空，需在 .env 中配置
    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""
    AI_MODEL: str = ""
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def get(self, key: str) -> Any:
        """获取配置值，AI 相关配置优先使用活跃服务商"""
        upper_key = key.upper()
        if upper_key in ("AI_API_KEY", "AI_BASE_URL", "AI_MODEL"):
            val = get_active_ai_config(upper_key)
            if val:
                return val
        return getattr(self, upper_key, None)


settings = Settings()
