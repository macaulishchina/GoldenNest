"""
小金库 (Golden Nest) - 速率限制配置
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# 创建全局频率限制器
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
