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

    def fetch_stock_list(self) -> pd.DataFrame:
        df = ak.stock_info_a_code_name()
        df.rename(columns={'code': 'ts_code'}, inplace=True)
        return df

    def fetch_daily_kline(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # 1. 主接口：TuShare
        if self.ts_pro:
            try:
                tushare_code = f"{ts_code}.SZ" if ts_code.startswith(('0', '3')) else f"{ts_code}.SH"
                df = self.ts_pro.daily(ts_code=tushare_code, start_date=start_date, end_date=end_date)
                # 获取换手率
                df_basic = self.ts_pro.daily_basic(ts_code=tushare_code, start_date=start_date, end_date=end_date, fields="ts_code,trade_date,turnover_rate")
                # 合并
                df = pd.merge(df, df_basic[['trade_date', 'turnover_rate']], on='trade_date', how='left')
                # 字段标准化
                df.rename(columns={
                    'trade_date': 'trade_date', 'open': 'open', 'close': 'close', 'high': 'high', 'low': 'low',
                    'vol': 'vol', 'amount': 'amount', 'pct_chg': 'pct_chg', 'turnover_rate': 'turnover_rate'
                }, inplace=True)
                keep = ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg', 'turnover_rate']
                if not df.empty:
                    print(f"[TuShare] 成功获取 {ts_code} 数据")
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
            keep = ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg', 'turnover_rate']
            if not df.empty:
                print(f"[akshare] 成功获取 {ts_code} 数据")
                return df[keep]
        except Exception as e:
            print(f"[akshare接口失败] {ts_code} ({symbol}): {e}")

        print(f"[警告] 股票代码 {ts_code} ({symbol}) 所有数据源均失败，已跳过。")
        return pd.DataFrame()

    def _tscode_to_akshare(self, ts_code: str) -> str:
        if ts_code.startswith('6'):
            return f'sh{ts_code}'
        elif ts_code.startswith('0') or ts_code.startswith('3'):
            return f'sz{ts_code}'
        # 新三板/北交所等其它板块直接返回None或raise
        else:
            raise ValueError(f"未知股票代码格式: {ts_code}")