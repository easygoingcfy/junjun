import pandas as pd

class StockSelector:
    def __init__(self):
        pass

    def filter_by_ma(self, df, ma_days=[5, 10, 20]):
        # 均线筛选示例：收盘价不破均线
        for ma in ma_days:
            df[f"MA{ma}"] = df['close'].rolling(ma).mean()
            df = df[df['close'] >= df[f"MA{ma}"]]
        return df

    def score_factors(self, df):
        # 多因子打分示例
        df['score'] = 0
        df.loc[df['close'] > df['open'], 'score'] += 2  # 阳线加分
        # 可扩展更多因子
        return df
