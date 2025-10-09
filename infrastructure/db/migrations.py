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
            
            # 行业统计表
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS industry_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    industry TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    total_volume REAL,
                    avg_volume REAL,
                    total_amount REAL,
                    avg_amount REAL,
                    avg_pct_chg REAL,
                    max_pct_chg REAL,
                    min_pct_chg REAL,
                    stock_count INTEGER,
                    rising_count INTEGER,
                    falling_count INTEGER,
                    UNIQUE(industry, trade_date)
                )
                """
            )
            cur.execute('CREATE INDEX IF NOT EXISTS idx_industry_stats_industry_date ON industry_stats (industry, trade_date)')
            
        # 股票日统计表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                volume REAL,
                amount REAL,
                pct_chg REAL,
                turnover_rate REAL,
                amplitude REAL,
                UNIQUE(ts_code, trade_date)
            )
            """
        )
        cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_daily_stats_code_date ON stock_daily_stats (ts_code, trade_date)')
        
        # 行业指数表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS industry_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_code TEXT NOT NULL,
                index_name TEXT NOT NULL,
                industry_name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                src TEXT DEFAULT 'SW',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(index_code)
            )
            """
        )
        cur.execute('CREATE INDEX IF NOT EXISTS idx_industry_index_code ON industry_index (index_code)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_industry_index_name ON industry_index (industry_name)')
        
        # 行业指数日线数据表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS industry_index_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                pre_close REAL,
                change REAL,
                pct_chg REAL,
                vol REAL,
                amount REAL,
                UNIQUE(index_code, trade_date)
            )
            """
        )
        cur.execute('CREATE INDEX IF NOT EXISTS idx_industry_index_daily_code_date ON industry_index_daily (index_code, trade_date)')
        
        # 行业成分股表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS industry_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_code TEXT NOT NULL,
                ts_code TEXT NOT NULL,
                con_date TEXT,
                is_new INTEGER DEFAULT 0,
                UNIQUE(index_code, ts_code)
            )
            """
        )
        cur.execute('CREATE INDEX IF NOT EXISTS idx_industry_members_index ON industry_members (index_code)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_industry_members_stock ON industry_members (ts_code)')

    def downgrade(self):
        # 简化实现：不执行回滚
        pass
