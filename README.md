# A股选股分析工具（本地版）

本项目使用 Python + SQLite 构建，提供A股本地化数据采集、数据库管理、策略筛选与可视化能力。

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
- 可视化：K线价格/成交量双子图，支持多均线、形态标注与当日涨跌幅标注
- 数据增强：板块/概念/成分、板块日线（热度近似）、个股新闻热度（示例源）
- 程序健壮性：支持数据表按需扩列迁移、批量采集限速（≤180/min）

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

## 采集流程
见 `data/fetch_and_save.py`：
1. 获取并保存股票列表
2. 拉取并保存概念列表与成分
3. 拉取并保存指数/板块及其成分，并获取指数日线（board_daily，作为板块热度）
4. 按股票增量更新日线行情（含扩展字段）
5. 采集“新闻条数热度”（按日计数，占位/粗略实现）并写入 heat_data

限速：默认 ≤ 180 请求/分钟。

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
在项目根目录创建 `config.toml` 并写入 TuShare token：
```
[tushare]
token = "你的TuShare Token"
```

## 注意事项
- TuShare 分钟级分时数据通常需要更高积分/权限，项目默认不抓分时。
- AkShare/网页源接口会不定期变化，若报错请根据实际接口字段及时调整函数。

## 后续建议
- 轻量回测模块：对当前策略在近1-3年滚动回测，输出胜率、均值/中位数收益、收益分布、最大回撤、收益曲线；支持导出
- 评分增强：加入因子维度（如量比、波动率、行业/板块热度加权、估值约束等）并做标准化与打分融合；支持保存/加载评分预设
- 更多原子策略：
  - 布林带（收口/开口/中轨支撑/上轨突破）
  - 均线粘合与发散、均线多重回踩
  - 高低点结构（HH/HL/LL/LH）与箱体震荡
  - 量价背离、MACD结构（双底/双顶/背离）
- 性能优化：为常用查询添加索引、异步加载与分页表格、向量化计算减少循环
- 数据增强：更稳定的热度源、资金流/龙虎榜、限售解禁/回购/分红、财务基本面与估值
- UI/UX：表格条件高亮、筛选条件保存/载入、评分颜色阈值可配置、快捷筛选模板

## 许可
仅做学习与研究使用，数据版权归原数据源所有。
