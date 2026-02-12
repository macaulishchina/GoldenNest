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
    has_image: bool = False
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
    """拍照识别OCR响应（旧版，保留兼容）"""
    amount: float
    category: str
    description: str
    confidence: float = Field(..., description="识别置信度 0-1")
    raw_text: str = Field(..., description="OCR原始文本")


class PhotoRecognizeItem(BaseModel):
    """单条图片识别结果"""
    amount: float = Field(0, description="金额")
    description: str = Field("消费", description="消费描述")
    category: str = Field("other", description="消费分类")
    entry_date: Optional[str] = Field(None, description="消费日期 ISO格式，null表示无法识别")
    confidence: float = Field(0.8, ge=0, le=1, description="识别置信度 0-1")


class PhotoRecognizeResponse(BaseModel):
    """图片识别响应"""
    items: List[PhotoRecognizeItem] = Field(..., description="识别出的消费条目列表")
    image_paths: List[str] = Field(default_factory=list, description="已保存的图片路径列表")


class PhotoCreateRequest(BaseModel):
    """确认创建记账条目请求（基于识别结果）"""
    items: List[PhotoRecognizeItem] = Field(..., min_length=1, description="确认的消费条目列表")
    image_paths: List[str] = Field(default_factory=list, description="关联的图片路径列表")


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


class DuplicateCheckRequest(BaseModel):
    """重复检测请求"""
    entries: List[AccountingEntryCreate] = Field(..., description="待检测的记账条目列表")


class DuplicateMatchLevel(str):
    """重复匹配级别"""
    EXACT = "exact"           # 完全匹配（时间+金额完全相同）
    LIKELY = "likely"         # 很可能重复（AI判断相似度高）
    POSSIBLE = "possible"     # 可能重复（有一定相似性）
    UNIQUE = "unique"         # 不重复


class DuplicateMatch(BaseModel):
    """重复匹配结果"""
    existing_entry_id: int = Field(..., description="已存在记账条目的ID")
    existing_entry: AccountingEntryResponse = Field(..., description="已存在的记账条目详情")
    match_level: str = Field(..., description="匹配级别: exact/likely/possible/unique")
    similarity_score: float = Field(..., description="相似度分数 0-1")
    match_reasons: List[str] = Field(..., description="匹配原因列表")


class DuplicateCheckResult(BaseModel):
    """单个条目的重复检测结果"""
    index: int = Field(..., description="原始列表中的索引")
    entry_data: AccountingEntryCreate = Field(..., description="待检测的记账条目数据")
    is_duplicate: bool = Field(..., description="是否为重复")
    match_level: str = Field(..., description="匹配级别")
    duplicates: List[DuplicateMatch] = Field(default_factory=list, description="匹配到的重复条目列表")


class DuplicateCheckResponse(BaseModel):
    """重复检测响应"""
    results: List[DuplicateCheckResult] = Field(..., description="检测结果列表")
    exact_duplicates_count: int = Field(..., description="完全匹配的数量")
    likely_duplicates_count: int = Field(..., description="很可能重复的数量")
    possible_duplicates_count: int = Field(..., description="可能重复的数量")
    unique_count: int = Field(..., description="不重复的数量")
