# TODO
# - 定义 IStrategy 接口：name, params, run/evaluate
# - 约定输入/输出数据格式，与服务层对齐

class IStrategy:
    """TODO: 策略接口"""
    def name(self) -> str:
        raise NotImplementedError

    def params(self) -> dict:
        raise NotImplementedError

    def run(self, data, cfg: dict):
        """返回信号或评分结果(list[dict])"""
        raise NotImplementedError


class MovingAverageStrategy(IStrategy):
    """基础均线策略(占位)：
    - 输入: data 为 (trade_date, close) 的列表或DataFrame
    - 规则: close > MA(N) 视为通过
    - 输出: [{ts_code, trade_date, score, passed}]
    """
    def name(self) -> str:
        return "ma_basic"

    def params(self) -> dict:
        return {"ma": 20}

    def run(self, data, cfg: dict):
        # 占位：仅返回空结果，后续接入真实DataFrame计算
        return []
