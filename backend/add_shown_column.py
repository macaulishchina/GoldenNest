"""
一次性脚本：为 user_achievement 表添加 shown 列
运行方式: cd backend && python add_shown_column.py
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "golden_nest.db")

def add_shown_column():
    """添加 shown 列到 user_achievement 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(user_achievements)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'shown' in columns:
            print("✓ shown 列已存在，无需添加")
        else:
            # 添加 shown 列，默认值为 1 (True)，表示已有成就都已展示
            cursor.execute("ALTER TABLE user_achievements ADD COLUMN shown BOOLEAN DEFAULT 1")
            conn.commit()
            print("✓ 成功添加 shown 列到 user_achievements 表")
            
            # 可选：将所有现有记录标记为已展示
            cursor.execute("UPDATE user_achievements SET shown = 1 WHERE shown IS NULL")
            conn.commit()
            print("✓ 已将所有现有成就标记为已展示")
            
    except Exception as e:
        print(f"✗ 错误: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_shown_column()
