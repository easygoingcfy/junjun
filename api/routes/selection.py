# TODO
# - /selection 触发选股、查询最近一次结果
# - 传入策略参数(cfg)与时间范围

from fastapi import APIRouter
from core.service.selection_service import SelectionService

router = APIRouter(prefix="/selection", tags=["selection"])


@router.post("")
async def run_selection(body: dict):
    # body: { cfg: {}, start: "yyyyMMdd", end: "yyyyMMdd", codes?: [] }
    cfg = body.get("cfg", {})
    start = body.get("start")
    end = body.get("end")
    codes = body.get("codes")
    svc = SelectionService()
    result = svc.select(cfg, start, end, codes)
    return {"items": result, "total": len(result)}
