# 🤖 AI 功能指南

小金库集成了丰富的 AI 能力，覆盖智能记账、语音交互、数据分析、宠物对话等核心场景。

## 📑 目录

- [系统架构](#系统架构)
- [AI 功能清单](#ai-功能清单)
- [按功能独立配置模型](#按功能独立配置模型)
- [AI 模型调用信息展示](#ai-模型调用信息展示)
- [可用模型参考](#可用模型参考)
- [开发指南](#开发指南)

---

## 系统架构

```
前端 (Vue 3)                          后端 (FastAPI)
┌─────────────────────┐    HTTP     ┌─────────────────────────┐
│ FloatingAIAssistant  │──────────→ │  API 路由层              │
│ AIChatDialog         │            │  (api/ai_chat.py 等)     │
│ 各业务页面 AI 按钮     │            └──────────┬──────────────┘
└─────────────────────┘                       │
                                    ┌──────────▼──────────────┐
                                    │  ai_service.py           │
                                    │  统一 AI 调用层            │
                                    │  · 按功能选择模型          │
                                    │  · 429 自动重试            │
                                    │  · 错误状态上报            │
                                    └──────────┬──────────────┘
                                               │
                                    ┌──────────▼──────────────┐
                                    │  OpenAI 兼容 API          │
                                    │  (DashScope / 自定义)      │
                                    └─────────────────────────┘
```

### 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| AI 统一调用层 | `backend/app/services/ai_service.py` | 所有 AI 请求的唯一入口，封装模型选择、重试、元数据上报 |
| AI 功能注册表 | `backend/app/core/ai_functions.py` | 19 个 AI 功能定义，分 5 组管理 |
| AI 记账服务 | `backend/app/services/ai_accounting.py` | 小票 OCR、语音转文字、批量导入解析 |
| AI 工具函数 | `backend/app/services/ai_tools.py` | 重复检测、分类推断等辅助 AI 调用 |
| AI 配置接口 | `backend/app/api/ai_config.py` | 服务商 CRUD、功能模型配置 API |
| AI 对话接口 | `backend/app/api/ai_chat.py` | 通用 AI 对话 + 语音转文字 |
| 前端 AI 对话 | `frontend/src/components/AIChatDialog.vue` | 对话面板 UI |
| 浮动 AI 助手 | `frontend/src/components/FloatingAIAssistant.vue` | 全局浮动按钮 + 快捷操作 |

---

## AI 功能清单

### 📝 智能记账（5 个功能）

| 功能 | function_key | 说明 |
|------|-------------|------|
| 智能记账 | `smart_accounting` | 文字输入自动识别金额、类别、日期 |
| 消费类型推断 | `consumer_type_inference` | 推断个人消费 vs 家庭消费 |
| 小票/发票识别 | `receipt_ocr` | 拍照上传后 AI 提取交易信息 |
| 语音转文字 | `voice_transcription` | 语音输入转文字（Whisper / 音频流） |
| 记账重复检测 | `duplicate_detection` | AI 判断是否与已有记录重复 |

### 📊 数据分析（4 个功能）

| 功能 | function_key | 说明 |
|------|-------------|------|
| 交易分析 | `transaction_analyze` | 分析收支趋势和消费结构 |
| 投资分析 | `investment_analyze` | 评估投资组合表现 |
| 赌注分析 | `bet_analyze` | 分析家庭赌注数据 |
| 年度报告 | `annual_report` | 生成家庭年度财务报告 |

### 💬 AI 对话（3 个功能）

| 功能 | function_key | 说明 |
|------|-------------|------|
| 仪表盘对话 | `dashboard_chat` | 基于用户财务概览的对话 |
| 宠物对话 | `pet_chat` | 宠物角色扮演，有进化阶段人设 |
| 通用对话 | `general_chat` | 浮动助手的自由对话 |

### ✏️ 内容生成（4 个功能）

| 功能 | function_key | 说明 |
|------|-------------|------|
| 公告起草 | `announcement_draft` | AI 辅助撰写家庭公告 |
| 投票方案建议 | `vote_suggestion` | 生成投票提案内容 |
| 清单建议 | `todo_suggestion` | 推荐清单项 |
| 日历事件建议 | `calendar_suggestion` | 根据上下文建议日程安排 |

### 📁 批量导入（3 个功能）

| 功能 | function_key | 说明 |
|------|-------------|------|
| PDF 解析 | `import_pdf` | 解析 PDF 消费记录（双模式：PyMuPDF + pdfplumber） |
| Excel 解析 | `import_excel` | 解析 Excel/CSV 消费记录 |
| 图片解析 | `import_image` | OCR 识别图片中的消费记录 |

---

## 按功能独立配置模型

系统支持为每个 AI 功能独立配置服务商和模型。管理员可在 **系统设置 → AI 功能模型配置** 中操作。

### 配置优先级

```
功能级配置（最高优先） → 全局活跃服务商 → 环境变量
```

- **功能级配置**：在 AI 配置界面为某个功能指定特定的 provider + model
- **全局活跃服务商**：在 AI 配置界面设置的默认服务商
- **环境变量**：`.env` 中的 `AI_BASE_URL` / `AI_API_KEY` / `AI_MODEL`

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ai-config/functions` | 获取所有 AI 功能定义及当前配置 |
| PUT | `/api/ai-config/functions/{key}` | 更新某功能的模型配置 |
| DELETE | `/api/ai-config/functions/{key}` | 删除某功能的独立配置（回退到全局） |
| POST | `/api/ai-config/functions/batch` | 批量更新功能配置 |

### 数据库模型

```python
class AIFunctionModelConfig(Base):
    __tablename__ = "ai_function_model_configs"
    id            = Column(Integer, primary_key=True)
    function_key  = Column(String, unique=True, index=True)  # 如 "receipt_ocr"
    provider_id   = Column(Integer, ForeignKey("ai_providers.id"))
    model_name    = Column(String)      # 如 "qwen-vl-max"
    is_enabled    = Column(Boolean, default=True)
    created_at    = Column(DateTime)
    updated_at    = Column(DateTime)
```

---

## AI 模型调用信息展示

用户可在 **系统设置** 中开启「显示 AI 模型调用信息」开关。开启后，每次 AI 调用完成时会在页面底部显示一条优雅的浮动提示，内容包含功能名称和实际使用的模型。

### 技术实现

1. **后端**：纯 ASGI 中间件 `AIMetadataMiddleware` 在响应头中注入 `X-AI-Function-Name` 和 `X-AI-Model` 等信息
2. **前端**：axios 响应拦截器检测 `X-AI-*` 头，触发 `AIModelToast` 组件
3. **存储**：开关状态保存在 `localStorage`（key: `showAIModelInfo`）

---

## 可用模型参考

详见 [DashScope 可用模型汇总](DASHSCOPE_MODELS.md)，包含 185 个模型的分类索引和项目推荐选型。

### 项目推荐选型

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 日常对话 | qwen-plus | 性价比高，响应快 |
| 复杂分析 | qwen-max | 最强推理能力 |
| 图片识别 | qwen-vl-max | 视觉理解能力最强 |
| 语音转文字 | qwen3-omni-flash | 支持音频直接输入 |
| 轻量任务 | qwen-turbo | 速度最快、成本最低 |

---

## 开发指南

### 添加新的 AI 功能

1. **注册功能**：在 `backend/app/core/ai_functions.py` 的 `AI_FUNCTION_REGISTRY` 中添加定义
2. **调用 AI**：在业务代码中使用 `ai_service.chat(..., function_key="your_key")`
3. **前端触发**：在对应页面调用 API，拦截器会自动处理模型信息展示

### 调用示例

```python
from app.services.ai_service import ai_service

# 指定功能的调用（自动选择该功能配置的模型）
reply = await ai_service.chat(
    "分析这笔交易...",
    function_key="transaction_analyze",
    system_prompt="你是一个专业的财务分析师"
)

# 不指定 function_key 则使用全局默认
reply = await ai_service.chat("你好", system_prompt="你是助手")
```

### 注意事项

- **所有 AI 调用必须经过 `ai_service`**，不要直接发 HTTP 请求
- 每个 `function_key` 必须在 `AI_FUNCTION_REGISTRY` 中注册
- 未配置独立模型的功能会自动回退到全局配置
- `ai_service` 内置 429 限流自动重试（最多 2 次）

---

> 📖 相关文档：[DashScope 模型目录](DASHSCOPE_MODELS.md) · [主题适配指南](THEME_GUIDE.md) · [启动脚本指南](RUN_SCRIPTS_GUIDE.md)
