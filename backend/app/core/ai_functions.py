"""
小金库 (Golden Nest) - AI 功能注册表

定义系统中所有使用 AI 的功能模块，以及每个功能推荐的模型类型和默认模型。
管理员可以为每个功能单独配置不同的服务商+模型组合。

设计原则：
- 每个 AI 功能有一个唯一的 function_key
- 每个功能标注所需的能力类型（text/vision/audio/...）
- 提供 DashScope 下的推荐默认模型
- 未配置的功能自动使用全局默认服务商+模型
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AIFunctionDef:
    """AI 功能定义"""
    key: str                        # 唯一标识，如 "receipt_ocr"
    name: str                       # 显示名称，如 "小票/发票识别"
    description: str                # 功能说明
    capability: str                 # 所需能力: text, vision, audio, text_json, vision_json
    group: str                      # 功能分组，便于 UI 展示
    default_model: str              # DashScope 推荐默认模型
    alternative_models: List[str] = field(default_factory=list)  # 备选模型列表


# ==================== AI 功能注册表 ====================
# 按功能分组排列

AI_FUNCTION_REGISTRY: Dict[str, AIFunctionDef] = {}


def _register(*funcs: AIFunctionDef):
    for f in funcs:
        AI_FUNCTION_REGISTRY[f.key] = f


# ---- 记账相关 ----
_register(
    AIFunctionDef(
        key="receipt_ocr",
        name="小票/发票识别",
        description="从拍照的小票、发票、订单截图中提取消费信息",
        capability="vision",
        group="accounting",
        default_model="qwen3-vl-plus",
        alternative_models=["qwen-vl-max", "qwen3-vl-flash", "qwen-vl-plus"],
    ),
    AIFunctionDef(
        key="voice_transcription",
        name="语音转文字",
        description="将录音转为文字（语音记账、AI对话语音输入）",
        capability="audio",
        group="accounting",
        default_model="qwen3-omni-flash",
        alternative_models=["qwen-omni-turbo"],
    ),
    AIFunctionDef(
        key="voice_parse",
        name="语音内容解析",
        description="从转录文本中提取结构化消费记录",
        capability="text_json",
        group="accounting",
        default_model="qwen-plus",
        alternative_models=["qwen-turbo", "qwen3-max", "qwen-flash"],
    ),
    AIFunctionDef(
        key="auto_category",
        name="自动分类",
        description="根据消费描述自动推断消费分类",
        capability="text",
        group="accounting",
        default_model="qwen-flash",
        alternative_models=["qwen-turbo", "qwen-plus"],
    ),
    AIFunctionDef(
        key="duplicate_detection",
        name="重复检测",
        description="AI判断两条记账记录是否重复",
        capability="text",
        group="accounting",
        default_model="qwen-flash",
        alternative_models=["qwen-turbo", "qwen-plus"],
    ),
    AIFunctionDef(
        key="import_parse",
        name="批量导入解析",
        description="从PDF/Excel/CSV文件中提取消费记录（文本模式）",
        capability="text",
        group="accounting",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
    AIFunctionDef(
        key="import_vision",
        name="批量导入视觉解析",
        description="从PDF页面图片中提取消费记录（视觉模式，如信用卡账单）",
        capability="vision",
        group="accounting",
        default_model="qwen3-vl-plus",
        alternative_models=["qwen-vl-max", "qwen3-vl-flash"],
    ),
)

# ---- 资产相关 ----
_register(
    AIFunctionDef(
        key="asset_ocr",
        name="资产凭证识别",
        description="从金融文件图片中提取资产信息（存单、保险单等）",
        capability="vision",
        group="asset",
        default_model="qwen3-vl-plus",
        alternative_models=["qwen-vl-max", "qwen3-vl-flash"],
    ),
)

# ---- AI 对话 ----
_register(
    AIFunctionDef(
        key="chat_tool_call",
        name="AI对话-工具调用",
        description="AI助手决策调用哪些数据查询工具",
        capability="text_json",
        group="chat",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
    AIFunctionDef(
        key="chat_reply",
        name="AI对话-回复生成",
        description="AI助手生成最终回复（结合工具查询结果）",
        capability="text",
        group="chat",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
)

# ---- 宠物对话 ----
_register(
    AIFunctionDef(
        key="pet_tool_call",
        name="宠物对话-工具调用",
        description="宠物角色决策调用数据查询工具",
        capability="text_json",
        group="chat",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
    AIFunctionDef(
        key="pet_chat",
        name="宠物对话-回复",
        description="宠物角色扮演对话（带性格和财务知识）",
        capability="text",
        group="chat",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-flash-character"],
    ),
)

# ---- 交易分析 ----
_register(
    AIFunctionDef(
        key="transaction_analyze",
        name="消费分析",
        description="AI分析消费模式，给出建议和节省方案",
        capability="text_json",
        group="analysis",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
    AIFunctionDef(
        key="transaction_categorize",
        name="交易分类",
        description="AI智能分类交易并推荐标签",
        capability="text_json",
        group="analysis",
        default_model="qwen-flash",
        alternative_models=["qwen-turbo", "qwen-plus"],
    ),
)

# ---- 任务管理 ----
_register(
    AIFunctionDef(
        key="todo_suggest",
        name="任务拆解建议",
        description="AI将目标拆解为可执行的子任务",
        capability="text_json",
        group="tools",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
    AIFunctionDef(
        key="todo_prioritize",
        name="任务优先级分析",
        description="AI分析任务紧急程度并排序",
        capability="text_json",
        group="tools",
        default_model="qwen-flash",
        alternative_models=["qwen-turbo", "qwen-plus"],
    ),
)

# ---- 投资分析 ----
_register(
    AIFunctionDef(
        key="investment_analyze",
        name="投资组合分析",
        description="AI分析投资组合风险和配置建议",
        capability="text_json",
        group="analysis",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
)

# ---- 公告助手 ----
_register(
    AIFunctionDef(
        key="announcement_draft",
        name="公告起草",
        description="AI根据主题和风格生成公告草稿",
        capability="text_json",
        group="tools",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
    AIFunctionDef(
        key="announcement_improve",
        name="公告优化",
        description="AI改进公告内容（简化/修辞/纠错）",
        capability="text_json",
        group="tools",
        default_model="qwen-plus",
        alternative_models=["qwen3-max", "qwen-turbo"],
    ),
)


# ==================== 分组定义 ====================

AI_FUNCTION_GROUPS = {
    "accounting": {"name": "记账", "icon": "📒", "order": 1},
    "asset": {"name": "资产", "icon": "💰", "order": 2},
    "chat": {"name": "对话", "icon": "💬", "order": 3},
    "analysis": {"name": "分析", "icon": "📊", "order": 4},
    "tools": {"name": "工具", "icon": "🛠️", "order": 5},
}


def get_function_registry_for_api() -> List[dict]:
    """返回前端用的注册表数据（按分组排序）"""
    items = []
    for key, func in AI_FUNCTION_REGISTRY.items():
        items.append({
            "key": func.key,
            "name": func.name,
            "description": func.description,
            "capability": func.capability,
            "group": func.group,
            "group_name": AI_FUNCTION_GROUPS.get(func.group, {}).get("name", func.group),
            "default_model": func.default_model,
            "alternative_models": func.alternative_models,
        })
    # 按分组 order 排序
    group_order = {k: v["order"] for k, v in AI_FUNCTION_GROUPS.items()}
    items.sort(key=lambda x: (group_order.get(x["group"], 99), x["key"]))
    return items
