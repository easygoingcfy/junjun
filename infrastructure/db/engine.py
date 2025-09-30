import os
import sqlite3
from contextlib import contextmanager

# TODO
# - 后续可扩展为SQLAlchemy引擎与连接池
# - 从 config.local.toml/env 读取数据库路径

def _db_path() -> str:
    # 优先读环境变量，其次默认项目根的 stock_data.db
    return os.environ.get("APP_DB_PATH", "stock_data.db")


def _configure_sqlite(conn: sqlite3.Connection) -> None:
    # 基本性能/一致性设置
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-20000;")  # 约 20MB page cache
    except Exception:
        pass


def get_connection() -> sqlite3.Connection:
    """
    返回底层SQLite连接。
    - 默认超时 30s，防止锁等待过早失败
    - 应用若干 PRAGMA 提升并发读写体验
    """
    conn = sqlite3.connect(_db_path(), timeout=30)
    _configure_sqlite(conn)
    return conn


@contextmanager
def get_session():
    """
    简易“会话”上下文，提交/回滚封装。
    使用方式：
        with get_session() as conn:
            conn.execute(...)
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
