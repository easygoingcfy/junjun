# A股选股分析工具（本地版）

本项目使用 Python + SQLite 构建，提供A股本地化数据采集、数据库管理、策略筛选、回测与可视化能力。

## 今日更新摘要（2025-08-11）
- 新增 回测模块：支持滚动回测、TopK、手续费（‰）、进出场模式（收盘/次日开盘等）、可选排除涨停信号；结果窗口包含资金曲线与可排序明细表，支持导出。
- 采集性能与配置升级：
  - 采集任务开关迁移至 `config.toml` 的 `[ingest]` 段，运行时自动读取；无需改代码即可切换任务。
  - 新增“按交易日批量采集”（TuShare）：单日合并抓取全市场 `daily + daily_basic` 并批量写库，显著减少请求次数。
  - 支持失败自动回退到“逐只增量”采集，以提升稳定性。
  - 板块/行业板块日线仅回填最近 N 天（可配置），并保留原有限速策略（≤180/min）。

---

## 最新进展（2025-08）
- 原子策略引擎（可自由组合）：
  - 涨幅类：区间累计涨幅阈值、窗口内存在单日大涨
  - 成交量：放量突破、缩量回调（可选回调收阴、回踩MA判定）
  - 均线系统：多头/空头排列、价格高于指定MA
  - 热度：基于新闻条数的近N日阈值（示例源）
  - 板块：包含/排除板块过滤
  - K线形态：吞没、锤子线、射击之星、十字星、晨星、黄昏星、母子形态、刺透、乌云盖顶、三白兵、三只乌鸦
  - 技术指标：N日新高突破、ATR波动过滤、MACD（dif>dea/金叉/hist>0）、RSI区间
- 结果列增强与可解释性：
  - 表格新增：通过明细（含tooltip详情）、评分（权重可配置并归一化到100）、未来5日收益%
  - 评分颜色：低分绿色→高分红色渐变；支持按列排序
  - 未来5日收益颜色：亏损红→盈利绿（±10%饱和）；支持按列排序
  - 查看详情：选中行一键弹窗查看完整通过明细
  - 导出：导出Excel包含增强列
- 回测模块：
  - 滚动回测，按交易日生成信号；支持 TopK（按评分选前K）、手续费（‰，双边计扣）、最大回撤、均值/中位数/胜率等统计
  - 进出场模式：入场（收盘/次日开盘）、出场（收盘/开盘）
  - 排除涨停：可选开启并配置阈值
  - 结果窗口：资金曲线 + 可排序明细表（收益列颜色映射）
  - 导出：回测信号CSV
- 可视化：K线价格/成交量双子图，支持多均线、形态标注与当日涨跌幅标注
- 数据增强：板块/概念/成分、板块日线（热度近似）、个股新闻热度（示例源）
- 性能与健壮性：
  - 新增按交易日批量采集（TuShare）+ 批量写库（executemany）
  - 采集任务可配置化（config.toml/[ingest]）
  - 板块/行业板块日线仅回填最近 N 天
  - 支持数据表按需扩列迁移、批量采集限速（≤180/min）

## 数据来源
- TuShare（推荐）：
  - 股票列表/基础字段（stock_basic）
  - 日线行情（daily）与基础（日频）扩展（daily_basic）
  - 指数基础（index_basic）、指数日线（index_daily）、指数成分（index_weight）
- AkShare（开源备选）：
  - A股历史行情（stock_zh_a_hist）
  - 概念名称与成分（同花顺板块接口）
  - 新闻列表（示例：stock_news_em，作为按日新闻条数热度的粗略来源）

说明：部分第三方接口策略可能调整，如数据字段或可用性变化，请根据运行时提示适配。

## 数据库存储结构
- stock_info（股票基础）
  - ts_code, name, industry, list_date, market, exchange, area, is_st, list_status
- daily_kline（日线行情）
  - ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, turnover_rate
  - 扩展：pre_close, amplitude(振幅%), volume_ratio(量比), circ_mv(流通市值), total_mv(总市值)
- concept / concept_member（概念与成分）
  - concept(concept_code, name, source, description)
  - concept_member(concept_code, ts_code, in_date, out_date)
- board / board_member（指数/板块与成分）
  - board(board_code, name, type, source)
  - board_member(board_code, ts_code, in_date, out_date, weight)
- board_daily（板块/指数日线快照，用于板块热度）
  - board_code, date, close, pct_chg, vol, amount
- heat_data（个股热度/情绪快照）
  - ts_code, date, source, news_count, search_score, forum_count, sentiment, board_hotness

注：数据库迁移采取“按需扩列”，首次运行会自动创建/补充缺失列。

## 采集流程（可配置）
见 `data/fetch_and_save.py`：
1. 获取并保存股票列表
2. 拉取并保存概念列表与成分（可选）
3. 拉取并保存指数/板块及其成分，并获取指数日线（board_daily，作为板块热度，可选）
4. 个股日线更新：
   - 优先：按交易日批量采集（TuShare，一天合并全市场 `daily+daily_basic`）→ 批量写库
   - 回退：逐只增量采集（沿用限速 ≤ 180/min）
   - 自动包含扩展字段：pre_close、amplitude、volume_ratio、circ_mv、total_mv
5. 采集“新闻条数热度”（按日计数，占位/粗略实现，可选）并写入 heat_data

## 回测模块
- 配置入口：主窗口回测配置区（窗口长度、前瞻N、手续费‰、TopK、入场/出场模式、排除涨停及阈值）
- 执行：点击“运行回测”打开结果窗口；可“导出回测明细CSV”
- 结果窗口：
  - 概览统计：周期、信号数、胜率、平均/中位收益、扣费后收益、最大回撤
  - 资金曲线：按信号顺序串行累积
  - 明细表：可排序；收益列按“亏损红→盈利绿”着色

## 策略筛选与评分
- 策略配置入口：主窗口中各组参数均可同时启用，作为“与”的关系逐一过滤
- 评分：对启用项按自定义权重计分并归一化到100，默认权重为 量能30/均线20/突破25/形态15/MACD5/RSI5；支持一键“重置默认”
- 通过明细：简要标签 + tooltip完整说明；支持“查看详情”弹窗
- 前瞻收益：以筛选区间末日收盘为基准，向后第5个交易日收益；数据不足显示“-”

## 可视化
- K线+成交量双子图、可选多条均线
- 形态标注与当日涨跌幅标注

## 依赖安装
```
pip install -r requirements.txt
```

## 配置
在项目根目录创建或编辑 `config.toml`：

- TuShare Token（启用按日批量采集需配置）：
```
[tushare]
token = "你的TuShare Token"
```

- 数据采集任务开关（无需改代码即可切换）：
```
[ingest]
# 概念与成分
do_concept = false
# 指数/板块与成分，以及板块日线
do_boards = false
# 同花顺行业板块与日线
do_industry_boards = false
# 个股日线增量
do_stocks_daily = true
# 个股日线优先按交易日批量抓取（需要 TuShare）
do_stocks_daily_batch = true
# 新闻条数热度
do_news_heat = false
# 限制板块/行业板块日线仅回填最近N天
board_recent_days = 7
```

## 注意事项
- TuShare 按日批量采集需有效 token；若不可用将自动回退到逐只增量模式。
- 接口存在频率限制，默认逐只模式限速 ≤180 次/分钟。
- AkShare/网页源接口会不定期变化，若报错请根据实际接口字段及时调整函数。

## 后续建议
- 数据采集：继续完善“按交易日批量”在无 `daily_basic` 可用时的兼容与重试；为常用查询添加数据库索引
- 回测增强：支持参数网格/多组对比、导出资金曲线与日度聚合统计、分层分析（行业/市值/因子）
- 评分与可视化：评分/颜色阈值可配置；表格分页/异步加载；结果列表导出更多格式
- 数据增强：更稳定的热度源、资金流/龙虎榜、限售解禁/回购/分红、财务因子与估值

## 许可
仅做学习与研究使用，数据版权归原数据源所有。
