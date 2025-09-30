import sqlite3

class Database:
    def __init__(self, db_path="stock_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def _column_exists(self, table: str, column: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cur.fetchall())

    def _ensure_column(self, table: str, column: str, col_def: str):
        if not self._column_exists(table, column):
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")

    def create_tables(self):
        cursor = self.conn.cursor()
        # 股票基本信息
        cursor.execute('''
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
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_info_ts_code ON stock_info (ts_code)')

        # 日线行情
        cursor.execute('''
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
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_kline_ts_code_date ON daily_kline (ts_code, trade_date)')

        # 迁移：为已有表补充新增列
        # stock_info 新增列
        for col, col_def in [
            ("market", "TEXT"),
            ("exchange", "TEXT"),
            ("area", "TEXT"),
            ("is_st", "INTEGER DEFAULT 0"),
            ("list_status", "TEXT"),
        ]:
            self._ensure_column("stock_info", col, col_def)
        # daily_kline 新增列
        for col, col_def in [
            ("pre_close", "REAL"),
            ("amplitude", "REAL"),
            ("volume_ratio", "REAL"),
            ("circ_mv", "REAL"),
            ("total_mv", "REAL"),
        ]:
            self._ensure_column("daily_kline", col, col_def)

        self.conn.commit()

    def close(self):
        self.conn.close()