from infrastructure.db.engine import get_session

# TODO
# - 简化的迁移：仅确保必须的表存在
# - 后续可接入 Alembic 或自定义版本表


class MigrationManager:
    def upgrade(self):
        with get_session() as conn:
            cur = conn.cursor()
            # stock_info
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_info (
                    ts_code TEXT PRIMARY KEY,
                    name TEXT,
                    industry TEXT,
                    list_date TEXT,
                    market TEXT,
                    exchange TEXT,
                    area TEXT,
                    is_st INTEGER DEFAULT 0,
                    list_status TEXT
                )
                """
            )
            cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_info_ts_code ON stock_info (ts_code)')

            # daily_kline
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_kline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    vol REAL,
                    amount REAL,
                    pct_chg REAL,
                    turnover_rate REAL,
                    pre_close REAL,
                    amplitude REAL,
                    volume_ratio REAL,
                    circ_mv REAL,
                    total_mv REAL,
                    UNIQUE(ts_code, trade_date)
                )
                """
            )
            cur.execute('CREATE INDEX IF NOT EXISTS idx_daily_kline_ts_code_date ON daily_kline (ts_code, trade_date)')

            # strategy & signals (占位)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    version TEXT,
                    params TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    score REAL,
                    payload TEXT
                )
                """
            )

    def downgrade(self):
        # 简化实现：不执行回滚
        pass
