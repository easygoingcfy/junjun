核心基础
配置与日志
在 config.local.toml/环境变量里放数据库路径、并在 infrastructure/db/engine.py 读取。
增加基础日志初始化（core/__init__.py 约定入口）。
数据库与迁移
完善 infrastructure/db/migrations.py：初始化表结构（stock_info、daily_kline、strategy、signals）。
提供一个启动脚本/命令调用 MigrationManager.upgrade()。
数据访问（DAO）
在 core/dao/repositories.py 实现最小可用方法：
StockRepository.get_all_codes()、save_many()
KlineRepository.get_range(ts_code, start, end)、latest_close_map()
这些实现内部使用 infrastructure.db.engine.get_session() 执行 SQL。
服务层（最小闭环）
DataService
refresh_stock_list()：从现有 data/fetcher.py 拉数据并通过 DAO 落库。
update_kline_range(codes, start, end)：增量拉取并落库。
SelectionService
select(cfg, start, end, codes=None)：基于已有逻辑的“无策略/全量”占位实现，先能返回结构化结果（空策略直通）。
可选：IndicatorService 先留空；BacktestService 先回传空 summary，占位即可。
API 路由打通
在 api/app.py 中 include_router 你的路由：
stocks：调用 StockRepository 返回分页列表（先用简单 LIMIT/OFFSET）
selection：调用 SelectionService.select 返回 JSON
backtest：返回占位数据或同步小回测
jobs：返回假数据，后续再接 JobQueue
定义 Pydantic Schema（新建 api/schemas/）以固定请求/响应字段，避免前后端耦合漂移。
WebUI 初步打通
在 webui/pages/02_选股.py 中添加一个简单表单与按钮，请求 POST /selection，把 JSON 渲染成表格。
在 webui/pages/01_仪表盘.py 调用 /health 显示数据库健康信息。
这一步只需要把最小闭环跑通（请求→响应→渲染）。
异步任务与进度（第二阶段）
实现 core/jobs/queue.py 简单内存队列/线程池。
selection 和 backtest 接口支持 async 模式（返回 job_id），/jobs/{id} 提供状态，WebUI 轮询或 WebSocket 展示进度。
策略与回测（第三阶段）
定义 core/strategy/interfaces.py 的真实输入输出契约。
实现基础策略（如 MA 交叉），在 SelectionService 调用。
完善 BacktestService 与 core/backtest/engine.py，生成 summary 与曲线数据。
工程化完善
加入 api/schemas、tests/、docker/（可选）、CI、代码格式化与类型检查。
README 增加接口文档与示例调用。