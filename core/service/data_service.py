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
