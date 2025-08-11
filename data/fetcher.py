import akshare as ak
import pandas as pd
import tushare as ts
import toml
import os

class DataFetcher:
    def __init__(self, tushare_token=None):
        self.ts_pro = None
        if tushare_token:
            self.ts_pro = ts.pro_api(tushare_token)
        else:
            # 优先从项目根目录读取config.toml
            config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.toml'))
            if os.path.exists(config_path):
                config = toml.load(config_path)
                token = config.get('tushare', {}).get('token', None)
                if token:
                    self.ts_pro = ts.pro_api(token)

    def _to_tushare_ts_code(self, code: str) -> str:
        # 若已带后缀则直接返回；否则按首位判断交易所
        if '.' in code:
            return code
        if code.startswith(('0', '3')):
            return f"{code}.SZ"
        if code.startswith('6'):
            return f"{code}.SH"
        return code

    def fetch_stock_list(self) -> pd.DataFrame:
        # 优先 TuShare 获取更全字段
        if self.ts_pro:
            try:
                df = self.ts_pro.stock_basic(fields='ts_code,symbol,name,area,industry,market,exchange,list_status,list_date,is_hs')
                return df
            except Exception:
                pass
        # 退化到 akshare
        df = ak.stock_info_a_code_name()
        df.rename(columns={'code': 'ts_code'}, inplace=True)
        return df

    def fetch_daily_kline(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # 1. 主接口：TuShare
        if self.ts_pro:
            try:
                tushare_code = self._to_tushare_ts_code(ts_code)
                # 行情与基础合并
                df = self.ts_pro.daily(ts_code=tushare_code, start_date=start_date, end_date=end_date)
                basic = self.ts_pro.daily_basic(ts_code=tushare_code, start_date=start_date, end_date=end_date,
                                                fields="ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe_ttm,pb,ps_ttm,total_mv,circ_mv")
                # 前收盘
                adj = self.ts_pro.adj_factor(ts_code=tushare_code, start_date=start_date, end_date=end_date)
                # 合并
                df = pd.merge(df, basic, on=['ts_code', 'trade_date'], how='left')
                if adj is not None and not adj.empty:
                    df = pd.merge(df, adj[['trade_date', 'adj_factor']], on='trade_date', how='left')
                # 计算补充字段
                df = df.sort_values('trade_date')
                if 'pre_close' not in df.columns or df['pre_close'].isna().all():
                    df['pre_close'] = df['close'].shift(1)
                # 振幅 = (高-低)/前收
                df['amplitude'] = (df['high'] - df['low']) / df['pre_close'] * 100
                keep = ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg', 'turnover_rate',
                        'pre_close', 'amplitude', 'volume_ratio', 'circ_mv', 'total_mv']
                if not df.empty:
                    return df[keep]
            except Exception as e:
                print(f"[TuShare接口失败] {ts_code}: {e}")

        # 2. 备用接口：akshare
        symbol = self._tscode_to_akshare(ts_code)
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            df.rename(columns={
                '日期': 'trade_date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                '成交量': 'vol', '成交额': 'amount', '涨跌幅': 'pct_chg', '换手率': 'turnover_rate'
            }, inplace=True)
            # 计算pre_close与振幅
            df = df.sort_values('trade_date')
            df['pre_close'] = df['close'].shift(1)
            df['amplitude'] = (df['high'] - df['low']) / df['pre_close'] * 100
            # 无 volume_ratio / mv，用空值
            df['volume_ratio'] = pd.NA
            df['circ_mv'] = pd.NA
            df['total_mv'] = pd.NA
            keep = ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg', 'turnover_rate',
                    'pre_close', 'amplitude', 'volume_ratio', 'circ_mv', 'total_mv']
            if not df.empty:
                return df[keep]
        except Exception as e:
            print(f"[akshare接口失败] {ts_code} ({symbol}): {e}")

        print(f"[警告] 股票代码 {ts_code} ({symbol}) 所有数据源均失败，已跳过。")
        return pd.DataFrame()

    # 新增：按交易日批量获取（TuShare）
    def fetch_daily_by_date(self, trade_date: str) -> pd.DataFrame:
        if not self.ts_pro:
            return pd.DataFrame()
        try:
            daily = self.ts_pro.daily(trade_date=trade_date)
            basic = self.ts_pro.daily_basic(trade_date=trade_date,
                                            fields="ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe_ttm,pb,ps_ttm,total_mv,circ_mv")
            if daily is None or daily.empty:
                return pd.DataFrame()
            df = pd.merge(daily, basic, on=['ts_code', 'trade_date'], how='left')
            # TuShare daily 自带 pre_close
            if 'pre_close' not in df.columns or df['pre_close'].isna().all():
                df['pre_close'] = df['close']  # 容错
            df['amplitude'] = (df['high'] - df['low']) / df['pre_close'] * 100
            keep = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg',
                    'turnover_rate', 'pre_close', 'amplitude', 'volume_ratio', 'circ_mv', 'total_mv']
            return df[keep]
        except Exception as e:
            print(f"[TuShare 按日批量失败] {trade_date}: {e}")
            return pd.DataFrame()

    # 新增：交易日历
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        if not self.ts_pro:
            return pd.DataFrame()
        try:
            cal = self.ts_pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
            if cal is None or cal.empty:
                return pd.DataFrame()
            cal = cal[cal['is_open'] == 1].copy()
            cal.rename(columns={'cal_date': 'trade_date'}, inplace=True)
            return cal[['trade_date']]
        except Exception as e:
            print(f"[TuShare 交易日历失败] {start_date}-{end_date}: {e}")
            return pd.DataFrame()

    # 概念相关
    def fetch_concepts(self) -> pd.DataFrame:
        # TuShare 概念列表
        if self.ts_pro:
            try:
                df = self.ts_pro.concept()
                df.rename(columns={'code': 'concept_code', 'name': 'name'}, inplace=True)
                df['source'] = 'tushare'
                return df[['concept_code', 'name', 'source']]
            except Exception as e:
                print(f"[TuShare 概念列表失败] {e}")
        # 备选：akshare 概念名称（同花顺）
        try:
            df = ak.stock_board_concept_name_ths()
            df.rename(columns={'板块代码': 'concept_code', '板块名称': 'name'}, inplace=True)
            df['source'] = 'eastmoney'
            return df[['concept_code', 'name', 'source']]
        except Exception as e:
            print(f"[akshare 概念名称失败] {e}")
            return pd.DataFrame()

    def fetch_concept_members(self, concept_code: str) -> pd.DataFrame:
        # TuShare 概念成分
        if self.ts_pro:
            try:
                df = self.ts_pro.concept_detail(id=concept_code)
                df.rename(columns={'id': 'concept_code'}, inplace=True)
                return df[['concept_code', 'ts_code']]
            except Exception:
                pass
        # 备选：akshare 同花顺概念成分
        try:
            df = ak.stock_board_concept_cons_ths(symbol=concept_code)
            if '代码' in df.columns:
                df.rename(columns={'代码': 'symbol'}, inplace=True)
            return df
        except Exception as e:
            print(f"[akshare 概念成分失败] {concept_code}: {e}")
            return pd.DataFrame()

    # 指数/板块（通用）
    def fetch_boards(self) -> pd.DataFrame:
        # 指数列表（上交所/深交所）
        if self.ts_pro:
            try:
                idx = self.ts_pro.index_basic(market='SSE')
                idx2 = self.ts_pro.index_basic(market='SZSE')
                df = pd.concat([idx, idx2], ignore_index=True)
                df['board_code'] = df['ts_code']
                df['name'] = df['name']
                df['type'] = 'index'
                df['source'] = 'tushare'
                return df[['board_code', 'name', 'type', 'source']]
            except Exception:
                pass
        return pd.DataFrame()

    def fetch_board_members(self, board_code: str) -> pd.DataFrame:
        # 指数成分
        if self.ts_pro:
            try:
                df = self.ts_pro.index_weight(index_code=board_code)
                df.rename(columns={'con_code': 'ts_code', 'weight': 'weight'}, inplace=True)
                return df[['ts_code', 'weight']]
            except Exception:
                pass
        return pd.DataFrame()

    def fetch_board_daily(self, board_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # 使用 TuShare 指数日线，作为板块热度（pct_chg）
        if self.ts_pro:
            try:
                df = self.ts_pro.index_daily(ts_code=board_code, start_date=start_date, end_date=end_date)
                if not df.empty:
                    df = df[['trade_date', 'close', 'pct_chg', 'vol', 'amount']].copy()
                    df.rename(columns={'trade_date': 'date'}, inplace=True)
                    return df
            except Exception as e:
                print(f"[TuShare 指数日线失败] {board_code}: {e}")
        return pd.DataFrame()

    # 行业板块（同花顺-东方财富数据）
    def fetch_industry_boards_ths(self) -> pd.DataFrame:
        try:
            df = ak.stock_board_industry_name_ths()
            # 统一为 board_code=板块名称，type=industry，source=eastmoney
            df.rename(columns={'板块名称': 'name', '板块代码': 'em_code'}, inplace=True)
            df['board_code'] = df['name']
            df['type'] = 'industry'
            df['source'] = 'eastmoney'
            return df[['board_code', 'name', 'type', 'source']]
        except Exception as e:
            print(f"[行业板块列表失败] {e}")
            return pd.DataFrame()

    def fetch_industry_board_members_ths(self, board_name: str) -> pd.DataFrame:
        try:
            df = ak.stock_board_industry_cons_ths(symbol=board_name)
            # 列通常包含 '代码','名称' 等
            if '代码' in df.columns:
                df.rename(columns={'代码': 'ts_code'}, inplace=True)
            return df
        except Exception as e:
            print(f"[行业板块成分失败] {board_name}: {e}")
            return pd.DataFrame()

    def fetch_industry_board_daily_ths(self, board_name: str) -> pd.DataFrame:
        try:
            df = ak.stock_board_industry_hist_em(symbol=board_name)
            # 字段：日期、收盘、涨跌幅、成交量、成交额
            if df is not None and not df.empty:
                df.rename(columns={'日期': 'date', '收盘': 'close', '涨跌幅': 'pct_chg', '成交量': 'vol', '成交额': 'amount'}, inplace=True)
                # 统一日期格式 YYYYMMDD
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y%m%d')
                return df[['date', 'close', 'pct_chg', 'vol', 'amount']]
        except Exception as e:
            print(f"[行业板块日线失败] {board_name}: {e}")
        return pd.DataFrame()

    # 新闻条数（热度）：使用 akshare 的新浪/东财新闻做简单按日计数
    def fetch_daily_news_count(self, ts_code: str, date: str) -> int:
        try:
            code = ts_code.split('.')[0] if '.' in ts_code else ts_code
            try:
                news_df = ak.stock_news_em(period='近1月')
                if news_df is not None and not news_df.empty:
                    tail3 = code[-3:]
                    tail4 = code[-4:]
                    the_day = pd.to_datetime(date)
                    # 兼容字段
                    publish_col = '发布时间' if '发布时间' in news_df.columns else '时间'
                    title_col = '标题' if '标题' in news_df.columns else 'title'
                    news_df['datetime'] = pd.to_datetime(news_df[publish_col], errors='coerce')
                    mask_date = news_df['datetime'].dt.strftime('%Y%m%d') == the_day.strftime('%Y%m%d')
                    mask_kw = news_df[title_col].astype(str).str.contains(tail3) | news_df[title_col].astype(str).str.contains(tail4)
                    return int((mask_date & mask_kw).sum())
            except Exception:
                pass
        except Exception:
            pass
        return 0

    def _tscode_to_akshare(self, ts_code: str) -> str:
        code = ts_code.split('.')[0] if '.' in ts_code else ts_code
        if code.startswith('6'):
            return f'sh{code}'
        elif code.startswith('0') or code.startswith('3'):
            return f'sz{code}'
        else:
            raise ValueError(f"未知股票代码格式: {ts_code}")