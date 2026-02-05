"""
一次性脚本：为 families 表添加通知配置列
运行方式: cd backend && python add_notification_columns.py
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "golden_nest.db")

def add_notification_columns():
    """添加通知配置列到 families 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='families'")
        if not cursor.fetchone():
            print("✗ 错误: families 表不存在")
            return
        
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(families)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 添加 wechat_webhook_url 列
        if 'wechat_webhook_url' in columns:
            print("✓ wechat_webhook_url 列已存在，无需添加")
        else:
            cursor.execute("ALTER TABLE families ADD COLUMN wechat_webhook_url VARCHAR(500)")
            conn.commit()
            print("✓ 成功添加 wechat_webhook_url 列到 families 表")
        
        # 添加 notification_enabled 列
        if 'notification_enabled' in columns:
            print("✓ notification_enabled 列已存在，无需添加")
        else:
            cursor.execute("ALTER TABLE families ADD COLUMN notification_enabled BOOLEAN DEFAULT 1")
            conn.commit()
            print("✓ 成功添加 notification_enabled 列到 families 表")
            
            # 将所有现有记录设置默认值
            cursor.execute("UPDATE families SET notification_enabled = 1 WHERE notification_enabled IS NULL")
            conn.commit()
            print("✓ 已将所有现有家庭的通知设置为启用")
            
    except Exception as e:
        print(f"✗ 错误: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_notification_columns()
