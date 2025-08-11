import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.database import Database
from data.fetcher import DataFetcher
from data.save_data import DataSaver
import time
import pandas as pd


def get_latest_trade_date(db: Database, ts_code: str):
    cursor = db.conn.cursor()
    cursor.execute("SELECT MAX(trade_date) FROM daily_kline WHERE ts_code=?", (ts_code,))
    result = cursor.fetchone()
    return result[0] if result and result[0] else None


def get_latest_board_date(db: Database, board_code: str):
    cursor = db.conn.cursor()
    cursor.execute("SELECT MAX(date) FROM board_daily WHERE board_code=?", (board_code,))
    result = cursor.fetchone()
    return result[0] if result and result[0] else None


if __name__ == "__main__":
    db = Database()
    fetcher = DataFetcher()
    saver = DataSaver(db)

    # 1) 基础股票列表
    stock_df = fetcher.fetch_stock_list()
    saver.save_stock_list(stock_df)
    print(f"已保存股票列表，共{len(stock_df)}只股票")

    # 2) 概念与成分
    try:
        concept_df = fetcher.fetch_concepts()
        saver.save_concepts(concept_df)
        print(f"已保存概念列表：{0 if concept_df is None else len(concept_df)} 条")
        if concept_df is not None and not concept_df.empty:
            for i, row in concept_df.iterrows():
                ccode = row.get('concept_code')
                if not ccode:
                    continue
                members = fetcher.fetch_concept_members(ccode)
                if members is not None and not members.empty:
                    if 'ts_code' not in members.columns:
                        if 'symbol' in members.columns:
                            members = members.rename(columns={'symbol': 'ts_code'})
                        elif '代码' in members.columns:
                            members = members.rename(columns={'代码': 'ts_code'})
                    saver.save_concept_members(members, concept_code=ccode)
                print(f"概念 {ccode} 成分 {0 if members is None else len(members)} 条")
    except Exception as e:
        print(f"概念数据采集失败: {e}")

    # 3) 指数/板块与成分（以指数为例）
    try:
        board_df = fetcher.fetch_boards()
        if board_df is not None and not board_df.empty:
            saver.save_boards(board_df)
            print(f"已保存板块/指数：{len(board_df)} 条")
            for i, row in board_df.iterrows():
                bcode = row.get('board_code')
                if not bcode:
                    continue
                members = fetcher.fetch_board_members(bcode)
                if members is not None and not members.empty:
                    saver.save_board_members(bcode, members)
                print(f"指数 {bcode} 成分 {0 if members is None else len(members)} 条")
                # 板块指数日线（板块热度）增量
                latest_bdate = get_latest_board_date(db, bcode)
                start_date = latest_bdate if latest_bdate else '20200101'
                end_date = time.strftime('%Y%m%d')
                bdf = fetcher.fetch_board_daily(bcode, start_date, end_date)
                if bdf is not None and not bdf.empty:
                    # 若 latest_bdate 存在，进一步过滤
                    if latest_bdate:
                        bdf = bdf[bdf['date'] > latest_bdate]
                    if not bdf.empty:
                        saver.save_board_daily(bcode, bdf)
    except Exception as e:
        print(f"板块/指数数据采集失败: {e}")

    # 3.1) 同花顺行业板块、成分与日线（板块热度）
    try:
        ind_df = fetcher.fetch_industry_boards_ths()
        if ind_df is not None and not ind_df.empty:
            saver.save_boards(ind_df)
            print(f"已保存行业板块（同花顺）：{len(ind_df)} 条")
            for i, row in ind_df.iterrows():
                bname = row.get('board_code')  # 使用板块名称作为board_code
                if not bname:
                    continue
                # 成分入库
                members = fetcher.fetch_industry_board_members_ths(bname)
                if members is not None and not members.empty:
                    if 'ts_code' not in members.columns:
                        if '代码' in members.columns:
                            members = members.rename(columns={'代码': 'ts_code'})
                    saver.save_board_members(bname, members)
                # 行业板块日线（板块热度）增量
                latest_bdate = get_latest_board_date(db, bname)
                bdf = fetcher.fetch_industry_board_daily_ths(bname)
                if bdf is not None and not bdf.empty:
                    if latest_bdate:
                        bdf = bdf[bdf['date'] > latest_bdate]
                    if not bdf.empty:
                        saver.save_board_daily(bname, bdf)
                print(f"行业板块 {bname} 成分 {0 if members is None else len(members)} 条，新增日线 {0 if bdf is None else len(bdf)} 条")
    except Exception as e:
        print(f"行业板块数据采集失败: {e}")

    # 4) 日线增量更新（含更多字段）
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
            if kline_df is not None and not kline_df.empty:
                saver.save_daily_kline(ts_code, kline_df)
                print(f"[{idx+1}/{total}] 已保存{ts_code}日线行情，共{kline_df.shape[0]}条")
            else:
                print(f"[{idx+1}/{total}] {ts_code} 无新数据")
        except Exception as e:
            print(f"[{idx+1}/{total}] {ts_code} 采集失败: {e}")

    # 5) 新闻条数热度（按日）
    try:
        today = time.strftime('%Y%m%d')
        heat_rows = []
        for _, r in stock_df.iterrows():
            cnt = fetcher.fetch_daily_news_count(r['ts_code'], today)
            heat_rows.append({
                'ts_code': r['ts_code'],
                'date': today,
                'source': 'news_count',
                'news_count': int(cnt) if cnt is not None else 0,
                'search_score': None,
                'forum_count': None,
                'sentiment': None,
                'board_hotness': None,
            })
        saver.save_heat_data(pd.DataFrame(heat_rows))
        print(f"已写入新闻热度 {len(heat_rows)} 条")
    except Exception as e:
        print(f"新闻热度采集失败: {e}")

    db.close()