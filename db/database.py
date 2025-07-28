import sqlite3

class Database:
    def __init__(self, db_path="stock_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # 股票基本信息
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_info (
            ts_code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            list_date TEXT
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
            UNIQUE(ts_code, trade_date)
        )
        ''')
        self.conn.commit()

    def close(self):
        self.conn.close()