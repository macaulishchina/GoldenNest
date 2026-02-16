"""
设计院 (Studio) - 工具注册表与执行引擎

为 AI 讨论提供代码感知能力:
  - read_file: 读取项目文件内容
  - search_text: 全文搜索 (支持正则)
  - list_directory: 列出目录内容
  - get_file_tree: 获取项目目录树

安全沙箱:
  - 路径限制在 workspace_path 内 (防止 ../ 逃逸和符号链接逃逸)
  - 敏感文件黑名单 (.env, *.key 等)
  - 文件读取行数上限 (默认 500 行)
  - 搜索结果数量上限 (默认 50 条)
  - 只读: 不提供任何写入/删除/执行工具
"""
import asyncio
import logging
import os
import re
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ==================== 权限定义 ====================

TOOL_PERMISSIONS = {
    "read_source",   # 读取源码文件
    "read_config",   # 读取配置文件
    "search",        # 全文搜索
    "tree",          # 目录浏览
}

DEFAULT_PERMISSIONS = set(TOOL_PERMISSIONS)  # 默认全部开启

# ==================== 安全限制 ====================

# 敏感文件/目录黑名单
_SENSITIVE_PATTERNS = {
    # 文件名精确匹配
    ".env", ".env.local", ".env.production",
    # 目录
    ".git/objects", ".git/refs", ".git/logs",
    "venv", ".venv", "node_modules", "__pycache__",
    # 安全相关
    "id_rsa", "id_ed25519",
}

_SENSITIVE_EXTENSIONS = {
    ".key", ".pem", ".p12", ".pfx", ".jks",
    ".secret", ".credentials",
}

# 允许读取的配置文件 (即使匹配了敏感模式)
_CONFIG_ALLOWLIST = {
    "package.json", "tsconfig.json", "vite.config.ts",
    "docker-compose.yml", "Dockerfile", "nginx.conf",
    "requirements.txt", "pyproject.toml", "setup.cfg",
    "CLAUDE.md", "README.md", "TODO.md",
}

# 文件读取限制
MAX_READ_LINES = 500
MAX_SEARCH_RESULTS = 50
SEARCH_CONTEXT_LINES = 2
TOOL_TIMEOUT_SECONDS = 10

# 目录树限制
MAX_TREE_DEPTH = 4
TREE_SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv",
    "dist", ".claude", "studio-data", "data", ".idea", ".vscode",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov",
    ".next", ".nuxt", "build", "target",
}


# ==================== 工具定义 (OpenAI Function Calling Format) ====================

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取项目中指定文件的内容。可以指定行范围只读取部分内容。适合查看具体的代码实现。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于项目根目录的文件路径，例如 'backend/app/games/adventure.py'",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "起始行号 (1-based)，不指定则从第 1 行开始",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "结束行号 (1-based, inclusive)，不指定则读到文件末尾 (最多 500 行)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "在项目文件中搜索文本或正则表达式。返回匹配的文件、行号和上下文。适合查找函数定义、变量引用等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索的文本或正则表达式",
                    },
                    "is_regex": {
                        "type": "boolean",
                        "description": "是否为正则表达式，默认 false (精确文本搜索)",
                        "default": False,
                    },
                    "include_pattern": {
                        "type": "string",
                        "description": "限制搜索的文件名 glob 模式，例如 '*.py'、'*.vue'、'*.ts'。注意: 只支持文件名匹配，不支持路径前缀",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出指定目录的内容（文件和子目录）。适合了解目录结构。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于项目根目录的目录路径，例如 'backend/app/api'。空字符串表示项目根目录。",
                        "default": "",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_tree",
            "description": "获取项目的目录树结构。适合了解项目整体布局。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "子目录路径 (相对于项目根目录)，空字符串表示整个项目",
                        "default": "",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "目录树最大深度，默认 3",
                        "default": 3,
                    },
                },
                "required": [],
            },
        },
    },
]


def get_tool_definitions(permissions: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """
    获取当前可用的工具定义列表 (根据权限过滤)

    Args:
        permissions: 允许的权限集合，None 表示使用默认权限 (全部开启)

    Returns:
        OpenAI tools format 列表
    """
    perms = permissions or DEFAULT_PERMISSIONS
    tools = []

    for tool_def in TOOL_DEFINITIONS:
        name = tool_def["function"]["name"]
        required_perm = _TOOL_PERMISSION_MAP.get(name)
        if required_perm and required_perm.issubset(perms):
            tools.append(tool_def)

    return tools


# 工具名 → 所需权限映射
_TOOL_PERMISSION_MAP: Dict[str, Set[str]] = {
    "read_file": {"read_source"},
    "search_text": {"search"},
    "list_directory": {"tree"},
    "get_file_tree": {"tree"},
}


# ==================== 路径安全检查 ====================

def _validate_path(workspace: str, rel_path: str) -> Tuple[bool, str, str]:
    """
    验证路径安全性

    Returns:
        (is_safe, absolute_path, error_message)
    """
    # 规范化路径
    rel_path = rel_path.strip().lstrip("/")

    # 阻止空路径用于文件操作
    abs_path = os.path.realpath(os.path.join(workspace, rel_path))

    # 沙箱检查: 必须在 workspace 内
    workspace_real = os.path.realpath(workspace)
    if not abs_path.startswith(workspace_real + os.sep) and abs_path != workspace_real:
        return False, abs_path, f"⚠️ 路径越界: '{rel_path}' 不在项目目录内"

    return True, abs_path, ""


def _is_sensitive_file(rel_path: str) -> bool:
    """检查文件是否在敏感黑名单中"""
    basename = os.path.basename(rel_path)
    _, ext = os.path.splitext(basename)

    # 允许列表优先
    if basename in _CONFIG_ALLOWLIST:
        return False

    # 精确文件名匹配
    if basename in _SENSITIVE_PATTERNS:
        return True

    # 扩展名匹配
    if ext.lower() in _SENSITIVE_EXTENSIONS:
        return True

    # 路径中包含敏感目录
    path_parts = rel_path.replace("\\", "/").split("/")
    for part in path_parts:
        if part in _SENSITIVE_PATTERNS:
            return True

    return False


# ==================== 工具执行器 ====================

async def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    workspace: str,
    permissions: Optional[Set[str]] = None,
) -> str:
    """
    执行指定工具并返回结果文本

    Args:
        name: 工具名称
        arguments: 工具参数
        workspace: 工作区根路径
        permissions: 允许的权限集合

    Returns:
        工具执行结果 (纯文本)
    """
    perms = permissions or DEFAULT_PERMISSIONS

    # 权限检查
    required_perm = _TOOL_PERMISSION_MAP.get(name)
    if required_perm and not required_perm.issubset(perms):
        return f"⚠️ 工具 '{name}' 已被项目管理员禁用"

    # 执行工具 (带超时)
    executor = _TOOL_EXECUTORS.get(name)
    if not executor:
        return f"⚠️ 未知工具: '{name}'"

    try:
        result = await asyncio.wait_for(
            executor(arguments, workspace),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
        return result
    except asyncio.TimeoutError:
        return f"⚠️ 工具 '{name}' 执行超时 ({TOOL_TIMEOUT_SECONDS}s)"
    except Exception as e:
        logger.exception(f"工具 {name} 执行失败")
        return f"⚠️ 工具执行失败: {str(e)}"


# ==================== 具体工具实现 ====================

async def _tool_read_file(args: Dict[str, Any], workspace: str) -> str:
    """读取文件内容"""
    path = args.get("path", "")
    start_line = args.get("start_line", 1)
    end_line = args.get("end_line")

    if not path:
        return "⚠️ 请指定文件路径"

    # 路径安全检查
    is_safe, abs_path, error = _validate_path(workspace, path)
    if not is_safe:
        return error

    # 敏感文件检查
    if _is_sensitive_file(path):
        return f"⚠️ 无法读取敏感文件: '{path}'"

    if not os.path.exists(abs_path):
        return f"⚠️ 文件不存在: '{path}'"

    if not os.path.isfile(abs_path):
        return f"⚠️ '{path}' 不是文件 (可能是目录，请使用 list_directory)"

    # 检查文件大小 (跳过过大的二进制文件)
    file_size = os.path.getsize(abs_path)
    if file_size > 1024 * 1024:  # 1MB
        return f"⚠️ 文件过大 ({file_size / 1024:.0f}KB)，请指定行范围读取"

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        return f"⚠️ '{path}' 是二进制文件，无法读取"

    total_lines = len(lines)

    # 处理行范围
    start = max(1, start_line or 1)
    end = min(total_lines, end_line or (start + MAX_READ_LINES - 1))

    # 最多读取 MAX_READ_LINES 行
    if end - start + 1 > MAX_READ_LINES:
        end = start + MAX_READ_LINES - 1

    selected = lines[start - 1:end]
    content = "".join(selected)

    # 构建结果头信息
    header = f"📄 {path} (行 {start}-{end}, 共 {total_lines} 行)"
    if end < total_lines:
        header += f" [截断: 使用 start_line/end_line 查看更多]"

    return f"{header}\n```\n{content}```"


async def _tool_search_text(args: Dict[str, Any], workspace: str) -> str:
    """全文搜索"""
    query = args.get("query", "")
    is_regex = args.get("is_regex", False)
    include_pattern = args.get("include_pattern", "")

    if not query:
        return "⚠️ 请指定搜索内容"

    # 构建 grep 命令
    cmd = ["grep", "-rn", "--color=never"]

    if is_regex:
        cmd.append("-E")
    else:
        cmd.append("-F")

    # 上下文行
    cmd.extend(["-B", str(SEARCH_CONTEXT_LINES), "-A", str(SEARCH_CONTEXT_LINES)])

    # 最大结果数
    cmd.extend(["-m", str(MAX_SEARCH_RESULTS)])

    # 排除目录
    for skip_dir in TREE_SKIP_DIRS:
        cmd.extend(["--exclude-dir", skip_dir])

    # 排除敏感文件
    for ext in _SENSITIVE_EXTENSIONS:
        cmd.extend(["--exclude", f"*{ext}"])
    cmd.extend(["--exclude", ".env*"])

    # 包含模式 (修正: grep --include 不支持 ** 或路径, 只支持文件名 glob)
    if include_pattern:
        # 去掉路径前缀 (如 **/*.py → *.py, src/**/*.ts → *.ts)
        clean_pattern = include_pattern
        if '/' in clean_pattern:
            clean_pattern = clean_pattern.rsplit('/', 1)[-1]
        if not clean_pattern or clean_pattern == '**':
            clean_pattern = '*'
        cmd.extend(["--include", clean_pattern])

    cmd.append(query)
    cmd.append(".")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TOOL_TIMEOUT_SECONDS)
        output = stdout.decode("utf-8", errors="replace").strip()

        if not output:
            return f"🔍 未找到匹配: '{query}'"

        # 清理路径 (去掉 ./ 前缀)
        output = output.replace("\n./", "\n").lstrip("./")

        # 限制输出长度
        lines = output.split("\n")
        if len(lines) > 200:
            output = "\n".join(lines[:200])
            output += f"\n\n... (结果过多，已截断。请使用 include_pattern 缩小范围)"

        pattern_desc = f"正则 '{query}'" if is_regex else f"'{query}'"
        scope = f" (范围: {include_pattern})" if include_pattern else ""
        return f"🔍 搜索 {pattern_desc}{scope}:\n\n{output}"

    except FileNotFoundError:
        # grep 不可用，退回到 Python 实现
        return await _python_search(query, is_regex, include_pattern, workspace)


async def _python_search(
    query: str, is_regex: bool, include_pattern: str, workspace: str,
) -> str:
    """Python 备用搜索实现 (grep 不可用时)"""
    import fnmatch

    if is_regex:
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return f"⚠️ 无效的正则表达式: {e}"
    else:
        pattern = None

    results: List[str] = []
    count = 0

    for root, dirs, files in os.walk(workspace):
        # 跳过排除目录
        dirs[:] = [d for d in dirs if d not in TREE_SKIP_DIRS]

        for fname in files:
            if count >= MAX_SEARCH_RESULTS:
                break

            # 敏感文件检查
            rel_path = os.path.relpath(os.path.join(root, fname), workspace)
            if _is_sensitive_file(rel_path):
                continue

            # include_pattern 过滤
            if include_pattern and not fnmatch.fnmatch(fname, include_pattern):
                continue

            try:
                with open(os.path.join(root, fname), "r", encoding="utf-8", errors="replace") as f:
                    file_lines = f.readlines()
            except Exception:
                continue

            for i, line in enumerate(file_lines):
                if count >= MAX_SEARCH_RESULTS:
                    break

                matched = False
                if pattern:
                    matched = bool(pattern.search(line))
                else:
                    matched = query.lower() in line.lower()

                if matched:
                    count += 1
                    line_num = i + 1
                    # 上下文
                    ctx_start = max(0, i - SEARCH_CONTEXT_LINES)
                    ctx_end = min(len(file_lines), i + SEARCH_CONTEXT_LINES + 1)
                    ctx = ""
                    for j in range(ctx_start, ctx_end):
                        prefix = ">" if j == i else " "
                        ctx += f"{prefix} {j+1}: {file_lines[j]}"
                    results.append(f"{rel_path}:{line_num}\n{ctx}")

    if not results:
        return f"🔍 未找到匹配: '{query}'"

    output = "\n---\n".join(results)
    truncated = f"\n\n... (已达到 {MAX_SEARCH_RESULTS} 条上限)" if count >= MAX_SEARCH_RESULTS else ""
    return f"🔍 搜索 '{query}' 找到 {count} 个匹配:\n\n{output}{truncated}"


async def _tool_list_directory(args: Dict[str, Any], workspace: str) -> str:
    """列出目录内容"""
    path = args.get("path", "")

    # 路径安全检查
    is_safe, abs_path, error = _validate_path(workspace, path or ".")
    if not is_safe:
        return error

    if not os.path.exists(abs_path):
        return f"⚠️ 目录不存在: '{path}'"

    if not os.path.isdir(abs_path):
        return f"⚠️ '{path}' 不是目录 (请使用 read_file 读取文件)"

    try:
        entries = sorted(os.listdir(abs_path))
    except PermissionError:
        return f"⚠️ 无权访问: '{path}'"

    # 过滤隐藏和忽略的目录
    entries = [e for e in entries if e not in TREE_SKIP_DIRS and not e.startswith("__pycache__")]

    dirs = []
    files = []
    for entry in entries:
        full = os.path.join(abs_path, entry)
        if os.path.isdir(full):
            # 计算子项数量
            try:
                sub_count = len(os.listdir(full))
            except Exception:
                sub_count = 0
            dirs.append(f"📁 {entry}/ ({sub_count} items)")
        else:
            size = os.path.getsize(full)
            size_str = f"{size}B" if size < 1024 else f"{size / 1024:.1f}KB" if size < 1048576 else f"{size / 1048576:.1f}MB"
            files.append(f"📄 {entry} ({size_str})")

    display_path = path or "."
    result = f"📂 {display_path}/\n"
    result += "\n".join(dirs + files)

    if not dirs and not files:
        result += "(空目录)"

    return result


async def _tool_get_file_tree(args: Dict[str, Any], workspace: str) -> str:
    """获取目录树"""
    path = args.get("path", "")
    max_depth = min(args.get("max_depth", 3), MAX_TREE_DEPTH)

    # 路径安全检查
    target = os.path.join(workspace, path) if path else workspace
    is_safe, abs_path, error = _validate_path(workspace, path or ".")
    if not is_safe:
        return error

    if not os.path.exists(abs_path):
        return f"⚠️ 路径不存在: '{path}'"

    if not os.path.isdir(abs_path):
        return f"⚠️ '{path}' 不是目录"

    tree = _build_tree(abs_path, max_depth)
    display_path = path or "."
    return f"🌳 {display_path}/ 目录树 (深度: {max_depth}):\n\n{tree}"


def _build_tree(path: str, max_depth: int, prefix: str = "", depth: int = 0) -> str:
    """递归构建目录树"""
    if depth >= max_depth:
        return ""

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return f"{prefix}(无权限访问)\n"

    # 过滤
    entries = [e for e in entries if e not in TREE_SKIP_DIRS and not e.startswith(".")]

    lines = []
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        full_path = os.path.join(path, entry)

        if os.path.isdir(full_path):
            lines.append(f"{prefix}{connector}{entry}/")
            extension = "    " if is_last else "│   "
            subtree = _build_tree(full_path, max_depth, prefix + extension, depth + 1)
            if subtree:
                lines.append(subtree)
        else:
            lines.append(f"{prefix}{connector}{entry}")

    return "\n".join(lines)


# 工具执行器映射
_TOOL_EXECUTORS: Dict[str, Callable] = {
    "read_file": _tool_read_file,
    "search_text": _tool_search_text,
    "list_directory": _tool_list_directory,
    "get_file_tree": _tool_get_file_tree,
}
