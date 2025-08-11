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

    def save_concepts(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        cur = self.db.conn.cursor()
        for _, row in df.iterrows():
            cur.execute('''
                INSERT OR REPLACE INTO concept (concept_code, name, source, description)
                VALUES (?, ?, ?, ?)
            ''', (
                row.get('concept_code'), row.get('name'), row.get('source', ''), row.get('description', '')
            ))
        self.db.conn.commit()

    def save_concept_members(self, df: pd.DataFrame, concept_code: str = None):
        if df is None or df.empty:
            return
        cur = self.db.conn.cursor()
        if 'ts_code' in df.columns:
            for _, row in df.iterrows():
                cur.execute('''
                    INSERT OR REPLACE INTO concept_member (concept_code, ts_code, in_date, out_date)
                    VALUES (?, ?, ?, ?)
                ''', (
                    concept_code or row.get('concept_code'), row.get('ts_code'), row.get('in_date', ''), row.get('out_date', '')
                ))
        self.db.conn.commit()

    def save_boards(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        cur = self.db.conn.cursor()
        for _, row in df.iterrows():
            cur.execute('''
                INSERT OR REPLACE INTO board (board_code, name, type, source)
                VALUES (?, ?, ?, ?)
            ''', (row.get('board_code'), row.get('name'), row.get('type'), row.get('source', '')))
        self.db.conn.commit()

    def save_board_members(self, board_code: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        cur = self.db.conn.cursor()
        for _, row in df.iterrows():
            cur.execute('''
                INSERT OR REPLACE INTO board_member (board_code, ts_code, in_date, out_date, weight)
                VALUES (?, ?, ?, ?, ?)
            ''', (board_code, row.get('ts_code'), row.get('in_date', ''), row.get('out_date', ''), row.get('weight')))
        self.db.conn.commit()

    def save_board_daily(self, board_code: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        cur = self.db.conn.cursor()
        for _, row in df.iterrows():
            cur.execute('''
                INSERT OR REPLACE INTO board_daily (board_code, date, close, pct_chg, vol, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                board_code, row.get('date'), row.get('close'), row.get('pct_chg'), row.get('vol'), row.get('amount')
            ))
        self.db.conn.commit()

    def save_heat_data(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        cur = self.db.conn.cursor()
        for _, row in df.iterrows():
            cur.execute('''
                INSERT OR REPLACE INTO heat_data (ts_code, date, source, news_count, search_score, forum_count, sentiment, board_hotness)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('ts_code'), row.get('date'), row.get('source', ''), row.get('news_count'),
                row.get('search_score'), row.get('forum_count'), row.get('sentiment'), row.get('board_hotness')
            ))
        self.db.conn.commit()

    # 新增：批量保存热度（可选）
    def bulk_save_heat_data(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        records = [(
            row.get('ts_code'), row.get('date'), row.get('source', ''), row.get('news_count'),
            row.get('search_score'), row.get('forum_count'), row.get('sentiment'), row.get('board_hotness')
        ) for _, row in df.iterrows()]
        cur = self.db.conn.cursor()
        cur.executemany('''
            INSERT OR REPLACE INTO heat_data (ts_code, date, source, news_count, search_score, forum_count, sentiment, board_hotness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        self.db.conn.commit()