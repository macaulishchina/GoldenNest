"""
设计院 (Studio) - 项目上下文构建服务
构建 AI 讨论的 system prompt，使 AI 具备项目感知能力

支持自适应压缩: 根据模型上下文窗口大小调整 system prompt 内容量
  - 极小 (<16K):  仅包含角色定义 + 项目概况 + plan 格式
  - 中等 (16K-128K): + 目录结构 + 关键目录列表 + 少量代码摘要
  - 大型 (>128K):  + 完整关键文件内容 (原始行为)
"""
import os
import logging
from typing import Optional

from studio.backend.core.config import settings
from studio.backend.core.token_utils import estimate_tokens

logger = logging.getLogger(__name__)

# 需要摘要的关键文件
KEY_FILES = [
    "CLAUDE.md",
    "backend/app/models/models.py",
    "backend/app/main.py",
    "frontend/src/router/index.ts",
    "frontend/src/api/index.ts",
    "docker-compose.yml",
]

# 需要列出内容的目录
KEY_DIRS = [
    "backend/app/api",
    "backend/app/services",
    "backend/app/schemas",
    "frontend/src/views",
    "frontend/src/components",
    "frontend/src/stores",
]


def get_tree(path: str, max_depth: int = 3, prefix: str = "", current_depth: int = 0) -> str:
    """生成目录树字符串"""
    if current_depth >= max_depth:
        return ""

    result = []
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return ""

    # 过滤掉不需要的目录
    skip = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", ".claude",
            "studio-data", "data", ".idea", ".vscode"}
    entries = [e for e in entries if e not in skip]

    for i, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        result.append(f"{prefix}{connector}{entry}")

        if os.path.isdir(full_path):
            extension = "    " if is_last else "│   "
            subtree = get_tree(full_path, max_depth, prefix + extension, current_depth + 1)
            if subtree:
                result.append(subtree)

    return "\n".join(result)


def read_file_safe(filepath: str, max_lines: int = 200) -> str:
    """安全读取文件, 截断过长内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            content = "".join(lines[:max_lines])
            content += f"\n... (截断, 共 {len(lines)} 行)"
        else:
            content = "".join(lines)
        return content
    except Exception as e:
        return f"(读取失败: {e})"


def list_dir_files(dirpath: str) -> str:
    """列出目录中的文件"""
    try:
        entries = sorted(os.listdir(dirpath))
        entries = [e for e in entries if not e.startswith("__")]
        return ", ".join(entries)
    except Exception:
        return "(目录不存在)"


def build_project_context(extra_context: str = "", budget_tokens: int = 0) -> str:
    """
    构建项目上下文用于 AI system prompt

    Args:
        extra_context: 额外上下文 (需求标题/描述等)
        budget_tokens: system prompt token 预算 (0 = 不限制, 使用最大内容)

    自适应策略:
        budget <= 0 或 > 32K  → 完整内容 (CLAUDE.md 300行 + 5个文件)
        8K < budget <= 32K    → 中等内容 (目录树 + 目录列表 + 少量代码)
        budget <= 8K          → 最小内容 (仅角色定义 + plan 格式)
    """
    ws = settings.workspace_path

    # 根据 budget 决定内容粒度
    level = "full"  # full / medium / minimal
    if 0 < budget_tokens <= 8000:
        level = "minimal"
    elif 0 < budget_tokens <= 32000:
        level = "medium"

    # 项目结构 (medium + full)
    tree = ""
    if level != "minimal":
        tree = get_tree(ws, max_depth=2)

    # 关键文件 (full only)
    key_file_contents = []
    if level == "full":
        for f in KEY_FILES:
            fp = os.path.join(ws, f)
            if os.path.exists(fp):
                content = read_file_safe(fp, max_lines=100 if f != "CLAUDE.md" else 300)
                key_file_contents.append(f"### {f}\n```\n{content}\n```")
    elif level == "medium":
        # 中等模式: 只取 CLAUDE.md 前 50 行 + docker-compose
        for f in ["CLAUDE.md", "docker-compose.yml"]:
            fp = os.path.join(ws, f)
            if os.path.exists(fp):
                content = read_file_safe(fp, max_lines=50)
                key_file_contents.append(f"### {f}\n```\n{content}\n```")

    # 关键目录 (medium + full)
    key_dir_contents = []
    if level != "minimal":
        for d in KEY_DIRS:
            dp = os.path.join(ws, d)
            if os.path.isdir(dp):
                key_dir_contents.append(f"- `{d}/`: {list_dir_files(dp)}")

    # 基础角色定义 (所有级别都包含)
    parts = ["""你是 GoldenNest (小金库) 项目的高级产品设计师和软件架构师。
你正在「设计院」中和产品负责人讨论一个新需求。

## 你的职责
1. **深入理解需求**: 主动提问，澄清模糊点，挖掘隐含需求
2. **架构设计**: 基于项目现有架构提出合理的实现方案
3. **全栈考虑**: 分析前后端影响、数据库变更、API 设计、兼容性
4. **风险评估**: 指出潜在风险和注意事项
5. **Plan 输出**: 讨论成熟后，生成结构化的实施计划 (plan.md)

## 项目概况
这是一个家庭财富管理 Web 应用，使用 Vue 3 + TypeScript + Naive UI (前端) + FastAPI + SQLAlchemy 2.0 + SQLite (后端)"""]

    # 项目结构 (medium + full)
    if tree:
        parts.append(f"## 项目结构\n```\n{tree}\n```")

    # 关键目录 (medium + full)
    if key_dir_contents:
        parts.append(f"## 关键目录内容\n{chr(10).join(key_dir_contents)}")

    # 关键文件 (medium: 精简, full: 完整)
    if key_file_contents:
        parts.append(f"## 关键文件内容摘要\n{chr(10).join(key_file_contents)}")

    # Plan 输出格式 (所有级别)
    parts.append("""## 实施计划 (Plan) 输出格式
当用户要求敲定方案时，请输出如下格式的 plan.md:

```markdown
# [需求标题]

## 1. 需求概述
简明描述需求目标和范围

## 2. 技术方案
### 2.1 后端变更
### 2.2 前端变更
### 2.3 其他变更

## 3. 实施步骤 (按顺序)
1. [ ] 步骤1 ...

## 4. 注意事项

## 5. 影响范围
```""")

    if extra_context:
        parts.append(extra_context)

    parts.append("""## 工具使用指引
- 你拥有以下工具，可以主动调用来查看项目源码:
  - `read_file`: 读取文件内容 (可指定行范围)
  - `search_text`: 全文搜索文本或正则
  - `list_directory`: 列出目录内容
  - `get_file_tree`: 获取目录树结构
- **当用户询问代码实现细节时，必须先用工具查看相关源码，再回答**
- 不要在没有查看代码的情况下猜测实现细节
- 先用 `get_file_tree` 了解项目结构，再用 `read_file` 深入具体文件
- 搜索时优先使用精确文件名或函数名，避免过于宽泛的搜索
- 回答要具体到代码层面，不要泛泛而谈
- 使用中文回答""")

    context = "\n\n".join(parts)

    # 最终 token 检查: 如果仍然超预算则截断
    if budget_tokens > 0:
        current_tokens = estimate_tokens(context)
        if current_tokens > budget_tokens:
            logger.warning(
                f"System prompt ({current_tokens} tokens) 超出预算 ({budget_tokens}),"
                f" 级别={level}, 进行截断"
            )
            from studio.backend.core.token_utils import truncate_text
            context = truncate_text(context, budget_tokens)

    return context


def build_plan_generation_prompt(discussion_summary: str) -> str:
    """构建从讨论生成 plan.md 的 prompt"""
    return f"""基于以下讨论内容，生成一份详尽的实施计划 (plan.md)。

要求：
1. 严格按照上面定义的 Plan 输出格式
2. 实施步骤要具体到文件和代码层面
3. 列出所有需要修改的文件
4. 考虑数据库迁移（如果有 schema 变更）
5. 考虑前后端兼容性

讨论内容摘要：
{discussion_summary}

请直接输出 plan.md 内容（不需要代码块包裹）:"""
