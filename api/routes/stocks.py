# TODO
# - /stocks 列表、详情、基础信息查询
# - 依赖注入 session/service

from fastapi import APIRouter
from core.dao.repositories import StockRepository, IndustryRepository
from core.service.real_industry_service import RealIndustryService
from core.service.database_industry_service import DatabaseIndustryService

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("")
async def list_stocks(q: str | None = None, limit: int = 50, offset: int = 0):
    repo = StockRepository()
    items, total = repo.paged_list(q, limit, offset)
    return {"items": items, "total": total}

@router.get("/stats")
async def get_stats():
    """获取股票统计信息"""
    repo = StockRepository()
    # 获取股票总数
    items, total = repo.paged_list(None, 1, 0)
    
    # 获取最新交易日
    from infrastructure.db.engine import get_session
    with get_session() as conn:
        latest_date_row = conn.execute("SELECT MAX(trade_date) FROM daily_kline").fetchone()
        latest_date = latest_date_row[0] if latest_date_row and latest_date_row[0] else None
    
    return {
        "total_stocks": total,
        "latest_trade_date": latest_date
    }

@router.get("/industries")
async def get_industries():
    """获取所有行业列表"""
    repo = IndustryRepository()
    return repo.get_all_industries()

@router.get("/industries/stats")
async def get_industry_stats(days: int = 7):
    """获取行业统计数据"""
    repo = IndustryRepository()
    return repo.get_industry_stats(days)

@router.get("/industries/{industry}/stocks")
async def get_stocks_by_industry(industry: str, sort_by: str = "volume", limit: int = 100):
    """获取指定行业的股票列表"""
    repo = IndustryRepository()
    return repo.get_stocks_by_industry(industry, sort_by, limit)

@router.post("/refresh")
async def refresh_stock_list():
    """刷新股票列表"""
    from core.service.data_service import DataService
    
    data_service = DataService()
    count = data_service.refresh_stock_list()
    
    return {"count": count}

@router.post("/update-industries-real")
async def update_stock_industries_real():
    """使用tushare真实数据更新股票行业标签"""
    try:
        real_service = RealIndustryService()
        count = real_service.update_stock_industries_from_tushare()
        
        return {
            "updated_count": count,
            "message": "使用tushare真实数据更新成功"
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "更新失败，请检查tushare配置"
        }

@router.post("/sync-industry-data")
async def sync_industry_data():
    """同步行业指数数据到数据库"""
    try:
        db_service = DatabaseIndustryService()
        result = db_service.sync_all_industry_data()
        
        return {
            "message": "行业数据同步完成",
            "result": result
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "同步失败"
        }

@router.get("/validate-industries")
async def validate_industry_data():
    """验证行业数据的有效性"""
    try:
        real_service = RealIndustryService()
        validation_result = real_service.validate_industry_data()
        
        return validation_result
    except Exception as e:
        return {
            "error": str(e),
            "message": "验证失败"
        }

@router.get("/industries")
async def get_industry_list():
    """获取行业列表"""
    try:
        db_service = DatabaseIndustryService()
        industries = db_service.get_industry_list()
        return industries
    except Exception as e:
        return {"error": str(e)}

@router.get("/industries/stats")
async def get_industry_stats(trade_date: str = None):
    """获取行业统计数据"""
    try:
        db_service = DatabaseIndustryService()
        stats = db_service.get_industry_stats(trade_date)
        return stats
    except Exception as e:
        return {"error": str(e)}

@router.get("/industries/{index_code}/kline")
async def get_industry_kline(index_code: str, start_date: str = None, end_date: str = None, limit: int = 100):
    """获取行业指数K线数据"""
    try:
        db_service = DatabaseIndustryService()
        kline_data = db_service.get_industry_kline(index_code, start_date, end_date, limit)
        return kline_data
    except Exception as e:
        return {"error": str(e)}

@router.get("/industries/{index_code}/members")
async def get_industry_members(index_code: str):
    """获取行业成分股列表"""
    try:
        db_service = DatabaseIndustryService()
        members = db_service.get_industry_members(index_code)
        return members
    except Exception as e:
        return {"error": str(e)}

@router.post("/calculate-stats")
async def calculate_stats(request: dict):
    """计算指定日期的统计数据"""
    from core.service.data_service import DataService
    
    trade_date = request.get("trade_date")
    if not trade_date:
        return {"error": "trade_date is required"}
    
    data_service = DataService()
    industry_count = data_service.calculate_industry_stats(trade_date)
    stock_count = data_service.calculate_stock_daily_stats(trade_date)
    
    return {
        "trade_date": trade_date,
        "industry_stats_calculated": industry_count,
        "stock_stats_calculated": stock_count
    }
