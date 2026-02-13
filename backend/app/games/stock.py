"""
迷你炒股游戏 - 数据定义与逻辑
"""
import random
from datetime import datetime
from fastapi import HTTPException


# ==================== 数据定义 ====================

STOCK_DIFFICULTIES = {
    "easy":   {"rounds": 5,  "volatility": 0.08, "initial_cash": 10000, "allow_short": False,
               "exp_tiers": [(50, 40), (30, 30), (10, 20), (0, 10), (-999, 5)]},
    "medium": {"rounds": 10, "volatility": 0.15, "initial_cash": 10000, "allow_short": False,
               "exp_tiers": [(50, 80), (30, 50), (10, 30), (0, 15), (-999, 5)]},
    "hard":   {"rounds": 15, "volatility": 0.22, "initial_cash": 10000, "allow_short": True,
               "exp_tiers": [(50, 200), (30, 120), (10, 60), (0, 30), (-999, 10)]},
    "expert": {"rounds": 25, "volatility": 0.35, "initial_cash": 10000, "allow_short": True,
               "exp_tiers": [(100, 1000), (50, 500), (20, 200), (0, 80), (-999, 20)]},
}


# ==================== 会话创建 ====================

def create_stock_session(difficulty: str = "easy") -> dict:
    cfg = STOCK_DIFFICULTIES.get(difficulty, STOCK_DIFFICULTIES["easy"])
    rounds = cfg["rounds"]
    volatility = cfg["volatility"]
    initial_cash = cfg["initial_cash"]
    prices = [100.0]
    for _ in range(rounds):
        change = random.uniform(-volatility, volatility)
        new_price = round(prices[-1] * (1 + change), 2)
        new_price = max(20, min(300, new_price))
        prices.append(new_price)
    return {
        "started_at": datetime.utcnow().isoformat(),
        "difficulty": difficulty,
        "prices": prices,
        "current_round": 0,
        "total_rounds": rounds,
        "cash": float(initial_cash),
        "initial_cash": float(initial_cash),
        "shares": 0,
        "allow_short": cfg.get("allow_short", False),
        "history": [],
    }


# ==================== 状态脱敏 ====================

def sanitize_stock_state(session: dict) -> dict:
    """清除服务端秘密，返回客户端安全的炒股游戏状态"""
    visible_prices = session["prices"][:session["current_round"] + 1]
    total_rounds = session.get("total_rounds", 10)
    initial_cash = session.get("initial_cash", 10000)
    result = {
        "prices": visible_prices,
        "current_round": session["current_round"],
        "total_rounds": total_rounds,
        "initial_cash": initial_cash,
        "difficulty": session.get("difficulty", "easy"),
        "cash": round(session["cash"], 2),
        "shares": session["shares"],
        "allow_short": session.get("allow_short", False),
        "portfolio_value": round(session["cash"] + session["shares"] * visible_prices[-1], 2),
        "history": session["history"],
        "completed": session.get("completed", False),
    }
    if session.get("completed"):
        result["exp_earned"] = session.get("exp_earned", 0)
        result["final_value"] = session.get("final_value")
        result["profit_pct"] = session.get("profit_pct")
    return result


# ==================== 游戏逻辑处理 ====================

def process_stock_action(session: dict, action: dict) -> dict:
    """处理迷你炒股操作"""
    act = action.get("action")
    
    # 处理放弃
    if act == "abandon":
        session["completed"] = True
        session["exp_earned"] = 0
        session["abandoned"] = True
        initial_cash = session.get("initial_cash", 10000)
        # For short positions, negative shares * price is subtracted (cover cost)
        session["final_value"] = round(session["cash"] + session["shares"] * session["prices"][session["current_round"]], 2)
        session["profit_pct"] = round((session["final_value"] - initial_cash) / initial_cash * 100, 2)
        return {"completed": True, "exp_earned": 0, "abandoned": True}
    
    if act not in ("buy", "sell", "hold"):
        raise HTTPException(status_code=400, detail="操作必须是 buy、sell 或 hold")

    total_rounds = session["total_rounds"]
    round_idx = session["current_round"]
    if round_idx >= total_rounds:
        raise HTTPException(status_code=400, detail="游戏已结束")

    price = session["prices"][round_idx]
    quantity = int(action.get("quantity", 0))

    if act == "buy":
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="买入数量必须大于0")
        cost = quantity * price
        if cost > session["cash"]:
            raise HTTPException(status_code=400, detail="资金不足")
        session["cash"] -= cost
        session["shares"] += quantity
    elif act == "sell":
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="卖出数量必须大于0")
        allow_short = session.get("allow_short", False)
        if not allow_short and quantity > session["shares"]:
            raise HTTPException(status_code=400, detail="持股不足")
        # Short selling: limit max short position to avoid excessive risk
        if allow_short:
            max_short = int(session["cash"] / price)  # margin based on current cash
            if session["shares"] - quantity < -max_short:
                raise HTTPException(status_code=400, detail="做空保证金不足")
        session["cash"] += quantity * price
        session["shares"] -= quantity

    session["history"].append({
        "round": round_idx,
        "action": act,
        "quantity": quantity if act != "hold" else 0,
        "price": price,
        "cash": round(session["cash"], 2),
        "shares": session["shares"],
    })
    session["current_round"] += 1

    completed = session["current_round"] >= total_rounds
    exp_earned = 0
    if completed:
        final_price = session["prices"][total_rounds]
        # For short positions (negative shares), this deducts the cover cost
        session["cash"] += session["shares"] * final_price
        session["cash"] = round(session["cash"], 2)
        session["shares"] = 0
        initial_cash = session.get("initial_cash", 10000)
        profit_pct = (session["cash"] - initial_cash) / initial_cash * 100
        # 根据难度配置获取经验奖励
        difficulty = session.get("difficulty", "easy")
        cfg = STOCK_DIFFICULTIES.get(difficulty, STOCK_DIFFICULTIES["easy"])
        exp_tiers = cfg["exp_tiers"]
        for threshold, exp in exp_tiers:
            if profit_pct >= threshold:
                exp_earned = exp
                break
        session["completed"] = True
        session["exp_earned"] = exp_earned
        session["final_value"] = session["cash"]
        session["profit_pct"] = round(profit_pct, 2)

    return {"completed": completed, "exp_earned": exp_earned}
