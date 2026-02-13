"""
宠物探险RPG游戏 - 数据定义与逻辑

包含: 背包系统(Backpack Hero inspired)、怪物、遭遇、祝福、战斗等
"""
import re as _re
import random
from datetime import datetime
from collections import Counter
from fastapi import HTTPException


# ---- 工具函数: 清除 UTF-16 surrogate 字符 ----
_SURROGATE_RE = _re.compile(r'[\ud800-\udfff]')

def _strip_surrogates(obj):
    """递归清除字符串中的 UTF-16 surrogate 字符，防止 JSON 序列化报错"""
    if isinstance(obj, str):
        return _SURROGATE_RE.sub('', obj)
    if isinstance(obj, dict):
        return {k: _strip_surrogates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_surrogates(v) for v in obj]
    return obj


# ==================== 数据定义 ====================

ADVENTURE_MONSTERS = [
    {"name": "小偷鼠", "hp": 20, "attack": 5},
    {"name": "贪婪蛇", "hp": 30, "attack": 8},
    {"name": "税务怪", "hp": 35, "attack": 10},
    {"name": "通胀兽", "hp": 45, "attack": 12},
]

ADVENTURE_DIFFICULTIES = {
    "easy":   {
        "max_floor": 5, "player_hp": 120, "atk_bonus": 5,
        "monster_hp_mult": 0.85, "monster_atk_mult": 0.8,
        "floor_exp": [0, 5, 8, 12, 16, 25],
        "boss": {"name": "小贪官", "hp": 50, "attack": 10},
    },
    "medium": {
        "max_floor": 8, "player_hp": 100, "atk_bonus": 0,
        "monster_hp_mult": 1.2, "monster_atk_mult": 1.15,
        "floor_exp": [0, 5, 10, 16, 22, 30, 40, 50, 65],
        "boss": {"name": "金融危机龙", "hp": 100, "attack": 18},
    },
    "hard":   {
        "max_floor": 12, "player_hp": 100, "atk_bonus": 0,
        "monster_hp_mult": 1.8, "monster_atk_mult": 1.5,
        "floor_exp": [0, 8, 14, 20, 28, 36, 44, 52, 60, 70, 80, 95, 115],
        "boss": {"name": "黑天鹅巨兽", "hp": 200, "attack": 28},
    },
    "expert": {
        "max_floor": 18, "player_hp": 80, "atk_bonus": -3,
        "monster_hp_mult": 2.5, "monster_atk_mult": 2.0,
        "floor_exp": [0, 10, 18, 26, 35, 45, 55, 65, 78, 90, 105, 120, 135, 150, 168, 185, 205, 230, 260],
        "boss": {"name": "末日收割者", "hp": 400, "attack": 42},
    },
    "endless": {
        "max_floor": 999999, "player_hp": 120, "atk_bonus": 0,
        "monster_hp_mult": 1.0, "monster_atk_mult": 1.0,
        "floor_exp": [],
        "boss": None,
        "endless": True,
    },
}

# 精英怪物能力
ELITE_ABILITIES = [
    {"id": "enrage",      "name": "🔥狂暴",  "desc": "HP<30%时攻击翻倍"},
    {"id": "regen",       "name": "💚再生",  "desc": "每回合恢复6%最大HP"},
    {"id": "thorns",      "name": "🌵荆棘",  "desc": "受击反弹15%伤害"},
    {"id": "vampiric",    "name": "🧛吸血",  "desc": "攻击恢复25%伤害为HP"},
    {"id": "armor_break", "name": "⚡破甲",  "desc": "无视50%防御"},
]

# 楼层诅咒 (每15层触发)
FLOOR_CURSES = [
    {"id": "weakness",  "name": "⬇️虚弱之地",  "desc": "攻击力-25%"},
    {"id": "corrosion", "name": "🧪腐蚀之风",  "desc": "防御力-50%"},
    {"id": "chaos",     "name": "🌀混乱领域",  "desc": "暴击率减半"},
    {"id": "seal",      "name": "🚫封疗结界",  "desc": "吸血无效"},
    {"id": "empowered", "name": "💪怪物增幅",  "desc": "怪物攻击+30%"},
]

# ===================== 临时增益/减益 (Timed Buffs) =====================
# 每个 buff/debuff 有 turns 持续回合数（战斗回合 或 楼层）
# scope: "combat" = 每次战斗回合递减, "floor" = 每过一层递减
TIMED_BUFF_DEFS = {
    # ── 正向 buff ──
    "battle_fury":   {"name": "🔥战意",     "type": "buff", "scope": "combat", "desc": "攻击+30%",
                      "effects": {"atk_pct": 30}},
    "stone_skin":    {"name": "🪨石肤",     "type": "buff", "scope": "combat", "desc": "防御+50%",
                      "effects": {"def_pct": 50}},
    "swift_step":    {"name": "💨疾风",     "type": "buff", "scope": "combat", "desc": "闪避+20%",
                      "effects": {"dodge_bonus": 20}},
    "war_cry":       {"name": "📯战吼",     "type": "buff", "scope": "combat", "desc": "暴击率+25%",
                      "effects": {"crit_bonus": 25}},
    "regeneration":  {"name": "🩹再生",     "type": "buff", "scope": "combat", "desc": "每回合恢复5%HP",
                      "effects": {"hot_pct": 5}},
    "lucky_star":    {"name": "⭐幸运",     "type": "buff", "scope": "combat", "desc": "暴击伤害+50%",
                      "effects": {"crit_dmg_bonus": 50}},
    "iron_will":     {"name": "🛡️意志",    "type": "buff", "scope": "floor",  "desc": "防御+5（持续数层）",
                      "effects": {"def_flat": 5}},
    "vigor":         {"name": "💪活力",     "type": "buff", "scope": "floor",  "desc": "攻击+5（持续数层）",
                      "effects": {"atk_flat": 5}},
    # ── 负向 debuff ──
    "bleed":         {"name": "🩸流血",     "type": "debuff", "scope": "combat", "desc": "每回合失去4%HP",
                      "effects": {"dot_pct": 4}},
    "weakness":      {"name": "💔虚弱",     "type": "debuff", "scope": "combat", "desc": "攻击-25%",
                      "effects": {"atk_pct": -25}},
    "armor_crack":   {"name": "🔓破甲",     "type": "debuff", "scope": "combat", "desc": "防御-50%",
                      "effects": {"def_pct": -50}},
    "slow":          {"name": "🐌迟缓",     "type": "debuff", "scope": "combat", "desc": "闪避-15%",
                      "effects": {"dodge_bonus": -15}},
    "blind":         {"name": "🌑致盲",     "type": "debuff", "scope": "combat", "desc": "暴击率-20%",
                      "effects": {"crit_bonus": -20}},
    "poison":        {"name": "☠️中毒",     "type": "debuff", "scope": "combat", "desc": "每回合失去固定HP",
                      "effects": {"dot_flat": 8}},
    "curse_frail":   {"name": "💀脆弱",     "type": "debuff", "scope": "floor",  "desc": "防御-3（持续数层）",
                      "effects": {"def_flat": -3}},
    "curse_exhaust": {"name": "😵疲惫",     "type": "debuff", "scope": "floor",  "desc": "攻击-3（持续数层）",
                      "effects": {"atk_flat": -3}},
}

# 精英怪附加debuff概率表 (ability_id → debuff_id, 概率)
_ELITE_COMBAT_DEBUFFS = {
    "enrage":      ("bleed",       0.30),  # 狂暴→流血
    "thorns":      ("armor_crack", 0.25),  # 荆棘→破甲
    "vampiric":    ("weakness",    0.30),  # 吸血→虚弱
    "armor_break": ("slow",        0.25),  # 破甲→迟缓
    "regen":       ("poison",      0.20),  # 再生→中毒
}

# 陷阱失败时的debuff (随机选一个)
_TRAP_DEBUFFS = ["bleed", "poison", "curse_frail", "curse_exhaust"]


def _apply_timed_buff(session: dict, buff_id: str, turns: int, source: str = ""):
    """给玩家添加一个临时buff/debuff。同id叠加刷新持续时间取最大值。"""
    defn = TIMED_BUFF_DEFS.get(buff_id)
    if not defn:
        return
    tb_list: list = session.setdefault("timed_buffs", [])
    # 查找已有同id buff → 刷新
    for tb in tb_list:
        if tb["id"] == buff_id:
            tb["turns_left"] = max(tb["turns_left"], turns)
            tb["source"] = source
            return
    tb_list.append({
        "id": buff_id,
        "turns_left": turns,
        "source": source,
    })


def _tick_timed_buffs(session: dict, scope: str):
    """递减指定scope的timed_buffs持续时间，移除已过期的。"""
    tb_list = session.get("timed_buffs", [])
    if not tb_list:
        return
    log = session.get("log", [])
    remaining = []
    for tb in tb_list:
        defn = TIMED_BUFF_DEFS.get(tb["id"])
        if not defn:
            continue
        if defn["scope"] == scope:
            tb["turns_left"] -= 1
            if tb["turns_left"] <= 0:
                log.append(f"⏳ {defn['name']}效果消失了")
                continue
        remaining.append(tb)
    session["timed_buffs"] = remaining


def _get_timed_buff_effects(session: dict) -> dict:
    """汇总当前所有timed_buff的效果。返回 {effect_key: total_value}"""
    result: dict = {}
    for tb in session.get("timed_buffs", []):
        defn = TIMED_BUFF_DEFS.get(tb["id"])
        if not defn:
            continue
        for ek, ev in defn["effects"].items():
            result[ek] = result.get(ek, 0) + ev
    return result


def _apply_timed_dot_hot(session: dict, log: list):
    """处理DoT(持续伤害)和HoT(持续恢复)效果。在战斗回合开始时调用。"""
    effects = _get_timed_buff_effects(session)
    # HoT: 百分比恢复
    hot = effects.get("hot_pct", 0)
    if hot > 0:
        heal = max(1, int(session["max_hp"] * hot / 100))
        old_hp = session["hp"]
        session["hp"] = min(session["max_hp"], session["hp"] + heal)
        actual = session["hp"] - old_hp
        if actual > 0:
            log.append(f"🩹 再生恢复{actual}HP")
    # DoT: 百分比伤害
    dot_pct = effects.get("dot_pct", 0)
    if dot_pct > 0:
        dmg = max(1, int(session["max_hp"] * dot_pct / 100))
        session["hp"] -= dmg
        log.append(f"🩸 流血-{dmg}HP (HP: {session['hp']}/{session['max_hp']})")
    # DoT: 固定伤害
    dot_flat = effects.get("dot_flat", 0)
    if dot_flat > 0:
        session["hp"] -= dot_flat
        log.append(f"☠️ 中毒-{dot_flat}HP (HP: {session['hp']}/{session['max_hp']})")


BACKPACK_ITEMS = {
    # ---- 武器 (1×2 竖向) ----
    "wooden_stick":  {"name": "木棍",   "icon": "🪵", "type": "weapon",  "w": 1, "h": 2, "rarity": "common",    "effects": {"atk": 3},  "adj": {"weapon": {"atk": 1}},  "price": 6,  "desc": "攻击+3"},
    "iron_sword":    {"name": "铁剑",   "icon": "🗡️", "type": "weapon",  "w": 1, "h": 2, "rarity": "uncommon",  "effects": {"atk": 6},  "adj": {"weapon": {"atk": 2}},  "price": 12, "desc": "攻击+6"},
    "flame_blade":   {"name": "烈焰刃", "icon": "🔥", "type": "weapon",  "w": 1, "h": 2, "rarity": "rare",      "effects": {"atk": 9, "crit_damage": 15},  "adj": {"weapon": {"atk": 3}}, "price": 22, "desc": "攻击+9 爆伤+15%"},
    "divine_sword":  {"name": "圣剑",   "icon": "✨", "type": "weapon",  "w": 1, "h": 2, "rarity": "legendary", "effects": {"atk": 14, "crit": 10, "lifesteal": 8}, "adj": {"weapon": {"atk": 4}}, "price": 38, "desc": "攻击+14 暴击+10% 吸血+8%"},
    "dagger":        {"name": "匕首",   "icon": "🔪", "type": "weapon",  "w": 1, "h": 1, "rarity": "common",    "effects": {"atk": 2, "crit": 5},   "price": 5, "desc": "攻击+2 暴击+5%"},
    "poison_blade":  {"name": "淬毒刃", "icon": "🧪", "type": "weapon",  "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"atk": 4, "lifesteal": 8}, "price": 10, "desc": "攻击+4 吸血+8%"},
    # ---- 盾牌 (2×1 横向) ----
    "wooden_shield": {"name": "木盾",   "icon": "🧱", "type": "shield",  "w": 2, "h": 1, "rarity": "common",    "effects": {"def": 4},  "adj": {"shield": {"def": 1}}, "price": 5,  "desc": "防御+4"},
    "iron_shield":   {"name": "铁盾",   "icon": "🛡️", "type": "shield",  "w": 2, "h": 1, "rarity": "uncommon",  "effects": {"def": 5},  "adj": {"shield": {"def": 2}}, "price": 11, "desc": "防御+5"},
    "holy_shield":   {"name": "圣盾",   "icon": "⚜️", "type": "shield",  "w": 2, "h": 1, "rarity": "rare",      "effects": {"def": 8, "max_hp": 15}, "adj": {"shield": {"def": 3}}, "price": 20, "desc": "防御+8 HP+15"},
    "buckler":       {"name": "圆盾",   "icon": "🔰", "type": "shield",  "w": 1, "h": 1, "rarity": "common",    "effects": {"def": 2},  "price": 4,  "desc": "防御+2"},
    # ---- 药水 (1×1, 消耗品) ----
    "small_potion":  {"name": "小药水", "icon": "💧", "type": "potion", "w": 1, "h": 1, "rarity": "common",    "effects": {"heal": 25},  "consumable": True, "price": 5,  "desc": "恢复25HP"},
    "medium_potion": {"name": "中药水", "icon": "💊", "type": "potion", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"heal": 55},  "consumable": True, "price": 10, "desc": "恢复55HP"},
    "large_potion":  {"name": "大药水", "icon": "🍷", "type": "potion", "w": 1, "h": 1, "rarity": "rare",      "effects": {"heal": 110}, "consumable": True, "price": 18, "desc": "恢复110HP"},
    "elixir":        {"name": "万能药", "icon": "⚗️", "type": "potion", "w": 1, "h": 1, "rarity": "legendary", "effects": {"heal_pct": 100}, "consumable": True, "price": 30, "desc": "恢复全部HP"},
    "bomb":          {"name": "炸弹",   "icon": "💣", "type": "potion", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"damage": 30}, "consumable": True, "price": 10, "desc": "对怪物造成30点伤害"},
    "mega_bomb":     {"name": "巨型炸弹", "icon": "🧨", "type": "potion", "w": 1, "h": 1, "rarity": "rare",    "effects": {"damage": 60}, "consumable": True, "price": 18, "desc": "对怪物造成60点伤害"},
    # ---- 饰品 (1×1) ----
    "lucky_coin":    {"name": "幸运币", "icon": "🪙", "type": "accessory", "w": 1, "h": 1, "rarity": "common",    "effects": {"crit": 8},   "price": 6,  "desc": "暴击+8%"},
    "vampire_fang":  {"name": "吸血牙", "icon": "🧛", "type": "accessory", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"lifesteal": 12}, "price": 10, "desc": "吸血+12%"},
    "power_ring":    {"name": "力戒",   "icon": "💍", "type": "accessory", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"atk": 4},    "adj": {"weapon": {"atk": 3}}, "price": 9, "desc": "攻击+4"},
    "crit_gem":      {"name": "暴击宝石","icon": "💎", "type": "accessory", "w": 1, "h": 1, "rarity": "rare",     "effects": {"crit": 12, "crit_damage": 25}, "price": 18, "desc": "暴击+12% 爆伤+25%"},
    "dragon_heart":  {"name": "龙心",   "icon": "❤️‍🔥", "type": "accessory", "w": 1, "h": 1, "rarity": "legendary", "effects": {"max_hp": 25, "lifesteal": 10, "atk": 5}, "price": 35, "desc": "HP+25 吸血+10% 攻击+5"},
    "exp_magnet":    {"name": "经验磁铁","icon": "🧲", "type": "accessory", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"exp_bonus": 15}, "price": 8, "desc": "经验+15%"},
    # ---- 护甲 (2×2) ----
    "leather_armor": {"name": "皮甲",   "icon": "🦺", "type": "armor", "w": 2, "h": 2, "rarity": "common",   "effects": {"def": 3, "max_hp": 10},  "price": 10, "desc": "防御+3 HP+10"},
    "chain_mail":    {"name": "锁甲",   "icon": "⛓️", "type": "armor", "w": 2, "h": 2, "rarity": "uncommon", "effects": {"def": 6, "max_hp": 20},  "price": 18, "desc": "防御+6 HP+20"},
    "plate_armor":   {"name": "板甲",   "icon": "🏰", "type": "armor", "w": 2, "h": 2, "rarity": "rare",     "effects": {"def": 10, "max_hp": 35}, "price": 28, "desc": "防御+10 HP+35"},
    # ---- 特殊 (1×1) ----
    "whetstone":     {"name": "磨刀石", "icon": "🪨", "type": "special", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {}, "adj": {"weapon": {"atk": 5}}, "price": 8, "desc": "相邻武器攻击+5"},
    "shield_polish": {"name": "盾蜡",   "icon": "🫧", "type": "special", "w": 1, "h": 1, "rarity": "uncommon",  "effects": {}, "adj": {"shield": {"def": 4}}, "price": 8, "desc": "相邻盾牌防御+4"},
    "heart_crystal": {"name": "生命水晶","icon": "💗", "type": "special", "w": 1, "h": 1, "rarity": "rare",     "effects": {"max_hp": 20}, "price": 15, "desc": "最大HP+20"},
    "berserker_mark":{"name": "狂战印记","icon": "🔴", "type": "special", "w": 1, "h": 1, "rarity": "rare",     "effects": {"atk": 6, "def": -2}, "price": 14, "desc": "攻击+6 防御-2"},
    # ---- 诅咒物品 (强属性 + 负面效果) ----
    "cursed_blade":  {"name": "诅咒之刃", "icon": "🩸", "type": "weapon",  "w": 1, "h": 2, "rarity": "rare",   "effects": {"atk": 16}, "curse": {"max_hp": -20}, "adj": {"weapon": {"atk": 3}}, "price": 15, "desc": "攻击+16 但HP-20", "cursed": True},
    "cursed_crown":  {"name": "噩梦王冠", "icon": "🖤", "type": "accessory","w": 1, "h": 1, "rarity": "rare",   "effects": {"crit": 20, "crit_damage": 35}, "curse": {"def": -3}, "price": 16, "desc": "暴击+20% 爆伤+35% 但防御-3", "cursed": True},
    "cursed_shield": {"name": "苦痛之盾", "icon": "🟣", "type": "shield",  "w": 2, "h": 1, "rarity": "rare",   "effects": {"def": 12}, "curse": {"atk": -4}, "price": 14, "desc": "防御+12 但攻击-4", "cursed": True},
    "cursed_ring":   {"name": "贪婪指环", "icon": "💀", "type": "accessory","w": 1, "h": 1, "rarity": "legendary","effects": {"atk": 8, "lifesteal": 15, "crit": 10}, "curse": {"max_hp": -30}, "price": 22, "desc": "全属性大幅提升 但HP-30", "cursed": True},
    "purify_stone":  {"name": "净化石",   "icon": "🔮", "type": "special",  "w": 1, "h": 1, "rarity": "rare",   "effects": {}, "adj": {}, "price": 20, "desc": "相邻诅咒物品→净化(移除负面)", "purifier": True},
    # ---- 被动技能物品 ----
    "regen_amulet":  {"name": "回春项链", "icon": "💚", "type": "accessory","w": 1, "h": 1, "rarity": "uncommon", "effects": {}, "passive": {"heal_per_turn": 5}, "price": 12, "desc": "每回合恢复5HP"},
    "thorn_mail":    {"name": "荆棘甲",   "icon": "🌵", "type": "armor",   "w": 2, "h": 2, "rarity": "rare",     "effects": {"def": 5}, "passive": {"reflect_pct": 20}, "price": 22, "desc": "防御+5 反弹20%受到的伤害"},
    "first_strike":  {"name": "先手指环", "icon": "💨", "type": "accessory","w": 1, "h": 1, "rarity": "uncommon", "effects": {}, "passive": {"first_hit_shield": 15}, "price": 10, "desc": "每场战斗首次受击减免15点伤害"},
    "exp_tome":      {"name": "经验宝典", "icon": "📖", "type": "special",  "w": 1, "h": 1, "rarity": "uncommon", "effects": {"exp_bonus": 10}, "passive": {"bonus_exp_pct": 10}, "price": 12, "desc": "经验+10% 击杀额外+10%EXP"},
    "lucky_clover":  {"name": "四叶草",   "icon": "🍀", "type": "accessory","w": 1, "h": 1, "rarity": "uncommon", "effects": {"crit": 5}, "passive": {"dodge_pct": 10}, "price": 10, "desc": "暴击+5% 10%概率闪避攻击"},
    # ---- 史诗级武器 ----
    "void_blade":    {"name": "虚空之刃", "icon": "🌌", "type": "weapon",  "w": 1, "h": 2, "rarity": "legendary", "effects": {"atk": 18, "crit": 8}, "passive": {"multi_strike": 20}, "adj": {"weapon": {"atk": 5}}, "price": 45, "desc": "攻+18 暴击+8% 20%概率连击"},
    "soul_reaper":   {"name": "灵魂收割者","icon": "☠️", "type": "weapon",  "w": 1, "h": 2, "rarity": "legendary", "effects": {"atk": 12, "lifesteal": 12}, "passive": {"execute_pct": 15}, "price": 42, "desc": "攻+12 吸血+12% 怪物HP<15%时斩杀", "cursed": True, "curse": {"max_hp": -25}},
    # ---- 史诗级护甲 ----
    "phoenix_armor": {"name": "凤凰战甲", "icon": "🦤", "type": "armor", "w": 2, "h": 2, "rarity": "legendary", "effects": {"def": 12, "max_hp": 50}, "passive": {"battle_heal": 8}, "price": 48, "desc": "防+12 HP+50 每场战斗结束回复8%HP"},
    # ---- 史诗级盾牌 ----
    "aegis_shield":  {"name": "神盾埃吉斯","icon": "🏵️", "type": "shield", "w": 2, "h": 1, "rarity": "legendary", "effects": {"def": 10, "max_hp": 20}, "passive": {"block_chance": 15}, "adj": {"shield": {"def": 4}}, "price": 40, "desc": "防+10 HP+20 15%概率完全格挡"},
    # ---- 史诗级饰品 ----
    "phoenix_feather":{"name": "凤凰羽",  "icon": "🪶", "type": "accessory","w": 1, "h": 1, "rarity": "legendary", "effects": {"max_hp": 15}, "passive": {"revive": 1}, "price": 50, "desc": "HP+15 死亡时复活1次(恢复30%HP)"},
    "chaos_orb":     {"name": "混沌宝珠", "icon": "🎱", "type": "accessory","w": 1, "h": 1, "rarity": "legendary", "effects": {"atk": 6, "crit": 6, "def": 3}, "passive": {"random_buff": 1}, "price": 38, "desc": "全属性+每回合随机增强"},
    "crit_crown":    {"name": "裁决之冠", "icon": "👑", "type": "accessory","w": 1, "h": 1, "rarity": "legendary", "effects": {"crit": 15, "crit_damage": 40}, "passive": {"crit_heal": 10}, "price": 42, "desc": "暴击+15% 爆伤+40% 暴击时回复10%伤害"},
    "blood_chalice": {"name": "血之圣杯", "icon": "🏆", "type": "accessory","w": 1, "h": 1, "rarity": "legendary", "effects": {"lifesteal": 20, "atk": 5}, "passive": {"overkill_heal": 25}, "price": 40, "desc": "吸血+20% 攻+5 击杀超额伤害25%转回HP", "cursed": True, "curse": {"def": -4}},
    # ---- 史诗级药水 ----
    "divine_elixir":  {"name": "神泰之药", "icon": "⭐", "type": "potion", "w": 1, "h": 1, "rarity": "legendary", "effects": {"heal_pct": 100, "max_hp": 20}, "consumable": True, "price": 35, "desc": "恢复全部HP并+20最大HP"},
    "nuke_bomb":     {"name": "核弹",     "icon": "☢️", "type": "potion", "w": 1, "h": 1, "rarity": "legendary", "effects": {"damage": 120}, "consumable": True, "price": 35, "desc": "对怪物造成120点伤害"},
    # ---- 史诗级特殊 ----
    "amplifier":     {"name": "增幅器",   "icon": "📡", "type": "special", "w": 1, "h": 1, "rarity": "legendary", "effects": {}, "adj": {"weapon": {"atk": 8}, "shield": {"def": 6}, "armor": {"def": 4, "max_hp": 10}}, "price": 35, "desc": "相邻武器/盾/甲大幅增强"},
    # ==================== 新装备栏: 头盔 (1×1) ====================
    "cloth_hood":      {"name": "布兜帽",   "icon": "🧢", "type": "helmet",   "w": 1, "h": 1, "rarity": "common",    "effects": {"def": 1, "max_hp": 5},  "price": 4,  "desc": "防御+1 HP+5"},
    "iron_helm":       {"name": "铁头盔",   "icon": "⛑️", "type": "helmet",   "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"def": 3, "max_hp": 12}, "price": 9,  "desc": "防御+3 HP+12"},
    "war_helm":        {"name": "战争头盔", "icon": "🪖", "type": "helmet",   "w": 1, "h": 1, "rarity": "rare",      "effects": {"def": 5, "max_hp": 20, "crit": 5}, "price": 18, "desc": "防+5 HP+20 暴击+5%"},
    "dragon_helm":     {"name": "龙首盔",   "icon": "🐲", "type": "helmet",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 8, "max_hp": 35, "crit": 10, "atk": 3}, "price": 35, "desc": "防+8 HP+35 暴击+10% 攻+3"},
    "titan_helm":      {"name": "泰坦头冠", "icon": "🏛️", "type": "helmet",   "w": 1, "h": 1, "rarity": "mythic",    "effects": {"def": 12, "max_hp": 50, "crit": 15, "atk": 6}, "price": 55, "desc": "防+12 HP+50 暴击+15% 攻+6"},
    "eternal_helm":    {"name": "永恒之冠", "icon": "🌟", "type": "helmet",   "w": 1, "h": 1, "rarity": "eternal",   "effects": {"def": 16, "max_hp": 70, "crit": 20, "atk": 10}, "passive": {"block_chance": 10}, "price": 80, "desc": "防+16 HP+70 暴击+20% 攻+10 10%格挡"},
    # ==================== 新装备栏: 护臂 (1×1) ====================
    "cloth_bracer":    {"name": "布护腕",   "icon": "🧤", "type": "bracer",   "w": 1, "h": 1, "rarity": "common",    "effects": {"def": 1, "atk": 1},  "price": 4,  "desc": "防御+1 攻击+1"},
    "iron_bracer":     {"name": "铁护臂",   "icon": "🦾", "type": "bracer",   "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"def": 2, "atk": 3},  "price": 9,  "desc": "防御+2 攻击+3"},
    "war_bracer":      {"name": "战争护臂", "icon": "💪", "type": "bracer",   "w": 1, "h": 1, "rarity": "rare",      "effects": {"def": 4, "atk": 5, "crit_damage": 10}, "price": 18, "desc": "防+4 攻+5 爆伤+10%"},
    "dragon_bracer":   {"name": "龙鳞护臂", "icon": "🐉", "type": "bracer",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 6, "atk": 8, "crit_damage": 20}, "price": 35, "desc": "防+6 攻+8 爆伤+20%"},
    "titan_bracer":    {"name": "泰坦臂铠", "icon": "⚙️", "type": "bracer",   "w": 1, "h": 1, "rarity": "mythic",    "effects": {"def": 9, "atk": 12, "crit_damage": 30}, "price": 55, "desc": "防+9 攻+12 爆伤+30%"},
    "eternal_bracer":  {"name": "永恒臂环", "icon": "🔗", "type": "bracer",   "w": 1, "h": 1, "rarity": "eternal",   "effects": {"def": 12, "atk": 16, "crit_damage": 45}, "passive": {"reflect_pct": 10}, "price": 80, "desc": "防+12 攻+16 爆伤+45% 反弹10%"},
    # ==================== 新装备栏: 鞋子 (1×1) ====================
    "cloth_boots":     {"name": "布鞋",     "icon": "👟", "type": "boots",    "w": 1, "h": 1, "rarity": "common",    "effects": {"def": 1, "max_hp": 3},  "passive": {"dodge_pct": 3},  "price": 4,  "desc": "防+1 HP+3 闪避3%"},
    "iron_boots":      {"name": "铁靴",     "icon": "🥾", "type": "boots",    "w": 1, "h": 1, "rarity": "uncommon",  "effects": {"def": 3, "max_hp": 8},  "passive": {"dodge_pct": 5},  "price": 9,  "desc": "防+3 HP+8 闪避5%"},
    "war_boots":       {"name": "战靴",     "icon": "👢", "type": "boots",    "w": 1, "h": 1, "rarity": "rare",      "effects": {"def": 5, "max_hp": 15}, "passive": {"dodge_pct": 8},  "price": 18, "desc": "防+5 HP+15 闪避8%"},
    "dragon_boots":    {"name": "龙皮战靴", "icon": "🦶", "type": "boots",    "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 7, "max_hp": 25}, "passive": {"dodge_pct": 12}, "price": 35, "desc": "防+7 HP+25 闪避12%"},
    "titan_boots":     {"name": "泰坦重靴", "icon": "🏃", "type": "boots",    "w": 1, "h": 1, "rarity": "mythic",    "effects": {"def": 10, "max_hp": 38}, "passive": {"dodge_pct": 16}, "price": 55, "desc": "防+10 HP+38 闪避16%"},
    "eternal_boots":   {"name": "永恒足履", "icon": "💫", "type": "boots",    "w": 1, "h": 1, "rarity": "eternal",   "effects": {"def": 14, "max_hp": 55}, "passive": {"dodge_pct": 22}, "price": 80, "desc": "防+14 HP+55 闪避22%"},
    # ==================== 新装备栏: 护腿 (1×2) ====================
    "cloth_leggings":  {"name": "布裤",     "icon": "👖", "type": "leggings", "w": 1, "h": 2, "rarity": "common",    "effects": {"def": 2, "max_hp": 8},  "price": 6,  "desc": "防御+2 HP+8"},
    "iron_leggings":   {"name": "铁护腿",   "icon": "🦿", "type": "leggings", "w": 1, "h": 2, "rarity": "uncommon",  "effects": {"def": 4, "max_hp": 15}, "price": 12, "desc": "防御+4 HP+15"},
    "war_leggings":    {"name": "战争护腿", "icon": "🩳", "type": "leggings", "w": 1, "h": 2, "rarity": "rare",      "effects": {"def": 7, "max_hp": 28}, "price": 22, "desc": "防御+7 HP+28"},
    "dragon_leggings": {"name": "龙鳞腿甲", "icon": "🐊", "type": "leggings", "w": 1, "h": 2, "rarity": "legendary", "effects": {"def": 10, "max_hp": 45}, "price": 40, "desc": "防御+10 HP+45"},
    "titan_leggings":  {"name": "泰坦腿铠", "icon": "🏗️", "type": "leggings", "w": 1, "h": 2, "rarity": "mythic",    "effects": {"def": 14, "max_hp": 60}, "price": 60, "desc": "防御+14 HP+60"},
    "eternal_leggings":{"name": "永恒腿甲", "icon": "🌠", "type": "leggings", "w": 1, "h": 2, "rarity": "eternal",   "effects": {"def": 20, "max_hp": 80}, "passive": {"heal_per_turn": 8}, "price": 85, "desc": "防+20 HP+80 每回合回复8HP"},
    # ==================== 神话级合成装备 (Mythic - 合成专属) ====================
    "astral_blade":    {"name": "星辰之刃", "icon": "☄️", "type": "weapon",    "w": 1, "h": 2, "rarity": "mythic", "effects": {"atk": 24, "crit": 12, "crit_damage": 20}, "passive": {"multi_strike": 30}, "adj": {"weapon": {"atk": 6}}, "price": 65, "desc": "攻+24 暴击+12% 爆伤+20% 30%连击"},
    "death_scythe":    {"name": "死神之镰", "icon": "⚰️", "type": "weapon",    "w": 1, "h": 2, "rarity": "mythic", "effects": {"atk": 18, "lifesteal": 18, "crit": 10}, "passive": {"execute_pct": 25}, "price": 60, "desc": "攻+18 吸血+18% 暴击+10% 斩杀<25%", "cursed": True, "curse": {"max_hp": -35}},
    "titan_bulwark":   {"name": "泰坦壁垒", "icon": "🗿", "type": "shield",   "w": 2, "h": 1, "rarity": "mythic", "effects": {"def": 15, "max_hp": 35}, "passive": {"block_chance": 25}, "adj": {"shield": {"def": 5}}, "price": 58, "desc": "防+15 HP+35 25%格挡"},
    "dragon_plate":    {"name": "龙鳞天甲", "icon": "🦖", "type": "armor",     "w": 2, "h": 2, "rarity": "mythic", "effects": {"def": 18, "max_hp": 70}, "passive": {"battle_heal": 12, "reflect_pct": 10}, "price": 68, "desc": "防+18 HP+70 战后回复12%HP 反弹10%"},
    "miracle_elixir":  {"name": "奇迹之药", "icon": "🍶", "type": "potion",    "w": 1, "h": 1, "rarity": "mythic", "effects": {"heal_pct": 100, "max_hp": 40}, "consumable": True, "price": 50, "desc": "恢复全部HP+40最大HP"},
    "antimatter_bomb": {"name": "反物质弹", "icon": "⚛️", "type": "potion",    "w": 1, "h": 1, "rarity": "mythic", "effects": {"damage": 200}, "consumable": True, "price": 50, "desc": "造成200点伤害"},
    "destiny_crown":   {"name": "命运之冠", "icon": "🎇", "type": "accessory", "w": 1, "h": 1, "rarity": "mythic", "effects": {"crit": 22, "crit_damage": 55}, "passive": {"crit_heal": 15}, "price": 60, "desc": "暴击+22% 爆伤+55% 暴击回复15%"},
    "titan_core":      {"name": "泰坦之核", "icon": "💠", "type": "accessory", "w": 1, "h": 1, "rarity": "mythic", "effects": {"max_hp": 40, "lifesteal": 15, "atk": 8}, "price": 55, "desc": "HP+40 吸血+15% 攻+8"},
    "soul_chalice":    {"name": "灵魂圣杯", "icon": "🏺", "type": "accessory", "w": 1, "h": 1, "rarity": "mythic", "effects": {"lifesteal": 28, "atk": 8}, "passive": {"overkill_heal": 35}, "price": 58, "desc": "吸血+28% 攻+8 击杀超额35%回HP", "cursed": True, "curse": {"def": -6}},
    "fate_plume":      {"name": "命运之羽", "icon": "🕊️", "type": "accessory", "w": 1, "h": 1, "rarity": "mythic", "effects": {"max_hp": 25, "def": 5}, "passive": {"revive": 1, "battle_heal": 5}, "price": 65, "desc": "HP+25 防+5 复活+战后回复5%HP"},
    "dimension_sphere":{"name": "维度球体", "icon": "🪐", "type": "accessory", "w": 1, "h": 1, "rarity": "mythic", "effects": {"atk": 10, "crit": 10, "def": 5}, "passive": {"random_buff": 2}, "price": 55, "desc": "全属性+ 每回合2次随机增强"},
    "guardian_charm":  {"name": "守护符文", "icon": "🧿", "type": "accessory", "w": 1, "h": 1, "rarity": "rare",      "effects": {"def": 3}, "passive": {"first_hit_shield": 25, "heal_per_turn": 3}, "price": 16, "desc": "防+3 首击减伤25 回复3HP/回合"},
    "divine_charm":    {"name": "神佑护符", "icon": "☀️", "type": "accessory", "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 5, "max_hp": 15}, "passive": {"first_hit_shield": 35, "heal_per_turn": 5}, "price": 32, "desc": "防+5 HP+15 首击减伤35 回复5HP/回合"},
    "cosmic_charm":    {"name": "星辰护符", "icon": "💜", "type": "accessory", "w": 1, "h": 1, "rarity": "mythic",    "effects": {"def": 8, "max_hp": 30}, "passive": {"first_hit_shield": 50, "heal_per_turn": 8}, "price": 52, "desc": "防+8 HP+30 首击减伤50 回复8HP/回合"},
    # ==================== 永恒级合成装备 (Eternal - 合成专属) ====================
    "eternal_blade":   {"name": "永恒之剑", "icon": "⚔️", "type": "weapon",    "w": 1, "h": 2, "rarity": "eternal", "effects": {"atk": 32, "crit": 18, "crit_damage": 35, "lifesteal": 10}, "passive": {"multi_strike": 40}, "adj": {"weapon": {"atk": 8}}, "price": 90, "desc": "攻+32 暴击+18% 爆伤+35% 吸血+10% 40%连击"},
    "oblivion_edge":   {"name": "湮灭之刃", "icon": "🕳️", "type": "weapon",    "w": 1, "h": 2, "rarity": "eternal", "effects": {"atk": 25, "lifesteal": 25, "crit": 15}, "passive": {"execute_pct": 35}, "price": 85, "desc": "攻+25 吸血+25% 暴击+15% 斩杀<35%", "cursed": True, "curse": {"max_hp": -50}},
    "cosmos_barrier":  {"name": "宇宙屏障", "icon": "🌐", "type": "shield",    "w": 2, "h": 1, "rarity": "eternal", "effects": {"def": 22, "max_hp": 50}, "passive": {"block_chance": 35}, "adj": {"shield": {"def": 7}}, "price": 82, "desc": "防+22 HP+50 35%格挡"},
    "celestial_plate": {"name": "天穹圣甲", "icon": "🛸", "type": "armor",     "w": 2, "h": 2, "rarity": "eternal", "effects": {"def": 25, "max_hp": 100}, "passive": {"battle_heal": 15, "reflect_pct": 15}, "price": 95, "desc": "防+25 HP+100 战后回复15%HP 反弹15%"},
    "ambrosia":        {"name": "众神佳酿", "icon": "🍾", "type": "potion",    "w": 1, "h": 1, "rarity": "eternal", "effects": {"heal_pct": 100, "max_hp": 60}, "consumable": True, "price": 70, "desc": "恢复全部HP+60最大HP"},
    "big_bang":        {"name": "创世之炸", "icon": "💥", "type": "potion",    "w": 1, "h": 1, "rarity": "eternal", "effects": {"damage": 350}, "consumable": True, "price": 70, "desc": "造成350点伤害"},
    "omniscient_eye":  {"name": "全知之眼", "icon": "👁️", "type": "accessory", "w": 1, "h": 1, "rarity": "eternal", "effects": {"crit": 30, "crit_damage": 75}, "passive": {"crit_heal": 20}, "price": 85, "desc": "暴击+30% 爆伤+75% 暴击回复20%"},
    "creation_heart":  {"name": "创世之心", "icon": "🫀", "type": "accessory", "w": 1, "h": 1, "rarity": "eternal", "effects": {"max_hp": 60, "lifesteal": 20, "atk": 12, "def": 5}, "price": 80, "desc": "HP+60 吸血+20% 攻+12 防+5"},
    "eternal_goblet":  {"name": "永生圣杯", "icon": "🍸", "type": "accessory", "w": 1, "h": 1, "rarity": "eternal", "effects": {"lifesteal": 35, "atk": 12}, "passive": {"overkill_heal": 50}, "price": 82, "desc": "吸血+35% 攻+12 击杀超额50%回HP", "cursed": True, "curse": {"def": -8}},
    "immortal_wing":   {"name": "不朽之翼", "icon": "🦅", "type": "accessory", "w": 1, "h": 1, "rarity": "eternal", "effects": {"max_hp": 40, "def": 8}, "passive": {"revive": 2, "battle_heal": 10}, "price": 90, "desc": "HP+40 防+8 复活2次+战后回复10%HP"},
    "cosmos_core":     {"name": "宇宙之核", "icon": "🪩", "type": "accessory", "w": 1, "h": 1, "rarity": "eternal", "effects": {"atk": 15, "crit": 15, "def": 8, "max_hp": 20}, "passive": {"random_buff": 3}, "price": 80, "desc": "全属性+ 每回合3次随机增强"},
    "eternal_charm":   {"name": "永恒护符", "icon": "🌅", "type": "accessory", "w": 1, "h": 1, "rarity": "eternal", "effects": {"def": 12, "max_hp": 45}, "passive": {"first_hit_shield": 70, "heal_per_turn": 12}, "price": 78, "desc": "防+12 HP+45 首击减伤70 回复12HP/回合"},
    # ==================== 🔥 烈焰套装 (rare - 攻击/爆伤) ====================
    "inferno_blade":   {"name": "烈焰长剑", "icon": "⚔️", "type": "weapon",   "w": 1, "h": 2, "rarity": "rare", "effects": {"atk": 10, "crit_damage": 20},  "price": 20, "desc": "攻+10 爆伤+20%"},
    "inferno_helm":    {"name": "烈焰头盔", "icon": "🪖", "type": "helmet",   "w": 1, "h": 1, "rarity": "rare", "effects": {"atk": 3, "max_hp": 12, "crit_damage": 10}, "price": 16, "desc": "攻+3 HP+12 爆伤+10%"},
    "inferno_chest":   {"name": "烈焰胸甲", "icon": "🎽", "type": "armor",    "w": 2, "h": 2, "rarity": "rare", "effects": {"def": 6, "atk": 5, "max_hp": 15}, "price": 24, "desc": "防+6 攻+5 HP+15"},
    "inferno_legs":    {"name": "烈焰护腿", "icon": "🩳", "type": "leggings", "w": 1, "h": 2, "rarity": "rare", "effects": {"def": 4, "atk": 3, "max_hp": 12}, "price": 20, "desc": "防+4 攻+3 HP+12"},
    "inferno_bracer":  {"name": "烈焰手套", "icon": "🧤", "type": "bracer",   "w": 1, "h": 1, "rarity": "rare", "effects": {"atk": 5, "crit_damage": 10}, "price": 16, "desc": "攻+5 爆伤+10%"},
    "inferno_boots":   {"name": "烈焰战靴", "icon": "👞", "type": "boots",    "w": 1, "h": 1, "rarity": "rare", "effects": {"atk": 3, "def": 2, "max_hp": 8}, "price": 16, "desc": "攻+3 防+2 HP+8"},
    # ==================== ❄️ 冰霜套装 (rare - 防御/生命) ====================
    "frost_blade":     {"name": "寒冰之剑", "icon": "⚔️", "type": "weapon",   "w": 1, "h": 2, "rarity": "rare", "effects": {"atk": 7, "def": 3, "max_hp": 10}, "price": 20, "desc": "攻+7 防+3 HP+10"},
    "frost_helm":      {"name": "冰霜头盔", "icon": "🪖", "type": "helmet",   "w": 1, "h": 1, "rarity": "rare", "effects": {"def": 5, "max_hp": 18}, "price": 16, "desc": "防+5 HP+18"},
    "frost_chest":     {"name": "冰霜胸甲", "icon": "🎽", "type": "armor",    "w": 2, "h": 2, "rarity": "rare", "effects": {"def": 10, "max_hp": 30}, "price": 24, "desc": "防+10 HP+30"},
    "frost_legs":      {"name": "冰霜护腿", "icon": "🩳", "type": "leggings", "w": 1, "h": 2, "rarity": "rare", "effects": {"def": 7, "max_hp": 22}, "price": 20, "desc": "防+7 HP+22"},
    "frost_bracer":    {"name": "冰霜手套", "icon": "🧤", "type": "bracer",   "w": 1, "h": 1, "rarity": "rare", "effects": {"def": 4, "max_hp": 12}, "price": 16, "desc": "防+4 HP+12"},
    "frost_boots":     {"name": "冰霜之靴", "icon": "👞", "type": "boots",    "w": 1, "h": 1, "rarity": "rare", "effects": {"def": 4, "max_hp": 10}, "price": 16, "desc": "防+4 HP+10"},
    # ==================== ⚡ 雷霆套装 (legendary - 暴击) ====================
    "storm_blade":     {"name": "雷霆之剑", "icon": "⚔️", "type": "weapon",   "w": 1, "h": 2, "rarity": "legendary", "effects": {"atk": 13, "crit": 12, "crit_damage": 25}, "price": 38, "desc": "攻+13 暴击+12% 爆伤+25%"},
    "storm_helm":      {"name": "雷霆头盔", "icon": "🪖", "type": "helmet",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 5, "crit": 10, "crit_damage": 15, "max_hp": 15}, "price": 32, "desc": "防+5 暴击+10% 爆伤+15% HP+15"},
    "storm_chest":     {"name": "雷霆战甲", "icon": "🎽", "type": "armor",    "w": 2, "h": 2, "rarity": "legendary", "effects": {"def": 8, "crit": 6, "max_hp": 25}, "price": 40, "desc": "防+8 暴击+6% HP+25"},
    "storm_legs":      {"name": "雷霆护腿", "icon": "🩳", "type": "leggings", "w": 1, "h": 2, "rarity": "legendary", "effects": {"def": 5, "crit": 5, "max_hp": 18}, "price": 35, "desc": "防+5 暴击+5% HP+18"},
    "storm_bracer":    {"name": "雷霆手套", "icon": "🧤", "type": "bracer",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"crit": 8, "atk": 5, "crit_damage": 12}, "price": 32, "desc": "暴击+8% 攻+5 爆伤+12%"},
    "storm_boots":     {"name": "雷霆之靴", "icon": "👞", "type": "boots",    "w": 1, "h": 1, "rarity": "legendary", "effects": {"crit": 6, "def": 3, "max_hp": 10}, "passive": {"dodge_pct": 10}, "price": 32, "desc": "暴击+6% 防+3 HP+10 闪避10%"},
    # ==================== 🌑 暗影套装 (legendary - 吸血/暗系) ====================
    "shadow_blade":    {"name": "暗影之刃", "icon": "⚔️", "type": "weapon",   "w": 1, "h": 2, "rarity": "legendary", "effects": {"atk": 15, "lifesteal": 15}, "price": 38, "desc": "攻+15 吸血+15%"},
    "shadow_helm":     {"name": "暗影头冠", "icon": "🪖", "type": "helmet",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"lifesteal": 8, "atk": 4, "max_hp": 10}, "price": 32, "desc": "吸血+8% 攻+4 HP+10"},
    "shadow_chest":    {"name": "暗影胸甲", "icon": "🎽", "type": "armor",    "w": 2, "h": 2, "rarity": "legendary", "effects": {"def": 7, "lifesteal": 8, "max_hp": 22}, "price": 40, "desc": "防+7 吸血+8% HP+22"},
    "shadow_legs":     {"name": "暗影护腿", "icon": "🩳", "type": "leggings", "w": 1, "h": 2, "rarity": "legendary", "effects": {"def": 5, "lifesteal": 6, "max_hp": 18}, "price": 35, "desc": "防+5 吸血+6% HP+18"},
    "shadow_bracer":   {"name": "暗影手套", "icon": "🧤", "type": "bracer",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"lifesteal": 10, "atk": 4}, "price": 32, "desc": "吸血+10% 攻+4"},
    "shadow_boots":    {"name": "暗影之靴", "icon": "👞", "type": "boots",    "w": 1, "h": 1, "rarity": "legendary", "effects": {"lifesteal": 6, "def": 3, "max_hp": 8}, "price": 32, "desc": "吸血+6% 防+3 HP+8"},
    # ==================== 套装盾牌 ====================
    "inferno_shield":  {"name": "烈焰之盾", "icon": "🛡️", "type": "shield",  "w": 2, "h": 1, "rarity": "rare",      "effects": {"def": 5, "atk": 3},  "price": 18, "desc": "防+5 攻+3"},
    "frost_shield":    {"name": "冰霜之盾", "icon": "🛡️", "type": "shield",  "w": 2, "h": 1, "rarity": "rare",      "effects": {"def": 8, "max_hp": 15}, "price": 18, "desc": "防+8 HP+15"},
    "storm_shield":    {"name": "雷霆之盾", "icon": "🛡️", "type": "shield",  "w": 2, "h": 1, "rarity": "legendary", "effects": {"def": 5, "crit": 8, "crit_damage": 10}, "price": 35, "desc": "防+5 暴击+8% 爆伤+10%"},
    "shadow_shield":   {"name": "暗影之盾", "icon": "🛡️", "type": "shield",  "w": 2, "h": 1, "rarity": "legendary", "effects": {"def": 5, "lifesteal": 8, "max_hp": 10}, "price": 35, "desc": "防+5 吸血+8% HP+10"},
    # ==================== 套装合体 (2×2 - 七件合一) ====================
    "inferno_set_merged": {"name": "烈焰全套", "icon": "🔥", "type": "set_merged", "w": 2, "h": 2, "rarity": "rare",      "effects": {"atk": 32, "def": 17, "max_hp": 47, "crit_damage": 40}, "merged_set": "inferno_set", "price": 0, "desc": "烈焰套装合体"},
    "frost_set_merged":   {"name": "冰霜全套", "icon": "❄️", "type": "set_merged", "w": 2, "h": 2, "rarity": "rare",      "effects": {"atk": 7, "def": 41, "max_hp": 117},                      "merged_set": "frost_set",   "price": 0, "desc": "冰霜套装合体"},
    "storm_set_merged":   {"name": "雷霆全套", "icon": "⚡", "type": "set_merged", "w": 2, "h": 2, "rarity": "legendary", "effects": {"atk": 18, "def": 26, "crit": 55, "crit_damage": 62, "max_hp": 68}, "merged_set": "storm_set",  "price": 0, "desc": "雷霆套装合体"},
    "shadow_set_merged":  {"name": "暗影全套", "icon": "🌑", "type": "set_merged", "w": 2, "h": 2, "rarity": "legendary", "effects": {"atk": 23, "def": 20, "lifesteal": 61, "max_hp": 68},             "merged_set": "shadow_set",  "price": 0, "desc": "暗影套装合体"},
    # ==================== 🌿 自然套装 (legendary - 均衡/续航) ====================
    "nature_blade":    {"name": "自然之杖", "icon": "⚔️", "type": "weapon",   "w": 1, "h": 2, "rarity": "legendary", "effects": {"atk": 12, "max_hp": 20, "lifesteal": 8},  "price": 36, "desc": "攻+12 HP+20 吸血+8%"},
    "nature_shield":   {"name": "自然之盾", "icon": "🛡️", "type": "shield",  "w": 2, "h": 1, "rarity": "legendary", "effects": {"def": 6, "max_hp": 15, "lifesteal": 5}, "price": 35, "desc": "防+6 HP+15 吸血+5%"},
    "nature_helm":     {"name": "自然头冠", "icon": "🪖", "type": "helmet",  "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 5, "max_hp": 18, "crit": 6},  "price": 30, "desc": "防+5 HP+18 暴击+6%"},
    "nature_chest":    {"name": "自然胸甲", "icon": "🎽", "type": "armor",   "w": 2, "h": 2, "rarity": "legendary", "effects": {"def": 8, "max_hp": 30, "atk": 4},   "price": 40, "desc": "防+8 HP+30 攻+4"},
    "nature_legs":     {"name": "自然护腿", "icon": "🩳", "type": "leggings","w": 1, "h": 2, "rarity": "legendary", "effects": {"def": 6, "max_hp": 20, "lifesteal": 5}, "price": 35, "desc": "防+6 HP+20 吸血+5%"},
    "nature_bracer":   {"name": "自然手环", "icon": "🧤", "type": "bracer",  "w": 1, "h": 1, "rarity": "legendary", "effects": {"atk": 5, "def": 3, "max_hp": 10},   "price": 30, "desc": "攻+5 防+3 HP+10"},
    "nature_boots":    {"name": "自然之靴", "icon": "👞", "type": "boots",   "w": 1, "h": 1, "rarity": "legendary", "effects": {"def": 4, "max_hp": 12, "lifesteal": 5}, "passive": {"dodge_pct": 8}, "price": 30, "desc": "防+4 HP+12 吸血+5% 闪避8%"},
    "nature_set_merged":{"name": "自然全套", "icon": "🌿", "type": "set_merged", "w": 2, "h": 2, "rarity": "legendary", "effects": {"atk": 21, "def": 32, "max_hp": 125, "lifesteal": 28, "crit": 6}, "merged_set": "nature_set", "price": 0, "desc": "自然套装合体"},
    # ==================== 👑 如意金箍棒 (divine - 终极装备, 五套合一) ====================
    "ruyi_jingu_bang":  {"name": "如意金箍棒", "icon": "👑", "type": "ultimate", "w": 2, "h": 2, "rarity": "divine",
        "effects": {"atk": 200, "def": 100, "crit": 80, "crit_damage": 200, "lifesteal": 60, "max_hp": 500},
        "passive": {"multi_strike": 60, "execute_pct": 40, "revive": 3, "battle_heal": 25, "block_chance": 30, "reflect_pct": 25, "dodge_pct": 20, "heal_per_turn": 20, "crit_heal": 25, "overkill_heal": 50, "first_hit_shield": 100},
        "price": 0, "desc": "齐天大圣之兵器·毁天灭地·不受任何难度缩放", "no_scaling": True},
}

# ---- 合成升级链 ----
MERGE_CHAINS = {
    # 主手武器链 (木棍 → 永恒之剑, 7级)
    "wooden_stick": "iron_sword", "iron_sword": "flame_blade", "flame_blade": "divine_sword",
    "divine_sword": "void_blade", "void_blade": "astral_blade", "astral_blade": "eternal_blade",
    # 副手匕首链 (匕首 → 湮灭之刃, 5级)
    "dagger": "poison_blade", "poison_blade": "soul_reaper",
    "soul_reaper": "death_scythe", "death_scythe": "oblivion_edge",
    # 盾牌链 (圆盾 → 宇宙屏障, 7级)
    "buckler": "wooden_shield", "wooden_shield": "iron_shield", "iron_shield": "holy_shield",
    "holy_shield": "aegis_shield", "aegis_shield": "titan_bulwark", "titan_bulwark": "cosmos_barrier",
    # 护甲链 (皮甲 → 天穹圣甲, 6级)
    "leather_armor": "chain_mail", "chain_mail": "plate_armor", "plate_armor": "phoenix_armor",
    "phoenix_armor": "dragon_plate", "dragon_plate": "celestial_plate",
    # 药水链 (小药水 → 众神佳酿, 6级)
    "small_potion": "medium_potion", "medium_potion": "large_potion", "large_potion": "elixir",
    "elixir": "miracle_elixir", "miracle_elixir": "ambrosia",
    # 炸弹链 (炸弹 → 创世之炸, 5级)
    "bomb": "mega_bomb", "mega_bomb": "nuke_bomb",
    "nuke_bomb": "antimatter_bomb", "antimatter_bomb": "big_bang",
    # 暴击饰品链 (幸运币 → 全知之眼, 5级)
    "lucky_coin": "crit_gem", "crit_gem": "crit_crown",
    "crit_crown": "destiny_crown", "destiny_crown": "omniscient_eye",
    # 力量饰品链 (力戒 → 创世之心, 4级)
    "power_ring": "dragon_heart", "dragon_heart": "titan_core", "titan_core": "creation_heart",
    # 再生饰品链 (回春项链 → 永恒护符, 6级)
    "regen_amulet": "first_strike", "first_strike": "guardian_charm",
    "guardian_charm": "divine_charm", "divine_charm": "cosmic_charm", "cosmic_charm": "eternal_charm",
    # 吸血饰品链 (吸血牙 → 永生圣杯, 4级)
    "vampire_fang": "blood_chalice", "blood_chalice": "soul_chalice", "soul_chalice": "eternal_goblet",
    # 幸运饰品链 (四叶草 → 不朽之翼, 4级)
    "lucky_clover": "phoenix_feather", "phoenix_feather": "fate_plume", "fate_plume": "immortal_wing",
    # 经验饰品链 (经验磁铁 → 宇宙之核, 4级)
    "exp_magnet": "chaos_orb", "chaos_orb": "dimension_sphere", "dimension_sphere": "cosmos_core",
    # ==================== 新装备栏合成链 ====================
    # 头盔链 (布兜帽 → 永恒之冠, 6级)
    "cloth_hood": "iron_helm", "iron_helm": "war_helm", "war_helm": "dragon_helm",
    "dragon_helm": "titan_helm", "titan_helm": "eternal_helm",
    # 护臂链 (布护腕 → 永恒臂环, 6级)
    "cloth_bracer": "iron_bracer", "iron_bracer": "war_bracer", "war_bracer": "dragon_bracer",
    "dragon_bracer": "titan_bracer", "titan_bracer": "eternal_bracer",
    # 鞋子链 (布鞋 → 永恒足履, 6级)
    "cloth_boots": "iron_boots", "iron_boots": "war_boots", "war_boots": "dragon_boots",
    "dragon_boots": "titan_boots", "titan_boots": "eternal_boots",
    # 护腿链 (布裤 → 永恒腿甲, 6级)
    "cloth_leggings": "iron_leggings", "iron_leggings": "war_leggings", "war_leggings": "dragon_leggings",
    "dragon_leggings": "titan_leggings", "titan_leggings": "eternal_leggings",
}

# ---- 套装定义 (主题7件套=major, 经典3件套=minor) ----
ITEM_SETS = {
    # ==================== 主题完整7件套 (major: 激活限制 + 专属加成) ====================
    "inferno_set": {
        "name": "🔥 烈焰套装",
        "major": True,
        "items": {"inferno_blade", "inferno_shield", "inferno_helm", "inferno_chest", "inferno_legs", "inferno_bracer", "inferno_boots"},
        "piece_bonus": {"atk": 3, "crit_damage": 8},
        "desc": "每件: 攻+3 爆伤+8%",
        "exclusive_bonus": {"atk": 30, "crit_damage": 60},
        "exclusive_name": "🔥 焚天之力",
        "exclusive_desc": "攻击+30 爆伤+60%",
    },
    "frost_set": {
        "name": "❄️ 冰霜套装",
        "major": True,
        "items": {"frost_blade", "frost_shield", "frost_helm", "frost_chest", "frost_legs", "frost_bracer", "frost_boots"},
        "piece_bonus": {"def": 3, "max_hp": 15},
        "desc": "每件: 防+3 HP+15",
        "exclusive_bonus": {"def": 25, "max_hp": 100},
        "exclusive_name": "❄️ 冰封领域",
        "exclusive_desc": "防御+25 HP+100",
    },
    "storm_set": {
        "name": "⚡ 雷霆套装",
        "major": True,
        "items": {"storm_blade", "storm_shield", "storm_helm", "storm_chest", "storm_legs", "storm_bracer", "storm_boots"},
        "piece_bonus": {"crit": 4, "crit_damage": 10},
        "desc": "每件: 暴击+4% 爆伤+10%",
        "exclusive_bonus": {"crit": 30, "crit_damage": 80},
        "exclusive_name": "⚡ 雷神降临",
        "exclusive_desc": "暴击+30% 爆伤+80%",
    },
    "shadow_set": {
        "name": "🌑 暗影套装",
        "major": True,
        "items": {"shadow_blade", "shadow_shield", "shadow_helm", "shadow_chest", "shadow_legs", "shadow_bracer", "shadow_boots"},
        "piece_bonus": {"lifesteal": 5, "atk": 3},
        "desc": "每件: 吸血+5% 攻+3",
        "exclusive_bonus": {"lifesteal": 30, "atk": 25},
        "exclusive_name": "🌑 暗影吞噬",
        "exclusive_desc": "吸血+30% 攻击+25",
    },
    "nature_set": {
        "name": "🌿 自然套装",
        "major": True,
        "items": {"nature_blade", "nature_shield", "nature_helm", "nature_chest", "nature_legs", "nature_bracer", "nature_boots"},
        "piece_bonus": {"max_hp": 12, "def": 2, "lifesteal": 3},
        "desc": "每件: HP+12 防+2 吸血+3%",
        "exclusive_bonus": {"max_hp": 80, "def": 20, "lifesteal": 20, "atk": 15},
        "exclusive_name": "🌿 万物之力",
        "exclusive_desc": "HP+80 防+20 吸血+20% 攻+15",
    },
    # ==================== 经典3件套 (保留, 改为件数加成) ====================
    "holy_set": {
        "name": "🏆 圣骑士套装",
        "items": {"divine_sword", "holy_shield", "plate_armor"},
        "piece_bonus": {"atk": 4, "def": 4, "max_hp": 15},
        "desc": "每件: 攻+4 防+4 HP+15",
    },
    "assassin_set": {
        "name": "🗡️ 刺客套装",
        "items": {"poison_blade", "dagger", "lucky_coin"},
        "piece_bonus": {"crit": 5, "crit_damage": 10, "lifesteal": 4},
        "desc": "每件: 暴击+5% 爆伤+10% 吸血+4%",
    },
    "tank_set": {
        "name": "🛡️ 铁壁套装",
        "items": {"iron_shield", "chain_mail", "heart_crystal"},
        "piece_bonus": {"def": 3, "max_hp": 20},
        "desc": "每件: 防+3 HP+20",
    },
    "berserker_set": {
        "name": "🔥 狂战士套装",
        "items": {"flame_blade", "berserker_mark", "vampire_fang"},
        "piece_bonus": {"atk": 5, "lifesteal": 5, "crit_damage": 8},
        "desc": "每件: 攻+5 吸血+5% 爆伤+8%",
    },
    "cursed_set": {
        "name": "💀 诅咒套装",
        "items": {"cursed_blade", "cursed_crown", "cursed_ring"},
        "piece_bonus": {"atk": 6, "crit": 5, "lifesteal": 5},
        "desc": "每件: 攻+6 暴击+5% 吸血+5%",
    },
    "phoenix_set": {
        "name": "🦤 凤凰套装",
        "items": {"phoenix_armor", "phoenix_feather", "aegis_shield"},
        "piece_bonus": {"def": 5, "max_hp": 25},
        "desc": "每件: 防+5 HP+25",
    },
    "void_set": {
        "name": "🌌 虚空套装",
        "items": {"void_blade", "crit_crown", "chaos_orb"},
        "piece_bonus": {"atk": 5, "crit": 5, "crit_damage": 12},
        "desc": "每件: 攻+5 暴击+5% 爆伤+12%",
    },
    "blood_set": {
        "name": "🩸 血族套装",
        "items": {"soul_reaper", "blood_chalice", "vampire_fang"},
        "piece_bonus": {"lifesteal": 8, "atk": 4},
        "desc": "每件: 吸血+8% 攻+4",
    },
}

# ---- 套装徽标 (用于前端显示: 属性主题 + 装备类型双图标) ----
_SET_BADGE_EMOJI = {
    "inferno_set": "🔥", "frost_set": "❄️", "storm_set": "⚡", "shadow_set": "🌑", "nature_set": "🌿",
}

# 五套合一终极合成
ULTIMATE_FORGE_SETS = {"inferno_set_merged", "frost_set_merged", "storm_set_merged", "shadow_set_merged", "nature_set_merged"}
ULTIMATE_ITEM_ID = "ruyi_jingu_bang"
_SET_BADGE: dict[str, str] = {}
for _sid, _sdef in ITEM_SETS.items():
    _b = _SET_BADGE_EMOJI.get(_sid)
    if _b:
        for _iid in _sdef["items"]:
            _SET_BADGE[_iid] = _b

# ---- 附魔词缀池 ----
ENCHANT_AFFIXES = [
    {"name": "锋利", "icon": "⚔️", "stat": "atk", "range": (2, 5)},
    {"name": "坚韧", "icon": "🛡️", "stat": "def", "range": (2, 4)},
    {"name": "精准", "icon": "🎯", "stat": "crit", "range": (3, 8)},
    {"name": "嗜血", "icon": "🧛", "stat": "lifesteal", "range": (3, 7)},
    {"name": "强壮", "icon": "❤️", "stat": "max_hp", "range": (5, 15)},
    {"name": "猛烈", "icon": "💥", "stat": "crit_damage", "range": (5, 15)},
]
ENCHANT_BASE_COST = 15  # 基础附魔费用

# ---- 特殊区域定义: 扩容后出现的加成格 ----
# 格式: {(rows, cols): [(r, c), ...]}
# 物品占据这些格子时获得属性翻倍(1.5x)
BP_BONUS_ZONES = {
    (4, 5): [(0, 4), (3, 4)],                    # 4×5: 右上角+右下角
    (5, 6): [(0, 5), (4, 5), (0, 0), (4, 0)],    # 5×6: 四个角
    (6, 7): [(0, 6), (5, 6), (0, 0), (5, 0), (2, 3), (3, 3)],  # 6×7: 四角+中心2格
    (7, 8): [(0, 7), (6, 7), (0, 0), (6, 0), (3, 3), (3, 4), (0, 3), (6, 3)],  # 7×8: 四角+中心2格+上下中点
    (8, 9): [(0, 8), (7, 8), (0, 0), (7, 0), (3, 4), (4, 4), (0, 4), (7, 4), (3, 0), (4, 8)],  # 8×9: 四角+中心+十字
}

RARITY_SHOP_WEIGHTS = {
    "common":    lambda f: max(10, 50 - f * 2),
    "uncommon":  lambda f: 30 + min(f, 20),
    "rare":      lambda f: max(0, f * 2 - 5),
    "legendary": lambda f: max(0, f - 20),
}


# ===================== 背包操作函数 =====================

def _bp_init(is_endless: bool = False) -> dict:
    """初始化背包 (3行×4列 网格)"""
    bp = {"rows": 3, "cols": 4, "items": [], "next_uid": 1}
    if is_endless:
        # 初始装备: 木棍 + 小药水
        _bp_place(bp, "wooden_stick", 0, 0)
        _bp_place(bp, "small_potion", 0, 1)
    return bp


def _bp_item_wh(it: dict) -> tuple:
    """获取物品实际宽高(考虑旋转)"""
    defn = BACKPACK_ITEMS.get(it["id"], {})
    w, h = defn.get("w", 1), defn.get("h", 1)
    if it.get("rotated"):
        w, h = h, w
    return w, h


def _bp_occupied(bp: dict) -> dict:
    """返回 {(row,col): uid} 占用表"""
    occ = {}
    for it in bp["items"]:
        w, h = _bp_item_wh(it)
        for dr in range(h):
            for dc in range(w):
                occ[(it["row"] + dr, it["col"] + dc)] = it["uid"]
    return occ


def _bp_can_place(bp: dict, item_id: str, row: int, col: int, rotated: bool = False) -> bool:
    """检查物品能否放在指定位置"""
    defn = BACKPACK_ITEMS.get(item_id)
    if not defn:
        return False
    w, h = defn["w"], defn["h"]
    if rotated:
        w, h = h, w
    if row < 0 or col < 0 or row + h > bp["rows"] or col + w > bp["cols"]:
        return False
    occ = _bp_occupied(bp)
    for dr in range(h):
        for dc in range(w):
            if (row + dr, col + dc) in occ:
                return False
    return True


def _bp_place(bp: dict, item_id: str, row: int, col: int, rotated: bool = False) -> int | None:
    """放置物品，返回uid; 失败返回None"""
    if not _bp_can_place(bp, item_id, row, col, rotated):
        return None
    uid = bp["next_uid"]
    bp["next_uid"] += 1
    entry = {"id": item_id, "uid": uid, "row": row, "col": col}
    if rotated:
        entry["rotated"] = True
    bp["items"].append(entry)
    return uid


def _bp_auto_place(bp: dict, item_id: str) -> int | None:
    """自动寻找空位放置物品（先尝试原始方向，再尝试旋转）"""
    defn = BACKPACK_ITEMS.get(item_id)
    if not defn:
        return None
    for rotated in (False, True):
        for r in range(bp["rows"]):
            for c in range(bp["cols"]):
                if _bp_can_place(bp, item_id, r, c, rotated):
                    return _bp_place(bp, item_id, r, c, rotated)
    return None


def _bp_check_auto_merge(bp: dict, log: list) -> bool:
    """检查并执行自动合体: 集齐7件→合体, 5个合体→如意金箍棒. 返回是否发生了合成."""
    changed = False
    item_ids_in_bp = {it["id"] for it in bp["items"]}
    # 自动套装合体
    for sid, sdef in ITEM_SETS.items():
        if not sdef.get("major"):
            continue
        if not sdef["items"].issubset(item_ids_in_bp):
            continue
        merged_id = sid.replace("_set", "_set_merged")
        if merged_id not in BACKPACK_ITEMS:
            continue
        # 移除散件
        to_remove = set(sdef["items"])
        for it in list(bp["items"]):
            if it["id"] in to_remove:
                _bp_remove(bp, it["uid"])
                to_remove.discard(it["id"])
        uid = _bp_auto_place(bp, merged_id)
        if uid is None:
            continue  # 空间不够(理论上释放了7件,一定够放)
        merged_defn = BACKPACK_ITEMS[merged_id]
        log.append(f"✨ 自动合体！{sdef['name']} 七件合一 → {merged_defn['icon']}{merged_defn['name']}")
        changed = True
        item_ids_in_bp = {it["id"] for it in bp["items"]}
    # 检查五套合一 → 如意金箍棒
    if ULTIMATE_FORGE_SETS.issubset(item_ids_in_bp):
        for mid in ULTIMATE_FORGE_SETS:
            for it in list(bp["items"]):
                if it["id"] == mid:
                    _bp_remove(bp, it["uid"])
                    break
        uid = _bp_auto_place(bp, ULTIMATE_ITEM_ID)
        if uid is not None:
            log.append("🌟🌟🌟 五套合一！齐天大圣之兵器 —— 如意金箍棒 横空出世！前无古人，后无来者！🌟🌟🌟")
            changed = True
    return changed


def _bp_remove(bp: dict, uid: int) -> str | None:
    """移除物品，返回item_id; 不存在返回None"""
    for i, it in enumerate(bp["items"]):
        if it["uid"] == uid:
            bp["items"].pop(i)
            return it["id"]
    return None


def _bp_move(bp: dict, uid: int, new_row: int, new_col: int) -> bool:
    """移动物品到新位置"""
    item = None
    for it in bp["items"]:
        if it["uid"] == uid:
            item = it
            break
    if not item:
        return False
    # 临时移除再检查能否放
    bp["items"] = [i for i in bp["items"] if i["uid"] != uid]
    w, h = _bp_item_wh(item)
    if new_row < 0 or new_col < 0 or new_row + h > bp["rows"] or new_col + w > bp["cols"]:
        bp["items"].append(item)
        return False
    occ = _bp_occupied(bp)
    for dr in range(h):
        for dc in range(w):
            if (new_row + dr, new_col + dc) in occ:
                bp["items"].append(item)
                return False
    item["row"] = new_row
    item["col"] = new_col
    bp["items"].append(item)
    return True


def _bp_rotate_item(bp: dict, uid: int) -> bool:
    """旋转物品(交换宽高)，如果旋转后放不下则尝试微调位置"""
    item = None
    for it in bp["items"]:
        if it["uid"] == uid:
            item = it
            break
    if not item:
        return False
    defn = BACKPACK_ITEMS.get(item["id"], {})
    orig_w, orig_h = defn.get("w", 1), defn.get("h", 1)
    if orig_w == orig_h:
        return True  # 正方形无需旋转
    # 切换旋转状态
    new_rotated = not item.get("rotated", False)
    new_w = orig_h if new_rotated else orig_w
    new_h = orig_w if new_rotated else orig_h
    # 临时移除
    bp["items"] = [i for i in bp["items"] if i["uid"] != uid]
    occ = _bp_occupied(bp)
    # 尝试原位放置，失败则在附近搜索
    r0, c0 = item["row"], item["col"]
    candidates = [(r0, c0)]
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            if (dr, dc) != (0, 0):
                candidates.append((r0 + dr, c0 + dc))
    for nr, nc in candidates:
        if nr < 0 or nc < 0 or nr + new_h > bp["rows"] or nc + new_w > bp["cols"]:
            continue
        ok = True
        for dr2 in range(new_h):
            for dc2 in range(new_w):
                if (nr + dr2, nc + dc2) in occ:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            item["row"] = nr
            item["col"] = nc
            if new_rotated:
                item["rotated"] = True
            else:
                item.pop("rotated", None)
            bp["items"].append(item)
            return True
    # 无法旋转，恢复
    bp["items"].append(item)
    return False


# 背包扩展阶梯: (当前rows, 当前cols) -> (新rows, 新cols, 花费EXP)
BP_EXPAND_TIERS = [
    (3, 4, 4, 5, 50),     # 3×4 → 4×5, 花费50EXP
    (4, 5, 5, 6, 120),    # 4×5 → 5×6, 花费120EXP
    (5, 6, 6, 7, 250),    # 5×6 → 6×7, 花费250EXP
    (6, 7, 7, 8, 500),    # 6×7 → 7×8, 花费500EXP
    (7, 8, 8, 9, 1000),   # 7×8 → 8×9, 花费1000EXP
]


def _bp_expand_cost(bp: dict) -> int | None:
    """获取下一级扩展花费，None表示已满级"""
    for r, c, nr, nc, cost in BP_EXPAND_TIERS:
        if bp["rows"] == r and bp["cols"] == c:
            return cost
    return None


def _bp_expand(bp: dict) -> bool:
    """扩展背包到下一级"""
    for r, c, nr, nc, cost in BP_EXPAND_TIERS:
        if bp["rows"] == r and bp["cols"] == c:
            bp["rows"] = nr
            bp["cols"] = nc
            return True
    return False


def _bp_compute_set_info(bp: dict) -> dict:
    """计算套装激活状态 (major套用激活限制, minor套始终激活)"""
    item_ids_in_bp = {it["id"] for it in bp["items"]}
    bp_id_list = [it["id"] for it in bp["items"]]

    major_info = {}      # sid -> {eff_pieces, is_complete, has_merged, unique_pieces}
    total_complete = 0

    for sid, sdef in ITEM_SETS.items():
        if not sdef.get("major"):
            continue
        merged_id = sid.replace("_set", "_set_merged")
        n_merged = bp_id_list.count(merged_id)
        unique_pieces = len(sdef["items"] & item_ids_in_bp)
        set_size = len(sdef["items"])
        eff_pieces = min(set_size if n_merged > 0 else unique_pieces, set_size)
        is_complete = eff_pieces == set_size
        n_complete = n_merged + (1 if unique_pieces == set_size else 0)
        total_complete += n_complete
        if eff_pieces > 0 or n_merged > 0:
            major_info[sid] = {
                "eff_pieces": eff_pieces,
                "is_complete": is_complete,
                "n_complete": n_complete,
                "has_merged": n_merged > 0,
                "unique_pieces": unique_pieces,
            }

    max_active = total_complete + 1
    prev_active = set(bp.get("_prev_active_major", []))

    sorted_majors = sorted(
        major_info.items(),
        key=lambda x: (-x[1]["eff_pieces"], 0 if x[0] in prev_active else 1, x[0])
    )
    active_sids = set()
    for sid, info in sorted_majors[:max_active]:
        if info["eff_pieces"] >= 2:
            active_sids.add(sid)

    bp["_prev_active_major"] = list(active_sids)

    # Minor套
    minor_info = {}
    for sid, sdef in ITEM_SETS.items():
        if sdef.get("major"):
            continue
        owned = sdef["items"] & item_ids_in_bp
        count = len(owned)
        if count >= 2:
            minor_info[sid] = {"pieces": count, "total": len(sdef["items"])}

    return {
        "major": major_info,
        "active_major": active_sids,
        "minor": minor_info,
        "max_active": max_active,
        "total_complete": total_complete,
    }


def _bp_calc_stats(bp: dict, set_info: dict = None, exclude_no_scaling: bool = False) -> dict:
    """计算背包总属性 (基础 + 相邻加成 + 诅咒 + 附魔 + 连锁 + 套装 + 特殊区域)
    exclude_no_scaling=True 时，标记了 no_scaling 的物品不计入（用于动态难度计算）"""
    stats = {"atk": 0, "def": 0, "crit": 0, "crit_damage": 0, "lifesteal": 0, "max_hp": 0, "exp_bonus": 0}
    if not bp or not bp.get("items"):
        return stats
    # 基础属性 + 诅咒惩罚
    for it in bp["items"]:
        defn = BACKPACK_ITEMS.get(it["id"], {})
        if exclude_no_scaling and defn.get("no_scaling"):
            continue
        for k, v in defn.get("effects", {}).items():
            if k in stats:
                stats[k] += v
        # 诅咒负面
        if defn.get("cursed") and not it.get("purified"):
            for k, v in defn.get("curse", {}).items():
                if k in stats:
                    stats[k] += v
        # 附魔加成
        for ench in it.get("enchants", []):
            s = ench.get("stat")
            v = ench.get("value", 0)
            if s in stats:
                stats[s] += v
    # 相邻加成: 遍历每个物品, 检查相邻物品类型
    occ = {}  # (r,c) -> item dict
    for it in bp["items"]:
        w, h = _bp_item_wh(it)
        for dr in range(h):
            for dc in range(w):
                occ[(it["row"] + dr, it["col"] + dc)] = it
    for it in bp["items"]:
        defn = BACKPACK_ITEMS.get(it["id"], {})
        adj_rules = defn.get("adj")
        if not adj_rules:
            continue
        # 找出所有相邻的不同物品
        w, h = _bp_item_wh(it)
        my_cells = set()
        for dr in range(h):
            for dc in range(w):
                my_cells.add((it["row"] + dr, it["col"] + dc))
        neighbor_uids = set()
        for (r, c) in my_cells:
            for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
                nb = occ.get((nr, nc))
                if nb and nb["uid"] != it["uid"]:
                    neighbor_uids.add(nb["uid"])
        for nb_uid in neighbor_uids:
            nb_it = next((i for i in bp["items"] if i["uid"] == nb_uid), None)
            if not nb_it:
                continue
            nb_type = BACKPACK_ITEMS.get(nb_it["id"], {}).get("type", "")
            if nb_type in adj_rules:
                for k, v in adj_rules[nb_type].items():
                    if k in stats:
                        stats[k] += v
    # 净化石: 相邻诅咒物品的curse惩罚已计入，净化石抵消之
    for it in bp["items"]:
        defn = BACKPACK_ITEMS.get(it["id"], {})
        if not defn.get("purifier"):
            continue
        w, h = _bp_item_wh(it)
        my_cells = set()
        for dr in range(h):
            for dc in range(w):
                my_cells.add((it["row"] + dr, it["col"] + dc))
        for (r, c) in my_cells:
            for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
                nb = occ.get((nr, nc))
                if nb and nb["uid"] != it["uid"]:
                    nb_defn = BACKPACK_ITEMS.get(nb["id"], {})
                    if nb_defn.get("cursed") and not nb.get("purified"):
                        # 抵消curse惩罚(加回被扣的值)
                        for k, v in nb_defn.get("curse", {}).items():
                            if k in stats:
                                stats[k] -= v  # v is negative, so -= negative = add

    # 连锁加成: 同一行或同一列中 >=3 个相同类型物品 → 额外加成
    chain_bonus = _bp_calc_chain_bonus(bp)
    for k, v in chain_bonus.items():
        if k in stats:
            stats[k] += v

    # 套装加成 (major套: 激活限制 + 专属加成; minor套: 始终激活)
    if set_info is None:
        set_info = _bp_compute_set_info(bp)
    # Major套 (仅激活的套装获得加成)
    for sid in set_info["active_major"]:
        sdef = ITEM_SETS[sid]
        info = set_info["major"][sid]
        count = info["eff_pieces"]
        for k, v in sdef["piece_bonus"].items():
            if k in stats:
                stats[k] += v * count
        # 专属加成 (集齐7件)
        if info["is_complete"] and sdef.get("exclusive_bonus"):
            for k, v in sdef["exclusive_bonus"].items():
                if k in stats:
                    stats[k] += v
    # Minor套 (始终激活)
    for sid, minfo in set_info["minor"].items():
        sdef = ITEM_SETS[sid]
        for k, v in sdef["piece_bonus"].items():
            if k in stats:
                stats[k] += v * minfo["pieces"]

    # 特殊区域加成: 物品占据bonus zone格子时，该物品的基础effects×0.5额外加成
    bonus_cells = set(BP_BONUS_ZONES.get((bp["rows"], bp["cols"]), []))
    if bonus_cells:
        for it in bp["items"]:
            defn = BACKPACK_ITEMS.get(it["id"], {})
            w, h = _bp_item_wh(it)
            on_bonus = False
            for dr in range(h):
                for dc in range(w):
                    if (it["row"] + dr, it["col"] + dc) in bonus_cells:
                        on_bonus = True
                        break
                if on_bonus:
                    break
            if on_bonus:
                for k, v in defn.get("effects", {}).items():
                    if k in stats and v > 0:
                        stats[k] += int(v * 0.5)  # 50% bonus

    return stats


def _bp_calc_chain_bonus(bp: dict) -> dict:
    """计算连锁加成: 同行或同列>=3个同类型物品获得额外加成"""
    bonus = {"atk": 0, "def": 0, "crit": 0, "max_hp": 0}
    if not bp or not bp.get("items"):
        return bonus
    # 按物品左上角位置索引类型
    type_by_row = {}  # row -> [type, ...]
    type_by_col = {}  # col -> [type, ...]
    for it in bp["items"]:
        defn = BACKPACK_ITEMS.get(it["id"], {})
        t = defn.get("type", "")
        if t in ("potion",):  # 药水不参与连锁
            continue
        w, h = _bp_item_wh(it)
        rows_occ = set(range(it["row"], it["row"] + h))
        cols_occ = set(range(it["col"], it["col"] + w))
        for r in rows_occ:
            type_by_row.setdefault(r, []).append(t)
        for c in cols_occ:
            type_by_col.setdefault(c, []).append(t)
    # 检查每行每列
    chain_types = set()
    for cells in list(type_by_row.values()) + list(type_by_col.values()):
        counts = Counter(cells)
        for t, cnt in counts.items():
            if cnt >= 3:
                chain_types.add(t)
    # 每种连锁类型给予固定加成
    chain_rewards = {
        "weapon": {"atk": 5}, "shield": {"def": 4}, "armor": {"def": 3, "max_hp": 15},
        "accessory": {"crit": 5}, "special": {"atk": 3, "def": 3},
        "helmet": {"def": 2, "max_hp": 10}, "bracer": {"atk": 3, "crit_damage": 5},
        "boots": {"def": 2}, "leggings": {"def": 3, "max_hp": 10},
    }
    for t in chain_types:
        for k, v in chain_rewards.get(t, {}).items():
            if k in bonus:
                bonus[k] += v
    return bonus


def _bp_get_passives(bp: dict) -> dict:
    """收集背包中所有被动技能"""
    passives = {}
    if not bp or not bp.get("items"):
        return passives
    for it in bp["items"]:
        defn = BACKPACK_ITEMS.get(it["id"], {})
        p = defn.get("passive")
        if not p:
            continue
        for k, v in p.items():
            passives[k] = passives.get(k, 0) + v
    return passives


def _bp_generate_shop(floor: int) -> list:
    """生成商店物品列表 (3-4个随机物品)"""
    by_rarity = {}
    for iid, defn in BACKPACK_ITEMS.items():
        if defn.get("type") in ("set_merged", "ultimate"):
            continue  # 合体/终极物品不出现在商店
        by_rarity.setdefault(defn["rarity"], []).append(iid)
    rarities = ["common", "uncommon", "rare", "legendary"]
    weights = [RARITY_SHOP_WEIGHTS[r](floor) for r in rarities]
    count = 3 if floor < 10 else 4
    shop = []
    used_ids = set()
    for _ in range(count):
        rarity = random.choices(rarities, weights=weights, k=1)[0]
        pool = [iid for iid in by_rarity.get(rarity, []) if iid not in used_ids]
        if not pool:
            pool = [iid for iid in by_rarity.get("common", []) if iid not in used_ids]
        if not pool:
            continue
        iid = random.choice(pool)
        used_ids.add(iid)
        defn = BACKPACK_ITEMS[iid]
        # 价格随楼层微调
        price = defn["price"] + random.randint(-1, max(1, floor // 10))
        shop.append({"item_id": iid, "price": max(3, price)})
    return shop


def _hint(session: dict, key: str, msg: str):
    """首次出现时在日志中显示教学提示"""
    shown = session.get("_hints_shown", [])
    if key not in shown:
        shown.append(key)
        session["_hints_shown"] = shown
        session.get("log", []).append(f"💡 {msg}")


def _bp_sanitize(bp: dict) -> dict:
    """返回前端需要的背包数据"""
    items = []
    set_info = _bp_compute_set_info(bp)
    bp_stats = _bp_calc_stats(bp, set_info)
    item_ids_in_bp = {it["id"] for it in bp["items"]}
    for it in bp["items"]:
        defn = BACKPACK_ITEMS.get(it["id"], {})
        w, h = _bp_item_wh(it)
        entry = {
            "uid": it["uid"], "id": it["id"], "row": it["row"], "col": it["col"],
            "name": defn.get("name", "?"), "icon": defn.get("icon", "?"),
            "type": defn.get("type", ""), "w": w, "h": h,
            "rotated": bool(it.get("rotated")),
            "rarity": defn.get("rarity", "common"), "desc": defn.get("desc", ""),
            "consumable": defn.get("consumable", False),
            "effects": defn.get("effects", {}),
            "adj": defn.get("adj", {}),
            "adj_desc": _bp_adj_desc(defn),
            "cursed": defn.get("cursed", False) and not it.get("purified"),
            "purified": bool(it.get("purified")),
            "enchants": it.get("enchants", []),
            "passive": defn.get("passive"),
            "can_merge": it["id"] in MERGE_CHAINS,
            "merge_target": MERGE_CHAINS.get(it["id"]),
            "sell_price": max(1, defn.get("price", 5) // 2),
            "set_badge": _SET_BADGE.get(it["id"]),
            "is_merged": defn.get("type") in ("set_merged", "ultimate"),
        }
        items.append(entry)
    expand_cost = _bp_expand_cost(bp)
    # 套装信息 (major + minor)
    _stat_cn = {"atk": "攻", "def": "防", "crit": "暴击", "crit_damage": "爆伤", "lifesteal": "吸血", "max_hp": "HP"}
    major_sets = []
    for sid, sdef in ITEM_SETS.items():
        if not sdef.get("major"):
            continue
        info = set_info["major"].get(sid)
        if not info and sid not in set_info["active_major"]:
            # 没有任何散件也没合体 → 完全不显示
            continue
        eff = info["eff_pieces"] if info else 0
        set_size = len(sdef["items"])
        is_active = sid in set_info["active_major"]
        is_complete = info["is_complete"] if info else False
        has_merged = info["has_merged"] if info else False
        unique_pieces = info["unique_pieces"] if info else 0
        bonus_desc = " ".join(f"{_stat_cn.get(k, k)}+{v * eff}" for k, v in sdef["piece_bonus"].items()) if eff >= 2 else sdef["desc"]
        entry = {
            "id": sid, "name": sdef["name"],
            "pieces": eff, "total": set_size,
            "active": is_active,
            "complete": is_complete,
            "bonus_desc": bonus_desc,
            "can_merge": is_complete and not has_merged and unique_pieces == set_size,
        }
        if sdef.get("exclusive_bonus"):
            entry["exclusive"] = {
                "name": sdef.get("exclusive_name", ""),
                "desc": sdef.get("exclusive_desc", ""),
                "active": is_complete and is_active,
            }
        major_sets.append(entry)
    # minor套(保持原格式)
    active_sets = []
    for sid, minfo in set_info["minor"].items():
        sdef = ITEM_SETS[sid]
        bonus_desc = " ".join(f"{_stat_cn.get(k, k)}+{v * minfo['pieces']}" for k, v in sdef["piece_bonus"].items())
        active_sets.append({"id": sid, "name": sdef["name"], "desc": f"({minfo['pieces']}/{minfo['total']}件) {bonus_desc}", "pieces": minfo["pieces"], "total": minfo["total"]})
    # 连锁
    chain_bonus = _bp_calc_chain_bonus(bp)
    has_chain = any(v > 0 for v in chain_bonus.values())
    # 被动
    passives = _bp_get_passives(bp)
    # 特殊区域
    bonus_cells = list(BP_BONUS_ZONES.get((bp["rows"], bp["cols"]), []))
    return {
        "rows": bp["rows"], "cols": bp["cols"], "items": items, "stats": bp_stats,
        "expand_cost": expand_cost,
        "major_sets": major_sets,
        "active_sets": active_sets,
        "max_active_major": set_info["max_active"],
        "chain_bonus": chain_bonus if has_chain else None,
        "passives": passives if passives else None,
        "bonus_cells": bonus_cells,
        "enchant_cost": ENCHANT_BASE_COST,
    }


def _bp_adj_desc(defn: dict) -> str:
    """生成相邻加成描述"""
    adj = defn.get("adj")
    if not adj:
        return ""
    parts = []
    type_names = {"weapon": "武器", "shield": "盾牌", "armor": "护甲", "accessory": "饰品", "potion": "药水", "special": "特殊", "helmet": "头盔", "bracer": "护臂", "boots": "鞋子", "leggings": "护腿"}
    stat_names = {"atk": "攻击", "def": "防御", "crit": "暴击", "crit_damage": "爆伤", "lifesteal": "吸血", "max_hp": "HP"}
    for ntype, bonuses in adj.items():
        for stat, val in bonuses.items():
            parts.append(f"相邻{type_names.get(ntype, ntype)}: {stat_names.get(stat, stat)}+{val}")
    return " | ".join(parts)


# ===================== 楼层与遭遇生成 =====================

def _generate_floor_plan(difficulty: str = "medium") -> list:
    """预生成所有楼层的遭遇类型（不含boss层），遵循规则：
    1. 第1层不出现商店
    2. 商店不连续出现
    3. boss战前1-2层必有商店
    4. 每3-4层出现一次祝福事件
    5. 合理分布怪物、宝箱、陷阱
    """
    cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["medium"])
    max_floor = cfg["max_floor"]
    # 不含boss层，生成1到max_floor-1层的遭遇
    total = max_floor - 1
    if total <= 0:
        return []
    
    plan = [None] * (total + 1)  # index 0不用, 1~total
    
    # 规则3: boss前1-2层保证有商店
    if total >= 2:
        shop_before_boss = total - random.randint(0, 1)
        plan[shop_before_boss] = "shop"
    elif total >= 1:
        plan[total] = "shop"
    
    # 规则4: 每3-4层安排一次祝福（从第2层开始）
    blessing_interval = 3 if total <= 8 else 4
    for f in range(blessing_interval, total + 1, blessing_interval):
        if plan[f] is None:
            plan[f] = "blessing"
    
    # 规则1+2: 填充剩余楼层
    for f in range(1, total + 1):
        if plan[f] is not None:
            continue
        
        # 第1层不出现商店
        allowed = ["monster", "chest", "trap"]
        if f > 1:
            allowed.append("shop")
        
        # 商店不连续：检查前一层
        if f > 1 and plan[f - 1] == "shop" and "shop" in allowed:
            allowed.remove("shop")
        
        weights_map = {
            "monster": 45,
            "chest": 20,
            "trap": 20,
            "shop": 15,
        }
        weights = [weights_map.get(t, 10) for t in allowed]
        plan[f] = random.choices(allowed, weights=weights, k=1)[0]
    
    # 规则2后置检查: 确保商店不连续
    for f in range(2, total + 1):
        if plan[f] == "shop" and plan[f - 1] == "shop":
            plan[f] = random.choice(["monster", "chest", "trap"])
    
    return plan  # plan[1..total], plan[0]未使用


# 祝福/增益选项池
ADVENTURE_BLESSINGS = [
    # ── 普通祝福 (weight 10) ──
    {"id": "atk_up", "name": "⚔️ 力量祝福", "desc": "攻击+5", "effect": {"atk": 5}, "weight": 10, "rarity": "common"},
    {"id": "def_up", "name": "🛡️ 铁壁祝福", "desc": "防御+4", "effect": {"def": 4}, "weight": 10, "rarity": "common"},
    {"id": "hp_restore", "name": "💚 治愈祝福", "desc": "恢复40HP", "effect": {"heal": 40}, "weight": 10, "rarity": "common"},
    {"id": "max_hp_up", "name": "❤️ 生命祝福", "desc": "最大HP+20", "effect": {"max_hp": 20}, "weight": 10, "rarity": "common"},
    {"id": "potion_gift", "name": "🧪 药剂祝福", "desc": "获得2瓶药水", "effect": {"potions": 2}, "weight": 10, "rarity": "common"},
    # ── 稀有祝福 (weight 6) ──
    {"id": "atk_up_large", "name": "🗡️ 狂战祝福", "desc": "攻击+8", "effect": {"atk": 8}, "weight": 6, "rarity": "rare"},
    {"id": "def_up_large", "name": "🏰 堡垒祝福", "desc": "防御+7", "effect": {"def": 7}, "weight": 6, "rarity": "rare"},
    {"id": "hp_restore_large", "name": "💖 圣光祝福", "desc": "恢复70HP", "effect": {"heal": 70}, "weight": 6, "rarity": "rare"},
    {"id": "max_hp_up_large", "name": "💗 巨力心脏", "desc": "最大HP+35", "effect": {"max_hp": 35}, "weight": 6, "rarity": "rare"},
    {"id": "crit_chance", "name": "🎯 精准祝福", "desc": "暴击率+15%", "effect": {"crit": 15}, "weight": 6, "rarity": "rare"},
    {"id": "lifesteal", "name": "🧛 吸血祝福", "desc": "攻击恢复20%伤害值HP", "effect": {"lifesteal": 20}, "weight": 6, "rarity": "rare"},
    {"id": "crit_dmg_up", "name": "💢 暴击强化", "desc": "爆伤+25%", "effect": {"crit_damage": 25}, "weight": 6, "rarity": "rare"},
    {"id": "exp_boost", "name": "📖 智慧祝福", "desc": "获得30EXP", "effect": {"exp_grant": 30}, "weight": 6, "rarity": "rare"},
    # ── 史诗祝福 (weight 3) ──
    {"id": "all_stats", "name": "🌟 全属性祝福", "desc": "攻击+4 防御+3 最大HP+15", "effect": {"atk": 4, "def": 3, "max_hp": 15}, "weight": 3, "rarity": "epic"},
    {"id": "crit_burst", "name": "💥 暴击爆发", "desc": "暴击率+10% 爆伤+30%", "effect": {"crit": 10, "crit_damage": 30}, "weight": 3, "rarity": "epic"},
    {"id": "berserker", "name": "🔥 狂战士之血", "desc": "攻击+12 但最大HP-20", "effect": {"atk": 12, "max_hp": -20}, "weight": 3, "rarity": "epic"},
    {"id": "fortress", "name": "🏯 绝对防御", "desc": "防御+10 最大HP+25", "effect": {"def": 10, "max_hp": 25}, "weight": 3, "rarity": "epic"},
    {"id": "vampire_lord", "name": "🦇 吸血领主", "desc": "吸血+15% 攻击+5", "effect": {"lifesteal": 15, "atk": 5}, "weight": 3, "rarity": "epic"},
    {"id": "hp_surge", "name": "💓 生命涌泉", "desc": "最大HP+60 恢复全部HP", "effect": {"max_hp": 60, "heal_full": True}, "weight": 3, "rarity": "epic"},
    {"id": "potion_rain", "name": "🌧️ 药水雨", "desc": "获得4瓶药水", "effect": {"potions": 4}, "weight": 3, "rarity": "epic"},
    # ── 传说祝福 (weight 1) ── 极其稀有但能改变局势
    {"id": "immortal_body", "name": "👼 不死之躯", "desc": "最大HP+100 恢复全部HP", "effect": {"max_hp": 100, "heal_full": True}, "weight": 1, "rarity": "legendary"},
    {"id": "god_slayer", "name": "⚡ 弑神之力", "desc": "攻击+15 暴击率+10% 爆伤+25%", "effect": {"atk": 15, "crit": 10, "crit_damage": 25}, "weight": 1, "rarity": "legendary"},
    {"id": "divine_protection", "name": "🛡️ 神圣护盾", "desc": "防御+15 获得永久首击减伤30", "effect": {"def": 15, "grant_passive": {"first_hit_shield": 30}}, "weight": 1, "rarity": "legendary"},
    {"id": "soul_harvest", "name": "💀 灵魂收割", "desc": "吸血+25% 攻击+8 但防御-5", "effect": {"lifesteal": 25, "atk": 8, "def": -5}, "weight": 1, "rarity": "legendary"},
    {"id": "gamblers_fortune", "name": "🎰 赌徒的命运", "desc": "随机获得强力增益(攻击/防御/暴击/HP大幅提升)", "effect": {"random_mega": True}, "weight": 1, "rarity": "legendary"},
]


def _weighted_blessing_sample(blessings: list, k: int = 3) -> list:
    """加权随机选择k个不重复的祝福"""
    pool = list(blessings)
    weights = [b.get("weight", 10) for b in pool]
    chosen = []
    for _ in range(min(k, len(pool))):
        if not pool:
            break
        selected = random.choices(range(len(pool)), weights=weights, k=1)[0]
        chosen.append(pool[selected])
        pool.pop(selected)
        weights.pop(selected)
    return chosen


# ===================== 无尽模式缩放函数 =====================

import math as _math


def _calc_dominance_scaling(floor: int, player_stats: dict = None) -> dict:
    """计算玩家对敌人的力量压制系数，返回敌人的 HP / ATK / DEF 倍率。

    设计目标：
    - 前期 (1-15层) 几乎无影响，让玩家享受成长快感
    - 中期 (15-50层) 当玩家 DPS 显著超过基线时开始温和调整
    - 后期 (50层+) 差距越大调整越猛烈，但有上限防止离谱

    使用对数曲线: multiplier = 1 + k * ln(dominance_ratio)
    - dominance_ratio = player_effective_dps / enemy_baseline_power
    - k 随楼层缓慢增长，让后期调整更积极
    """
    result = {"hp_mult": 1.0, "atk_mult": 1.0, "def_mult": 1.0, "active": False}
    if not player_stats or floor < 10:
        return result

    lagged_dps = player_stats.get("scaling_dps", 0)
    p_def = player_stats.get("defense", 0)
    if lagged_dps <= 0:
        return result

    # 敌人基线战力 = 楼层基础 DPS (与 _endless_monster_stats 的 base atk 对应)
    enemy_baseline = 4 + floor * 0.7 + (floor ** 0.5) * 2

    # 玩家综合战力：DPS 为主，防御高也说明玩家很强
    player_power = lagged_dps + p_def * 0.5

    # 压制比 = 玩家战力 / 敌人基线
    dominance_ratio = player_power / max(1, enemy_baseline)

    # 压制阈值：比值低于此值时不触发调整
    threshold = 2.5 if floor < 30 else 2.0 if floor < 60 else 1.8
    if dominance_ratio <= threshold:
        return result

    # 有效压制量 = 超出阈值的部分
    excess = dominance_ratio - threshold

    # k 系数随楼层缓慢增长: 前期温柔，后期更积极
    # floor 10: k≈0.20, floor 30: k≈0.28, floor 60: k≈0.35, floor 100: k≈0.40
    k_hp = 0.15 + min(0.30, floor * 0.003)
    k_atk = 0.10 + min(0.20, floor * 0.002)
    k_def = 0.08 + min(0.15, floor * 0.0015)

    # 对数曲线缩放: ln(1+excess) 在 excess 小时接近 excess, 大时压缩增长
    log_factor = _math.log1p(excess)  # ln(1 + excess)

    hp_mult = 1.0 + k_hp * log_factor
    atk_mult = 1.0 + k_atk * log_factor
    def_mult = 1.0 + k_def * log_factor

    # 硬上限: 防止极端情况
    hp_mult = min(hp_mult, 6.0)
    atk_mult = min(atk_mult, 3.5)
    def_mult = min(def_mult, 3.0)

    result["hp_mult"] = hp_mult
    result["atk_mult"] = atk_mult
    result["def_mult"] = def_mult
    result["active"] = True
    return result


def _endless_floor_exp(floor: int) -> int:
    """Calculate EXP reward for an endless mode floor.
    Scales roughly as: base 5 + floor * 1.5, with some variance.
    """
    base = 5 + int(floor * 1.5)
    variance = max(1, int(base * 0.15))
    return base + random.randint(-variance, variance)


def _endless_monster_stats(floor: int, player_stats: dict = None) -> dict:
    """Generate a monster with stats scaled to floor level in endless mode.
    Also factors in player power via dominance scaling to keep challenge proportional.
    """
    effective_floor = floor
    # Random upward spike: 35% chance to face a harder monster (disabled on early floors)
    if floor > 5 and random.random() < 0.35:
        spike = random.uniform(1.15, 1.6)
        effective_floor = int(floor * spike)
    effective_floor = max(floor, effective_floor)
    
    # Base stats from floor (flattened curve for better pacing)
    hp = int(18 + effective_floor * 2.8 + (effective_floor ** 0.55) * 5)
    atk = int(4 + effective_floor * 0.7 + (effective_floor ** 0.5) * 2)
    defense = max(0, int((effective_floor - 15) * 0.25)) if effective_floor > 15 else 0
    
    # Soft start: reduce monster stats on early floors so player can build up
    if floor <= 6:
        soft = 0.5 + 0.5 * (floor / 6)  # F1=0.58, F3=0.75, F6=1.0
        hp = max(8, int(hp * soft))
        atk = max(2, int(atk * soft))
    
    # ── 压制系数：当玩家实力远超怪物基线时，动态提升怪物属性 ──
    dom = _calc_dominance_scaling(floor, player_stats)
    if dom["active"]:
        hp = int(hp * dom["hp_mult"])
        atk = int(atk * dom["atk_mult"])
        defense = int(defense * dom["def_mult"]) if defense > 0 else 0

    # 兜底：玩家防御远超怪物攻击时，保证怪物能打出伤害
    if player_stats:
        p_def = player_stats.get("defense", 0)
        if p_def > 0 and atk <= p_def * 1.2:
            atk = int(p_def * 1.3 + floor * 0.5)
    
    # Name pool with tier-based naming
    if effective_floor <= 10:
        names = ["小偷鼠", "贪婪蛇", "税务怪"]
    elif effective_floor <= 30:
        names = ["通胀兽", "市场狼", "干预者"]
    elif effective_floor <= 60:
        names = ["金融危机龙", "蒲公英恶魔", "黑天鹅"]
    elif effective_floor <= 100:
        names = ["末日收割者", "混沌巨兽", "时空裂隙"]
    else:
        names = ["天启古神", "宇宙吐息者", "无尽深渊"]
    
    return {"name": random.choice(names), "hp": hp, "attack": atk, "defense": defense}


def _endless_boss_stats(floor: int, player_stats: dict = None) -> dict:
    """Generate a mini-boss for endless mode (appears every 10 floors).
    Scales with player power via dominance scaling for sustained challenge.
    """
    effective_floor = floor
    hp = int(40 + effective_floor * 4 + (effective_floor ** 0.6) * 8)
    atk = int(7 + effective_floor * 1.0 + (effective_floor ** 0.5) * 2.8)
    defense = max(0, int((effective_floor - 8) * 0.4)) if effective_floor > 8 else 0
    
    # ── 压制系数：Boss 额外加强 20% 倍率 ──
    dom = _calc_dominance_scaling(floor, player_stats)
    if dom["active"]:
        boss_extra = 1.2  # Boss 比普通怪多 20% 的压制缩放
        hp = int(hp * (1.0 + (dom["hp_mult"] - 1.0) * boss_extra))
        atk = int(atk * (1.0 + (dom["atk_mult"] - 1.0) * boss_extra))
        defense = int(defense * (1.0 + (dom["def_mult"] - 1.0) * boss_extra)) if defense > 0 else 0

    # 兜底：玩家防御远超 Boss 攻击时
    if player_stats:
        p_def = player_stats.get("defense", 0)
        if p_def > 0 and atk <= p_def * 1.2:
            atk = int(p_def * 1.5 + floor * 0.8)
    
    if effective_floor <= 20:
        names = ["小贪官", "市场操纵者"]
    elif effective_floor <= 50:
        names = ["金融危机龙", "老千岁魔"]
    elif effective_floor <= 100:
        names = ["末日收割者", "混沌魔神"]
    else:
        names = ["宇宙统治者", "时空破坏神"]
    
    return {"name": random.choice(names), "hp": hp, "attack": atk, "defense": defense}


# ===================== 遭遇生成 =====================

def _make_encounter(enc_type: str, floor: int, difficulty: str, player_stats: dict = None) -> dict:
    """根据遭遇类型生成具体遭遇数据"""
    cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["medium"])
    is_endless = cfg.get("endless", False)
    
    if enc_type == "boss":
        if is_endless:
            stats = _endless_boss_stats(floor, player_stats)
            return {"type": "boss", "name": stats["name"],
                    "monster_hp": stats["hp"], "monster_max_hp": stats["hp"],
                    "monster_attack": stats["attack"], "monster_defense": stats.get("defense", 0)}
        b = cfg["boss"]
        return {"type": "boss", "name": b["name"],
                "monster_hp": b["hp"], "monster_max_hp": b["hp"],
                "monster_attack": b["attack"]}
    elif enc_type == "monster":
        if is_endless:
            stats = _endless_monster_stats(floor, player_stats)
            enc_d = {"type": "monster", "name": stats["name"],
                    "monster_hp": stats["hp"], "monster_max_hp": stats["hp"],
                    "monster_attack": stats["attack"], "monster_defense": stats.get("defense", 0)}
            # 精英怪 (8层起, 22% 概率)
            if floor >= 8 and random.random() < 0.22:
                ability = random.choice(ELITE_ABILITIES)
                enc_d["elite"] = True
                enc_d["ability"] = ability
                enc_d["name"] = f"⭐{stats['name']}"
                enc_d["monster_hp"] = int(enc_d["monster_hp"] * 1.5)
                enc_d["monster_max_hp"] = enc_d["monster_hp"]
                enc_d["monster_attack"] = int(enc_d["monster_attack"] * 1.25)
            return enc_d
        m = random.choice(ADVENTURE_MONSTERS)
        hp = int(m["hp"] * cfg["monster_hp_mult"])
        atk = int(m["attack"] * cfg["monster_atk_mult"])
        return {"type": "monster", "name": m["name"],
                "monster_hp": hp, "monster_max_hp": hp,
                "monster_attack": atk}
    elif enc_type == "chest":
        return {"type": "chest", "name": "宝箱", "reward_exp": random.randint(5, 15)}
    elif enc_type == "trap":
        trap_dmg = random.randint(10, 25)
        if difficulty == "hard":
            trap_dmg = random.randint(15, 35)
        elif difficulty == "expert":
            trap_dmg = random.randint(20, 45)
        elif is_endless:
            base_dmg = 10 + int(floor * 0.8)
            trap_dmg = random.randint(base_dmg, int(base_dmg * 1.5))
            # 压制系数应用于陷阱伤害
            dom = _calc_dominance_scaling(floor, player_stats)
            if dom["active"]:
                trap_dmg = int(trap_dmg * dom["atk_mult"])
        return {"type": "trap", "name": "陷阱", "damage": trap_dmg}
    elif enc_type == "shop":
        if is_endless:
            shop_items = _bp_generate_shop(floor)
            return {"type": "shop", "name": "旅行商人", "shop_items": shop_items}
        return {"type": "shop", "name": "商店", "shop_items": [
            {"item_id": "small_potion", "price": 6},
            {"item_id": "buckler", "price": 5},
            {"item_id": "dagger", "price": 6},
        ]}
    elif enc_type == "blessing":
        # 加权随机选3个祝福供玩家选择
        choices = _weighted_blessing_sample(ADVENTURE_BLESSINGS, 3)
        return {"type": "blessing", "name": "神秘祝福",
                "choices": [{"id": c["id"], "name": c["name"], "desc": c["desc"], "rarity": c.get("rarity", "common")} for c in choices]}
    else:
        # fallback
        return _make_encounter("monster", floor, difficulty)


def _generate_encounter(floor: int, difficulty: str = "medium", floor_plan: list = None, player_stats: dict = None) -> dict:
    """生成指定楼层的遭遇。如果有预生成计划则使用计划，否则回退到旧逻辑"""
    cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["medium"])
    is_endless = cfg.get("endless", False)
    
    if is_endless:
        # Endless mode: dynamic generation per floor
        # Mini-boss every 10 floors
        if floor > 0 and floor % 10 == 0:
            return _make_encounter("boss", floor, difficulty, player_stats)
        # Blessing every 3-4 floors (starting from floor 3)
        blessing_interval = 3 if floor <= 30 else 4
        if floor >= 3 and floor % blessing_interval == 0:
            return _make_encounter("blessing", floor, difficulty, player_stats)
        # Shop guaranteed before mini-boss (floor 9, 19, 29, ...)
        if floor > 0 and floor % 10 == 9:
            return _make_encounter("shop", floor, difficulty, player_stats)
        # Regular floors: weighted random
        # No shop on floor 1
        if floor <= 1:
            allowed = ["monster", "chest", "trap"]
        else:
            allowed = ["monster", "chest", "trap", "shop"]
        weights_map = {"monster": 50, "chest": 18, "trap": 18, "shop": 14}
        weights = [weights_map.get(t, 10) for t in allowed]
        enc_type = random.choices(allowed, weights=weights, k=1)[0]
        return _make_encounter(enc_type, floor, difficulty, player_stats)
    
    if floor >= cfg["max_floor"]:
        return _make_encounter("boss", floor, difficulty)
    
    if floor_plan and 1 <= floor < len(floor_plan) and floor_plan[floor]:
        return _make_encounter(floor_plan[floor], floor, difficulty)
    
    # 回退：简单随机（兼容旧存档）
    enc_type = random.choices(
        ["monster", "chest", "trap", "shop"],
        weights=[40, 20, 20, 20], k=1
    )[0]
    return _make_encounter(enc_type, floor, difficulty)


# ==================== 会话创建 ====================

def create_adventure_session(pet_level: int, difficulty: str = "easy") -> dict:
    cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["easy"])
    is_endless = cfg.get("endless", False)
    floor_plan = None if is_endless else _generate_floor_plan(difficulty)
    encounter = _generate_encounter(1, difficulty, floor_plan)
    return {
        "started_at": datetime.utcnow().isoformat(),
        "difficulty": difficulty,
        "floor": 1,
        "max_floor": cfg["max_floor"],
        "endless": is_endless,
        "hp": cfg["player_hp"],
        "max_hp": cfg["player_hp"],
        "attack": 10 + pet_level + cfg["atk_bonus"],
        "defense": 0,
        "potions": 0,
        "exp_earned": 0,
        "encounter": encounter,
        "encounter_resolved": False,
        "floors_cleared": 0,
        "log": [f"📍 进入第1层，遭遇了{encounter['name']}！"],
        "game_over": False,
        "floor_plan": floor_plan,
        "crit_chance": 0,
        "crit_damage": 180,
        "lifesteal": 0,
        "buffs": {},
        "timed_buffs": [],
        "scaling_dps": 0,
        "backpack": _bp_init(is_endless),
        "base_max_hp": cfg["player_hp"],
        "_hints_shown": [],
    }


# ==================== 状态脱敏 ====================

_ENC_TYPE_ICONS = {
    "monster": "👾", "boss": "🐉", "chest": "🎁",
    "trap": "⚠️", "shop": "🏪", "blessing": "✨",
}
_ENC_TYPE_NAMES = {
    "monster": "怪物", "boss": "Boss", "chest": "宝箱",
    "trap": "陷阱", "shop": "商店", "blessing": "祝福",
}


def _build_next_floor_preview(session: dict) -> dict | None:
    """构建下一层预览信息（仅在遭遇已解决、非game_over时显示）"""
    if session.get("game_over") or not session.get("encounter_resolved"):
        return None
    floor = session["floor"]
    difficulty = session.get("difficulty", "easy")
    cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["easy"])
    is_endless = cfg.get("endless", False)
    max_floor = cfg["max_floor"]

    next_f = floor + 1

    if not is_endless:
        # 非无尽: 下一层是boss层?
        if next_f >= max_floor:
            boss = cfg.get("boss", {})
            return {"floor": next_f, "type": "boss", "icon": "🐉",
                    "name": boss.get("name", "Boss"), "is_final": True}
        # 从 floor_plan 读取
        fp = session.get("floor_plan")
        if fp and 1 <= next_f < len(fp) and fp[next_f]:
            t = fp[next_f]
            return {"floor": next_f, "type": t,
                    "icon": _ENC_TYPE_ICONS.get(t, "❓"),
                    "name": _ENC_TYPE_NAMES.get(t, "未知")}
        return None  # 无计划回退

    # 无尽模式: 给出明确规律提示
    if next_f % 10 == 0:
        return {"floor": next_f, "type": "boss", "icon": "🐉",
                "name": f"第{next_f}层 Boss", "is_final": False}
    if next_f % 10 == 9:
        return {"floor": next_f, "type": "shop", "icon": "🏪",
                "name": "旅行商人"}
    blessing_interval = 3 if next_f <= 30 else 4
    if next_f >= 3 and next_f % blessing_interval == 0:
        return {"floor": next_f, "type": "blessing", "icon": "✨",
                "name": "神秘祝福"}
    # 普通层给一个模糊提示
    floors_to_boss = 10 - (next_f % 10)
    return {"floor": next_f, "type": "random", "icon": "❓",
            "name": "未知遭遇", "hint": f"距Boss还有{floors_to_boss}层"}


def sanitize_adventure_state(session: dict) -> dict:
    """清除服务端秘密，返回客户端安全的探险游戏状态"""
    # 永久祝福列表（仅供属性面板查看，不在主状态栏显示）
    raw_buffs = session.get("buffs", {})
    if isinstance(raw_buffs, list):
        migrated = {}
        for b in raw_buffs:
            migrated[b] = migrated.get(b, 0) + 1
        raw_buffs = migrated
        session["buffs"] = migrated
    _blessing_rarity = {b["name"]: b.get("rarity", "common") for b in ADVENTURE_BLESSINGS}
    blessings_display = [{"name": name, "count": count, "rarity": _blessing_rarity.get(name, "common")} for name, count in raw_buffs.items()]
    # 临时buff/debuff（主状态栏显示）
    timed_buffs_display = []
    for tb in session.get("timed_buffs", []):
        defn = TIMED_BUFF_DEFS.get(tb["id"])
        if defn:
            timed_buffs_display.append({
                "id": tb["id"], "name": defn["name"], "type": defn["type"],
                "desc": defn["desc"], "turns_left": tb["turns_left"],
                "scope": defn["scope"], "source": tb.get("source", ""),
            })
    state = {
        "floor": session["floor"],
        "max_floor": session["max_floor"],
        "difficulty": session.get("difficulty", "easy"),
        "endless": session.get("endless", False),
        "retreated": session.get("retreated", False),
        "hp": session["hp"],
        "max_hp": session["max_hp"],
        "attack": session["attack"],
        "defense": session["defense"],
        "potions": session["potions"],
        "exp_earned": session["exp_earned"],
        "log": session["log"][-10:],
        "floors_cleared": session["floors_cleared"],
        "game_over": session.get("game_over", False),
        "encounter_resolved": session.get("encounter_resolved", False),
        "crit_chance": min(session.get("crit_chance", 0), 100),
        "crit_damage": session.get("crit_damage", 180),
        "lifesteal": session.get("lifesteal", 0),
        "blessings": blessings_display,
        "timed_buffs": timed_buffs_display,
    }
    # 背包数据
    bp = session.get("backpack")
    if bp:
        bp_san = _bp_sanitize(bp)
        # 合并祝福赐予的永久被动到backpack passives显示
        _bps = session.get("blessing_passives", {})
        if _bps and bp_san.get("passives"):
            for pk, pv in _bps.items():
                bp_san["passives"][pk] = bp_san["passives"].get(pk, 0) + pv
        elif _bps:
            bp_san["passives"] = dict(_bps)
        state["backpack"] = bp_san
        state["bp_stats"] = bp_san["stats"]
    # 被动技能汇总（背包 + 祝福永久被动）
    bp_passives = {}
    if bp:
        bp_san_p = bp_san.get("passives", {})
        bp_passives = dict(bp_san_p) if bp_san_p else {}
    state["passives"] = bp_passives

    # 下一层预览
    _next = _build_next_floor_preview(session)
    if _next:
        state["next_floor_preview"] = _next

    if session.get("floor_curse"):
        state["floor_curse"] = session["floor_curse"]
    enc = session.get("encounter")
    if enc:
        if not session.get("encounter_resolved"):
            safe_enc = {"type": enc["type"], "name": enc["name"]}
            if enc["type"] in ("monster", "boss"):
                safe_enc["monster_hp"] = enc["monster_hp"]
                safe_enc["monster_max_hp"] = enc["monster_max_hp"]
                safe_enc["monster_attack"] = enc["monster_attack"]
                safe_enc["monster_defense"] = enc.get("monster_defense", 0)
                if enc.get("elite"):
                    safe_enc["elite"] = True
                    safe_enc["ability"] = enc.get("ability")
            elif enc["type"] == "shop":
                raw_si = enc.get("shop_items", [])
                enriched = []
                for si in raw_si:
                    d = BACKPACK_ITEMS.get(si.get("item_id", ""), {})
                    enriched.append({
                        "item_id": si.get("item_id", ""), "price": si.get("price", 0),
                        "name": d.get("name", "?"), "icon": d.get("icon", "📦"),
                        "desc": d.get("desc", ""), "rarity": d.get("rarity", "common"),
                        "w": d.get("w", 1), "h": d.get("h", 1),
                        "cursed": d.get("cursed", False),
                        "passive": bool(d.get("passive")),
                        "set_badge": _SET_BADGE.get(si.get("item_id", "")),
                    })
                safe_enc["shop_items"] = enriched
            elif enc["type"] == "blessing":
                safe_enc["choices"] = enc.get("choices", [])
                safe_enc["reroll_count"] = enc.get("reroll_count", 0)
            state["encounter"] = safe_enc
        else:
            state["encounter"] = {"type": enc["type"], "name": enc["name"], "resolved": True}
    return _strip_surrogates(state)


# ==================== 游戏逻辑处理 ====================

def process_adventure_action(session: dict, action: dict) -> dict:
    """处理宠物探险操作"""
    act = action.get("action")
    
    # 处理放弃
    if act == "abandon":
        session["game_over"] = True
        session["completed"] = True
        session["abandoned"] = True
        session["exp_earned"] = 0  # 放弃不获得任何经验
        session["log"].append("🏳️ 你放弃了探险...")
        return {"completed": True, "exp_earned": 0, "abandoned": True}
    
    # 处理撤退（无尽模式专用 - 保留已获得的经验）
    if act == "retreat":
        is_endless = session.get("endless", False)
        if not is_endless:
            raise HTTPException(status_code=400, detail="只有无尽模式可以撤退")
        session["game_over"] = True
        session["completed"] = True
        session["retreated"] = True
        earned = session["exp_earned"]
        session["log"].append(f"🚪 你选择了撤退，带回了 {earned} EXP！")
        return {"completed": True, "exp_earned": earned, "retreated": True}
    
    if session.get("game_over"):
        raise HTTPException(status_code=400, detail="探险已结束")

    enc = session["encounter"]
    log = session["log"]

    # 遭遇已解决 → 允许进入下一层或撤退 (背包管理动作放行到下面统一处理)
    _bp_actions = {"use_item", "discard_item", "move_item", "rotate_item", "expand_backpack", "sell_item", "enchant_item", "merge_items", "merge_set"}
    if session.get("encounter_resolved"):
        if act == "retreat":
            is_endless = session.get("endless", False)
            if not is_endless:
                raise HTTPException(status_code=400, detail="只有无尽模式可以撤退")
            session["game_over"] = True
            session["completed"] = True
            session["retreated"] = True
            earned = session["exp_earned"]
            log.append(f"🚪 你选择了撤退，带回了 {earned} EXP！")
            return {"completed": True, "exp_earned": earned, "retreated": True}
        if act not in ("next_floor",) and act not in _bp_actions:
            raise HTTPException(status_code=400, detail="请进入下一层")
        is_endless = session.get("endless", False)
        if not is_endless and session["floor"] >= session["max_floor"]:
            session["game_over"] = True
            session["completed"] = True
            log.append("🏆 恭喜通关全部楼层！")
            return {"completed": True, "exp_earned": session["exp_earned"], "adventure_cleared": session.get("difficulty", "easy")}
        # 楼层级timed buff倒计时
        _tick_timed_buffs(session, "floor")
        session["floor"] += 1
        difficulty = session.get("difficulty", "easy")
        floor_plan = session.get("floor_plan")
        player_stats = None
        if session.get("endless"):
            # Compute current real DPS: 80% base stats + 20% backpack contribution
            p_atk = session.get("attack", 10)
            p_crit = min(session.get("crit_chance", 0), 100)
            p_crit_dmg = session.get("crit_damage", 180)
            p_lifesteal = session.get("lifesteal", 0)
            p_def = session.get("defense", 0)
            # 背包属性 (排除不受缩放影响的物品)
            bp_s = _bp_calc_stats(session.get("backpack"), exclude_no_scaling=True) if session.get("backpack") else {}
            bp_atk = bp_s.get("atk", 0)
            bp_crit = bp_s.get("crit", 0)
            bp_crit_dmg = bp_s.get("crit_damage", 0)
            bp_lifesteal = bp_s.get("lifesteal", 0)
            bp_def = bp_s.get("def", 0)
            # 加权混合: 背包贡献 80% 用于敌人缩放计算
            eff_atk = p_atk + bp_atk * 0.8
            eff_crit = min(p_crit + bp_crit * 0.8, 100)
            eff_crit_dmg = p_crit_dmg + bp_crit_dmg * 0.8
            eff_lifesteal = p_lifesteal + bp_lifesteal * 0.8
            eff_def = p_def + bp_def * 0.8
            crit_mult = 1.0 + (eff_crit / 100.0) * ((eff_crit_dmg - 100) / 100.0)
            sustain_mult = 1.0 + eff_lifesteal / 200.0
            current_dps = eff_atk * crit_mult * sustain_mult
            # Blend with lagged scaling_dps (decay=0.5 → catches up in ~2-3 floors)
            old_scaling = session.get("scaling_dps", 0)
            session["scaling_dps"] = old_scaling * 0.5 + current_dps * 0.5
            player_stats = {
                "scaling_dps": session["scaling_dps"],
                "defense": eff_def,
            }
        new_enc = _generate_encounter(session["floor"], difficulty, floor_plan, player_stats)
        session["encounter"] = new_enc
        session["encounter_resolved"] = False
        session["_first_hit_used"] = False  # 重置首击护盾
        # 楼层诅咒 (无尽模式每15层触发)
        _f = session["floor"]
        if session.get("endless") and _f >= 15 and _f % 15 == 0:
            _curse = random.choice(FLOOR_CURSES)
            session["floor_curse"] = _curse
            log.append(f"⚠️ {_curse['name']}！{_curse['desc']}")
        else:
            session.pop("floor_curse", None)
        log.append(f"📍 进入第{session['floor']}层，遭遇了{new_enc['name']}！")
        _floor_result = {"completed": False, "exp_earned": 0, "new_floor": session["floor"]}
        if session.get("endless"):
            _floor_result["adventure_endless_floor"] = session["floor"]
        return _floor_result

    enc_type = enc["type"]

    # 计算总属性 = 基础(祝福) + 背包
    bp = session.get("backpack")
    bp_stats = _bp_calc_stats(bp) if bp else {"atk": 0, "def": 0, "crit": 0, "crit_damage": 0, "lifesteal": 0, "max_hp": 0, "exp_bonus": 0}
    total_atk = session["attack"] + bp_stats["atk"]
    total_def = session["defense"] + bp_stats["def"]
    total_crit = min(session.get("crit_chance", 0) + bp_stats["crit"], 100)
    total_crit_dmg = session.get("crit_damage", 180) + bp_stats["crit_damage"]
    total_lifesteal = session.get("lifesteal", 0) + bp_stats["lifesteal"]
    # 楼层诅咒效果
    _fc = session.get("floor_curse")
    if _fc:
        _fid = _fc["id"]
        if _fid == "weakness": total_atk = int(total_atk * 0.75)
        elif _fid == "corrosion": total_def = int(total_def * 0.5)
        elif _fid == "chaos": total_crit = total_crit // 2
        elif _fid == "seal": total_lifesteal = 0
    # 临时buff/debuff效果
    _tb_fx = _get_timed_buff_effects(session)
    if _tb_fx:
        if _tb_fx.get("atk_pct"):
            total_atk = max(1, int(total_atk * (100 + _tb_fx["atk_pct"]) / 100))
        if _tb_fx.get("def_pct"):
            total_def = max(0, int(total_def * (100 + _tb_fx["def_pct"]) / 100))
        if _tb_fx.get("crit_bonus"):
            total_crit = max(0, min(100, total_crit + _tb_fx["crit_bonus"]))
        if _tb_fx.get("crit_dmg_bonus"):
            total_crit_dmg += _tb_fx["crit_dmg_bonus"]
        if _tb_fx.get("atk_flat"):
            total_atk = max(1, total_atk + _tb_fx["atk_flat"])
        if _tb_fx.get("def_flat"):
            total_def = max(0, total_def + _tb_fx["def_flat"])
    # 背包max_hp加成
    base_mhp = session.get("base_max_hp", session["max_hp"])
    bonus_mhp = bp_stats["max_hp"]
    new_max_hp = base_mhp + bonus_mhp
    if new_max_hp != session.get("_last_max_hp", 0):
        diff = new_max_hp - session["max_hp"]
        session["max_hp"] = new_max_hp
        if diff > 0:
            session["hp"] = min(session["max_hp"], session["hp"] + diff)
        session["_last_max_hp"] = new_max_hp

    # 使用背包物品 (任何遭遇中都能使用)
    if act == "use_item":
        item_uid = action.get("item_uid")
        if not bp or not item_uid:
            raise HTTPException(status_code=400, detail="无效的物品")
        bp_item = next((i for i in bp["items"] if i["uid"] == item_uid), None)
        if not bp_item:
            raise HTTPException(status_code=400, detail="物品不存在")
        defn = BACKPACK_ITEMS.get(bp_item["id"], {})
        if not defn.get("consumable"):
            raise HTTPException(status_code=400, detail="该物品不可使用")
        effects = defn.get("effects", {})
        _bp_remove(bp, item_uid)
        # 药水效果
        if "heal" in effects:
            old_hp = session["hp"]
            session["hp"] = min(session["max_hp"], session["hp"] + effects["heal"])
            actual = session["hp"] - old_hp
            log.append(f"{defn['icon']} 使用{defn['name']}，恢复{actual}HP！(HP: {session['hp']}/{session['max_hp']})")
        if "heal_pct" in effects:
            old_hp = session["hp"]
            session["hp"] = session["max_hp"]
            actual = session["hp"] - old_hp
            log.append(f"{defn['icon']} 使用{defn['name']}，恢复{actual}HP！(HP: {session['hp']}/{session['max_hp']})")
        # 增加最大HP效果
        if "max_hp" in effects:
            delta = effects["max_hp"]
            session["base_max_hp"] = session.get("base_max_hp", session["max_hp"]) + delta
            session["max_hp"] += delta
            session["hp"] = min(session["hp"] + delta, session["max_hp"])
            log.append(f"{defn['icon']} 最大HP+{delta}！(HP: {session['hp']}/{session['max_hp']})")
        # 炸弹效果
        if "damage" in effects and enc_type in ("monster", "boss"):
            bomb_dmg = effects["damage"]
            enc["monster_hp"] -= bomb_dmg
            log.append(f"{defn['icon']} {defn['name']}爆炸！对{enc['name']}造成{bomb_dmg}点伤害！")
            if enc["monster_hp"] <= 0:
                difficulty = session.get("difficulty", "easy")
                cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["easy"])
                is_endless = cfg.get("endless", False)
                floor = session["floor"]
                earned = _endless_floor_exp(floor) * (2 if enc_type == "boss" else 1) if is_endless else cfg["floor_exp"][min(floor, len(cfg["floor_exp"]) - 1)]
                session["exp_earned"] += earned
                session["floors_cleared"] += 1
                session["encounter_resolved"] = True
                log.append(f"🎉 {enc['name']}被炸弹消灭了！获得{earned}EXP")
                return {"completed": False, "exp_earned": 0, "battle_result": "victory"}
        return {"completed": False, "exp_earned": 0}

    # 丢弃物品
    if act == "discard_item":
        item_uid = action.get("item_uid")
        if not bp or not item_uid:
            raise HTTPException(status_code=400, detail="无效的物品")
        removed_id = _bp_remove(bp, item_uid)
        if removed_id:
            defn = BACKPACK_ITEMS.get(removed_id, {})
            log.append(f"🗑️ 丢弃了{defn.get('name', '?')}")
        return {"completed": False, "exp_earned": 0}

    # 移动物品
    if act == "move_item":
        item_uid = action.get("item_uid")
        new_row = action.get("row")
        new_col = action.get("col")
        if bp and item_uid is not None and new_row is not None and new_col is not None:
            ok = _bp_move(bp, item_uid, new_row, new_col)
            if not ok:
                log.append("❌ 无法放置到该位置")
        return {"completed": False, "exp_earned": 0}

    # 旋转物品
    if act == "rotate_item":
        item_uid = action.get("item_uid")
        if bp and item_uid is not None:
            ok = _bp_rotate_item(bp, item_uid)
            if not ok:
                log.append("❌ 空间不足，无法旋转")
        return {"completed": False, "exp_earned": 0}

    # 扩展背包
    if act == "expand_backpack":
        if not bp:
            raise HTTPException(status_code=400, detail="没有背包")
        cost = _bp_expand_cost(bp)
        if cost is None:
            raise HTTPException(status_code=400, detail="背包已达最大")
        if session["exp_earned"] < cost:
            raise HTTPException(status_code=400, detail="经验值不足")
        session["exp_earned"] -= cost
        _bp_expand(bp)
        log.append(f"🎒 背包扩展为 {bp['rows']}×{bp['cols']}！（花费{cost}EXP）")
        if BP_BONUS_ZONES.get((bp["rows"], bp["cols"])):
            _hint(session, "bonus_zone", "背包中出现了 ★金色格子 — 这是特殊区域，放在上面的物品基础属性+50%！")
        return {"completed": False, "exp_earned": 0}

    # 出售物品
    if act == "sell_item":
        item_uid = action.get("item_uid")
        if not bp or not item_uid:
            raise HTTPException(status_code=400, detail="无效的物品")
        bp_item = next((i for i in bp["items"] if i["uid"] == item_uid), None)
        if not bp_item:
            raise HTTPException(status_code=400, detail="物品不存在")
        defn = BACKPACK_ITEMS.get(bp_item["id"], {})
        sell_price = max(1, defn.get("price", 5) // 2)
        # 附魔额外回收
        for ench in bp_item.get("enchants", []):
            sell_price += 3
        _bp_remove(bp, item_uid)
        session["exp_earned"] += sell_price
        log.append(f"💰 出售{defn.get('icon', '')}{defn.get('name', '?')}，获得{sell_price}EXP")
        _hint(session, "sell", "出售物品可回收一半购买价格的EXP，附魔过的物品额外返还每个附魔3EXP。")
        return {"completed": False, "exp_earned": 0}

    # 附魔物品
    if act == "enchant_item":
        item_uid = action.get("item_uid")
        if not bp or not item_uid:
            raise HTTPException(status_code=400, detail="无效的物品")
        bp_item = next((i for i in bp["items"] if i["uid"] == item_uid), None)
        if not bp_item:
            raise HTTPException(status_code=400, detail="物品不存在")
        defn = BACKPACK_ITEMS.get(bp_item["id"], {})
        if defn.get("consumable"):
            raise HTTPException(status_code=400, detail="消耗品不可附魔")
        existing = bp_item.get("enchants", [])
        max_enchants = 1 if defn.get("rarity") in ("common",) else (2 if defn.get("rarity") in ("uncommon",) else 3)
        if len(existing) >= max_enchants:
            raise HTTPException(status_code=400, detail=f"该物品最多{max_enchants}个附魔")
        cost = ENCHANT_BASE_COST + len(existing) * 10
        if session["exp_earned"] < cost:
            raise HTTPException(status_code=400, detail=f"经验不足（需要{cost}EXP）")
        session["exp_earned"] -= cost
        affix = random.choice(ENCHANT_AFFIXES)
        value = random.randint(affix["range"][0], affix["range"][1])
        ench_entry = {"name": affix["name"], "icon": affix["icon"], "stat": affix["stat"], "value": value}
        if "enchants" not in bp_item:
            bp_item["enchants"] = []
        bp_item["enchants"].append(ench_entry)
        stat_names = {"atk": "攻击", "def": "防御", "crit": "暴击", "crit_damage": "爆伤", "lifesteal": "吸血", "max_hp": "HP"}
        log.append(f"💎 附魔成功！{defn.get('name', '?')}获得 [{affix['icon']}{affix['name']}] {stat_names.get(affix['stat'], affix['stat'])}+{value}（花费{cost}EXP）")
        _hint(session, "enchant_info", f"附魔为物品添加随机属性。品质越高可附魔次数越多（普通1/优秀2/稀有+3），费用逐次递增。")
        return {"completed": False, "exp_earned": 0}

    # 合成物品
    if act == "merge_items":
        item_uid1 = action.get("item_uid1")
        item_uid2 = action.get("item_uid2")
        if not bp or not item_uid1 or not item_uid2:
            raise HTTPException(status_code=400, detail="需要选择两个物品")
        it1 = next((i for i in bp["items"] if i["uid"] == item_uid1), None)
        it2 = next((i for i in bp["items"] if i["uid"] == item_uid2), None)
        if not it1 or not it2:
            raise HTTPException(status_code=400, detail="物品不存在")
        if it1["id"] != it2["id"]:
            raise HTTPException(status_code=400, detail="只能合成两个相同的物品")
        target_id = MERGE_CHAINS.get(it1["id"])
        if not target_id:
            raise HTTPException(status_code=400, detail="该物品无法合成升级")
        target_defn = BACKPACK_ITEMS.get(target_id)
        if not target_defn:
            raise HTTPException(status_code=400, detail="合成目标不存在")
        # 移除两个源物品, 在it2(未被拖动的)位置放置新物品
        row, col = it2["row"], it2["col"]
        rotated = it2.get("rotated", False)
        _bp_remove(bp, item_uid1)
        _bp_remove(bp, item_uid2)
        # 尝试在原位放置，失败则自动寻位
        uid = None
        if _bp_can_place(bp, target_id, row, col, rotated):
            uid = _bp_place(bp, target_id, row, col, rotated)
        else:
            uid = _bp_auto_place(bp, target_id)
        if uid is None:
            # 放不下 → 放回原物品（回滚）
            _bp_place(bp, it1["id"], row, col, rotated)
            raise HTTPException(status_code=400, detail="背包空间不足，无法放置合成物品")
        src_defn = BACKPACK_ITEMS.get(it1["id"], {})
        log.append(f"🔨 合成成功！2×{src_defn.get('icon', '')}{src_defn.get('name', '?')} → {target_defn['icon']}{target_defn['name']}")
        _bp_check_auto_merge(bp, log)
        return {"completed": False, "exp_earned": 0}

    # 套装合体 (7件 → 1个2×2合体物品) - 已由自动合体处理，保留手动触发入口
    if act == "merge_set":
        set_id = action.get("set_id")
        if not bp or not set_id:
            raise HTTPException(status_code=400, detail="无效的套装")
        sdef = ITEM_SETS.get(set_id)
        if not sdef or not sdef.get("major"):
            raise HTTPException(status_code=400, detail="无效的套装")
        item_ids_in_bp = {it["id"] for it in bp["items"]}
        if not sdef["items"].issubset(item_ids_in_bp):
            raise HTTPException(status_code=400, detail="套装未集齐，无法合体")
        merged_item_id = set_id.replace("_set", "_set_merged")
        if merged_item_id not in BACKPACK_ITEMS:
            raise HTTPException(status_code=400, detail="合体物品不存在")
        # 移除每个套装散件 (每种只移除1个)
        to_remove = set(sdef["items"])
        for it in list(bp["items"]):
            if it["id"] in to_remove:
                _bp_remove(bp, it["uid"])
                to_remove.discard(it["id"])
        # 放置合体物品
        uid = _bp_auto_place(bp, merged_item_id)
        if uid is None:
            raise HTTPException(status_code=400, detail="背包空间不足，无法放置合体物品")
        merged_defn = BACKPACK_ITEMS[merged_item_id]
        log.append(f"✨ 套装合体！{sdef['name']} 七件合一 → {merged_defn['icon']}{merged_defn['name']}")
        _hint(session, "set_merge", "套装合体将7件散装合并为1个2×2物品，保留全部属性和套装加成，大幅节省背包空间！")
        return {"completed": False, "exp_earned": 0}

    if enc_type in ("monster", "boss"):
        if act == "fight":
            # 收集被动技能 (背包 + 祝福赐予的永久被动)
            bp_passives = _bp_get_passives(bp) if bp else {}
            bless_passives = session.get("blessing_passives", {})
            for bpk, bpv in bless_passives.items():
                bp_passives[bpk] = bp_passives.get(bpk, 0) + bpv
            # 首次触发新机制时的教学提示
            if bp:
                _chain = _bp_calc_chain_bonus(bp)
                if any(v > 0 for v in _chain.values()):
                    _hint(session, "chain", "连锁加成已激活！同一行或列放置3+同类型物品可获得额外属性加成。")
                _ids = {it["id"] for it in bp["items"]}
                for sdef in ITEM_SETS.values():
                    if len(sdef["items"] & _ids) >= 2:
                        _hint(session, "set", f"套装激活！拥有同套装2件以上即可获得加成。主题套装(7件)受激活限制，集齐全套可获得史诗级专属加成，还能合体节省空间！")
                        break
            monster_def = enc.get("monster_defense", 0)
            elite_ability = enc.get("ability", {}).get("id") if enc.get("elite") else None
            # ── 临时buff DoT/HoT 处理 ──
            _apply_timed_dot_hot(session, log)
            if session["hp"] <= 0:
                session["hp"] = 0; session["game_over"] = True; session["completed"] = True
                log.append("💀 你被持续伤害击败了...")
                return {"completed": True, "exp_earned": session["exp_earned"]}
            # 闪避加成来自 timed buff
            _tb_dodge = _tb_fx.get("dodge_bonus", 0)
            # ── 被动: random_buff 每回合战斗随机临时增益 ──
            _rb = bp_passives.get("random_buff", 0)
            temp_atk_bonus = 0
            temp_def_bonus = 0
            if _rb > 0:
                buff_type = random.choice(["atk", "def", "crit_dmg", "heal"])
                if buff_type == "atk":
                    temp_atk_bonus = random.randint(3, 8)
                    log.append(f"🎲 随机增益：攻击+{temp_atk_bonus}！")
                elif buff_type == "def":
                    temp_def_bonus = random.randint(3, 6)
                    log.append(f"🎲 随机增益：防御+{temp_def_bonus}！")
                elif buff_type == "crit_dmg":
                    _cd_bonus = random.randint(15, 30)
                    total_crit_dmg += _cd_bonus
                    log.append(f"🎲 随机增益：爆伤+{_cd_bonus}%！")
                else:
                    _rh = random.randint(5, 15)
                    old_hp = session["hp"]
                    session["hp"] = min(session["max_hp"], session["hp"] + _rh)
                    actual = session["hp"] - old_hp
                    if actual > 0:
                        log.append(f"🎲 随机增益：恢复{actual}HP！")
            effective_atk = total_atk + temp_atk_bonus
            effective_def_for_turn = total_def + temp_def_bonus
            dmg_to_monster = max(1, effective_atk - monster_def)
            # 暴击检查
            is_crit = total_crit > 0 and random.randint(1, 100) <= total_crit
            if is_crit:
                dmg_to_monster = int(dmg_to_monster * total_crit_dmg / 100)
                log.append(f"💥 暴击！({total_crit_dmg}%伤害)")
                # ── 被动: crit_heal 暴击回血 ──
                _ch = bp_passives.get("crit_heal", 0)
                if _ch > 0:
                    crit_heal_amt = max(1, int(dmg_to_monster * _ch / 100))
                    old_hp = session["hp"]
                    session["hp"] = min(session["max_hp"], session["hp"] + crit_heal_amt)
                    actual = session["hp"] - old_hp
                    if actual > 0:
                        log.append(f"💜 暴击回血+{actual}HP！")
            enc["monster_hp"] -= dmg_to_monster
            log.append(f"⚔️ 你对{enc['name']}造成{dmg_to_monster}点伤害！")
            # ── 被动: multi_strike 连击 ──
            _ms = bp_passives.get("multi_strike", 0)
            if _ms > 0 and enc["monster_hp"] > 0 and random.randint(1, 100) <= _ms:
                extra_dmg = max(1, int(dmg_to_monster * 0.7))
                enc["monster_hp"] -= extra_dmg
                log.append(f"⚡ 连击！额外造成{extra_dmg}点伤害！")
            # 精英荆棘: 反弹玩家伤害
            if elite_ability == "thorns":
                thorn_dmg = max(1, int(dmg_to_monster * 0.15))
                session["hp"] -= thorn_dmg
                log.append(f"🌵 精英荆棘反弹{thorn_dmg}点！(HP: {session['hp']}/{session['max_hp']})")
                if session["hp"] <= 0:
                    session["hp"] = 0; session["game_over"] = True; session["completed"] = True
                    log.append("💀 你被荆棘反弹击败了...")
                    return {"completed": True, "exp_earned": session["exp_earned"]}
            # 吸血检查
            if total_lifesteal > 0 and dmg_to_monster > 0:
                heal_amt = max(1, int(dmg_to_monster * total_lifesteal / 100))
                old_hp = session["hp"]
                session["hp"] = min(session["max_hp"], session["hp"] + heal_amt)
                actual_heal = session["hp"] - old_hp
                if actual_heal > 0:
                    log.append(f"🧛 吸血恢复{actual_heal}HP")
            # 被动: 每回合恢复HP
            hpt = bp_passives.get("heal_per_turn", 0)
            if hpt > 0:
                old_hp = session["hp"]
                session["hp"] = min(session["max_hp"], session["hp"] + hpt)
                actual = session["hp"] - old_hp
                if actual > 0:
                    log.append(f"💚 回春效果恢复{actual}HP")
            # 精英再生: 怪物回血
            if elite_ability == "regen" and enc["monster_hp"] > 0:
                regen_amt = max(1, int(enc["monster_max_hp"] * 0.06))
                enc["monster_hp"] = min(enc["monster_max_hp"], enc["monster_hp"] + regen_amt)
                log.append(f"💚 精英再生+{regen_amt}HP！({enc['monster_hp']}/{enc['monster_max_hp']})")
            # ── 被动: execute_pct 斩杀 ──
            _ep = bp_passives.get("execute_pct", 0)
            if _ep > 0 and enc["monster_hp"] > 0:
                m_hp_pct = enc["monster_hp"] / max(1, enc["monster_max_hp"]) * 100
                if m_hp_pct <= _ep:
                    overkill_amt = enc["monster_hp"]
                    enc["monster_hp"] = 0
                    log.append(f"💀 斩杀！直接消灭残血怪物！(HP<{_ep}%)")
            if enc["monster_hp"] <= 0:
                # ── 被动: overkill_heal 溢出回血 ──
                _oh = bp_passives.get("overkill_heal", 0)
                overkill = abs(enc["monster_hp"])
                if _oh > 0 and overkill > 0:
                    oh_amt = max(1, int(overkill * _oh / 100))
                    old_hp = session["hp"]
                    session["hp"] = min(session["max_hp"], session["hp"] + oh_amt)
                    actual = session["hp"] - old_hp
                    if actual > 0:
                        log.append(f"🩸 溢出回血+{actual}HP！")
                # 根据难度配置获取楼层经验
                difficulty = session.get("difficulty", "easy")
                cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["easy"])
                is_endless = cfg.get("endless", False)
                floor = session["floor"]
                if is_endless:
                    earned = _endless_floor_exp(floor)
                    if enc_type == "boss":
                        earned = earned * 2
                else:
                    floor_exp_list = cfg["floor_exp"]
                    earned = floor_exp_list[min(floor, len(floor_exp_list) - 1)]
                # 精英额外经验 +50%
                if enc.get("elite"):
                    earned = int(earned * 1.5)
                session["exp_earned"] += earned
                session["floors_cleared"] += 1
                session["encounter_resolved"] = True
                log.append(f"🎉 击败了{enc['name']}！获得{earned}EXP")
                # 被动: 击杀额外EXP
                bonus_exp_pct = bp_passives.get("bonus_exp_pct", 0)
                if bonus_exp_pct > 0:
                    bonus_exp = max(1, int(earned * bonus_exp_pct / 100))
                    session["exp_earned"] += bonus_exp
                    log.append(f"📖 经验宝典额外+{bonus_exp}EXP")
                # ── 被动: battle_heal 战后恢复 ──
                _bh = bp_passives.get("battle_heal", 0)
                if _bh > 0:
                    bh_amt = max(1, int(session["max_hp"] * _bh / 100))
                    old_hp = session["hp"]
                    session["hp"] = min(session["max_hp"], session["hp"] + bh_amt)
                    actual = session["hp"] - old_hp
                    if actual > 0:
                        log.append(f"🏥 战后恢复+{actual}HP！")
                return {"completed": False, "exp_earned": 0, "battle_result": "victory"}
            # ── 被动: block_chance 格挡 (在闪避之前判定) ──
            block_pct = bp_passives.get("block_chance", 0)
            if block_pct > 0 and random.randint(1, 100) <= block_pct:
                log.append(f"🛡️ 完美格挡！挡住了{enc['name']}的攻击！")
                return {"completed": False, "exp_earned": 0, "battle_result": "continue"}
            # 被动: 闪避
            dodge_pct = bp_passives.get("dodge_pct", 0) + _tb_dodge
            if dodge_pct > 0 and random.randint(1, 100) <= dodge_pct:
                log.append(f"🍀 幸运闪避！躲开了{enc['name']}的攻击！")
                return {"completed": False, "exp_earned": 0, "battle_result": "continue"}
            # 怪物攻击: 精英能力修正
            m_atk = enc["monster_attack"]
            if elite_ability == "enrage" and enc["monster_hp"] < enc["monster_max_hp"] * 0.3:
                m_atk = m_atk * 2
                log.append("🔥 精英狂暴！攻击力翻倍！")
            if elite_ability == "armor_break":
                monster_dmg = max(1, m_atk - effective_def_for_turn // 2)
                log.append("⚡ 精英破甲！无视50%防御！")
            else:
                monster_dmg = max(1, m_atk - effective_def_for_turn)
            # 楼层诅咒: 怪物增幅
            if _fc and _fc["id"] == "empowered":
                monster_dmg = int(monster_dmg * 1.3)
            # 被动: 首次受击减伤
            fhs = bp_passives.get("first_hit_shield", 0)
            if fhs > 0 and not session.get("_first_hit_used"):
                absorbed = min(fhs, monster_dmg)
                monster_dmg = max(1, monster_dmg - absorbed)
                session["_first_hit_used"] = True
                log.append(f"⚡ 先手指环吸收{absorbed}点伤害！")
            session["hp"] -= monster_dmg
            log.append(f"💥 {enc['name']}造成{monster_dmg}点伤害！(HP: {session['hp']}/{session['max_hp']})")
            # 精英吸血: 怪物回血
            if elite_ability == "vampiric" and monster_dmg > 0:
                vamp_heal = max(1, int(monster_dmg * 0.25))
                enc["monster_hp"] = min(enc["monster_max_hp"], enc["monster_hp"] + vamp_heal)
                log.append(f"🧛 精英吸血+{vamp_heal}HP！({enc['monster_hp']}/{enc['monster_max_hp']})")
            # 被动: 反弹伤害
            reflect_pct = bp_passives.get("reflect_pct", 0)
            if reflect_pct > 0 and monster_dmg > 0:
                reflect_dmg = max(1, int(monster_dmg * reflect_pct / 100))
                enc["monster_hp"] -= reflect_dmg
                log.append(f"🌵 荆棘反弹{reflect_dmg}点伤害！")
                if enc["monster_hp"] <= 0:
                    difficulty = session.get("difficulty", "easy")
                    cfg = ADVENTURE_DIFFICULTIES.get(difficulty, ADVENTURE_DIFFICULTIES["easy"])
                    is_endless = cfg.get("endless", False)
                    floor = session["floor"]
                    earned2 = _endless_floor_exp(floor) * (2 if enc_type == "boss" else 1) if is_endless else cfg["floor_exp"][min(floor, len(cfg["floor_exp"]) - 1)]
                    if enc.get("elite"):
                        earned2 = int(earned2 * 1.5)
                    session["exp_earned"] += earned2
                    session["floors_cleared"] += 1
                    session["encounter_resolved"] = True
                    log.append(f"🎉 {enc['name']}被荆棘反弹消灭了！获得{earned2}EXP")
                    return {"completed": False, "exp_earned": 0, "battle_result": "victory"}
            if session["hp"] <= 0:
                # ── 被动: revive 复活 ──
                _rev = bp_passives.get("revive", 0)
                if _rev > 0 and not session.get("_revive_used"):
                    session["_revive_used"] = True
                    session["hp"] = int(session["max_hp"] * 0.3)
                    log.append(f"🔥 凤凰重生！复活并恢复{session['hp']}HP！")
                    # 消耗背包中的复活道具
                    if bp:
                        for it in bp["items"]:
                            defn = BACKPACK_ITEMS.get(it["id"], {})
                            if defn.get("passive", {}).get("revive", 0) > 0:
                                _bp_remove(bp, it["uid"])
                                log.append(f"🪶 {defn['name']}化为灰烬...")
                                break
                    return {"completed": False, "exp_earned": 0, "battle_result": "continue"}
                session["hp"] = 0
                session["game_over"] = True
                session["completed"] = True
                log.append("💀 你被击败了...探险结束")
                return {"completed": True, "exp_earned": session["exp_earned"]}
            # ── 精英怪命中后可能附加debuff ──
            if elite_ability and elite_ability in _ELITE_COMBAT_DEBUFFS:
                _debuff_id, _debuff_chance = _ELITE_COMBAT_DEBUFFS[elite_ability]
                if random.random() < _debuff_chance:
                    _ddef = TIMED_BUFF_DEFS.get(_debuff_id)
                    if _ddef:
                        _apply_timed_buff(session, _debuff_id, 3, enc["name"])
                        log.append(f"⚠️ {enc['name']}的攻击附带了{_ddef['name']}！({_ddef['desc']}，持续3回合)")
            # ── 战斗回合结束，递减 combat scope buffs ──
            _tick_timed_buffs(session, "combat")
            return {"completed": False, "exp_earned": 0, "battle_result": "continue"}

        elif act == "use_potion":
            # 兼容旧药水计数系统
            if session["potions"] <= 0:
                raise HTTPException(status_code=400, detail="没有药水了")
            session["potions"] -= 1
            heal = 30
            session["hp"] = min(session["max_hp"], session["hp"] + heal)
            log.append(f"🧪 使用药水恢复{heal}HP！(HP: {session['hp']}/{session['max_hp']})")
            return {"completed": False, "exp_earned": 0}

        elif act == "flee":
            if random.random() < 0.5:
                session["encounter_resolved"] = True
                session["floors_cleared"] += 1
                log.append(f"🏃 成功逃离了{enc['name']}！")
                return {"completed": False, "exp_earned": 0, "battle_result": "fled"}
            monster_dmg = max(1, enc["monster_attack"] - total_def)
            session["hp"] -= monster_dmg
            log.append(f"🏃 逃跑失败！受到{monster_dmg}点伤害！(HP: {session['hp']}/{session['max_hp']})")
            if session["hp"] <= 0:
                session["hp"] = 0
                session["game_over"] = True
                session["completed"] = True
                log.append("💀 你被击败了...探险结束")
                return {"completed": True, "exp_earned": session["exp_earned"]}
            return {"completed": False, "exp_earned": 0, "battle_result": "flee_failed"}
        else:
            raise HTTPException(status_code=400, detail="怪物遭遇只能 fight、use_potion 或 flee")

    elif enc_type == "chest":
        reward = enc["reward_exp"]
        session["exp_earned"] += reward
        session["encounter_resolved"] = True
        session["floors_cleared"] += 1
        log.append(f"🎁 打开宝箱获得{reward}EXP！")
        # 25%概率获得一个临时buff
        if random.random() < 0.25:
            _chest_buffs = ["battle_fury", "stone_skin", "war_cry", "lucky_star", "regeneration", "vigor", "iron_will"]
            _cb_id = random.choice(_chest_buffs)
            _cb_def = TIMED_BUFF_DEFS[_cb_id]
            _cb_dur = 4 if _cb_def["scope"] == "combat" else 3
            _apply_timed_buff(session, _cb_id, _cb_dur, "宝箱")
            log.append(f"✨ 宝箱中涌出一股能量！获得{_cb_def['name']}（{_cb_def['desc']}，{_cb_dur}{'回合' if _cb_def['scope'] == 'combat' else '层'}）")
        # 50%概率掉落物品
        if bp and random.random() < 0.5:
            floor = session.get("floor", 1)
            drop_pool = []
            for iid, defn in BACKPACK_ITEMS.items():
                r = defn["rarity"]
                if r == "common" and floor >= 1:
                    drop_pool.append(iid)
                elif r == "uncommon" and floor >= 5:
                    drop_pool.append(iid)
                elif r == "rare" and floor >= 12:
                    drop_pool.append(iid)
            if drop_pool:
                drop_id = random.choice(drop_pool)
                uid = _bp_auto_place(bp, drop_id)
                if uid:
                    dd = BACKPACK_ITEMS[drop_id]
                    log.append(f"✨ 宝箱中发现了{dd['icon']}{dd['name']}！已放入背包")
                    if dd.get("cursed"):
                        _hint(session, "cursed", "诅咒物品属性强力但有负面效果（红框💀标记）。将🔮净化石放在旁边可抵消诅咒！")
                    if dd.get("passive"):
                        _hint(session, "passive", "带⚡被动技能的物品放入背包即自动生效，无需手动激活。战斗中自动触发！")
                    _bp_check_auto_merge(bp, log)
                else:
                    dd = BACKPACK_ITEMS[drop_id]
                    log.append(f"💔 宝箱中有{dd['icon']}{dd['name']}但背包已满")
        return {"completed": False, "exp_earned": 0}

    elif enc_type == "trap":
        if act == "disarm":
            if random.random() < 0.6:
                session["encounter_resolved"] = True
                session["floors_cleared"] += 1
                bonus = 8
                session["exp_earned"] += bonus
                log.append(f"🔧 成功拆除陷阱！获得{bonus}EXP")
                # 拆除成功有30%概率获得buff
                if random.random() < 0.3:
                    _td_buffs = ["swift_step", "iron_will", "vigor"]
                    _td_id = random.choice(_td_buffs)
                    _td_def = TIMED_BUFF_DEFS[_td_id]
                    _td_dur = 3 if _td_def["scope"] == "combat" else 2
                    _apply_timed_buff(session, _td_id, _td_dur, "陷阱拆除")
                    log.append(f"🔧 拆除经验让你获得{_td_def['name']}！（{_td_def['desc']}）")
            else:
                dmg = enc["damage"]
                session["hp"] -= dmg
                session["encounter_resolved"] = True
                session["floors_cleared"] += 1
                log.append(f"💥 拆除失败！受到{dmg}点伤害 (HP: {session['hp']}/{session['max_hp']})")
                # 拆除失败50%概率获得debuff
                if random.random() < 0.5 and session["hp"] > 0:
                    _trap_db = random.choice(_TRAP_DEBUFFS)
                    _trap_def = TIMED_BUFF_DEFS[_trap_db]
                    _trap_dur = 3 if _trap_def["scope"] == "combat" else 2
                    _apply_timed_buff(session, _trap_db, _trap_dur, "陷阱")
                    log.append(f"⚠️ 陷阱造成了{_trap_def['name']}效果！（{_trap_def['desc']}）")
                if session["hp"] <= 0:
                    session["hp"] = 0
                    session["game_over"] = True
                    session["completed"] = True
                    log.append("💀 你被陷阱击败了...探险结束")
                    return {"completed": True, "exp_earned": session["exp_earned"]}
            return {"completed": False, "exp_earned": 0}
        elif act == "bypass":
            session["encounter_resolved"] = True
            session["floors_cleared"] += 1
            log.append("🚶 小心翼翼地绕过了陷阱")
            return {"completed": False, "exp_earned": 0}
        else:
            raise HTTPException(status_code=400, detail="陷阱遭遇只能 disarm 或 bypass")

    elif enc_type == "shop":
        if act == "buy_item":
            shop_idx = action.get("shop_index")
            shop_items = enc.get("shop_items", [])
            if shop_idx is None or shop_idx < 0 or shop_idx >= len(shop_items):
                raise HTTPException(status_code=400, detail="无效的商品")
            si = shop_items[shop_idx]
            price = si["price"]
            if session["exp_earned"] < price:
                raise HTTPException(status_code=400, detail="经验值不足")
            item_id = si["item_id"]
            defn = BACKPACK_ITEMS.get(item_id)
            if not defn:
                raise HTTPException(status_code=400, detail="未知物品")
            if not bp:
                raise HTTPException(status_code=400, detail="没有背包")
            uid = _bp_auto_place(bp, item_id)
            if uid is None:
                raise HTTPException(status_code=400, detail="背包已满，请先丢弃物品")
            session["exp_earned"] -= price
            # 从商店移除已购买的物品
            shop_items.pop(shop_idx)
            log.append(f"🛒 购买了{defn['icon']}{defn['name']}（花费{price}EXP）")
            # 新机制提示
            if defn.get("cursed"):
                _hint(session, "cursed", "诅咒物品属性强力但有负面效果（红框💀标记）。将🔮净化石放在旁边可抵消诅咒！")
            if defn.get("purifier"):
                _hint(session, "purifier", "净化石放在诅咒物品旁边即可自动抵消其负面效果，无需其他操作。")
            if defn.get("passive"):
                _hint(session, "passive", "带⚡被动技能的物品放入背包即自动生效，无需手动激活。战斗中自动触发！")
            # 合成提示: 背包内已有同款可合成物品
            if item_id in MERGE_CHAINS:
                same_count = sum(1 for it in bp["items"] if it["id"] == item_id)
                if same_count >= 2:
                    _hint(session, "merge", "背包中有2个相同物品可以合成升级！选中物品后点击🔨合成按钮。")
            _bp_check_auto_merge(bp, log)
            return {"completed": False, "exp_earned": 0}
        elif act == "skip":
            session["encounter_resolved"] = True
            session["floors_cleared"] += 1
            log.append("🚶 离开了商店")
            return {"completed": False, "exp_earned": 0}
        else:
            raise HTTPException(status_code=400, detail="商店遭遇只能 buy_item 或 skip")

    elif enc_type == "blessing":
        if act == "reroll_blessing":
            reroll_count = enc.get("reroll_count", 0)
            cost = 8 + reroll_count * 8  # 8, 16, 24, ...
            if session["exp_earned"] < cost:
                raise HTTPException(status_code=400, detail=f"\u7ecf\u9a8c\u4e0d\u8db3\uff0c\u91cd\u65b0\u9009\u62e9\u9700\u8981{cost}EXP")
            session["exp_earned"] -= cost
            # \u91cd\u65b0\u968f\u673a3\u4e2a\u795d\u798f
            new_choices = _weighted_blessing_sample(ADVENTURE_BLESSINGS, 3)
            enc["choices"] = [{"id": c["id"], "name": c["name"], "desc": c["desc"], "rarity": c.get("rarity", "common")} for c in new_choices]
            enc["reroll_count"] = reroll_count + 1
            log.append(f"🎲 花费{cost}EXP重新选择祝福！")
            return {"completed": False, "exp_earned": 0}
        if act == "choose_blessing":
            blessing_id = action.get("blessing_id")
            if not blessing_id:
                raise HTTPException(status_code=400, detail="请选择一个祝福")
            # 从选项中查找
            choices = enc.get("choices", [])
            chosen = None
            for c in choices:
                if c["id"] == blessing_id:
                    chosen = c
                    break
            if not chosen:
                raise HTTPException(status_code=400, detail="无效的祝福选项")
            # 查找对应的效果
            blessing_def = None
            for b in ADVENTURE_BLESSINGS:
                if b["id"] == blessing_id:
                    blessing_def = b
                    break
            if not blessing_def:
                raise HTTPException(status_code=400, detail="无效的祝福")
            effect = blessing_def["effect"]
            # 应用效果
            if "atk" in effect:
                session["attack"] = max(1, session["attack"] + effect["atk"])
                sign = "+" if effect["atk"] >= 0 else ""
                log.append(f"{chosen['name']}：攻击{sign}{effect['atk']}")
            if "def" in effect:
                session["defense"] = max(0, session["defense"] + effect["def"])
                sign = "+" if effect["def"] >= 0 else ""
                log.append(f"{chosen['name']}：防御{sign}{effect['def']}")
            if "heal" in effect:
                old_hp = session["hp"]
                session["hp"] = min(session["max_hp"], session["hp"] + effect["heal"])
                actual = session["hp"] - old_hp
                log.append(f"{chosen['name']}：恢复{actual}HP")
            if effect.get("heal_full"):
                old_hp = session["hp"]
                session["hp"] = session["max_hp"]
                actual = session["hp"] - old_hp
                if actual > 0:
                    log.append(f"{chosen['name']}：恢复全部HP(+{actual})")
            if "max_hp" in effect:
                delta = effect["max_hp"]
                session["base_max_hp"] = session.get("base_max_hp", session["max_hp"]) + delta
                session["max_hp"] += delta
                if delta > 0:
                    session["hp"] += delta
                else:
                    session["hp"] = min(session["hp"], session["max_hp"])
                sign = "+" if delta >= 0 else ""
                log.append(f"{chosen['name']}：最大HP{sign}{delta}")
            if "potions" in effect:
                bp = session.get("backpack")
                count = effect["potions"]
                placed = 0
                if bp:
                    for _ in range(count):
                        uid = _bp_auto_place(bp, "small_potion")
                        if uid is not None:
                            placed += 1
                if placed > 0:
                    log.append(f"{chosen['name']}：获得{placed}瓶药水（已放入背包）")
                if placed < count:
                    leftover = count - placed
                    log.append(f"⚠️ 背包空间不足，{leftover}瓶药水丢失了！")
            if "crit" in effect:
                current_crit = session.get("crit_chance", 0)
                add_crit = effect["crit"]
                if current_crit >= 100:
                    bonus_crit_dmg = int(add_crit / 15 * 20)
                    session["crit_damage"] = session.get("crit_damage", 180) + bonus_crit_dmg
                    log.append(f"{chosen['name']}：暴击率已满！转化为爆伤+{bonus_crit_dmg}%（当前{session['crit_damage']}%）")
                elif current_crit + add_crit > 100:
                    overflow = current_crit + add_crit - 100
                    session["crit_chance"] = 100
                    bonus_crit_dmg = int(overflow / 15 * 20)
                    session["crit_damage"] = session.get("crit_damage", 180) + bonus_crit_dmg
                    log.append(f"{chosen['name']}：暴击率→100%！溢出转化爆伤+{bonus_crit_dmg}%")
                else:
                    session["crit_chance"] = current_crit + add_crit
                    log.append(f"{chosen['name']}：暴击率+{add_crit}%")
            if "crit_damage" in effect:
                session["crit_damage"] = session.get("crit_damage", 180) + effect["crit_damage"]
                log.append(f"{chosen['name']}：爆伤+{effect['crit_damage']}%")
            if "lifesteal" in effect:
                session["lifesteal"] = session.get("lifesteal", 0) + effect["lifesteal"]
                log.append(f"{chosen['name']}：吸血+{effect['lifesteal']}%")
            if "exp_grant" in effect:
                session["exp_earned"] += effect["exp_grant"]
                log.append(f"{chosen['name']}：获得{effect['exp_grant']}EXP")
            if "grant_passive" in effect:
                # 永久增加被动属性到session层面（不受背包影响）
                sp = session.setdefault("blessing_passives", {})
                for pk, pv in effect["grant_passive"].items():
                    sp[pk] = sp.get(pk, 0) + pv
                log.append(f"{chosen['name']}：获得永久被动效果！")
            if "grant_timed" in effect:
                gt = effect["grant_timed"]
                _apply_timed_buff(session, gt["id"], gt["turns"], chosen["name"])
                _gtdef = TIMED_BUFF_DEFS.get(gt["id"], {})
                log.append(f"{chosen['name']}：获得{_gtdef.get('name', '')} {_gtdef.get('desc', '')}（持续{gt['turns']}{'回合' if _gtdef.get('scope') == 'combat' else '层'}）")
            if effect.get("random_mega"):
                # 赌徒的命运：随机一项大幅增益
                mega_options = [
                    ("攻击+18", lambda s: s.__setitem__("attack", s["attack"] + 18)),
                    ("防御+15", lambda s: s.__setitem__("defense", s["defense"] + 15)),
                    ("最大HP+80", lambda s: (s.__setitem__("base_max_hp", s.get("base_max_hp", s["max_hp"]) + 80), s.__setitem__("max_hp", s["max_hp"] + 80), s.__setitem__("hp", s["hp"] + 80))),
                    ("暴击率+25%", lambda s: s.__setitem__("crit_chance", min(100, s.get("crit_chance", 0) + 25))),
                    ("吸血+30%", lambda s: s.__setitem__("lifesteal", s.get("lifesteal", 0) + 30)),
                    ("爆伤+50%", lambda s: s.__setitem__("crit_damage", s.get("crit_damage", 180) + 50)),
                ]
                desc, fn = random.choice(mega_options)
                fn(session)
                log.append(f"{chosen['name']}：🎰 命运转轮… {desc}！")
            # 记录已获得的祝福（累计计数）
            buffs = session.get("buffs", {})
            if isinstance(buffs, list):
                migrated = {}
                for b in buffs:
                    migrated[b] = migrated.get(b, 0) + 1
                buffs = migrated
            buffs[chosen["name"]] = buffs.get(chosen["name"], 0) + 1
            session["buffs"] = buffs
            session["encounter_resolved"] = True
            session["floors_cleared"] += 1
            return {"completed": False, "exp_earned": 0, "blessing_applied": chosen["name"]}
        else:
            raise HTTPException(status_code=400, detail="祝福遭遇只能 choose_blessing")

    raise HTTPException(status_code=400, detail="未知遭遇类型")
