import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class StrategyConfig:
    # 原子策略配置，均可选，可组合
    # 1) 涨幅类
    range_increase_days: int | None = None
    range_increase_min_pct: float | None = None
    exists_day_increase_within_days: int | None = None
    exists_day_increase_min_pct: float | None = None

    # 2) 成交量类
    volume_mode: Optional[str] = None  # None | "volume_breakout" | "volume_pullback"
    volume_ma_days: int = 5
    volume_ratio_min: float | None = None  # 放量阈值，例如 1.5 表示当日量/均量 >= 1.5
    volume_ratio_max: float | None = None  # 缩量阈值，例如 0.7 表示当日量/均量 <= 0.7
    # 缩量回调附加条件
    pullback_require_red: Optional[bool] = None  # 要求回调为收阴
    pullback_touch_ma: Optional[int] = None  # 回踩某均线天数，如20

    # 3) 均线系统
    ma_days: List[int] = field(default_factory=lambda: [5, 10, 20])
    ma_alignment: Optional[str] = None  # None | "long"(多头) | "short"(空头)
    price_above_ma: Optional[int] = None  # 要求价格高于某条均线，如 20

    # 4) K线形态
    enable_patterns: List[str] = field(default_factory=list)  # ["bullish_engulfing","hammer","shooting_star","doji","morning_star","evening_star"]
    pattern_window: int = 5
    pattern_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 5) 突破与波动过滤
    breakout_n: Optional[int] = None  # N日新高突破
    breakout_min_pct: Optional[float] = None  # 突破幅度下限（%）
    atr_period: Optional[int] = None  # ATR周期，开启则计算
    atr_max_pct_of_price: Optional[float] = None  # ATR/价格 百分比上限，用于过滤高波动

    # 6) 动量指标
    macd_enable: Optional[bool] = None
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_rule: Optional[str] = None  # dif>dea | 金叉 | hist>0

    rsi_enable: Optional[bool] = None
    rsi_period: int = 14
    rsi_min: Optional[float] = None
    rsi_max: Optional[float] = None


class StockSelector:
    def __init__(self, db_conn=None):
        # 可注入数据库连接
        self.conn = db_conn

    # ====== 工具方法 ======
    def _load_kline(self, ts_code: str, start: str, end: str) -> pd.DataFrame:
        q = """
        SELECT trade_date, open, high, low, close, vol, pct_chg
        FROM daily_kline
        WHERE ts_code=? AND trade_date>=? AND trade_date<=?
        ORDER BY trade_date ASC
        """
        df = pd.read_sql_query(q, self.conn, params=(ts_code, start, end))
        return df

    def _calc_ma(self, s: pd.Series, n: int) -> pd.Series:
        return s.rolling(n, min_periods=1).mean()

    # ====== 原子信号 ======
    def _volume_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        if not cfg.volume_mode:
            return True
        vol_ma = df['vol'].rolling(cfg.volume_ma_days, min_periods=1).mean()
        today_vol = df['vol'].iloc[-1]
        today_ratio = today_vol / max(vol_ma.iloc[-1], 1e-6)
        if cfg.volume_mode == 'volume_breakout':
            if cfg.volume_ratio_min is None:
                return True
            return today_ratio >= cfg.volume_ratio_min
        if cfg.volume_mode == 'volume_pullback':
            # 基本缩量条件
            if cfg.volume_ratio_max is not None and not (today_ratio <= cfg.volume_ratio_max):
                return False
            # 细化：是否要求收阴
            if cfg.pullback_require_red:
                if not (df['close'].iloc[-1] < df['open'].iloc[-1]):
                    return False
            # 细化：是否回踩某条MA
            if cfg.pullback_touch_ma:
                ma_n = cfg.pullback_touch_ma
                ma_s = self._calc_ma(df['close'], ma_n)
                # 触及：最低价≤MA≤最高价 或 收盘接近MA（|close-MA|/MA<1%）
                near = abs(df['close'].iloc[-1] - ma_s.iloc[-1]) / max(abs(ma_s.iloc[-1]), 1e-6) < 0.01
                touched = (df['low'].iloc[-1] <= ma_s.iloc[-1] <= df['high'].iloc[-1]) or near
                if not touched:
                    return False
            return True
        return True

    def _ma_system_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        closes = df['close']
        ma_map = {n: self._calc_ma(closes, n).iloc[-1] for n in cfg.ma_days}
        price_ok = True
        if cfg.price_above_ma:
            price_ok = closes.iloc[-1] >= ma_map.get(cfg.price_above_ma, closes.iloc[-1])
        align_ok = True
        if cfg.ma_alignment == 'long':
            ordered = sorted(cfg.ma_days)
            align_ok = all(ma_map[ordered[i]] >= ma_map[ordered[i+1]] for i in range(len(ordered)-1))
        elif cfg.ma_alignment == 'short':
            ordered = sorted(cfg.ma_days)
            align_ok = all(ma_map[ordered[i]] <= ma_map[ordered[i+1]] for i in range(len(ordered)-1))
        return price_ok and align_ok

    def _range_increase_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        ok = True
        if cfg.range_increase_min_pct is not None:
            if cfg.range_increase_days is None:
                ref = df['close'].iloc[0]
            else:
                if len(df['close']) < cfg.range_increase_days:
                    return False
                ref = df['close'].iloc[-cfg.range_increase_days]
            chg = (df['close'].iloc[-1] - ref) / max(ref, 1e-6) * 100
            ok = ok and (chg >= cfg.range_increase_min_pct)
        if cfg.exists_day_increase_within_days and cfg.exists_day_increase_min_pct is not None:
            recent = df['pct_chg'].tail(cfg.exists_day_increase_within_days).dropna()
            ok = ok and (not recent.empty and recent.max() >= cfg.exists_day_increase_min_pct)
        return ok

    def _pattern_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        if not cfg.enable_patterns:
            return True
        from strategy.patterns import detect_patterns
        found = detect_patterns(df[['open','high','low','close']].reset_index(drop=True), cfg.enable_patterns, cfg.pattern_window, cfg.pattern_params)
        return any(len(v) > 0 for v in found.values())

    def _breakout_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        if not cfg.breakout_n:
            return True
        from strategy.indicators import n_day_breakout
        return n_day_breakout(df['high'], df['close'], cfg.breakout_n, cfg.breakout_min_pct or 0)

    def _atr_filter(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        if not cfg.atr_period or not cfg.atr_max_pct_of_price:
            return True
        from strategy.indicators import atr
        atr_series = atr(df['high'], df['low'], df['close'], cfg.atr_period)
        last_atr = atr_series.iloc[-1]
        price = df['close'].iloc[-1]
        if price == 0:
            return False
        return (last_atr / price * 100.0) <= cfg.atr_max_pct_of_price

    def _macd_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        if not cfg.macd_enable:
            return True
        from strategy.indicators import macd
        dif, dea, hist = macd(df['close'], cfg.macd_fast, cfg.macd_slow, cfg.macd_signal)
        rule = cfg.macd_rule or 'hist>0'
        if rule == 'dif>dea':
            return dif.iloc[-1] > dea.iloc[-1]
        if rule == '金叉':
            if len(dif) < 2:
                return False
            return (dif.iloc[-2] <= dea.iloc[-2]) and (dif.iloc[-1] > dea.iloc[-1])
        # 默认：hist>0
        return hist.iloc[-1] > 0

    def _rsi_signal(self, df: pd.DataFrame, cfg: StrategyConfig) -> bool:
        if not cfg.rsi_enable:
            return True
        from strategy.indicators import rsi
        r = rsi(df['close'], cfg.rsi_period)
        last = r.iloc[-1]
        if cfg.rsi_min is not None and last < cfg.rsi_min:
            return False
        if cfg.rsi_max is not None and last > cfg.rsi_max:
            return False
        return True

    # ====== 主入口：对单只股票评估 ======
    def evaluate_single(self, ts_code: str, start: str, end: str, cfg: StrategyConfig) -> Dict[str, Any]:
        df = self._load_kline(ts_code, start, end)
        if df is None or df.empty or len(df) < 3:
            return {"ts_code": ts_code, "pass": False, "reason": "no_data"}
        checks = {
            "volume": self._volume_signal(df, cfg),
            "ma": self._ma_system_signal(df, cfg),
            "range": self._range_increase_signal(df, cfg),
            "pattern": self._pattern_signal(df, cfg),
            "breakout": self._breakout_signal(df, cfg),
            "atr": self._atr_filter(df, cfg),
            "macd": self._macd_signal(df, cfg),
            "rsi": self._rsi_signal(df, cfg),
        }
        passed = all(checks.values())
        return {"ts_code": ts_code, "pass": passed, "checks": checks}

    # ====== 对股票列表进行筛选 ======
    def filter_stocks(self, ts_codes: List[str], start: str, end: str, cfg: StrategyConfig) -> pd.DataFrame:
        rows = []
        for code in ts_codes:
            res = self.evaluate_single(code, start, end, cfg)
            if res.get('pass'):
                rows.append(res)
        return pd.DataFrame(rows)
