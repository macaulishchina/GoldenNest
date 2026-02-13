import math

def _calc_dominance_scaling(floor, player_stats=None):
    result = {"hp_mult": 1.0, "atk_mult": 1.0, "def_mult": 1.0, "active": False}
    if not player_stats or floor < 10:
        return result
    lagged_dps = player_stats.get("scaling_dps", 0)
    p_def = player_stats.get("defense", 0)
    if lagged_dps <= 0:
        return result
    enemy_baseline = 4 + floor * 0.7 + (floor ** 0.5) * 2
    player_power = lagged_dps + p_def * 0.5
    dominance_ratio = player_power / max(1, enemy_baseline)
    threshold = 2.5 if floor < 30 else 2.0 if floor < 60 else 1.8
    if dominance_ratio <= threshold:
        return result
    excess = dominance_ratio - threshold
    k_hp = 0.15 + min(0.30, floor * 0.003)
    k_atk = 0.10 + min(0.20, floor * 0.002)
    k_def = 0.08 + min(0.15, floor * 0.0015)
    log_factor = math.log1p(excess)
    hp_mult = min(1.0 + k_hp * log_factor, 6.0)
    atk_mult = min(1.0 + k_atk * log_factor, 3.5)
    def_mult = min(1.0 + k_def * log_factor, 3.0)
    result.update({"hp_mult": hp_mult, "atk_mult": atk_mult, "def_mult": def_mult, "active": True})
    return result

test_cases = [
    ("F5, low dps", 5, {"scaling_dps": 30, "defense": 5}),
    ("F10, normal", 10, {"scaling_dps": 40, "defense": 8}),
    ("F10, strong", 10, {"scaling_dps": 200, "defense": 20}),
    ("F30, normal", 30, {"scaling_dps": 80, "defense": 15}),
    ("F30, 5x strong", 30, {"scaling_dps": 400, "defense": 50}),
    ("F30, 20x strong", 30, {"scaling_dps": 1500, "defense": 100}),
    ("F60, 10x strong", 60, {"scaling_dps": 1000, "defense": 80}),
    ("F60, 50x strong", 60, {"scaling_dps": 5000, "defense": 200}),
    ("F100, 20x strong", 100, {"scaling_dps": 3000, "defense": 150}),
    ("F100, 100x strong", 100, {"scaling_dps": 15000, "defense": 500}),
]

print(f"{'Scenario':<22} {'Floor':>5} {'DPS':>6} {'Def':>4} {'Dom':>6} {'HP*':>6} {'ATK*':>6} {'DEF*':>6} {'Active'}")
print("-" * 80)
for name, f, ps in test_cases:
    d = _calc_dominance_scaling(f, ps)
    baseline = 4 + f * 0.7 + (f**0.5) * 2
    pp = ps["scaling_dps"] + ps["defense"] * 0.5
    dom = pp / baseline
    print(f"{name:<22} {f:>5} {ps['scaling_dps']:>6} {ps['defense']:>4} {dom:>6.1f} {d['hp_mult']:>6.2f} {d['atk_mult']:>6.2f} {d['def_mult']:>6.2f} {d['active']}")
