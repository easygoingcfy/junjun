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
            # 优先从环境变量获取token
            token = os.environ.get('TUSHARE_TOKEN')
            if not token:
                # 其次从config.local.toml读取（本地私密文件）
                local_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.local.toml'))
                if os.path.exists(local_config_path):
                    local_config = toml.load(local_config_path)
                    token = local_config.get('tushare', {}).get('token', None)
            if not token:
                # 最后从config.toml读取（但应为空，避免提交私密信息）
                config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.toml'))
                if os.path.exists(config_path):
                    config = toml.load(config_path)
                    token = config.get('tushare', {}).get('token', None)
            if token and token.strip():
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

    def fetch_stock_list(self, from_db_conn=None) -> pd.DataFrame:
        # 优先从数据库读取，避免重复网络请求
        if from_db_conn:
            try:
                df = pd.read_sql("SELECT ts_code, name, industry FROM stock_info", from_db_conn)
                if not df.empty:
                    # 确保数据库返回的也没有后缀
                    df['ts_code'] = df['ts_code'].str.split('.').str[0]
                    return df
            except Exception as e:
                print(f"[DB] 读取股票列表失败: {e}")

        # 其次 TuShare 获取更全字段
        if self.ts_pro:
            try:
                df = self.ts_pro.stock_basic(fields='ts_code,symbol,name,area,industry,market,exchange,list_status,list_date,is_hs')
                if not df.empty:
                    df['ts_code'] = df['ts_code'].str.split('.').str[0]
                    return df
            except Exception:
                pass
        
        # 最后退化到 akshare
        try:
            df = ak.stock_info_a_code_name()
            # akshare 的 code 列已经是无后缀的，只需重命名
            df.rename(columns={'code': 'ts_code'}, inplace=True)
            return df
        except Exception as e:
            print(f"[akshare] 股票列表获取失败: {e}")
            return pd.DataFrame()

    def fetch_daily_kline(self, ts_code: str, start_date: str, end_date: str, progress_callback=None) -> pd.DataFrame:
        # 1. 主接口：TuShare
        if self.ts_pro:
            try:
                tushare_code = self._to_tushare_ts_code(ts_code)
                # 行情与基础合并
                df = self.ts_pro.daily(ts_code=tushare_code, start_date=start_date, end_date=end_date)
                if progress_callback:
                    progress_callback(ts_code, "daily")
                
                basic = self.ts_pro.daily_basic(ts_code=tushare_code, start_date=start_date, end_date=end_date,
                                                fields="ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe_ttm,pb,ps_ttm,total_mv,circ_mv")
                if progress_callback:
                    progress_callback(ts_code, "basic")

                # 前收盘
                adj = self.ts_pro.adj_factor(ts_code=tushare_code, start_date=start_date, end_date=end_date)
                if progress_callback:
                    progress_callback(ts_code, "adj")

                # 合并
                if df is None or df.empty:
                     return pd.DataFrame()
                
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
                
                # 确保所有列都存在
                for col in keep:
                    if col not in df.columns:
                        df[col] = pd.NA
                
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
            if progress_callback:
                progress_callback(ts_code, "akshare_hist")

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
            
            # 确保所有列都存在
            for col in keep:
                if col not in df.columns:
                    df[col] = pd.NA

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

    def _tscode_to_akshare(self, ts_code: str) -> str:
        code = ts_code.split('.')[0] if '.' in ts_code else ts_code
        if code.startswith('6'):
            return f'sh{code}'
        elif code.startswith('0') or code.startswith('3'):
            return f'sz{code}'
        else:
            raise ValueError(f"未知股票代码格式: {ts_code}")