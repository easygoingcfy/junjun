# TODO
# - 定义领域实体：Stock, OHLCV, Indicator, Strategy, Signal, BacktestResult
# - 选择使用dataclass/pydantic(BaseModel)并定义基础字段
# - 约定ID/时间/版本等通用属性

# 占位：
class Stock:
    """TODO: 股票基础信息实体"""
    pass

class OHLCV:
    """TODO: 日线K线实体"""
    pass

class Indicator:
    """TODO: 指标实体(如MA/MACD/RSI)"""
    pass

class Strategy:
    """TODO: 策略实体(元数据、参数)"""
    pass

class Signal:
    """TODO: 选股信号实体"""
    pass

class BacktestResult:
    """TODO: 回测结果实体(绩效指标+明细)"""
    pass
