import pandas as pd

# 基础K线形态识别工具（可被筛选与绘图复用）
# 约定：df包含列 open, high, low, close，按日期升序

def is_bullish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i <= 0 or i >= len(df):
        return False
    o1, c1 = df['open'].iat[i-1], df['close'].iat[i-1]
    o2, c2 = df['open'].iat[i], df['close'].iat[i]
    # 前一日阴线，后一日阳线，且后一日实体包住前一日实体
    return (c1 < o1) and (c2 > o2) and (o2 < c1) and (c2 > o1)

def is_bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i <= 0 or i >= len(df):
        return False
    o1, c1 = df['open'].iat[i-1], df['close'].iat[i-1]
    o2, c2 = df['open'].iat[i], df['close'].iat[i]
    # 前一日阳线，后一日阴线，且后一日实体包住前一日实体
    return (c1 > o1) and (c2 < o2) and (o2 > c1) and (c2 < o1)

def is_hammer(df: pd.DataFrame, i: int, body_ratio_max=0.35, lower_shadow_min=2.0) -> bool:
    # 锤子线：小实体、下影线长（相对实体）
    o, h, low_, c = df['open'].iat[i], df['high'].iat[i], df['low'].iat[i], df['close'].iat[i]
    body = abs(c - o)
    rng = h - low_
    if rng <= 0:
        return False
    body_ratio = body / rng
    lower_shadow = min(o, c) - low_
    upper_shadow = h - max(o, c)
    return (body_ratio <= body_ratio_max) and (lower_shadow >= lower_shadow_min * body) and (upper_shadow <= body)

def is_shooting_star(df: pd.DataFrame, i: int, body_ratio_max=0.35, upper_shadow_min=2.0) -> bool:
    # 射击之星：小实体、上影线长（相对实体）
    o, h, low_, c = df['open'].iat[i], df['high'].iat[i], df['low'].iat[i], df['close'].iat[i]
    body = abs(c - o)
    rng = h - low_
    if rng <= 0:
        return False
    body_ratio = body / rng
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - low_
    return (body_ratio <= body_ratio_max) and (upper_shadow >= upper_shadow_min * body) and (lower_shadow <= body)

def is_doji(df: pd.DataFrame, i: int, threshold=0.001) -> bool:
    # 十字星：开收接近
    o, c = df['open'].iat[i], df['close'].iat[i]
    if o == 0:
        return False
    return abs(c - o) / max(abs(o), 1e-6) <= threshold

# 三日形态：晨星与黄昏星（简化版规则）
def is_morning_star(df: pd.DataFrame, i: int, body_min_ratio=0.5) -> bool:
    if i < 2 or i >= len(df):
        return False
    o1, c1 = df['open'].iat[i-2], df['close'].iat[i-2]
    o2, c2 = df['open'].iat[i-1], df['close'].iat[i-1]
    o3, c3 = df['open'].iat[i], df['close'].iat[i]
    cond1 = c1 < o1 and abs(o1 - c1) > 0
    body2 = abs(c2 - o2)
    rng2 = df['high'].iat[i-1] - df['low'].iat[i-1]
    cond2 = rng2 > 0 and (body2 / rng2) < 0.4
    cond3 = c3 > o3 and (c3 - min(o1, c1)) >= body_min_ratio * abs(o1 - c1)
    return cond1 and cond2 and cond3

def is_evening_star(df: pd.DataFrame, i: int, body_min_ratio=0.5) -> bool:
    if i < 2 or i >= len(df):
        return False
    o1, c1 = df['open'].iat[i-2], df['close'].iat[i-2]
    o2, c2 = df['open'].iat[i-1], df['close'].iat[i-1]
    o3, c3 = df['open'].iat[i], df['close'].iat[i]
    cond1 = c1 > o1 and abs(c1 - o1) > 0
    body2 = abs(c2 - o2)
    rng2 = df['high'].iat[i-1] - df['low'].iat[i-1]
    cond2 = rng2 > 0 and (body2 / rng2) < 0.4
    cond3 = c3 < o3 and (max(o1, c1) - c3) >= body_min_ratio * abs(c1 - o1)
    return cond1 and cond2 and cond3

# 其他常见形态（简化版）
def is_bullish_harami(df: pd.DataFrame, i: int) -> bool:
    # 母子形态（看涨）：前阴后阳，且第二日实体包含于第一日实体内
    if i <= 0:
        return False
    o1, c1 = df['open'].iat[i-1], df['close'].iat[i-1]
    o2, c2 = df['open'].iat[i], df['close'].iat[i]
    return (c1 < o1) and (c2 > o2) and (min(o2, c2) > min(o1, c1)) and (max(o2, c2) < max(o1, c1))

def is_bearish_harami(df: pd.DataFrame, i: int) -> bool:
    # 母子形态（看跌）
    if i <= 0:
        return False
    o1, c1 = df['open'].iat[i-1], df['close'].iat[i-1]
    o2, c2 = df['open'].iat[i], df['close'].iat[i]
    return (c1 > o1) and (c2 < o2) and (min(o2, c2) > min(o1, c1)) and (max(o2, c2) < max(o1, c1))

def is_piercing_line(df: pd.DataFrame, i: int) -> bool:
    # 刺透形态：前阴后阳，第二天收盘穿越第一天实体中点
    if i <= 0:
        return False
    o1, c1 = df['open'].iat[i-1], df['close'].iat[i-1]
    o2, c2 = df['open'].iat[i], df['close'].iat[i]
    mid = (o1 + c1) / 2
    return (c1 < o1) and (c2 > o2) and (c2 > mid) and (o2 < c1)

def is_dark_cloud_cover(df: pd.DataFrame, i: int) -> bool:
    # 乌云盖顶：前阳后阴，第二天收盘跌破第一天实体中点
    if i <= 0:
        return False
    o1, c1 = df['open'].iat[i-1], df['close'].iat[i-1]
    o2, c2 = df['open'].iat[i], df['close'].iat[i]
    mid = (o1 + c1) / 2
    return (c1 > o1) and (c2 < o2) and (c2 < mid) and (o2 > c1)

def is_three_white_soldiers(df: pd.DataFrame, i: int) -> bool:
    # 三白兵：连续三根阳线，实体逐日上移（简化）
    if i < 2:
        return False
    closes = df['close']
    opens = df['open']
    return (closes.iat[i-2] > opens.iat[i-2] and closes.iat[i-1] > opens.iat[i-1] and closes.iat[i] > opens.iat[i] and
            closes.iat[i-1] >= closes.iat[i-2] and closes.iat[i] >= closes.iat[i-1])

def is_three_black_crows(df: pd.DataFrame, i: int) -> bool:
    # 三只乌鸦：连续三根阴线，实体逐日下移（简化）
    if i < 2:
        return False
    closes = df['close']
    opens = df['open']
    return (closes.iat[i-2] < opens.iat[i-2] and closes.iat[i-1] < opens.iat[i-1] and closes.iat[i] < opens.iat[i] and
            closes.iat[i-1] <= closes.iat[i-2] and closes.iat[i] <= closes.iat[i-1])


def detect_patterns(df: pd.DataFrame, patterns: list, window: int = 5, params: dict | None = None) -> dict:
    """
    返回形态出现的索引集合，形如：{"bullish_engulfing": [i1,i2], ...}
    支持：
    ["bullish_engulfing","bearish_engulfing","hammer","shooting_star","doji",
     "morning_star","evening_star","bullish_harami","bearish_harami",
     "piercing_line","dark_cloud_cover","three_white_soldiers","three_black_crows"]
    """
    params = params or {}
    res = {p: [] for p in patterns}
    n = len(df)
    start = max(0, n - window)
    for i in range(start, n):
        if 'bullish_engulfing' in patterns and is_bullish_engulfing(df, i):
            res['bullish_engulfing'].append(i)
        if 'bearish_engulfing' in patterns and is_bearish_engulfing(df, i):
            res['bearish_engulfing'].append(i)
        if 'hammer' in patterns and is_hammer(df, i, **params.get('hammer', {})):
            res['hammer'].append(i)
        if 'shooting_star' in patterns and is_shooting_star(df, i, **params.get('shooting_star', {})):
            res['shooting_star'].append(i)
        if 'doji' in patterns and is_doji(df, i, **params.get('doji', {})):
            res['doji'].append(i)
        if 'morning_star' in patterns and is_morning_star(df, i, **params.get('morning_star', {})):
            res['morning_star'].append(i)
        if 'evening_star' in patterns and is_evening_star(df, i, **params.get('evening_star', {})):
            res['evening_star'].append(i)
        if 'bullish_harami' in patterns and is_bullish_harami(df, i):
            res['bullish_harami'].append(i)
        if 'bearish_harami' in patterns and is_bearish_harami(df, i):
            res['bearish_harami'].append(i)
        if 'piercing_line' in patterns and is_piercing_line(df, i):
            res['piercing_line'].append(i)
        if 'dark_cloud_cover' in patterns and is_dark_cloud_cover(df, i):
            res['dark_cloud_cover'].append(i)
        if 'three_white_soldiers' in patterns and is_three_white_soldiers(df, i):
            res['three_white_soldiers'].append(i)
        if 'three_black_crows' in patterns and is_three_black_crows(df, i):
            res['three_black_crows'].append(i)
    return res
