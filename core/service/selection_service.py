from typing import Iterable, List, Dict
from core.dao.repositories import StockRepository, KlineRepository


class SelectionService:
    """选股服务(最小可运行占位)：
    - 当前不应用任何复杂策略，仅返回存在K线数据的股票与最新收盘价(若有)
    """
    def __init__(self, stock_repo: StockRepository | None = None, kline_repo: KlineRepository | None = None):
        self.stock_repo = stock_repo or StockRepository()
        self.kline_repo = kline_repo or KlineRepository()

    def select(self, cfg: Dict, start: str, end: str, codes: Iterable[str] | None = None) -> List[Dict]:
        codes_list = list(codes) if codes else self.stock_repo.get_all_codes()
        latest_map = self.kline_repo.latest_close_map()
        info_map = self.stock_repo.info_map()
        result: List[Dict] = []
        for code in codes_list:
            result.append({
                "ts_code": code,
                "name": info_map.get(code, {}).get("name"),
                "industry": info_map.get(code, {}).get("industry"),
                "close": latest_map.get(code),
                "score": 0.0,       # TODO: 策略评分
                "passed": True      # TODO: 策略判断
            })
        return result
