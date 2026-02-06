"""
小金库 (Golden Nest) - 数据库配置
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # 开发模式下打印SQL
    future=True
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


# 基础模型类
class Base(DeclarativeBase):
    pass


# 获取数据库会话的依赖
async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 初始化数据库（创建所有表 + 自动迁移新列）
async def init_db():
    async with engine.begin() as conn:
        # 1. 创建新表（已有表不受影响）
        await conn.run_sync(Base.metadata.create_all)
        # 2. 自动添加缺失的列到已有表
        await conn.run_sync(_auto_migrate_columns)


def _auto_migrate_columns(connection):
    """比对 ORM 模型与实际表结构，自动 ALTER TABLE ADD COLUMN 缺失列。
    仅做加列操作，不会删列、改类型或重命名，安全性高。"""
    from sqlalchemy import inspect, text

    inspector = inspect(connection)
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue  # 新表已由 create_all 处理

        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}

        for column in table.columns:
            if column.name in existing_cols:
                continue

            # 推断 SQLite 列类型
            col_type = column.type.compile(dialect=connection.dialect)
            nullable = "NULL" if column.nullable else "NOT NULL"
            default = ""
            if column.default is not None:
                val = column.default.arg
                if callable(val):
                    default = ""  # 跳过 Python 可调用默认值，SQLite 不支持
                elif isinstance(val, str):
                    default = f"DEFAULT '{val}'"
                elif isinstance(val, bool):
                    default = f"DEFAULT {1 if val else 0}"
                elif val is not None:
                    default = f"DEFAULT {val}"

            # nullable 列不需要 DEFAULT 即可安全添加
            stmt = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {col_type} {nullable} {default}'
            connection.execute(text(stmt.strip()))
            print(f"[auto-migrate] ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}")
