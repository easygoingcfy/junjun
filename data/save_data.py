import pandas as pd
from db.database import Database

class DataSaver:
    def __init__(self, db: Database):
        self.db = db

    def save_stock_list(self, stock_df: pd.DataFrame):
        cursor = self.db.conn.cursor()
        for _, row in stock_df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO stock_info (ts_code, name, industry, list_date)
                VALUES (?, ?, ?, ?)
            ''', (
                row['ts_code'],
                row.get('name', ''),
                row.get('industry', ''),
                row.get('list_date', '')
            ))
        self.db.conn.commit()

    def save_daily_kline(self, ts_code: str, kline_df: pd.DataFrame):
        cursor = self.db.conn.cursor()
        for _, row in kline_df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO daily_kline
                (ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, turnover_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts_code,
                row['trade_date'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['vol'],
                row['amount'],
                row['pct_chg'],
                row['turnover_rate']
            ))
        self.db.conn.commit()