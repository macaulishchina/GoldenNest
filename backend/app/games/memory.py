"""
记忆翻牌游戏 - 数据定义与逻辑
"""
import random
from datetime import datetime
from fastapi import HTTPException


# ==================== 数据定义 ====================

MEMORY_SYMBOLS = ["💰", "💎", "📈", "🏦", "🎁", "⭐", "🔥", "🌙", "🎯", "🍀", "👑", "🎪", "🚀", "🌈", "🎭", "🎵", "🎲", "🧲"]

MEMORY_DIFFICULTIES = {
    "easy":   {"pairs": 6,  "cols": 4, "rows": 3, "exp_perfect": 30,  "exp_good": 20,  "exp_ok": 15},
    "medium": {"pairs": 8,  "cols": 4, "rows": 4, "exp_perfect": 60,  "exp_good": 45,  "exp_ok": 30},
    "hard":   {"pairs": 10, "cols": 5, "rows": 4, "exp_perfect": 120, "exp_good": 90,  "exp_ok": 60},
    "expert": {"pairs": 18, "cols": 6, "rows": 6, "exp_perfect": 1000,"exp_good": 600, "exp_ok": 300},
}


# ==================== 会话创建 ====================

def create_memory_session(difficulty: str = "easy") -> dict:
    cfg = MEMORY_DIFFICULTIES.get(difficulty, MEMORY_DIFFICULTIES["easy"])
    pairs = cfg["pairs"]
    symbols = MEMORY_SYMBOLS[:pairs]
    board = symbols * 2
    random.shuffle(board)
    total_cards = pairs * 2
    return {
        "started_at": datetime.utcnow().isoformat(),
        "difficulty": difficulty,
        "board": board,
        "revealed": [False] * total_cards,
        "flips": 0,
        "first_flip": None,
        "matched_pairs": 0,
        "total_pairs": pairs,
        "cols": cfg["cols"],
        "rows": cfg["rows"],
        "last_flip_result": None,
    }


# ==================== 状态脱敏 ====================

def sanitize_memory_state(session: dict) -> dict:
    """清除服务端秘密，返回客户端安全的记忆翻牌状态"""
    board_display = []
    for i in range(len(session["board"])):
        if session["revealed"][i]:
            board_display.append(session["board"][i])
        else:
            board_display.append(None)
    result = {
        "board": board_display,
        "flips": session["flips"],
        "matched_pairs": session["matched_pairs"],
        "total_pairs": session["total_pairs"],
        "rows": session.get("rows", 3),
        "cols": session.get("cols", 4),
        "difficulty": session.get("difficulty", "easy"),
        "first_flip": session.get("first_flip"),
        "last_flip_result": session.get("last_flip_result"),
        "completed": session.get("completed", False),
    }
    if session.get("completed"):
        result["exp_earned"] = session.get("exp_earned", 0)
    return result


# ==================== 游戏逻辑处理 ====================

def process_memory_action(session: dict, action: dict) -> dict:
    """处理记忆翻牌操作"""
    # 处理放弃
    if action.get("action") == "abandon":
        session["completed"] = True
        session["exp_earned"] = 0
        session["abandoned"] = True
        return {"completed": True, "exp_earned": 0, "abandoned": True}
    
    # 处理超时
    if action.get("timeout"):
        session["completed"] = True
        session["exp_earned"] = 0
        session["timeout"] = True
        return {"completed": True, "exp_earned": 0, "timeout": True}
    
    pos = action.get("position")
    total_cards = session["total_pairs"] * 2
    if pos is None or not (0 <= pos < total_cards):
        raise HTTPException(status_code=400, detail="无效的翻牌位置")
    if session["revealed"][pos]:
        raise HTTPException(status_code=400, detail="该卡牌已被翻开")

    if session["first_flip"] is None:
        # 翻第一张牌
        session["first_flip"] = pos
        session["last_flip_result"] = {
            "action": "first_flip",
            "position": pos,
            "symbol": session["board"][pos],
        }
    else:
        # 翻第二张牌
        first_pos = session["first_flip"]
        if pos == first_pos:
            raise HTTPException(status_code=400, detail="不能翻同一张牌")
        session["flips"] += 1
        first_symbol = session["board"][first_pos]
        second_symbol = session["board"][pos]

        if first_symbol == second_symbol:
            session["revealed"][first_pos] = True
            session["revealed"][pos] = True
            session["matched_pairs"] += 1
            session["last_flip_result"] = {
                "action": "match",
                "positions": [first_pos, pos],
                "symbol": first_symbol,
            }
        else:
            session["last_flip_result"] = {
                "action": "no_match",
                "positions": [first_pos, pos],
                "symbols": [first_symbol, second_symbol],
            }
        session["first_flip"] = None

    # 检查完成
    total_pairs = session["total_pairs"]
    completed = session["matched_pairs"] >= total_pairs
    exp_earned = 0
    if completed:
        flips = session["flips"]
        difficulty = session.get("difficulty", "easy")
        cfg = MEMORY_DIFFICULTIES.get(difficulty, MEMORY_DIFFICULTIES["easy"])
        # 根据翻牌效率计算经验：完美(翻牌数<=对数)、良好(<=对数*1.5)、一般
        if flips <= total_pairs:
            exp_earned = cfg["exp_perfect"]
        elif flips <= int(total_pairs * 1.5):
            exp_earned = cfg["exp_good"]
        else:
            exp_earned = cfg["exp_ok"]
        session["completed"] = True
        session["exp_earned"] = exp_earned

    return {"completed": completed, "exp_earned": exp_earned}
