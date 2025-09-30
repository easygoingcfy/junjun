import pandas as pd
from db.database import Database


class DataSaver:
    def __init__(self, db: Database):
        self.db = db

    def save_stock_list(self, stock_df: pd.DataFrame):
        cursor = self.db.conn.cursor()
        for _, row in stock_df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO stock_info (ts_code, name, industry, list_date, market, exchange, area, is_st, list_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('ts_code'),
                row.get('name', ''),
                row.get('industry', ''),
                row.get('list_date', ''),
                row.get('market', ''),
                row.get('exchange', ''),
                row.get('area', ''),
                int(row.get('is_st', 0)) if str(row.get('is_st', '0')).isdigit() else 0,
                row.get('list_status', '')
            ))
        self.db.conn.commit()

    def save_daily_kline(self, ts_code: str, kline_df: pd.DataFrame):
        cursor = self.db.conn.cursor()
        for _, row in kline_df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO daily_kline
                (ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, turnover_rate, pre_close, amplitude, volume_ratio, circ_mv, total_mv)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts_code,
                row.get('trade_date'),
                row.get('open'),
                row.get('high'),
                row.get('low'),
                row.get('close'),
                row.get('vol'),
                row.get('amount'),
                row.get('pct_chg'),
                row.get('turnover_rate'),
                row.get('pre_close'),
                row.get('amplitude'),
                row.get('volume_ratio'),
                row.get('circ_mv'),
                row.get('total_mv'),
            ))
        self.db.conn.commit()

    # 新增：批量保存日线（按交易日批量抓取后直接写入）
    def bulk_save_daily_kline(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        records = [(
            row.get('ts_code'), row.get('trade_date'), row.get('open'), row.get('high'), row.get('low'),
            row.get('close'), row.get('vol'), row.get('amount'), row.get('pct_chg'), row.get('turnover_rate'),
            row.get('pre_close'), row.get('amplitude'), row.get('volume_ratio'), row.get('circ_mv'), row.get('total_mv')
        ) for _, row in df.iterrows()]
        cursor = self.db.conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO daily_kline
            (ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, turnover_rate, pre_close, amplitude, volume_ratio, circ_mv, total_mv)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        self.db.conn.commit()

    # Concept, board, heat related persistence removed to keep data lean.