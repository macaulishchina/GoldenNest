"""
小金库 (Golden Nest) - 资产凭证图片解析服务
通过 AI 视觉模型（OpenAI兼容格式）识别图片内容并提取资产信息
"""
import json
import logging
import base64
import io
import re
import asyncio
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# 支持的资产类型映射（中文 → 系统枚举值）
ASSET_TYPE_KEYWORDS = {
    "time_deposit": ["定期", "定存", "整存整取", "零存整取", "存单", "大额存单", "通知存款", "结构性存款", "存款"],
    "fund": ["基金", "货币基金", "指数基金", "混合基金", "债券基金", "ETF", "FOF", "QDII", "定投"],
    "stock": ["股票", "股份", "A股", "港股", "美股", "证券"],
    "bond": ["债券", "国债", "企业债", "可转债", "公司债"],
    "other": ["保险", "信托", "理财", "黄金", "贵金属", "期货", "期权", "外汇"]
}

# 币种映射
CURRENCY_KEYWORDS = {
    "CNY": ["人民币", "¥", "￥", "RMB", "CNY", "元"],
    "USD": ["美元", "$", "USD", "美金"],
    "HKD": ["港币", "港元", "HKD", "HK$"],
    "JPY": ["日元", "日币", "JPY"],
    "EUR": ["欧元", "EUR", "€"],
    "GBP": ["英镑", "GBP", "£"],
    "AUD": ["澳元", "AUD", "A$"],
    "CAD": ["加元", "CAD", "C$"],
    "SGD": ["新加坡元", "新币", "SGD", "S$"],
    "KRW": ["韩元", "韩币", "KRW", "₩"]
}

# AI 提示词
SYSTEM_PROMPT = """你是一个专业的金融凭证图片解析助手。用户会上传银行存款凭证、基金购买确认单、投资产品截图等图片。
你需要从图片中提取以下信息，返回一个JSON对象。

字段说明：
- name: 产品名称（如"招商银行定期存款"、"易方达沪深300ETF"等）
- asset_type: 资产类型，只能是以下值之一: time_deposit(定期存款), fund(基金), stock(股票), bond(债券), other(其他)
- currency: 币种代码，只能是: CNY, USD, HKD, JPY, EUR, GBP, AUD, CAD, SGD, KRW
- amount: 金额数字（不带货币符号和千位分隔符，纯数字）
- start_date: 开始日期/购买日期/起息日，格式 YYYY-MM-DD
- end_date: 到期日期/结束日期，格式 YYYY-MM-DD（如果有的话）
- bank_name: 银行或金融机构名称
- note: 其他有用的备注信息（利率、产品代码等）

规则：
1. 只返回JSON对象，不要其他文字
2. 无法识别的字段设为 null
3. amount 必须是纯数字，不能包含逗号或货币符号
4. 尽你所能从图片中提取最多的信息
5. 如果图片不是金融凭证，返回 {"error": "无法识别为金融凭证"}"""

USER_PROMPT = """请分析这张图片，从中提取资产/投资相关信息，严格按照JSON格式返回结果。"""


class ImageParserService:
    """资产凭证图片解析服务"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """检查 AI 服务是否已配置"""
        return bool(settings.AI_API_KEY)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def parse_image(self, image_base64: str) -> Dict[str, Any]:
        """
        解析资产凭证图片
        
        Args:
            image_base64: Base64 编码的图片（可带或不带 data:image/xxx;base64, 前缀）
        
        Returns:
            解析结果字典，包含识别出的字段
        """
        if not self.is_configured:
            raise ValueError("AI 服务未配置，请在 .env 中设置 AI_API_KEY")
        
        # 处理 base64 前缀
        image_data = image_base64
        mime_type = "image/jpeg"
        if image_base64.startswith("data:"):
            # 提取 MIME 类型和数据
            match = re.match(r"data:(image/[^;]+);base64,(.*)", image_base64, re.DOTALL)
            if match:
                mime_type = match.group(1)
                image_data = match.group(2)
        
        # 验证 base64 有效性
        try:
            decoded = base64.b64decode(image_data)
            if len(decoded) > 20 * 1024 * 1024:  # 20MB
                raise ValueError("图片文件过大，请使用小于 20MB 的图片")
        except Exception as e:
            if "图片文件过大" in str(e):
                raise
            raise ValueError(f"无效的图片数据: {str(e)}")
        
        # 压缩图片以减少 token 消耗（目标: 短边不超过 768px）
        image_data, mime_type = self._compress_image(decoded, mime_type)
        
        # 构建请求
        data_url = f"data:{mime_type};base64,{image_data}"
        
        request_body = {
            "model": settings.AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": USER_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url,
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1
        }
        
        # 调用 API
        client = await self._get_client()
        api_url = f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions"
        
        logger.info(f"Calling AI vision API: {api_url}, model: {settings.AI_MODEL}")
        
        # 带重试的 API 调用（429 自动重试最多2次）
        max_retries = 2
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    api_url,
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {settings.AI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                break  # 成功，跳出重试循环
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < max_retries:
                    # 从响应头提取等待时间，默认等 5 秒
                    retry_after = int(e.response.headers.get("retry-after", "5"))
                    retry_after = min(retry_after, 30)  # 最多等 30 秒
                    logger.warning(f"AI API rate limited (429), retry after {retry_after}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                    continue
                logger.error(f"AI API HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 429:
                    raise ValueError("AI 服务请求频率超限，请稍后再试（建议等待 30 秒）")
                raise ValueError(f"AI 服务调用失败: HTTP {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"AI API request error: {e}")
                raise ValueError(f"AI 服务连接失败: {str(e)}")
        else:
            # 所有重试都失败
            if last_error:
                raise ValueError("AI 服务请求频率超限，请稍后再试（建议等待 30 秒）")
        
        # 解析响应
        result = response.json()
        
        if "choices" not in result or not result["choices"]:
            logger.error(f"AI API unexpected response: {result}")
            raise ValueError("AI 服务返回了意外的结果")
        
        content = result["choices"][0]["message"]["content"].strip()
        logger.info(f"AI raw response: {content}")
        
        # 提取 JSON（处理可能的 markdown 代码块包裹）
        parsed = self._extract_json(content)
        
        if parsed is None:
            logger.warning(f"Failed to parse AI response as JSON: {content}")
            raise ValueError("AI 返回的结果无法解析")
        
        if "error" in parsed:
            return parsed
        
        # 校验和标准化字段
        return self._normalize_result(parsed)
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """从 AI 响应中提取 JSON"""
        # 先尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试从 markdown 代码块中提取
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _normalize_result(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """标准化解析结果"""
        result: Dict[str, Any] = {}
        
        # 产品名称
        if parsed.get("name"):
            result["name"] = str(parsed["name"]).strip()
        
        # 资产类型
        asset_type = parsed.get("asset_type")
        valid_types = {"time_deposit", "fund", "stock", "bond", "other"}
        if asset_type in valid_types:
            result["asset_type"] = asset_type
        elif asset_type:
            # 尝试通过关键词匹配
            result["asset_type"] = self._match_asset_type(str(asset_type))
        
        # 币种
        currency = parsed.get("currency")
        valid_currencies = {"CNY", "USD", "HKD", "JPY", "EUR", "GBP", "AUD", "CAD", "SGD", "KRW"}
        if currency and currency.upper() in valid_currencies:
            result["currency"] = currency.upper()
        
        # 金额
        amount = parsed.get("amount")
        if amount is not None:
            try:
                # 清理可能的非数字字符
                amount_str = str(amount).replace(",", "").replace("，", "").strip()
                amount_str = re.sub(r"[^\d.]", "", amount_str)
                result["amount"] = float(amount_str)
            except (ValueError, TypeError):
                pass
        
        # 日期
        for date_field in ["start_date", "end_date"]:
            date_val = parsed.get(date_field)
            if date_val:
                normalized_date = self._normalize_date(str(date_val))
                if normalized_date:
                    result[date_field] = normalized_date
        
        # 银行名称
        if parsed.get("bank_name"):
            result["bank_name"] = str(parsed["bank_name"]).strip()
        
        # 备注
        if parsed.get("note"):
            result["note"] = str(parsed["note"]).strip()
        
        return result
    
    def _match_asset_type(self, text: str) -> str:
        """通过关键词匹配资产类型"""
        text = text.lower()
        for asset_type, keywords in ASSET_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return asset_type
        return "other"
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """标准化日期格式为 YYYY-MM-DD"""
        if not date_str or date_str == "null":
            return None
        
        # 替换中文日期分隔符
        date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
        date_str = date_str.replace("/", "-").strip()
        
        # 尝试匹配 YYYY-MM-DD
        match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        # 尝试匹配 YYYY.MM.DD
        match = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        return None
    
    def _compress_image(self, image_bytes: bytes, mime_type: str) -> tuple:
        """
        压缩图片以减少 token 消耗
        短边缩放到不超过 768px，转为 JPEG 质量 85
        
        Returns:
            (base64_str, mime_type)
        """
        try:
            from PIL import Image
            
            img = Image.open(io.BytesIO(image_bytes))
            
            # 如果是 RGBA，转为 RGB
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            
            # 短边不超过 768px
            max_short = 768
            w, h = img.size
            short_side = min(w, h)
            if short_side > max_short:
                scale = max_short / short_side
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                logger.info(f"Image resized: {w}x{h} -> {new_w}x{new_h}")
            
            # 压缩为 JPEG
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            compressed = buf.getvalue()
            
            logger.info(f"Image compressed: {len(image_bytes)} -> {len(compressed)} bytes")
            return base64.b64encode(compressed).decode("utf-8"), "image/jpeg"
        except ImportError:
            logger.warning("Pillow not installed, skipping image compression")
            return base64.b64encode(image_bytes).decode("utf-8"), mime_type
        except Exception as e:
            logger.warning(f"Image compression failed, using original: {e}")
            return base64.b64encode(image_bytes).decode("utf-8"), mime_type
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# 全局单例
image_parser_service = ImageParserService()
