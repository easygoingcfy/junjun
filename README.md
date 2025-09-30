# 架构设计
设计原则：

简洁：最小化层间依赖，用接口/抽象类定义通信。核心层聚焦业务逻辑（统计/选股），避免UI细节。
高效：用ORM（如SQLAlchemy）简化数据库交互；Pandas/NumPy加速计算；策略模式（Strategy Pattern）允许动态切换自定义策略。缓存（如Redis，如果规模大）或内存数据框优化重复查询。
扩展性：支持插件式策略（用户自定义Python脚本加载）；日志/错误处理确保鲁棒性。
性能考虑：SQLite单线程限速，对于海量股票数据（历史OHLCV），预计算指标存储；用多线程/异步（asyncio）并行选股。
## 数据层： Sqlite
## 核心层
设计目标： 可重用、模块化、易测试

把核心层拆分成单独的子模块，职责单一、接口明确：
core/
  dao/                # 数据访问层（SQLite 封装，SQLAlchemy）
  model/              # 域模型（Stock, OHLCV, Indicator, Strategy, Signal）
  service/            # 业务逻辑（指标计算、选股逻辑）
  strategy/           # 策略引擎（策略定义、策略插件）
  backtest/           # 回测引擎（交易模拟、绩效统计）
  jobs/               # 后台任务管理（调度、队列）
  api.py              # 如果用 HTTP：把service暴露为 REST/WS

关键设计点

* DAO（Repository）模式：所有 DB 操作通过 DAO，方便切换 DB 或 mock 测试。
* 服务层（Service）：封装指标计算、数据拉取、批量操作，不包含 UI 逻辑。
* 策略引擎（最重要）：
  * 策略为插件：每个策略实现一个统一接口（init、on_data/run、backtest、params）。
  * 策略运行有两种模式：实时/信号推送（stream）与 批量回测（batch）。
  * 将策略配置、版本、运行记录写到 DB（可回溯）。
* 事件/消息机制：核心对外推送事件（新信号/策略结果/任务进度），UI 通过 WebSocket 或 PyQt 信号订阅。
* 后台任务：长耗时的计算（如重算多数股票指标、回测）放到后台执行（ProcessPoolExecutor 或简单队列），返回 job_id，允许取消与查看进度。

架构
使用python后端(fastAPI) + Streamlit前端来实现， 前端通过REST/WS与后端交互。
## UI层

