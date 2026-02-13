"""
扫雷游戏 - 数据定义与逻辑
"""
import random
from datetime import datetime
from fastapi import HTTPException


# ==================== 数据定义 ====================

MINESWEEPER_DIFFICULTIES = {
    "easy":   {"rows": 6,  "cols": 6,  "mines": 5,  "exp": 20,  "label": "入门"},
    "medium": {"rows": 9,  "cols": 9,  "mines": 12, "exp": 50,  "label": "进阶"},
    "hard":   {"rows": 12, "cols": 12, "mines": 30, "exp": 120, "label": "困难"},
    "expert": {"rows": 16, "cols": 16, "mines": 55, "exp": 1000, "label": "地狱"},
}


# ==================== 会话创建 ====================

def create_minesweeper_session(difficulty: str) -> dict:
    cfg = MINESWEEPER_DIFFICULTIES[difficulty]
    rows, cols = cfg["rows"], cfg["cols"]
    return {
        "started_at": datetime.utcnow().isoformat(),
        "difficulty": difficulty,
        "rows": rows,
        "cols": cols,
        "mine_count": cfg["mines"],
        "board": [[0] * cols for _ in range(rows)],
        "revealed": [[False] * cols for _ in range(rows)],
        "flagged": [[False] * cols for _ in range(rows)],
        "questioned": [[False] * cols for _ in range(rows)],  # 添加问号标记支持
        "first_click": True,
        "completed": False,
        "won": False,
        "cells_revealed": 0,
        "total_safe": rows * cols - cfg["mines"],
        "exp_earned": 0,
    }


# ==================== 内部工具函数 ====================

def _place_mines(session: dict, safe_row: int, safe_col: int):
    """首次点击后放置地雷，确保点击位置及周围无雷"""
    rows, cols = session["rows"], session["cols"]
    mine_count = session["mine_count"]
    # 安全区域：点击位置及其8个邻居
    safe_cells = set()
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = safe_row + dr, safe_col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                safe_cells.add((nr, nc))
    # 可放雷的位置
    candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in safe_cells]
    # 如果可用位置不够（极小棋盘），放宽安全区域
    if len(candidates) < mine_count:
        candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) != (safe_row, safe_col)]
    mines = random.sample(candidates, mine_count)
    board = [[0] * cols for _ in range(rows)]
    for mr, mc in mines:
        board[mr][mc] = -1
    # 计算数字
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == -1:
                continue
            count = 0
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == -1:
                        count += 1
            board[r][c] = count
    session["board"] = board


def _flood_fill(session: dict, row: int, col: int):
    """翻开空格时递归展开相邻的0格"""
    rows, cols = session["rows"], session["cols"]
    stack = [(row, col)]
    while stack:
        r, c = stack.pop()
        if session["revealed"][r][c]:
            continue
        session["revealed"][r][c] = True
        session["cells_revealed"] += 1
        # 清除问号标记（翻开时）
        if session.get("questioned") and session["questioned"][r][c]:
            session["questioned"][r][c] = False
        # 如果是0，展开周围
        if session["board"][r][c] == 0:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and not session["revealed"][nr][nc]:
                        # 不展开标旗的格子，但可以展开问号格子
                        if not session["flagged"][nr][nc]:
                            stack.append((nr, nc))


# ==================== 状态脱敏 ====================

def sanitize_minesweeper_state(session: dict) -> dict:
    """清除服务端秘密，返回客户端安全的扫雷游戏状态"""
    rows = session["rows"]
    cols = session["cols"]
    completed = session.get("completed", False)
    # 构建脱敏棋盘：已翻开的格子显示数字，未翻开的显示 None
    visible_board = []
    for r in range(rows):
        row_data = []
        for c in range(cols):
            if session["revealed"][r][c]:
                row_data.append(session["board"][r][c])
            elif completed:
                # 游戏结束后显示所有格子
                row_data.append(session["board"][r][c])
            else:
                row_data.append(None)
        visible_board.append(row_data)
    return {
        "difficulty": session["difficulty"],
        "rows": rows,
        "cols": cols,
        "mine_count": session["mine_count"],
        "board": visible_board,
        "revealed": session["revealed"],
        "flagged": session["flagged"],
        "questioned": session.get("questioned", [[False] * cols for _ in range(rows)]),  # 修复: 传递问号标记到前端
        "first_click": session.get("first_click", False),
        "completed": completed,
        "won": session.get("won", False),
        "cells_revealed": session.get("cells_revealed", 0),
        "total_safe": session.get("total_safe", rows * cols - session["mine_count"]),
        "exp_earned": session.get("exp_earned", 0) if completed else 0,
    }


# ==================== 游戏逻辑处理 ====================

def process_minesweeper_action(session: dict, action: dict) -> dict:
    """处理扫雷操作"""
    act = action.get("action")
    
    # 处理放弃
    if act == "abandon":
        session["completed"] = True
        session["exp_earned"] = 0
        session["abandoned"] = True
        session["game_won"] = False
        return {"completed": True, "exp_earned": 0, "abandoned": True}
    
    if session.get("completed"):
        raise HTTPException(status_code=400, detail="游戏已结束")

    row = action.get("row")
    col = action.get("col")
    rows, cols = session["rows"], session["cols"]

    if row is None or col is None or not (0 <= row < rows and 0 <= col < cols):
        raise HTTPException(status_code=400, detail="无效的坐标")

    if act == "flag":
        if session["revealed"][row][col]:
            raise HTTPException(status_code=400, detail="不能标记已翻开的格子")
        # 循环状态: 隐藏 → 旗帜 → 问号 → 隐藏
        is_flagged = session["flagged"][row][col]
        is_questioned = session.get("questioned", [[False] * session["cols"] for _ in range(session["rows"])])[row][col]
        
        if not is_flagged and not is_questioned:
            # 隐藏 → 旗帜
            session["flagged"][row][col] = True
            session["questioned"][row][col] = False
        elif is_flagged and not is_questioned:
            # 旗帜 → 问号
            session["flagged"][row][col] = False
            session["questioned"][row][col] = True
        else:
            # 问号 → 隐藏
            session["flagged"][row][col] = False
            session["questioned"][row][col] = False
        
        return {"completed": False, "exp_earned": 0}

    elif act == "reveal":
        if session["revealed"][row][col]:
            raise HTTPException(status_code=400, detail="该格已翻开")
        if session["flagged"][row][col]:
            raise HTTPException(status_code=400, detail="请先取消标旗")

        # 首次点击：放置地雷
        if session.get("first_click"):
            _place_mines(session, row, col)
            session["first_click"] = False

        # 踩雷
        if session["board"][row][col] == -1:
            session["completed"] = True
            session["won"] = False
            session["exp_earned"] = 0
            session["revealed"][row][col] = True
            return {"completed": True, "exp_earned": 0, "won": False}

        # 翻开（含 flood fill）
        _flood_fill(session, row, col)

        # 检查是否胜利
        if session["cells_revealed"] >= session["total_safe"]:
            session["completed"] = True
            session["won"] = True
            exp = MINESWEEPER_DIFFICULTIES[session["difficulty"]]["exp"]
            session["exp_earned"] = exp
            return {"completed": True, "exp_earned": exp, "won": True}

        return {"completed": False, "exp_earned": 0}

    elif act == "chord":
        if not session["revealed"][row][col]:
            raise HTTPException(status_code=400, detail="只能对已翻开的格子使用快速翻开")
        num = session["board"][row][col]
        if num <= 0:
            raise HTTPException(status_code=400, detail="该格不是数字格")

        # 计算周围旗数和未翻开格子
        flag_count = 0
        unrevealed = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if session["flagged"][nr][nc]:
                        flag_count += 1
                    elif not session["revealed"][nr][nc]:
                        # 问号格子也算作未翻开
                        unrevealed.append((nr, nc))

        # 专业扫雷模式：两种和弦触发条件
        # 1. 旗数等于数字 - 经典模式
        # 2. 旗数 + 未翻开数 = 数字 - 智能模式(当剩余格子都是雷时)
        can_chord = False
        
        if flag_count == num:
            # 经典和弦：旗数正确，翻开其他格子
            can_chord = True
        elif flag_count + len(unrevealed) == num:
            # 智能和弦：剩余格子都是雷，自动标旗并翻开
            # 先标记所有未标记的格子为旗
            for nr, nc in unrevealed:
                if not session["flagged"][nr][nc]:
                    session["flagged"][nr][nc] = True
            unrevealed = []  # 清空待翻开列表
            can_chord = True
        
        if not can_chord:
            raise HTTPException(
                status_code=400, 
                detail=f"无法和弦：周围有{flag_count}面旗，{len(unrevealed)}个未翻开格子，但数字是{num}"
            )

        # 翻开所有未翻开未标旗的邻居
        hit_mine = False
        for nr, nc in unrevealed:
            if session["board"][nr][nc] == -1:
                hit_mine = True
                session["revealed"][nr][nc] = True
            else:
                _flood_fill(session, nr, nc)

        if hit_mine:
            session["completed"] = True
            session["won"] = False
            session["exp_earned"] = 0
            return {"completed": True, "exp_earned": 0, "won": False}

        if session["cells_revealed"] >= session["total_safe"]:
            session["completed"] = True
            session["won"] = True
            exp = MINESWEEPER_DIFFICULTIES[session["difficulty"]]["exp"]
            session["exp_earned"] = exp
            return {"completed": True, "exp_earned": exp, "won": True}

        return {"completed": False, "exp_earned": 0}

    else:
        raise HTTPException(status_code=400, detail="操作必须是 reveal、flag 或 chord")
