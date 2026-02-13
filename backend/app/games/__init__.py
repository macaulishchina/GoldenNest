"""
游戏子系统模块

将各个小游戏的数据定义和逻辑从 pet.py 中抽离，
每个游戏一个独立文件，便于维护和扩展。
"""

from app.games.memory import (
    MEMORY_SYMBOLS, MEMORY_DIFFICULTIES,
    create_memory_session, process_memory_action, sanitize_memory_state,
)
from app.games.stock import (
    STOCK_DIFFICULTIES,
    create_stock_session, process_stock_action, sanitize_stock_state,
)
from app.games.adventure import (
    ADVENTURE_MONSTERS, ADVENTURE_DIFFICULTIES,
    BACKPACK_ITEMS, MERGE_CHAINS, ITEM_SETS,
    create_adventure_session, process_adventure_action, sanitize_adventure_state,
)
from app.games.minesweeper import (
    MINESWEEPER_DIFFICULTIES,
    create_minesweeper_session, process_minesweeper_action, sanitize_minesweeper_state,
)

__all__ = [
    # memory
    "MEMORY_SYMBOLS", "MEMORY_DIFFICULTIES",
    "create_memory_session", "process_memory_action", "sanitize_memory_state",
    # stock
    "STOCK_DIFFICULTIES",
    "create_stock_session", "process_stock_action", "sanitize_stock_state",
    # adventure
    "ADVENTURE_MONSTERS", "ADVENTURE_DIFFICULTIES",
    "BACKPACK_ITEMS", "MERGE_CHAINS", "ITEM_SETS",
    "create_adventure_session", "process_adventure_action", "sanitize_adventure_state",
    # minesweeper
    "MINESWEEPER_DIFFICULTIES",
    "create_minesweeper_session", "process_minesweeper_action", "sanitize_minesweeper_state",
]
