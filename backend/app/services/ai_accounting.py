"""
小金库 (Golden Nest) - 记账系统 AI 服务
OCR识别小票、语音转文本、自动分类
"""
import base64
import json
import re
import logging
from typing import Optional, List, Dict, Any
from app.schemas.accounting import (
    AccountingPhotoOCRResponse,
    AccountingVoiceTranscriptResponse,
    PhotoRecognizeItem,
)
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


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
            function_key="receipt_ocr",
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


async def transcribe_audio_file(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    使用 AI 音频模型将音频转为文本。

    策略：
    1. 尝试 Whisper API（适用于 OpenAI / Azure）
    2. 使用后台配置的 AI_MODEL，通过 chat/completions 传入音频
       用户需自行在后台将模型切换到支持音频输入的模型，例如：
       - qwen3-omni-flash（推荐，全模态）
       - qwen-omni-turbo
       - qwen3-asr-flash（专用ASR）

    Args:
        audio_bytes: 音频文件的原始字节
        filename: 文件名（用于确定格式）

    Returns:
        转录的文本内容
    """
    import httpx
    from app.core.config import get_active_ai_config, settings

    def _get(key: str) -> str:
        val = get_active_ai_config(key)
        return val if val else getattr(settings, key, "")

    api_key = _get("AI_API_KEY")
    base_url = _get("AI_BASE_URL")

    if not api_key or not base_url:
        raise ValueError("AI 服务未配置")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 根据文件名推断格式
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    # --- 方案1: 尝试 Whisper API（OpenAI / Azure） ---
    whisper_url = f"{base_url.rstrip('/')}/audio/transcriptions"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, audio_bytes)}
            data = {"model": "whisper-1", "language": "zh", "response_format": "json"}
            logger.info(f"Trying Whisper → {whisper_url}")
            resp = await client.post(whisper_url, headers={"Authorization": f"Bearer {api_key}"}, files=files, data=data)
            if resp.status_code < 400:
                result = resp.json()
                text = result.get("text", "").strip()
                if text:
                    logger.info(f"Whisper OK: {text[:100]}")
                    return text
    except Exception as e:
        logger.info(f"Whisper not available: {e}")

    # --- 方案2: 使用后台配置的 AI_MODEL ---
    chat_url = f"{base_url.rstrip('/')}/chat/completions"
    ai_model = _get("AI_MODEL")

    # qwen3-omni-flash 支持的音频格式: AMR, WAV, 3GP, 3GPP, AAC, MP3 等
    # webm/opus 不在官方列表中，但可能兼容；如果不兼容需要转码
    # 尝试用 ffmpeg 将 webm 转为 wav（如果可用）
    actual_audio_b64 = audio_b64
    actual_ext = ext
    if ext in ("webm", "opus", "ogg"):
        try:
            import subprocess
            import tempfile
            import os as _os
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp_in:
                tmp_in.write(audio_bytes)
                tmp_in_path = tmp_in.name
            tmp_out_path = tmp_in_path.rsplit(".", 1)[0] + ".wav"
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_in_path, "-ar", "16000", "-ac", "1", tmp_out_path],
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and _os.path.exists(tmp_out_path):
                with open(tmp_out_path, "rb") as f:
                    wav_bytes = f.read()
                actual_audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
                actual_ext = "wav"
                logger.info(f"Converted {ext} → wav ({len(audio_bytes)} → {len(wav_bytes)} bytes)")
            else:
                logger.warning(f"ffmpeg conversion failed (rc={result.returncode}), using original {ext}")
            # 清理临时文件
            for p in [tmp_in_path, tmp_out_path]:
                try:
                    _os.unlink(p)
                except Exception:
                    pass
        except FileNotFoundError:
            logger.info("ffmpeg not found, sending original audio format")
        except Exception as e:
            logger.warning(f"Audio conversion failed: {e}, using original format")

    # Qwen-Omni 系列模型要求必须 stream=True，否则返回 400
    # input_audio.data 必须使用 data URI 格式: data:audio/{format};base64,{base64}
    audio_data_uri = f"data:audio/{actual_ext};base64,{actual_audio_b64}"
    body = {
        "model": ai_model,
        "messages": [
            {"role": "system", "content": "你是一个语音转文字助手。请将用户的音频内容完整转录为文字，只返回转录文本，不要添加任何额外说明。"},
            {"role": "user", "content": [
                {"type": "input_audio", "input_audio": {"data": audio_data_uri, "format": actual_ext}},
                {"type": "text", "text": "请将这段音频转录为文字。"},
            ]},
        ],
        "modalities": ["text"],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.1,
    }

    logger.info(f"Trying audio transcription (stream) via configured model → {ai_model}, format={actual_ext}")
    error_msg = None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 先发送请求，获取完整响应头
            resp = await client.send(
                client.build_request("POST", chat_url, json=body, headers=headers),
                stream=True,
            )

            try:
                if resp.status_code >= 400:
                    error_body = (await resp.aread()).decode("utf-8", errors="replace")[:500]
                    logger.error(f"Audio stream failed ({ai_model}): {resp.status_code} {error_body}")
                    error_msg = (
                        f"语音转录失败（模型: {ai_model}，状态码: {resp.status_code}）。"
                        f"请在后台将 AI_MODEL 切换到支持音频输入的模型，"
                        f"推荐：qwen3-omni-flash、qwen-omni-turbo、qwen3-asr-flash"
                    )
                else:
                    # 解析 SSE 流式响应，拼接文本
                    collected_text = []
                    async for raw_line in resp.aiter_lines():
                        raw_line = raw_line.strip()
                        if not raw_line or not raw_line.startswith("data:"):
                            continue
                        data_str = raw_line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    collected_text.append(content)
                        except Exception:
                            continue

                    text = "".join(collected_text).strip()
                    if text:
                        logger.info(f"Audio OK ({ai_model}): {text[:100]}")
                        return text
                    else:
                        logger.error(f"Audio stream returned empty text ({ai_model})")
            finally:
                await resp.aclose()

    except ValueError:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Audio error ({ai_model}): {e}\n{traceback.format_exc()}")

    raise ValueError(
        error_msg or (
            f"语音转录失败（模型: {ai_model}）。"
            f"请确认后台 AI_MODEL 已切换到支持音频输入的模型，"
            f"推荐：qwen3-omni-flash、qwen-omni-turbo、qwen3-asr-flash"
        )
    )


async def parse_voice_text(text: str) -> List[PhotoRecognizeItem]:
    """
    使用 AI 将语音转录文本解析为结构化的记账条目。

    Args:
        text: 语音转录的文本

    Returns:
        List[PhotoRecognizeItem]: 识别出的消费条目
    """
    if not text:
        return []

    prompt = f"""你是一个记账助手。用户通过语音说了以下内容：
"{text}"

请从中提取消费记录。用户可能一次说了多条消费。

对每条消费记录，提取：
1. amount: 金额（数字，不含货币符号）。如果说"块"="元"，"毛"="角"=0.1元。
2. description: 消费描述（简短，15字以内）
3. category: 从以下选项选择：
   food(餐饮), transport(交通), shopping(购物), entertainment(娱乐),
   healthcare(医疗), education(教育), housing(住房), utilities(水电煤), other(其他)
4. entry_date: 如果语音中提到了具体日期时间则提取（ISO 8601格式），否则返回 null
5. confidence: 识别置信度（0-1）
6. consumer_type: 判断是"personal"(个人消费)还是"family"(家庭消费)
   - 明确提到"我"、"我自己"或明显是个人行为（如"我买了"、"我吃了"）→ personal
   - 提到"我们"、"全家"、"一家人"、或明显是家庭开支（如水电费、房租）→ family
   - 如果无法判断，默认 family

返回JSON数组（即使只有1条）：
```json
[
  {{"amount": 38.5, "description": "午餐", "category": "food", "entry_date": null, "confidence": 0.9, "consumer_type": "personal"}}
]
```

注意：
- 如果无法识别出任何消费信息，返回空数组 []
- 金额无法确定时设为 0
"""

    try:
        result = await ai_service.chat_json(
            user_prompt=prompt,
            system_prompt="你是记账助手，从语音内容中提取消费记录。只返回JSON。",
            function_key="voice_parse",
            temperature=0.1,
        )

        if result is None:
            return []

        # 结果可能是 dict 包含列表，也可能直接是列表
        items_raw = result if isinstance(result, list) else result.get("items", result.get("entries", []))
        if not isinstance(items_raw, list):
            items_raw = [items_raw]

        items = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            items.append(PhotoRecognizeItem(
                amount=float(item.get("amount", 0)),
                description=str(item.get("description", "消费"))[:50],
                category=str(item.get("category", "other")),
                entry_date=item.get("entry_date"),
                confidence=min(max(float(item.get("confidence", 0.8)), 0), 1),
                consumer_type=str(item.get("consumer_type", "family")),
            ))

        return items if items else []

    except Exception as e:
        logger.error(f"Parse voice text failed: {e}")
        return []


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
            system_prompt="你是一个消费分类助手，根据用户提供的消费信息返回最合适的分类代码。",
            function_key="auto_category",
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
            system_prompt="你是一个重复检测专家，能够准确判断两条记账记录是否为重复。",
            function_key="duplicate_detection",
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


# ============================
# 文件批量导入解析
# ============================

VALID_CATEGORIES = [
    "food", "transport", "shopping", "entertainment",
    "healthcare", "education", "housing", "utilities", "other"
]


async def parse_import_file(file_bytes: bytes, filename: str) -> List[PhotoRecognizeItem]:
    """
    解析上传的文件（Excel/CSV/PDF/图片）为记账条目列表。

    Args:
        file_bytes: 文件的原始字节
        filename: 文件名（用于确定格式）

    Returns:
        List[PhotoRecognizeItem]: 解析出的消费条目列表
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("xlsx", "xls"):
        return await _parse_excel(file_bytes, filename)
    elif ext == "csv":
        return await _parse_csv(file_bytes)
    elif ext == "pdf":
        return await _parse_pdf(file_bytes)
    elif ext in ("jpg", "jpeg", "png", "gif", "bmp", "webp"):
        return await _parse_image(file_bytes, ext)
    else:
        raise ValueError(f"不支持的文件格式: .{ext}。支持的格式：Excel(.xlsx/.xls)、CSV、PDF、图片(.jpg/.png)")


async def _parse_excel(file_bytes: bytes, filename: str) -> List[PhotoRecognizeItem]:
    """解析 Excel 文件"""
    import io
    try:
        import openpyxl
    except ImportError:
        raise ValueError("Excel 解析需要 openpyxl 库，请联系管理员安装")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError("Excel 文件为空或无活动工作表")

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(rows) < 2:
        raise ValueError("Excel 文件至少需要表头行和一行数据")

    # 最多处理 200 行数据
    header = [str(h).strip().lower() if h else "" for h in rows[0]]
    data_rows = rows[1:201]

    # 尝试智能列映射
    col_map = _detect_columns(header)

    if col_map.get("amount") is not None and col_map.get("description") is not None:
        # 直接解析（不需要 AI）
        return _parse_rows_with_mapping(header, data_rows, col_map)
    else:
        # 列名不明确，用 AI 辅助解析
        return await _parse_table_with_ai(header, data_rows)


async def _parse_csv(file_bytes: bytes) -> List[PhotoRecognizeItem]:
    """解析 CSV 文件"""
    import csv
    import io

    # 尝试检测编码
    text = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"):
        try:
            text = file_bytes.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise ValueError("无法识别文件编码，请确保文件为 UTF-8 或 GBK 编码")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if len(rows) < 2:
        raise ValueError("CSV 文件至少需要表头行和一行数据")

    header = [str(h).strip().lower() for h in rows[0]]
    data_rows = [tuple(r) for r in rows[1:201]]

    col_map = _detect_columns(header)

    if col_map.get("amount") is not None and col_map.get("description") is not None:
        return _parse_rows_with_mapping(header, data_rows, col_map)
    else:
        return await _parse_table_with_ai(header, data_rows)


async def _parse_pdf(file_bytes: bytes) -> List[PhotoRecognizeItem]:
    """
    解析 PDF 文件。
    优先用 PyMuPDF 将页面渲染为图片 → 视觉模型解析（效果最佳），
    降级用 pdfplumber 提取文本 → AI 文本解析。
    """
    # ---- 方式 1：PDF → 图片 → 视觉模型（推荐） ----
    try:
        return await _parse_pdf_as_images(file_bytes)
    except ImportError:
        logger.info("PyMuPDF 未安装，降级为文本提取模式解析 PDF")
    except Exception as e:
        logger.warning(f"PDF 图片模式失败({e})，降级为文本提取模式")

    # ---- 方式 2：pdfplumber 提取文本 → AI 解析 ----
    return await _parse_pdf_as_text(file_bytes)


async def _parse_pdf_as_images(file_bytes: bytes) -> List[PhotoRecognizeItem]:
    """将 PDF 每页渲染为图片，发送给视觉模型解析（效果最佳，适合信用卡账单等复杂排版）"""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    if doc.page_count == 0:
        doc.close()
        raise ValueError("PDF 文件无页面")

    image_data_list: List[str] = []
    max_pages = min(doc.page_count, 8)  # 最多 8 页

    for page_num in range(max_pages):
        page = doc[page_num]
        # 150 DPI：兼顾清晰度与传输大小
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        image_data_list.append(f"data:image/png;base64,{img_b64}")

    doc.close()

    if not image_data_list:
        raise ValueError("PDF 文件无可渲染的页面")

    n = len(image_data_list)
    prompt = f"""你是专业的消费记录解析助手。用户上传了一份 PDF 文档（共 {n} 页）。
这可能是信用卡账单、银行流水、消费记录等。

请仔细分析所有页面，提取其中的 **每一笔消费/支出** 记录。

对每条消费记录，提取：
1. amount: 金额（正数，不含货币符号）
2. description: 简短描述（15字以内）
3. category: 分类，从 food/transport/shopping/entertainment/healthcare/education/housing/utilities/other 中选一个
4. entry_date: 消费日期（ISO 8601），无法识别返回 null
5. confidence: 置信度（0-1）
6. consumer_type: 判断是 "personal"(个人消费) 还是 "family"(家庭消费)
   - 明确只涉及一人的消费（如"某某的"、个人话费、个人保险）→ personal
   - 家庭共同开支（如水电费、房租、家庭聚餐、超市采购）→ family
   - 无法判断时默认 family

规则：
- 只提取支出/消费，忽略收入、还款、转账、利息等
- 信用卡账单请提取每笔消费明细
- 金额为正数，跳过汇总行/合计行
- 如果有人民币以外的货币，在 description 中注明

返回JSON数组（即使只有1条）：
[{{"amount": 38.5, "description": "午餐", "category": "food", "entry_date": "2025-01-15T12:30:00", "confidence": 0.9, "consumer_type": "personal"}}]

只返回JSON数组，不要返回任何其他文字。"""

    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for img_b64 in image_data_list:
        content.append({
            "type": "image_url",
            "image_url": {"url": img_b64},
        })

    messages = [
        {"role": "system", "content": "你是消费记录解析助手，从文档图片中精确提取每一笔消费信息并返回JSON数组。只返回JSON，不要解释。"},
        {"role": "user", "content": content},
    ]

    response_text = await ai_service._call_chat(
        messages=messages,
        function_key="import_vision",
        max_tokens=8000,
        temperature=0.1,
    )

    return _extract_items_from_ai_response(response_text, "PDF")


async def _parse_pdf_as_text(file_bytes: bytes) -> List[PhotoRecognizeItem]:
    """降级方案：用 pdfplumber 提取文本后交给 AI 文本模型解析"""
    import io
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("PDF 解析需要 PyMuPDF 或 pdfplumber 库，请联系管理员安装")

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages[:20]:  # 最多处理 20 页
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

            # 也尝试提取表格
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        text_parts.append(" | ".join(str(c) if c else "" for c in row))

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("PDF 文件中未提取到文本内容")

    # 截取前 8000 字符送给 AI
    if len(full_text) > 8000:
        full_text = full_text[:8000] + "\n...(文档内容过长，已截断)"

    return await _parse_text_with_ai(full_text, "PDF")


async def _parse_image(file_bytes: bytes, ext: str) -> List[PhotoRecognizeItem]:
    """解析图片文件（复用现有收据识别）"""
    img_b64 = base64.b64encode(file_bytes).decode("utf-8")
    data_uri = f"data:image/{ext};base64,{img_b64}"
    return await parse_receipt_images([data_uri])


def _detect_columns(header: List[str]) -> Dict[str, Optional[int]]:
    """
    智能检测列名映射。返回 {field: column_index} 的映射。
    """
    amount_names = {"金额", "amount", "amt", "价格", "price", "总价", "total", "合计", "消费金额",
                    "支出", "cost", "花费", "money", "sum", "收入", "支出金额"}
    desc_names = {"描述", "description", "desc", "备注", "remark", "note", "说明", "商品",
                  "内容", "摘要", "summary", "detail", "详情", "名称", "商品名称", "项目",
                  "交易说明", "comment", "comments", "memo", "用途"}
    date_names = {"日期", "date", "时间", "time", "交易日期", "消费日期", "entry_date",
                  "交易时间", "创建时间", "记录日期", "datetime", "发生日期"}
    cat_names = {"分类", "category", "类别", "类型", "type", "消费分类", "kind"}

    col_map: Dict[str, Optional[int]] = {
        "amount": None, "description": None, "date": None, "category": None
    }

    for i, h in enumerate(header):
        h_lower = h.strip().lower()
        if col_map["amount"] is None and h_lower in amount_names:
            col_map["amount"] = i
        elif col_map["description"] is None and h_lower in desc_names:
            col_map["description"] = i
        elif col_map["date"] is None and h_lower in date_names:
            col_map["date"] = i
        elif col_map["category"] is None and h_lower in cat_names:
            col_map["category"] = i

    return col_map


def _parse_rows_with_mapping(
    header: List[str],
    data_rows: List[tuple],
    col_map: Dict[str, Optional[int]]
) -> List[PhotoRecognizeItem]:
    """根据列映射直接解析行数据"""
    from dateutil import parser as date_parser

    items = []
    for row in data_rows:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        # 解析金额
        amount = 0.0
        if col_map["amount"] is not None and col_map["amount"] < len(row):
            raw_amount = row[col_map["amount"]]
            if raw_amount is not None:
                try:
                    # 清理金额字符串: 去掉 ¥, $, 逗号等
                    cleaned = str(raw_amount).replace("¥", "").replace("￥", "").replace(
                        "$", "").replace(",", "").replace(" ", "").strip()
                    # 处理负数（有些导出用负数表示支出）
                    amount = abs(float(cleaned))
                except (ValueError, TypeError):
                    continue  # 金额解析失败，跳过该行

        if amount <= 0:
            continue

        # 解析描述
        description = "消费"
        if col_map["description"] is not None and col_map["description"] < len(row):
            raw_desc = row[col_map["description"]]
            if raw_desc:
                description = str(raw_desc).strip()[:100]

        # 解析日期
        entry_date = None
        if col_map["date"] is not None and col_map["date"] < len(row):
            raw_date = row[col_map["date"]]
            if raw_date:
                try:
                    from datetime import datetime as _dt
                    if isinstance(raw_date, _dt):
                        entry_date = raw_date.isoformat()
                    else:
                        parsed_dt = date_parser.parse(str(raw_date), fuzzy=True)
                        entry_date = parsed_dt.isoformat()
                except Exception:
                    pass

        # 解析分类
        category = "other"
        if col_map["category"] is not None and col_map["category"] < len(row):
            raw_cat = row[col_map["category"]]
            if raw_cat:
                category = _map_category(str(raw_cat).strip())

        items.append(PhotoRecognizeItem(
            amount=amount,
            description=description,
            category=category,
            entry_date=entry_date,
            confidence=0.9,
        ))

    if not items:
        raise ValueError("未能从文件中解析出有效的消费记录")
    return items


def _map_category(raw: str) -> str:
    """将中文分类名映射到枚举值"""
    raw_lower = raw.lower()
    mapping = {
        "餐饮": "food", "食品": "food", "吃饭": "food", "外卖": "food", "food": "food", "餐": "food",
        "交通": "transport", "出行": "transport", "transport": "transport", "打车": "transport",
        "购物": "shopping", "网购": "shopping", "shopping": "shopping",
        "娱乐": "entertainment", "休闲": "entertainment", "entertainment": "entertainment",
        "医疗": "healthcare", "医药": "healthcare", "healthcare": "healthcare",
        "教育": "education", "学习": "education", "education": "education",
        "住房": "housing", "房租": "housing", "housing": "housing",
        "水电": "utilities", "水电煤": "utilities", "utilities": "utilities", "缴费": "utilities",
    }
    for key, val in mapping.items():
        if key in raw_lower:
            return val
    return "other"


async def _parse_table_with_ai(header: List[str], data_rows: List[tuple]) -> List[PhotoRecognizeItem]:
    """用 AI 解析表格数据（列名不明确时的兜底方案）"""
    # 构建表格文本（限制大小）
    rows_text = " | ".join(header) + "\n"
    for row in data_rows[:50]:  # AI 最多解析 50 行
        row_str = " | ".join(str(c) if c is not None else "" for c in row)
        rows_text += row_str + "\n"

    return await _parse_text_with_ai(rows_text, "表格")


def _extract_items_from_ai_response(response_text: str, source_type: str) -> List[PhotoRecognizeItem]:
    """
    从 AI 回复中提取记账条目列表。
    处理：思考标签、markdown 代码块、纯 JSON 等多种返回格式。
    """
    # 1. 去除 <think>...</think> 等思考标签
    cleaned = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
    if not cleaned:
        raise ValueError(f"AI 解析{source_type}返回内容为空")

    # 2. 提取 JSON：先尝试 markdown 代码块，再尝试裸 JSON
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned, re.DOTALL)
    json_str = json_match.group(1) if json_match else cleaned

    arr_match = re.search(r'\[.*\]', json_str, re.DOTALL)
    if arr_match:
        json_str = arr_match.group(0)

    try:
        results = json.loads(json_str)
    except json.JSONDecodeError:
        # 再尝试：去掉首尾非 JSON 字符后重试
        stripped = json_str.strip()
        if stripped.startswith('['):
            # 可能 JSON 尾部有多余字符
            bracket_count = 0
            end_idx = 0
            for i, ch in enumerate(stripped):
                if ch == '[':
                    bracket_count += 1
                elif ch == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            if end_idx:
                try:
                    results = json.loads(stripped[:end_idx])
                except json.JSONDecodeError:
                    logger.error(f"AI 回复 JSON 解析失败: {stripped[:500]}")
                    raise ValueError(f"AI 解析{source_type}结果格式异常，请检查文件内容")
            else:
                raise ValueError(f"AI 解析{source_type}结果格式异常，请检查文件内容")
        else:
            logger.error(f"AI 回复非 JSON 格式: {stripped[:500]}")
            raise ValueError(f"AI 解析{source_type}结果格式异常，请检查文件内容")

    if isinstance(results, dict):
        results = [results]

    items = []
    for r in results:
        try:
            amount = abs(float(r.get("amount", 0)))
            if amount <= 0:
                continue

            category = str(r.get("category", "other"))
            if category not in VALID_CATEGORIES:
                category = "other"

            consumer_type = str(r.get("consumer_type", "family"))
            if consumer_type not in ("personal", "family"):
                consumer_type = "family"

            items.append(PhotoRecognizeItem(
                amount=amount,
                description=str(r.get("description", "消费"))[:100],
                category=category,
                entry_date=r.get("entry_date"),
                confidence=min(1.0, max(0.0, float(r.get("confidence", 0.7)))),
                consumer_type=consumer_type,
            ))
        except (ValueError, TypeError):
            continue

    if not items:
        raise ValueError(f"AI 未能从{source_type}中识别出消费记录")
    return items


async def _parse_text_with_ai(text: str, source_type: str) -> List[PhotoRecognizeItem]:
    """通用的 AI 文本→记账条目解析"""
    prompt = f"""你是专业的消费记录解析助手。以下是从{source_type}中提取的文本内容，请从中识别所有消费记录。

文本内容：
{text}

对每条消费记录，提取以下字段：
1. amount: 金额（数字，不含货币符号。支出用正数）
2. description: 简短描述（15字以内）
3. category: 消费分类，必须从以下选项选一个：
   food(餐饮), transport(交通), shopping(购物), entertainment(娱乐),
   healthcare(医疗), education(教育), housing(住房), utilities(水电煤), other(其他)
4. entry_date: 消费日期时间（ISO 8601格式），无法识别返回 null
5. confidence: 识别置信度（0-1）
6. consumer_type: 判断是 "personal"(个人消费) 还是 "family"(家庭消费)
   - 明确只涉及一人的消费（如个人话费、个人保险、某人名下消费）→ personal
   - 家庭共同开支（如水电费、房租、家庭聚餐、超市采购）→ family
   - 无法判断时默认 family

注意：
- 忽略收入记录，只关注支出/消费
- 如果同一条目出现多个子项，合并为总计
- 金额为0或无法确定的记录跳过

返回JSON数组：
```json
[{{"amount": 38.5, "description": "午餐", "category": "food", "entry_date": "2024-01-15T12:30:00", "confidence": 0.9, "consumer_type": "personal"}}]
```
只返回JSON数组，不要返回其他内容。"""

    try:
        response_text = await ai_service.chat(
            user_prompt=prompt,
            system_prompt="你是消费记录解析助手，从文本中提取消费信息并返回JSON数组。只返回JSON，不要解释。",
            function_key="import_parse",
            temperature=0.1,
            max_tokens=4000,
        )

        return _extract_items_from_ai_response(response_text, source_type)

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"{source_type}解析失败: {str(e)[:100]}")

