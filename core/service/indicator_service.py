# TODO
# - 计算并缓存技术指标(MA/MACD/RSI/ATR等)
# - 支持批量计算与分片并行
# - 约定输出结构与缓存策略

class IndicatorService:
    """TODO: 指标计算服务"""
    def compute_batch(self, codes, start, end, indicators):
        raise NotImplementedError
