# 数据库自动迁移指南

## 🎯 功能说明

Golden Nest 的 Backend 内置了**自动数据库迁移**功能，当你修改模型定义时，系统会在启动时自动同步数据库schema。

## ✨ 支持的操作

### ✅ 自动支持（安全）
- **添加新表** - 定义新的模型类
- **添加新列** - 在现有模型中添加新字段
- **修改列的可空性** - `nullable=True/False` (仅限添加时)
- **设置默认值** - 新列的 `default` 值

### ⚠️ 不支持（需要手动操作）
- ❌ 删除表
- ❌ 删除列
- ❌ 修改列类型（如 VARCHAR → TEXT）
- ❌ 重命名表或列
- ❌ 添加索引或约束（除主键外）

## 📝 使用示例

### 示例1：添加新字段

**修改前** (`backend/app/models/models.py`):
```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100))
```

**修改后** - 添加 `avatar` 字段:
```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100))
    avatar: Mapped[str] = mapped_column(String(255), nullable=True)  # 新增
```

**操作步骤**:
1. 保存模型文件
2. 重启backend（`run.bat` 或 `run.sh`）
3. 查看控制台输出：
   ```
   [auto-migrate] ALTER TABLE users ADD COLUMN avatar VARCHAR(255) NULL
   🏠 小金库数据库初始化完成！
   ```

### 示例2：添加新表

**新增模型** (`backend/app/models/models.py`):
```python
class Setting(Base):
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**操作步骤**:
1. 保存模型文件
2. 重启backend
3. 新表自动创建，无需额外操作

### 示例3：带默认值的字段

```python
class Family(Base):
    __tablename__ = "family"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    
    # 添加新字段，带默认值
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 新增
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")  # 新增
```

**重启后自动执行**:
```sql
ALTER TABLE family ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1
ALTER TABLE family ADD COLUMN description TEXT NULL DEFAULT ''
```

## 🔧 工作原理

### 启动流程
```
Backend启动
    ↓
app.main.py → lifespan → init_db()
    ↓
1. Base.metadata.create_all()  # 创建新表
    ↓
2. _auto_migrate_columns()     # 添加缺失列
    ↓
比对 ORM模型 vs 实际表结构
    ↓
生成并执行 ALTER TABLE ADD COLUMN 语句
    ↓
完成初始化
```

### 实现代码位置
- **主逻辑**: `backend/app/core/database.py`
  - `init_db()` - 数据库初始化入口
  - `_auto_migrate_columns()` - 自动添加列的核心逻辑

## ⚠️ 注意事项

### 1. 数据安全
- ✅ 自动迁移**只添加**，不删除或修改
- ✅ 现有数据完全保留
- ⚠️ 建议定期备份数据库文件

### 2. 类型限制
- 主要支持 SQLite 基础类型
- 复杂类型可能需要手动处理

### 3. 默认值限制
- Python callable 默认值（如 `datetime.utcnow`）在数据库层面不生效
- 需要在应用层处理或使用 SQLite 支持的字面值

### 4. 性能考虑
- 检查是快速操作（毫秒级）
- 添加列的开销取决于表大小
- 大表添加 NOT NULL 列可能较慢

## 🛠️ 手动迁移指南

### 场景1：删除字段
SQLite 不支持 `DROP COLUMN`，需要重建表：

```sql
-- 1. 备份数据
CREATE TABLE users_backup AS SELECT * FROM users;

-- 2. 删除原表
DROP TABLE users;

-- 3. 重新创建表（去掉不需要的列）
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100)
    -- 不包含被删除的列
);

-- 4. 恢复数据
INSERT INTO users (id, username, email)
SELECT id, username, email FROM users_backup;

-- 5. 删除备份
DROP TABLE users_backup;
```

### 场景2：修改列类型
同样需要重建表：

```sql
-- 1. 创建新表（新列类型）
CREATE TABLE users_new (
    id INTEGER PRIMARY KEY,
    username VARCHAR(100),  -- 从 VARCHAR(50) 改为 VARCHAR(100)
    email VARCHAR(100)
);

-- 2. 迁移数据
INSERT INTO users_new SELECT * FROM users;

-- 3. 替换表
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;
```

### 场景3：重命名列
```sql
-- SQLite 3.25+ 支持
ALTER TABLE users RENAME COLUMN old_name TO new_name;

-- 旧版本需要重建表
```

## 📊 数据库备份

### 快速备份
```cmd
# Windows
copy backend\golden_nest.db backend\golden_nest.db.backup

# Linux/macOS
cp backend/golden_nest.db backend/golden_nest.db.backup
```

### 定期备份策略
```bash
# 创建带时间戳的备份
# Linux/macOS
cp backend/golden_nest.db "backend/backups/golden_nest_$(date +%Y%m%d_%H%M%S).db"

# Windows PowerShell
Copy-Item backend\golden_nest.db "backend\backups\golden_nest_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
```

### 恢复备份
```cmd
# 停止backend服务
# 然后恢复
copy backend\golden_nest.db.backup backend\golden_nest.db
```

## 🔍 数据库工具推荐

### GUI 工具
1. **DB Browser for SQLite** (推荐)
   - 官网: https://sqlitebrowser.org/
   - 免费、开源、跨平台
   - 可视化查看/编辑表结构和数据

2. **DBeaver Community**
   - 支持多种数据库
   - 功能强大的SQL编辑器

### 命令行工具
```cmd
# SQLite CLI (随SQLite安装)
sqlite3 backend/golden_nest.db

# 常用命令
.tables              # 列出所有表
.schema users        # 查看表结构
.mode column         # 格式化输出
.headers on          # 显示列名
SELECT * FROM users; # 查询数据
.quit                # 退出
```

## 💡 最佳实践

1. **修改模型前先备份数据库**
   ```bash
   cp backend/golden_nest.db backend/golden_nest.db.backup
   ```

2. **每次重启查看迁移日志**
   ```
   [auto-migrate] ALTER TABLE xxx ADD COLUMN yyy
   ```

3. **测试环境先验证**
   - 在测试环境尝试迁移
   - 确认无误后再应用到生产环境

4. **避免频繁修改表结构**
   - 一次性规划好字段
   - 减少迁移次数

5. **复杂迁移使用版本控制**
   - 记录手动迁移的SQL脚本
   - 便于回滚和审计

## 🔗 相关文件

- `backend/app/core/database.py` - 数据库配置和迁移逻辑
- `backend/app/models/models.py` - 数据模型定义
- `backend/golden_nest.db` - SQLite 数据库文件
- `RUN_SCRIPTS_GUIDE.md` - 启动脚本使用指南
