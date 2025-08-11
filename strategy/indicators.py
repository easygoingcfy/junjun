import pandas as pd
import numpy as np


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up, index=series.index).ewm(alpha=1/period, adjust=False).mean()
    roll_down = pd.Series(down, index=series.index).ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-12)
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea
    return dif, dea, hist


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def rolling_max(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).max()


def rolling_min(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).min()


def n_day_breakout(high: pd.Series, close: pd.Series, n: int, min_break_pct: float = 0.0) -> bool:
    if len(close) < n + 1:
        return False
    prev_high = high.iloc[-(n+1):-1].max()
    return close.iloc[-1] >= prev_high * (1 + (min_break_pct or 0) / 100.0)


def gap_percent(open_s: pd.Series, prev_close: pd.Series) -> float:
    if prev_close.iloc[-1] == 0 or np.isnan(prev_close.iloc[-1]):
        return 0.0
    return (open_s.iloc[-1] - prev_close.iloc[-1]) / prev_close.iloc[-1] * 100.0


def percent_distance_to(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    return (series_a - series_b) / (series_b.replace(0, np.nan)) * 100.0
