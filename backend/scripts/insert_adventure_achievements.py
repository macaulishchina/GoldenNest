"""Insert missing adventure achievements into the database."""
import sqlite3
from datetime import datetime

DB_PATH = '/data/golden_nest.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

now = datetime.utcnow().isoformat()

achievements = [
    ('adventure_clear_easy', '初出茅庐', '通关入门难度探险', 'adventure', '🏕️', 'common', 15, 0, 'adventure_clear', 'easy'),
    ('adventure_clear_medium', '勇往直前', '通关中等难度探险', 'adventure', '⚔️', 'rare', 30, 0, 'adventure_clear', 'medium'),
    ('adventure_clear_hard', '身经百战', '通关困难难度探险', 'adventure', '🛡️', 'epic', 60, 0, 'adventure_clear', 'hard'),
    ('adventure_clear_expert', '绝世高手', '通关专家难度探险', 'adventure', '👑', 'legendary', 120, 0, 'adventure_clear', 'expert'),
    ('adventure_endless_10', '深入地下', '无尽模式到达第 10 层', 'adventure', '🔟', 'common', 20, 0, 'adventure_endless_floor', '10'),
    ('adventure_endless_50', '地下探索者', '无尽模式到达第 50 层', 'adventure', '🗺️', 'rare', 50, 0, 'adventure_endless_floor', '50'),
    ('adventure_endless_100', '百层勇者', '无尽模式到达第 100 层', 'adventure', '🏔️', 'epic', 100, 0, 'adventure_endless_floor', '100'),
    ('adventure_endless_200', '深渊行者', '无尽模式到达第 200 层', 'adventure', '🌋', 'epic', 200, 0, 'adventure_endless_floor', '200'),
    ('adventure_endless_500', '传说冒险家', '无尽模式到达第 500 层', 'adventure', '🌌', 'legendary', 500, 0, 'adventure_endless_floor', '500'),
    ('adventure_endless_1000', '永恒征服者', '无尽模式到达第 1000 层', 'adventure', '✨', 'mythic', 1000, 0, 'adventure_endless_floor', '1000'),
]

inserted = 0
for a in achievements:
    c.execute('SELECT 1 FROM achievements WHERE code=?', (a[0],))
    if not c.fetchone():
        c.execute(
            "INSERT INTO achievements (code, name, description, category, icon, rarity, points, is_hidden, trigger_type, trigger_value, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (*a, now)
        )
        inserted += 1
        print(f'  Inserted: {a[0]}')

conn.commit()
print(f'Done. Inserted {inserted} adventure achievements.')

c.execute('SELECT COUNT(*) FROM achievements')
print(f'Total: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM achievements WHERE category='adventure'")
print(f'Adventure: {c.fetchone()[0]}')
conn.close()
