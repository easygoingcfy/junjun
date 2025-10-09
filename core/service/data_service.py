from typing import Iterable
import pandas as pd
from core.dao.repositories import StockRepository
from data.fetcher import DataFetcher


class DataService:
    """数据同步服务(最小实现)"""
    def __init__(self, fetcher: DataFetcher | None = None, stock_repo: StockRepository | None = None):
        self.fetcher = fetcher or DataFetcher()
        self.stock_repo = stock_repo or StockRepository()

    def refresh_stock_list(self) -> int:
        """
        拉取股票列表并落库，返回写入数量。
        - 优先从TuShare/akshare获取；若失败则返回0
        """
        df: pd.DataFrame = self.fetcher.fetch_stock_list()
        if df is None or df.empty:
            return 0
        # 统一列
        df['ts_code'] = df['ts_code'].astype(str).str.split('.').str[0]
        records = df.to_dict(orient='records')
        self.stock_repo.save_many(records)
        return len(records)

    def update_kline_range(self, codes: Iterable[str], start: str, end: str) -> int:
        """
        占位：增量更新日线。
        当前最小实现仅返回0，后续接入 fetcher.fetch_daily_kline 并落库。
        """
        return 0
    
    def calculate_industry_stats(self, trade_date: str) -> int:
        """计算指定日期的行业统计数据"""
        from infrastructure.db.engine import get_session
        
        with get_session() as conn:
            # 获取所有行业
            industries = conn.execute("SELECT DISTINCT industry FROM stock_info WHERE industry IS NOT NULL AND industry != ''").fetchall()
            
            count = 0
            for (industry,) in industries:
                # 计算该行业当日的统计数据
                stats_query = """
                SELECT 
                    COUNT(*) as stock_count,
                    SUM(dk.vol) as total_volume,
                    AVG(dk.vol) as avg_volume,
                    SUM(dk.amount) as total_amount,
                    AVG(dk.amount) as avg_amount,
                    AVG(dk.pct_chg) as avg_pct_chg,
                    MAX(dk.pct_chg) as max_pct_chg,
                    MIN(dk.pct_chg) as min_pct_chg,
                    SUM(CASE WHEN dk.pct_chg > 0 THEN 1 ELSE 0 END) as rising_count,
                    SUM(CASE WHEN dk.pct_chg < 0 THEN 1 ELSE 0 END) as falling_count
                FROM stock_info si
                LEFT JOIN daily_kline dk ON si.ts_code = dk.ts_code AND dk.trade_date = ?
                WHERE si.industry = ?
                """
                result = conn.execute(stats_query, (trade_date, industry)).fetchone()
                
                if result and result[0] > 0:  # 有数据
                    conn.execute("""
                        INSERT OR REPLACE INTO industry_stats 
                        (industry, trade_date, total_volume, avg_volume, total_amount, avg_amount, 
                         avg_pct_chg, max_pct_chg, min_pct_chg, stock_count, rising_count, falling_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        industry, trade_date, result[1], result[2], result[3], result[4],
                        result[5], result[6], result[7], result[0], result[8], result[9]
                    ))
                    count += 1
        return count
    
    def calculate_stock_daily_stats(self, trade_date: str) -> int:
        """计算指定日期的股票日统计数据"""
        from infrastructure.db.engine import get_session
        
        with get_session() as conn:
            # 获取当日所有股票数据
            query = """
            SELECT ts_code, vol, amount, pct_chg, turnover_rate, amplitude
            FROM daily_kline 
            WHERE trade_date = ?
            """
            rows = conn.execute(query, (trade_date,)).fetchall()
            
            count = 0
            for row in rows:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_daily_stats 
                    (ts_code, trade_date, volume, amount, pct_chg, turnover_rate, amplitude)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row[0], trade_date, row[1], row[2], row[3], row[4], row[5]))
                count += 1
        return count
