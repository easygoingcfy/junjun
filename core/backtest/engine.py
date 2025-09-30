# TODO
# - 实现基础回测循环(按交易日/信号执行)
# - 支持交易规则(开平仓/手续费/滑点/涨跌停处理)
# - 产出曲线与指标

class BacktestEngine:
    """TODO: 简单回测引擎占位"""
    def run(self, signals, config):
        """占位：根据输入信号计算简单绩效
        - 目前直接返回空summary，后续实现资金曲线/胜率等
        """
        return {"summary": {"signals": len(signals)}, "signals": signals}
