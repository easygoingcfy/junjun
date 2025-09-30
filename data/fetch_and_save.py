"""轻量数据采集脚本：仅同步股票列表与日线行情。"""

from __future__ import annotations

import datetime as dt
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import toml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database import Database
from data.fetcher import DataFetcher
from data.save_data import DataSaver


@dataclass
class IngestOptions:
    """采集配置，仅保留核心功能。"""

    fetch_stock_list: bool = True
    fetch_daily: bool = True
    use_batch_daily: bool = True
    daily_start_date: str = "20200101"
    rate_limit_per_min: int = 180

    @classmethod
    def load(cls, cfg_path: str) -> "IngestOptions":
        if not os.path.exists(cfg_path):
            return cls()
        try:
            data = toml.load(cfg_path)
            ingest = data.get("ingest", {}) if isinstance(data, dict) else {}
        except Exception as exc:  # pragma: no cover - 配置异常时使用默认
            print(f"[配置读取警告] {exc}")
            ingest = {}

        def _bool(key: str, default: bool) -> bool:
            if key in ingest:
                return bool(ingest[key])
            # 兼容旧字段命名
            legacy = {
                "stocks_daily": "do_stocks_daily",
                "stocks_daily_batch": "do_stocks_daily_batch",
            }.get(key)
            if legacy and legacy in ingest:
                return bool(ingest[legacy])
            return default

        daily_start = str(ingest.get("stocks_daily_start", "20200101"))
        rate_limit = int(ingest.get("rate_limit_per_min", 180))

        return cls(
            fetch_stock_list=_bool("stock_list", True),
            fetch_daily=_bool("stocks_daily", True),
            use_batch_daily=_bool("stocks_daily_batch", True),
            daily_start_date=daily_start,
            rate_limit_per_min=rate_limit,
        )


def _latest_trade_date_global(db: Database) -> Optional[str]:
    cur = db.conn.cursor()
    cur.execute("SELECT MAX(trade_date) FROM daily_kline")
    result = cur.fetchone()
    return result[0] if result and result[0] else None


def _latest_trade_date_for_stock(db: Database, ts_code: str) -> Optional[str]:
    cur = db.conn.cursor()
    cur.execute("SELECT MAX(trade_date) FROM daily_kline WHERE ts_code=?", (ts_code,))
    result = cur.fetchone()
    return result[0] if result and result[0] else None


def _ensure_start_date(config_start: str, latest_date: Optional[str]) -> str:
    if latest_date:
        return max(config_start, latest_date)
    return config_start


def update_stock_list(fetcher: DataFetcher, saver: DataSaver) -> pd.DataFrame:
    stock_df = fetcher.fetch_stock_list()
    saver.save_stock_list(stock_df)
    print(f"已保存股票列表，共 {len(stock_df)} 只股票")
    return stock_df


def update_daily_batch(db: Database, fetcher: DataFetcher, saver: DataSaver, options: IngestOptions):
    latest_all = _latest_trade_date_global(db)
    today = dt.date.today().strftime("%Y%m%d")
    start_from = _ensure_start_date(options.daily_start_date, latest_all)

    calendar = fetcher.fetch_trade_calendar(start_from, today)
    if calendar is None or calendar.empty:
        raise RuntimeError("无法获取交易日历")

    dates = sorted(str(d) for d in calendar['trade_date'].tolist())
    if latest_all in dates:
        dates = [d for d in dates if d > latest_all]

    if not dates:
        print("按日批量：无新增交易日")
        return

    print(f"按日批量：待更新 {len(dates)} 个交易日")
    for idx, trade_date in enumerate(dates, start=1):
        day_df = fetcher.fetch_daily_by_date(trade_date)
        if day_df is not None and not day_df.empty:
            saver.bulk_save_daily_kline(day_df)
            print(f"[{idx}/{len(dates)}] {trade_date} 保存 {len(day_df)} 条")
        else:
            print(f"[{idx}/{len(dates)}] {trade_date} 无有效数据")


def update_daily_incremental(db: Database, fetcher: DataFetcher, saver: DataSaver, stock_df: pd.DataFrame, options: IngestOptions):
    total = len(stock_df)
    throttle = max(1, options.rate_limit_per_min)
    request_count = 0
    window_start = time.time()

    for idx, row in stock_df.iterrows():
        ts_code = row['ts_code']
        latest = _latest_trade_date_for_stock(db, ts_code)
        start_date = _ensure_start_date(options.daily_start_date, latest)
        end_date = dt.date.today().strftime('%Y%m%d')

        try:
            df = fetcher.fetch_daily_kline(ts_code, start_date, end_date)
            request_count += 1
            if request_count >= throttle:
                elapsed = time.time() - window_start
                if elapsed < 60:
                    time.sleep(60 - elapsed)
                request_count = 0
                window_start = time.time()

            if df is not None and not df.empty:
                saver.save_daily_kline(ts_code, df)
                print(f"[{idx+1}/{total}] {ts_code} 更新 {df.shape[0]} 条")
            else:
                print(f"[{idx+1}/{total}] {ts_code} 无新增数据")
        except Exception as exc:
            print(f"[{idx+1}/{total}] {ts_code} 更新失败：{exc}")


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    cfg_path = os.path.join(project_root, 'config.toml')
    options = IngestOptions.load(cfg_path)

    db = Database()
    fetcher = DataFetcher()
    saver = DataSaver(db)

    try:
        stock_df = pd.DataFrame()
        if options.fetch_stock_list:
            stock_df = update_stock_list(fetcher, saver)
        else:
            # 若不刷新股票列表，也需读取一次以便日线更新
            stock_df = pd.read_sql_query("SELECT ts_code, name FROM stock_info", db.conn)

        if options.fetch_daily:
            has_token = getattr(fetcher, 'ts_pro', None) is not None
            if options.use_batch_daily and has_token:
                try:
                    update_daily_batch(db, fetcher, saver, options)
                except Exception as exc:
                    print(f"按日批量失败，回退逐只：{exc}")
                    update_daily_incremental(db, fetcher, saver, stock_df, options)
            else:
                update_daily_incremental(db, fetcher, saver, stock_df, options)
    finally:
        db.close()


if __name__ == "__main__":
    main()