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
        # 概念表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS concept (
            concept_code TEXT PRIMARY KEY,
            name TEXT,
            source TEXT,
            description TEXT
        )
        ''')
        # 概念-成分股关系
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS concept_member (
            concept_code TEXT,
            ts_code TEXT,
            in_date TEXT,
            out_date TEXT,
            PRIMARY KEY(concept_code, ts_code)
        )
        ''')
        # 板块/指数表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS board (
            board_code TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            source TEXT
        )
        ''')
        # 板块/指数成分
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS board_member (
            board_code TEXT,
            ts_code TEXT,
            in_date TEXT,
            out_date TEXT,
            weight REAL,
            PRIMARY KEY(board_code, ts_code)
        )
        ''')
        # 板块/指数日线快照（用于板块热度）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS board_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_code TEXT,
            date TEXT,
            close REAL,
            pct_chg REAL,
            vol REAL,
            amount REAL,
            UNIQUE(board_code, date)
        )
        ''')
        # 热度/情绪快照
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS heat_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code TEXT,
            date TEXT,
            source TEXT,
            news_count INTEGER,
            search_score REAL,
            forum_count INTEGER,
            sentiment REAL,
            board_hotness REAL,
            UNIQUE(ts_code, date, source)
        )
        ''')

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