"""
小金库 (Golden Nest) - 记账系统相关 Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class AccountingEntryBase(BaseModel):
    """记账条目基础模型"""
    amount: float = Field(..., gt=0, description="金额")
    category: str = Field(..., description="分类")
    description: str = Field(..., max_length=500, description="描述")
    entry_date: datetime = Field(..., description="消费日期")
    consumer_id: Optional[int] = Field(None, description="消费人ID（为空表示家庭共同消费）")


class AccountingEntryCreate(AccountingEntryBase):
    """创建记账条目请求"""
    pass


class AccountingEntryPhotoCreate(BaseModel):
    """拍照识别记账请求"""
    image_data: str = Field(..., description="图片Base64数据（需包含data:image前缀）")
    entry_date: Optional[datetime] = Field(None, description="消费日期（可选，默认当前日期）")


class AccountingEntryVoiceCreate(BaseModel):
    """语音输入记账请求"""
    audio_data: str = Field(..., description="音频Base64数据（需包含data:audio前缀）")
    entry_date: Optional[datetime] = Field(None, description="消费日期（可选，默认当前日期）")


class AccountingEntryImport(BaseModel):
    """批量导入记账条目"""
    entries: List[AccountingEntryCreate] = Field(..., description="记账条目列表")


class AccountingEntryUpdate(BaseModel):
    """更新记账条目请求"""
    amount: Optional[float] = Field(None, gt=0, description="金额")
    category: Optional[str] = Field(None, description="分类")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    entry_date: Optional[datetime] = Field(None, description="消费日期")
    consumer_id: Optional[int] = Field(None, description="消费人ID")


class AccountingEntryResponse(AccountingEntryBase):
    """记账条目响应"""
    id: int
    family_id: int
    user_id: int
    source: str
    image_data: Optional[str] = None
    is_accounted: bool
    expense_request_id: Optional[int] = None
    created_at: datetime

    # 额外字段
    user_nickname: Optional[str] = None
    consumer_nickname: Optional[str] = None

    class Config:
        from_attributes = True


class AccountingEntryListResponse(BaseModel):
    """记账条目列表响应"""
    total: int
    page: int
    page_size: int
    entries: List[AccountingEntryResponse]


class AccountingPhotoOCRResponse(BaseModel):
    """拍照识别OCR响应"""
    amount: float
    category: str
    description: str
    confidence: float = Field(..., description="识别置信度 0-1")
    raw_text: str = Field(..., description="OCR原始文本")


class AccountingVoiceTranscriptResponse(BaseModel):
    """语音转文本响应"""
    amount: float
    category: str
    description: str
    transcript: str = Field(..., description="语音转文字原文")


class AccountingBatchExpenseRequest(BaseModel):
    """批量转换为支出申请"""
    entry_ids: List[int] = Field(..., min_length=1, description="记账条目ID列表")
    title: str = Field(..., max_length=200, description="支出申请标题")
    description: Optional[str] = Field(None, max_length=500, description="支出申请描述")


class AccountingCategoryStatsResponse(BaseModel):
    """分类统计响应"""
    category: str
    category_name: str
    total_amount: float
    count: int
    percentage: float


class AccountingStatsResponse(BaseModel):
    """记账统计响应"""
    total_amount: float
    total_count: int
    accounted_amount: float
    accounted_count: int
    unaccounted_amount: float
    unaccounted_count: int
    category_stats: List[AccountingCategoryStatsResponse]
