"""
小金库 (Golden Nest) - 记账系统 AI 服务
OCR识别小票、语音转文本、自动分类
"""
import base64
import json
import re
from typing import Optional, List, Dict, Any
from app.schemas.accounting import (
    AccountingPhotoOCRResponse,
    AccountingVoiceTranscriptResponse,
    PhotoRecognizeItem,
)
from app.services.ai_service import ai_service


async def parse_receipt_images(image_data_list: List[str]) -> List[PhotoRecognizeItem]:
    """
    解析一张或多张消费凭证图片，智能判断是一次消费还是多次消费。

    Args:
        image_data_list: Base64编码的图片数据列表（每张包含data:image前缀）

    Returns:
        List[PhotoRecognizeItem]: 识别出的消费条目列表（可能1条也可能多条）
    """
    n = len(image_data_list)
    prompt = f"""你是专业的消费凭证识别助手。用户上传了 {n} 张图片。

请仔细分析所有图片，判断它们代表的消费情况：
- 多张图片可能是同一笔消费的不同角度/页面（如小票正反面），此时合并为1条记录
- 多张图片也可能是不同的消费记录，此时分别提取每条记录
- 单张图片中也可能包含多条消费记录（如月账单），此时拆分为多条

对每条消费记录，提取以下字段：
1. amount: 总金额（数字，不含货币符号）
2. description: 商品或服务的简短描述（15字以内）
3. category: 消费分类，必须从以下选项中选一个：
   food(餐饮), transport(交通), shopping(购物), entertainment(娱乐),
   healthcare(医疗), education(教育), housing(住房), utilities(水电煤), other(其他)
4. entry_date: 消费日期时间（ISO 8601格式，如 "2025-10-25T14:13:00"）。
   如果图片中有明确日期则提取；如果无法识别则返回 null
5. confidence: 识别置信度（0-1之间的数字）

返回JSON数组格式，即使只有1条也用数组：
```json
[
  {{
    "amount": 51.04,
    "description": "Steam游戏购买",
    "category": "entertainment",
    "entry_date": "2025-10-25T14:13:00",
    "confidence": 0.95
  }}
]
```

注意：
- 金额无法识别时返回 0
- 描述无法识别时返回 "消费"
- 分类不确定时返回 "other"
- 日期无法识别时 entry_date 返回 null
- 只返回JSON数组，不要返回其他内容
"""

    try:
        # 构建多图消息内容
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img_b64 in image_data_list:
            if not img_b64.startswith("data:"):
                img_b64 = f"data:image/jpeg;base64,{img_b64}"
            content.append({
                "type": "image_url",
                "image_url": {"url": img_b64},
            })

        # 直接构建消息调用底层API
        messages = [
            {"role": "system", "content": "你是专业的消费凭证识别助手，能从小票、发票、订单截图、账单等各类图片中准确提取消费信息。只返回JSON。"},
            {"role": "user", "content": content},
        ]

        response_text = await ai_service._call_chat(
            messages=messages,
            max_tokens=4000,
            temperature=0.1,
        )

        # 解析JSON数组
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        json_str = json_match.group(1) if json_match else response_text

        # 尝试提取 [ ... ]
        arr_match = re.search(r'\[.*\]', json_str, re.DOTALL)
        if arr_match:
            json_str = arr_match.group(0)

        results = json.loads(json_str)
        if isinstance(results, dict):
            results = [results]

        valid_categories = [
            "food", "transport", "shopping", "entertainment",
            "healthcare", "education", "housing", "utilities", "other"
        ]

        items = []
        for r in results:
            category = str(r.get("category", "other"))
            if category not in valid_categories:
                category = "other"

            entry_date = r.get("entry_date")
            if entry_date and isinstance(entry_date, str):
                # 保持字符串格式，前端/API层再解析
                pass
            else:
                entry_date = None

            items.append(PhotoRecognizeItem(
                amount=float(r.get("amount", 0)),
                description=str(r.get("description", "消费")),
                category=category,
                entry_date=entry_date,
                confidence=min(1.0, max(0.0, float(r.get("confidence", 0.8)))),
            ))

        return items if items else [PhotoRecognizeItem(
            amount=0, description="识别失败", category="other",
            entry_date=None, confidence=0.0
        )]

    except Exception as e:
        return [PhotoRecognizeItem(
            amount=0, description=f"识别失败: {str(e)[:50]}",
            category="other", entry_date=None, confidence=0.0
        )]


async def transcribe_voice(audio_data: str) -> AccountingVoiceTranscriptResponse:
    """
    将语音转换为记账信息

    Args:
        audio_data: Base64编码的音频数据（包含data:audio前缀）

    Returns:
        AccountingVoiceTranscriptResponse: 包含金额、分类、描述的响应对象
    """
    # 注意：OpenAI API需要音频文件，但这里我们简化处理
    # 实际生产环境中，应该使用Whisper API或其他语音识别服务

    # 这里使用模拟实现（假设用户语音内容被转录为文本）
    # 实际应用中，需要调用Whisper或其他ASR服务

    # 构造提示词（假设已经有转录文本）
    prompt = """假设我刚刚说了一句话来记账，例如：
"中午吃饭花了38块5"
"打车去公司15元"
"买了一本书59.9元"

请从这句话中提取以下信息（以JSON格式返回）：
1. amount: 金额（数字）
2. description: 消费描述
3. category: 消费分类（从以下选项中选择）：
   food, transport, shopping, entertainment, healthcare, education, housing, utilities, other

由于当前仅支持文本模拟，请根据常见语音记账场景返回默认值。

返回格式示例：
{
  "amount": 38.5,
  "description": "午餐",
  "category": "food",
  "transcript": "中午吃饭花了38块5"
}
"""

    try:
        # 模拟语音转文本（实际应调用Whisper API）
        # 这里简化处理：假设用户说了"消费50元"
        transcript_text = "语音记账（当前为模拟数据）"

        # 调用AI分析语音内容
        response_text = await ai_service.chat(
            user_prompt=prompt,
            system_prompt="你是一个记账助手，专门从用户的语音转录文本中提取金额、描述和分类。"
        )

        # 解析JSON响应
        import json

        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response_text

        result = json.loads(json_str)

        # 验证并提取字段
        amount = float(result.get("amount", 0))
        description = str(result.get("description", "消费"))
        category = str(result.get("category", "other"))
        transcript = str(result.get("transcript", transcript_text))

        # 验证分类有效性
        valid_categories = [
            "food", "transport", "shopping", "entertainment",
            "healthcare", "education", "housing", "utilities", "other"
        ]
        if category not in valid_categories:
            category = "other"

        return AccountingVoiceTranscriptResponse(
            amount=amount,
            category=category,
            description=description,
            transcript=transcript
        )

    except Exception as e:
        # 语音识别失败时返回默认值
        return AccountingVoiceTranscriptResponse(
            amount=0,
            category="other",
            description="识别失败",
            transcript=str(e)
        )


async def categorize_entry(description: str, amount: Optional[float] = None) -> str:
    """
    根据描述和金额自动判断消费分类

    Args:
        description: 消费描述
        amount: 消费金额（可选）

    Returns:
        str: 分类代码（food/transport/shopping等）
    """
    prompt = f"""请根据以下消费信息判断分类：
描述：{description}
金额：{amount if amount else '未知'}元

请从以下分类中选择最合适的一个（仅返回英文代码）：
- food: 餐饮（如外卖、餐厅、超市食品）
- transport: 交通（如打车、公交、地铁、加油）
- shopping: 购物（如衣服、日用品、电子产品）
- entertainment: 娱乐（如电影、游戏、旅游）
- healthcare: 医疗（如看病、买药、体检）
- education: 教育（如培训、书籍、课程）
- housing: 住房（如房租、房贷、装修）
- utilities: 水电煤（如水费、电费、燃气费、物业费）
- other: 其他（无法归类时选择）

仅返回分类代码，不要返回其他内容。
"""

    try:
        category = await ai_service.chat(
            user_prompt=prompt,
            system_prompt="你是一个消费分类助手，根据用户提供的消费信息返回最合适的分类代码。"
        )

        # 清理返回值（去除可能的空格、换行）
        category = category.strip().lower()

        # 验证分类有效性
        valid_categories = [
            "food", "transport", "shopping", "entertainment",
            "healthcare", "education", "housing", "utilities", "other"
        ]

        if category in valid_categories:
            return category
        else:
            return "other"

    except Exception:
        return "other"


async def check_duplicate_with_ai(
    new_entry_description: str,
    new_entry_amount: float,
    new_entry_category: str,
    existing_entry_description: str,
    existing_entry_amount: float,
    existing_entry_category: str
) -> tuple[float, str]:
    """
    使用AI判断两条记账记录是否为重复

    Args:
        new_entry_description: 新记录描述
        new_entry_amount: 新记录金额
        new_entry_category: 新记录分类
        existing_entry_description: 已存在记录描述
        existing_entry_amount: 已存在记录金额
        existing_entry_category: 已存在记录分类

    Returns:
        tuple[float, str]: (相似度分数 0-1, 判断理由)
    """
    prompt = f"""请判断以下两条记账记录是否为重复记录，并给出相似度分数（0-1之间）。

新记录：
- 描述：{new_entry_description}
- 金额：¥{new_entry_amount}
- 分类：{new_entry_category}

已存在记录：
- 描述：{existing_entry_description}
- 金额：¥{existing_entry_amount}
- 分类：{existing_entry_category}

请以JSON格式返回判断结果：
{{
  "similarity_score": 0.85,
  "reason": "两条记录的金额相同，描述高度相似，很可能是同一笔消费的重复记录"
}}

判断标准：
- 1.0: 完全相同的记录（金额、描述、分类都一致）
- 0.8-0.9: 很可能是重复（金额相同，描述相似）
- 0.5-0.7: 可能是重复（金额或描述有一定相似性）
- 0.0-0.4: 不是重复（差异明显）

注意：
- 金额完全相同时，相似度至少0.5
- 描述语义相同但表述不同时（如"超市购物"和"去超市买东西"），也应判定为高相似度
- 分类不同但金额和描述都相似时，也可能是重复（用户可能选错分类）
"""

    try:
        response_text = await ai_service.chat(
            user_prompt=prompt,
            system_prompt="你是一个重复检测专家，能够准确判断两条记账记录是否为重复。"
        )

        # 解析JSON响应
        import json
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response_text

        result = json.loads(json_str)
        similarity_score = float(result.get("similarity_score", 0.5))
        reason = str(result.get("reason", "AI判断相似度"))

        # 确保相似度在0-1范围内
        similarity_score = max(0.0, min(1.0, similarity_score))

        return similarity_score, reason

    except Exception as e:
        # AI判断失败时，返回保守的相似度
        return 0.3, f"AI判断失败，请人工确认: {str(e)}"

