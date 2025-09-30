# TODO
# - 创建FastAPI实例，挂载路由
# - CORS/日志/异常拦截
# - /health 路由占位

from fastapi import FastAPI
from api.routes.stocks import router as stocks_router
from api.routes.selection import router as selection_router
from api.routes.backtest import router as backtest_router
from api.routes.jobs import router as jobs_router


def create_app() -> FastAPI:
    app = FastAPI(title="Stock Selection Service")

    @app.get("/health")
    def health():
        # TODO: 返回数据库连接/版本等健康信息
        return {"status": "ok"}

    # 路由
    app.include_router(stocks_router)
    app.include_router(selection_router)
    app.include_router(backtest_router)
    app.include_router(jobs_router)
    return app


app = create_app()
