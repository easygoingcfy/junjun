# TODO
# - 策略注册/获取/动态加载
# - 插件路径扫描与热加载

class StrategyRegistry:
    """TODO: 策略注册中心"""
    def __init__(self):
        self._strategies = {}

    def register(self, key: str, strategy_cls):
        self._strategies[key] = strategy_cls

    def get(self, key: str):
        return self._strategies.get(key)

    def all(self):
        return dict(self._strategies)
