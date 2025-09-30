# TODO
# - /backtest 同步/异步回测
# - 提供参数校验与分页导出

from fastapi import APIRouter
from core.service.backtest_service import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("")
async def run_backtest(body: dict):
    cfg = body.get("cfg", {})
    start = body.get("start")
    end = body.get("end")
    codes = body.get("codes")
    lookback = int(body.get("lookback", 60))
    forward_n = int(body.get("forward_n", 5))
    svc = BacktestService()
    res = svc.run(cfg, start, end, codes, lookback, forward_n)
    return res
