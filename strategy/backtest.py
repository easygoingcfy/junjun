import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from strategy.selector import StrategyConfig, StockSelector


@dataclass
class BacktestResult:
    signals: pd.DataFrame
    summary: Dict[str, Any]


class Backtester:
    def __init__(self, conn):
        self.conn = conn
        self.selector = StockSelector(conn)

    def _get_all_trade_dates(self, start: str, end: str) -> List[str]:
        q = """
        SELECT DISTINCT trade_date FROM daily_kline
        WHERE trade_date>=? AND trade_date<=?
        ORDER BY trade_date ASC
        """
        rows = self.conn.execute(q, (start, end)).fetchall()
        return [r[0] for r in rows]

    def _get_window_start(self, date_list: List[str], i: int, lookback_days: int) -> str:
        j = max(0, i - lookback_days + 1)
        return date_list[j]

    def _get_price_on(self, ts_code: str, trade_date: str, field: str) -> Optional[float]:
        if field not in ("open", "close"):
            field = "close"
        row = self.conn.execute(
            f"SELECT {field} FROM daily_kline WHERE ts_code=? AND trade_date=?",
            (ts_code, trade_date)
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def _get_pct_chg_on(self, ts_code: str, trade_date: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT pct_chg FROM daily_kline WHERE ts_code=? AND trade_date=?",
            (ts_code, trade_date)
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def _get_next_trade_date_for_code(self, ts_code: str, date_: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT MIN(trade_date) FROM daily_kline WHERE ts_code=? AND trade_date>?",
            (ts_code, date_)
        ).fetchone()
        return row[0] if row and row[0] else None

    def _get_forward_price(self, ts_code: str, from_date: str, n: int, field: str) -> Optional[Tuple[str, float]]:
        if field not in ("open", "close"):
            field = "close"
        q = f"""
        SELECT trade_date, {field} FROM daily_kline
        WHERE ts_code=? AND trade_date>? ORDER BY trade_date ASC LIMIT ?
        """
        rows = self.conn.execute(q, (ts_code, from_date, n)).fetchall()
        if not rows or len(rows) < n:
            return None
        return rows[-1][0], float(rows[-1][1])

    def _calc_score(self, checks: Dict[str, bool], cfg: StrategyConfig, weights: Dict[str, float]) -> float:
        # 与UI一致：仅对启用项计分并归一化
        items = []
        items.append((cfg.volume_mode is not None, bool(checks.get('volume', False)), float(weights.get('vol', 30))))
        items.append(((cfg.ma_alignment is not None) or (cfg.price_above_ma is not None), bool(checks.get('ma', False)), float(weights.get('ma', 20))))
        items.append((cfg.breakout_n is not None, bool(checks.get('breakout', False)), float(weights.get('brk', 25))))
        items.append((bool(cfg.enable_patterns), bool(checks.get('pattern', False)), float(weights.get('pat', 15))))
        items.append((bool(cfg.macd_enable), bool(checks.get('macd', False)), float(weights.get('macd', 5))))
        items.append((bool(cfg.rsi_enable), bool(checks.get('rsi', False)), float(weights.get('rsi', 5))))
        total = sum(w for used, _pass, w in items if used and w > 0)
        if total <= 0:
            return 0.0
        earned = sum(w for used, _pass, w in items if used and _pass)
        return round(earned / total * 100.0, 3)

    def run(
        self,
        ts_codes: List[str],
        start: str,
        end: str,
        cfg: StrategyConfig,
        lookback_days: int = 60,
        forward_n: int = 5,
        fee_single_side_bps: float = 3.0,  # 单边手续费：千分之x（‰）
        top_k_per_day: int = 0,
        weights: Optional[Dict[str, float]] = None,
        entry_mode: str = "close",  # close | next_open
        exit_mode: str = "close",   # close | open （n日后）
        exclude_limit_up: bool = False,
        limit_up_threshold: float = 9.8,
    ) -> BacktestResult:
        weights = weights or {}
        dates = self._get_all_trade_dates(start, end)
        records = []
        # 遍历每个交易日
        for i, d in enumerate(dates):
            if i < 1:
                continue
            win_start = self._get_window_start(dates, i, lookback_days)
            day_candidates = []
            for code in ts_codes:
                # 排除信号日涨停（以信号日pct_chg判定）
                if exclude_limit_up:
                    pct = self._get_pct_chg_on(code, d)
                    if pct is not None and pct >= limit_up_threshold:
                        continue
                # 用窗口[win_start, d]评估信号
                res = self.selector.evaluate_single(code, win_start, d, cfg)
                if not res.get('pass'):
                    continue
                # 入场日期与价格
                if entry_mode == 'next_open':
                    entry_date = self._get_next_trade_date_for_code(code, d)
                    if not entry_date:
                        continue
                    entry_price = self._get_price_on(code, entry_date, 'open')
                else:  # 当日收盘买入
                    entry_date = d
                    entry_price = self._get_price_on(code, entry_date, 'close')
                if entry_price is None:
                    continue
                score = self._calc_score(res.get('checks', {}), cfg, weights)
                day_candidates.append((code, entry_date, entry_price, score, res.get('checks', {})))
            # 排序并按top_k限制
            if top_k_per_day and top_k_per_day > 0 and len(day_candidates) > top_k_per_day:
                day_candidates.sort(key=lambda x: x[3], reverse=True)
                day_candidates = day_candidates[:top_k_per_day]
            # 计算前瞻收益（从入场日起往后n日）
            for code, entry_date, entry_price, score, checks in day_candidates:
                fwd = self._get_forward_price(code, entry_date, forward_n, 'open' if exit_mode == 'open' else 'close')
                if not fwd:
                    continue
                exit_date, exit_price = fwd
                raw_ret = (exit_price - entry_price) / entry_price * 100.0
                fee_pct = 2.0 * fee_single_side_bps / 10.0  # 单边‰ 转为百分比并双边
                ret_after_fee = raw_ret - fee_pct
                records.append({
                    'trade_date': d,
                    'ts_code': code,
                    'entry_date': entry_date,
                    'entry_price': round(entry_price, 4),
                    'exit_date': exit_date,
                    'exit_price': round(exit_price, 4),
                    'ret_pct': round(raw_ret, 4),
                    'ret_pct_after_fee': round(ret_after_fee, 4),
                    'score': round(score, 3),
                    'passed': True,
                })
        signals = pd.DataFrame(records)
        if signals.empty:
            return BacktestResult(signals=signals, summary={
                'signals': 0,
                'win_rate': 0.0,
                'avg_ret': 0.0,
                'median_ret': 0.0,
                'avg_ret_after_fee': 0.0,
                'mdd': 0.0,
                'period': (start, end),
            })
        # 统计
        wins = (signals['ret_pct_after_fee'] > 0).sum()
        total = len(signals)
        avg_ret = float(signals['ret_pct'].mean())
        med_ret = float(signals['ret_pct'].median())
        avg_ret_fee = float(signals['ret_pct_after_fee'].mean())
        # 简单资金曲线（按信号顺序串行叠加）
        eq = (1.0 + signals['ret_pct_after_fee'] / 100.0).cumprod()
        roll_max = eq.cummax()
        dd = (eq / roll_max - 1.0)
        mdd = float(dd.min()) * 100.0 if not dd.empty else 0.0
        summary = {
            'signals': total,
            'win_rate': round(wins / total * 100.0, 2),
            'avg_ret': round(avg_ret, 3),
            'median_ret': round(med_ret, 3),
            'avg_ret_after_fee': round(avg_ret_fee, 3),
            'mdd': round(mdd, 2),
            'period': (start, end),
            'lookback_days': lookback_days,
            'forward_n': forward_n,
            'fee_single_side_bps': fee_single_side_bps,
            'top_k_per_day': top_k_per_day,
            'entry_mode': entry_mode,
            'exit_mode': exit_mode,
            'exclude_limit_up': exclude_limit_up,
            'limit_up_threshold': limit_up_threshold,
        }
        return BacktestResult(signals=signals, summary=summary)
