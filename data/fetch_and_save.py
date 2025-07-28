from db.database import Database
from data.fetcher import DataFetcher
from data.save_data import DataSaver
import time
import os
import threading

def get_latest_trade_date(db: Database, ts_code: str):
    cursor = db.conn.cursor()
    cursor.execute("SELECT MAX(trade_date) FROM daily_kline WHERE ts_code=?", (ts_code,))
    result = cursor.fetchone()
    return result[0] if result and result[0] else None

if __name__ == "__main__":
    db = Database()
    fetcher = DataFetcher()
    saver = DataSaver(db)

    stock_df = fetcher.fetch_stock_list()
    print(f"已保存股票列表，共{len(stock_df)}只股票")

    total = len(stock_df)
    req_count = 0
    req_limit = 180
    start_minute = time.time()

    for idx, row in stock_df.iterrows():
        ts_code = row['ts_code']
        latest_date = get_latest_trade_date(db, ts_code)
        start_date = latest_date if latest_date else '20200101'
        end_date = time.strftime('%Y%m%d')
        try:
            kline_df = fetcher.fetch_daily_kline(ts_code, start_date, end_date)
            req_count += 1
            if req_count >= req_limit:
                elapsed = time.time() - start_minute
                if elapsed < 60:
                    time.sleep(60 - elapsed)
                req_count = 0
                start_minute = time.time()
            if not kline_df.empty:
                saver.save_daily_kline(ts_code, kline_df)
                print(f"[{idx+1}/{total}] 已保存{ts_code}日线行情，共{kline_df.shape[0]}条")
            else:
                print(f"[{idx+1}/{total}] {ts_code} 无新数据")
        except Exception as e:
            print(f"[{idx+1}/{total}] {ts_code} 采集失败: {e}")
    db.close()