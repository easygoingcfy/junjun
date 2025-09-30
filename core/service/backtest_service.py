from typing import Iterable, Dict, Any


class BacktestService:
    """回测服务(简版占位)
    - 当前返回固定 summary 与空 signals
    - 后续接入 core/backtest/engine 与真实策略
    """
    def run(self, cfg: Dict[str, Any], start: str, end: str, codes: Iterable[str] | None = None, lookback: int = 60, forward_n: int = 5) -> Dict[str, Any]:
        summary = {
            "period": [start, end],
            "lookback_days": lookback,
            "forward_n": forward_n,
            "win_rate": 0.0,
            "avg_ret": 0.0,
            "avg_ret_after_fee": 0.0,
            "median_ret": 0.0,
            "mdd": 0.0,
            "signals": 0,
        }
        signals = []
        return {"summary": summary, "signals": signals}
