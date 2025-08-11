import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.database import Database
from data.fetcher import DataFetcher
from data.save_data import DataSaver
import time
import pandas as pd
# 新增：日期与任务开关
import datetime as dt
import toml

# 任务开关默认值（按需执行，减少每次全量耗时）
DO_CONCEPT = False               # 概念与成分
DO_BOARDS = False                # 指数/板块与成分，以及板块日线
DO_INDUSTRY_BOARDS = False       # 同花顺行业板块与日线
DO_STOCKS_DAILY = True           # 个股日线增量
DO_STOCKS_DAILY_BATCH = True     # 若可用，优先按交易日批量抓取（TuShare）
DO_NEWS_HEAT = False             # 新闻条数热度

# 限制板块/行业板块日线仅回填最近N天（默认）
BOARD_RECENT_DAYS = 7

# 从 config.toml 读取开关并覆盖默认值
try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.toml'))
    if os.path.exists(cfg_path):
        cfg = toml.load(cfg_path)
        ingest_cfg = cfg.get('ingest', {}) if isinstance(cfg, dict) else {}
        DO_CONCEPT = bool(ingest_cfg.get('do_concept', DO_CONCEPT))
        DO_BOARDS = bool(ingest_cfg.get('do_boards', DO_BOARDS))
        DO_INDUSTRY_BOARDS = bool(ingest_cfg.get('do_industry_boards', DO_INDUSTRY_BOARDS))
        DO_STOCKS_DAILY = bool(ingest_cfg.get('do_stocks_daily', DO_STOCKS_DAILY))
        DO_STOCKS_DAILY_BATCH = bool(ingest_cfg.get('do_stocks_daily_batch', DO_STOCKS_DAILY_BATCH))
        DO_NEWS_HEAT = bool(ingest_cfg.get('do_news_heat', DO_NEWS_HEAT))
        BOARD_RECENT_DAYS = int(ingest_cfg.get('board_recent_days', BOARD_RECENT_DAYS))
except Exception as _e:
    print(f"[配置读取警告] 未能读取 ingest 配置，使用默认值：{_e}")


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

    # 2) 概念与成分（可选）
    if DO_CONCEPT:
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

    # 3) 指数/板块与成分（以指数为例，可选）
    if DO_BOARDS:
        try:
            board_df = fetcher.fetch_boards()
            if board_df is not None and not board_df.empty:
                saver.save_boards(board_df)
                print(f"已保存板块/指数：{len(board_df)} 条")
                # 最近N天起始（字符串可与YYYYMMDD直接比较）
                recent_start = (dt.date.today() - dt.timedelta(days=BOARD_RECENT_DAYS)).strftime('%Y%m%d')
                for i, row in board_df.iterrows():
                    bcode = row.get('board_code')
                    if not bcode:
                        continue
                    members = fetcher.fetch_board_members(bcode)
                    if members is not None and not members.empty:
                        saver.save_board_members(bcode, members)
                    print(f"指数 {bcode} 成分 {0 if members is None else len(members)} 条")
                    # 板块指数日线（板块热度）增量，仅取最近N天
                    latest_bdate = get_latest_board_date(db, bcode)
                    start_date = max(latest_bdate if latest_bdate else '20200101', recent_start)
                    end_date = time.strftime('%Y%m%d')
                    bdf = fetcher.fetch_board_daily(bcode, start_date, end_date)
                    if bdf is not None and not bdf.empty:
                        # 若 latest_bdate 存在，进一步过滤
                        if latest_bdate:
                            bdf = bdf[bdf['date'] > latest_bdate]
                        # 再次按最近N天约束
                        bdf = bdf[bdf['date'] >= recent_start]
                        if not bdf.empty:
                            saver.save_board_daily(bcode, bdf)
        except Exception as e:
            print(f"板块/指数数据采集失败: {e}")

    # 3.1) 同花顺行业板块、成分与日线（板块热度，可选）
    if DO_INDUSTRY_BOARDS:
        try:
            ind_df = fetcher.fetch_industry_boards_ths()
            if ind_df is not None and not ind_df.empty:
                saver.save_boards(ind_df)
                print(f"已保存行业板块（同花顺）：{len(ind_df)} 条")
                recent_start = (dt.date.today() - dt.timedelta(days=BOARD_RECENT_DAYS)).strftime('%Y%m%d')
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
                    # 行业板块日线（板块热度）增量，仅取最近N天
                    latest_bdate = get_latest_board_date(db, bname)
                    bdf = fetcher.fetch_industry_board_daily_ths(bname)
                    if bdf is not None and not bdf.empty:
                        if latest_bdate:
                            bdf = bdf[bdf['date'] > latest_bdate]
                        bdf = bdf[bdf['date'] >= recent_start]
                        if not bdf.empty:
                            saver.save_board_daily(bname, bdf)
                    print(f"行业板块 {bname} 成分 {0 if members is None else len(members)} 条，新增日线 {0 if bdf is None else len(bdf)} 条")
        except Exception as e:
            print(f"行业板块数据采集失败: {e}")

    # 4) 日线增量更新（含更多字段，可选）
    if DO_STOCKS_DAILY:
        # 优先使用批量路径：按交易日批量抓取（要求 TuShare token 可用）
        if DO_STOCKS_DAILY_BATCH and getattr(fetcher, 'ts_pro', None) is not None:
            try:
                # 计算统一起始日期：取库内最早缺口后的最小日期；简化：取全市场最晚trade_date，回退1天作为起点
                cur = db.conn.cursor()
                cur.execute("SELECT MAX(trade_date) FROM daily_kline")
                latest_all = cur.fetchone()[0]
                start_date = latest_all if latest_all else '20200101'
                end_date = time.strftime('%Y%m%d')
                # 交易日历
                cal = fetcher.fetch_trade_calendar(start_date=start_date, end_date=end_date)
                if cal is not None and not cal.empty:
                    dates = cal['trade_date'].sort_values().tolist()
                    # 若已更新到某天，则从下一交易日开始
                    if latest_all and latest_all in dates:
                        pos = dates.index(latest_all)
                        dates = dates[pos+1:]
                    print(f"按交易日批量抓取：待更新 {len(dates)} 天")
                    for i, d in enumerate(dates):
                        d = str(d)
                        df_day = fetcher.fetch_daily_by_date(d)
                        if df_day is not None and not df_day.empty:
                            saver.bulk_save_daily_kline(df_day)
                            print(f"[{i+1}/{len(dates)}] 已保存 {d} 共 {len(df_day)} 条")
                        else:
                            print(f"[{i+1}/{len(dates)}] {d} 无新增数据")
                else:
                    print("交易日历为空，回退到逐只增量模式")
                    raise RuntimeError("empty calendar")
            except Exception as e:
                print(f"批量按日抓取失败，回退到逐只增量：{e}")
                # 回退到逐只逻辑
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
                    except Exception as e2:
                        print(f"[{idx+1}/{total}] {ts_code} 采集失败: {e2}")
        else:
            # 原有逐只增量路径
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

    # 5) 新闻条数热度（按日，可选）
    if DO_NEWS_HEAT:
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