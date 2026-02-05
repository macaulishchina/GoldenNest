"""
小金库 (Golden Nest) - 家庭相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FamilyCreate(BaseModel):
    """创建家庭请求"""
    name: str = Field(..., min_length=1, max_length=100, description="家庭名称")
    savings_target: float = Field(default=2000000.0, ge=0, description="储蓄目标")
    time_value_rate: float = Field(default=0.03, ge=0, le=1, description="时间价值系数（用于计算加权股权）")


class FamilyUpdate(BaseModel):
    """更新家庭请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    savings_target: Optional[float] = Field(None, ge=0)
    time_value_rate: Optional[float] = Field(None, ge=0, le=1)


class FamilyMemberResponse(BaseModel):
    """家庭成员响应"""
    id: int
    user_id: int
    username: str
    nickname: str
    avatar_version: int = 0  # 头像版本号，用于缓存失效
    role: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


class FamilyResponse(BaseModel):
    """家庭信息响应"""
    id: int
    name: str
    savings_target: float
    time_value_rate: float
    invite_code: str
    created_at: datetime
    members: List[FamilyMemberResponse] = []
    
    class Config:
        from_attributes = True


class JoinFamilyRequest(BaseModel):
    """加入家庭请求"""
    invite_code: str = Field(..., description="邀请码")


# ==================== 通知配置 ====================

class NotificationConfigResponse(BaseModel):
    """通知配置响应"""
    notification_enabled: bool = Field(default=True, description="是否启用通知")
    wechat_webhook_url: Optional[str] = Field(None, description="企业微信机器人 Webhook URL（脱敏显示）")
    has_wechat_webhook: bool = Field(default=False, description="是否已配置企业微信 Webhook")
    external_base_url: Optional[str] = Field(None, description="外网访问地址，用于通知中的链接")
    
    class Config:
        from_attributes = True


class NotificationConfigUpdate(BaseModel):
    """更新通知配置请求"""
    notification_enabled: Optional[bool] = Field(None, description="是否启用通知")
    wechat_webhook_url: Optional[str] = Field(None, max_length=500, description="企业微信机器人 Webhook URL")
    external_base_url: Optional[str] = Field(None, max_length=200, description="外网访问地址（如 http://192.168.1.100:8000）")


class NotificationTestRequest(BaseModel):
    """测试通知请求"""
    webhook_url: Optional[str] = Field(None, description="要测试的 Webhook URL（可选，不填则使用当前配置）")
