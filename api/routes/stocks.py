# TODO
# - /stocks 列表、详情、基础信息查询
# - 依赖注入 session/service

from fastapi import APIRouter
from core.dao.repositories import StockRepository

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("")
async def list_stocks(q: str | None = None, limit: int = 50, offset: int = 0):
    repo = StockRepository()
    items, total = repo.paged_list(q, limit, offset)
    return {"items": items, "total": total}
