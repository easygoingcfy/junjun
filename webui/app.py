import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Stock Selection", layout="wide")

st.title("📈 A股选股分析系统")

# 获取后端地址
backend = st.session_state.get("backend_url", "http://localhost:8000")
st.text_input("后端地址", value=backend, key="backend_url")

# 系统概览
st.header("📊 系统概览")
col1, col2, col3, col4 = st.columns(4)

try:
    # 健康检查
    health_resp = requests.get(f"{backend}/health", timeout=5)
    health_status = "✅ 正常" if health_resp.status_code == 200 else "❌ 异常"
except:
    health_status = "❌ 连接失败"

# 获取真实数据
try:
    # 获取股票统计信息
    stats_resp = requests.get(f"{backend}/stocks/stats", timeout=5)
    stats_data = stats_resp.json()
    total_stocks = stats_data.get("total_stocks", 0)
    latest_date = stats_data.get("latest_trade_date", "未知")
    if latest_date and latest_date != "未知":
        # 格式化日期显示
        try:
            from datetime import datetime
            dt = datetime.strptime(latest_date, "%Y%m%d")
            latest_date = dt.strftime("%Y-%m-%d")
        except:
            pass
except:
    total_stocks = "未知"
    latest_date = "未知"

# 运行中任务数
try:
    jobs_resp = requests.get(f"{backend}/jobs/stats", timeout=5)
    jobs_data = jobs_resp.json()
    running_tasks = jobs_data.get("running_tasks", 0)
except:
    running_tasks = 0

with col1:
    st.metric("系统状态", health_status)
with col2:
    st.metric("股票总数", f"{total_stocks:,d}")
with col3:
    st.metric("最新交易日", latest_date)
with col4:
    st.metric("运行中任务", running_tasks)

# 快速操作
st.header("🚀 快速操作")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔄 刷新股票列表", use_container_width=True):
        with st.spinner("正在刷新..."):
            try:
                # 通过API调用刷新股票列表
                refresh_resp = requests.post(f"{backend}/stocks/refresh", timeout=60)
                if refresh_resp.status_code == 200:
                    result = refresh_resp.json()
                    st.success(f"刷新完成！更新了 {result.get('count', 0)} 只股票")
                else:
                    st.error(f"刷新失败: {refresh_resp.text}")
            except Exception as e:
                st.error(f"刷新失败: {e}")

with col2:
    if st.button("📊 计算统计数据", use_container_width=True):
        with st.spinner("正在计算统计数据..."):
            try:
                # 获取最新交易日
                stats_resp = requests.get(f"{backend}/stocks/stats", timeout=5)
                stats_data = stats_resp.json()
                latest_date = stats_data.get("latest_trade_date")
                
                if latest_date:
                    # 计算统计数据
                    calc_resp = requests.post(f"{backend}/stocks/calculate-stats", 
                                            json={"trade_date": latest_date}, timeout=60)
                    calc_data = calc_resp.json()
                    st.success(f"统计完成！计算了 {calc_data['industry_stats_calculated']} 个行业和 {calc_data['stock_stats_calculated']} 只股票的统计数据")
                else:
                    st.warning("无法获取最新交易日")
            except Exception as e:
                st.error(f"计算失败: {e}")

with col3:
    if st.button("📈 快速选股", use_container_width=True):
        st.info("跳转到选股页面")

with col4:
    if st.button("📊 快速回测", use_container_width=True):
        st.info("跳转到回测页面")

# 市场概览
st.header("📊 市场概览")

# 行业标签
st.subheader("🏷️ 行业标签")

# 行业数据管理
st.subheader("📊 行业数据管理")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔄 更新股票行业", use_container_width=True):
        with st.spinner("正在更新股票行业标签..."):
            try:
                update_resp = requests.post(f"{backend}/stocks/update-industries-real", timeout=120)
                if update_resp.status_code == 200:
                    result = update_resp.json()
                    if "error" in result:
                        st.error(f"更新失败: {result['error']}")
                    else:
                        st.success(f"股票行业更新完成！更新了 {result.get('updated_count', 0)} 只股票")
                        st.rerun()
                else:
                    st.error(f"更新失败: {update_resp.text}")
            except Exception as e:
                st.error(f"更新失败: {e}")

with col2:
    if st.button("📈 同步行业指数", use_container_width=True):
        with st.spinner("正在同步行业指数数据..."):
            try:
                sync_resp = requests.post(f"{backend}/stocks/sync-industry-data", timeout=300)
                if sync_resp.status_code == 200:
                    result = sync_resp.json()
                    if "error" in result:
                        st.error(f"同步失败: {result['error']}")
                    else:
                        st.success("行业指数数据同步完成！")
                        st.json(result.get("result", {}))
                        st.rerun()
                else:
                    st.error(f"同步失败: {sync_resp.text}")
            except Exception as e:
                st.error(f"同步失败: {e}")

with col3:
    if st.button("🔍 验证数据", use_container_width=True):
        with st.spinner("正在验证数据..."):
            try:
                validation_resp = requests.get(f"{backend}/stocks/validate-industries", timeout=30)
                if validation_resp.status_code == 200:
                    result = validation_resp.json()
                    if "error" in result:
                        st.error(f"验证失败: {result['error']}")
                    else:
                        st.success("数据验证完成！")
                        st.json(result)
                else:
                    st.error(f"验证失败: {validation_resp.text}")
            except Exception as e:
                st.error(f"验证失败: {e}")

try:
    # 获取行业统计数据
    industry_stats_resp = requests.get(f"{backend}/stocks/industries/stats", timeout=10)
    industry_stats_resp.raise_for_status()
    industry_stats = industry_stats_resp.json()
    
    if industry_stats:
        # 使用排行榜式的柱状图显示行业标签
        st.markdown("**行业成交量排行榜**")
        
        # 准备数据
        top_industries = industry_stats[:15]  # 显示前15个行业
        industry_data = []
        for industry in top_industries:
            # 格式化成交量单位
            volume = industry['total_volume']
            if volume >= 1e8:
                volume_text = f"{volume/1e8:.1f}亿"
            elif volume >= 1e4:
                volume_text = f"{volume/1e4:.1f}万"
            else:
                volume_text = f"{volume:,.0f}"
            
            industry_data.append({
                "行业": industry['industry_name'],
                "成交量(万手)": volume / 10000,  # 转换为万手
                "股票数": industry['stock_count'],
                "成交量显示": volume_text,
                "指数代码": industry['index_code'],
                "涨跌幅": industry['avg_pct_chg']
            })
        
        # 创建DataFrame
        df = pd.DataFrame(industry_data)
        
        # 使用交互式图表
        import plotly.express as px
        fig = px.bar(
            df, 
            x="成交量(万手)", 
            y="行业",
            orientation='h',
            title="行业成交量排行榜",
            hover_data=["股票数", "成交量显示"],
            color="成交量(万手)",
            color_continuous_scale="Blues"
        )
        fig.update_layout(
            height=600,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title="成交量(万手)",
            yaxis_title="行业"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 添加点击选择功能
        st.markdown("**点击选择行业进行筛选**")
        selected_industry = st.selectbox(
            "选择行业进行筛选",
            ["全部"] + [industry['industry_name'] for industry in top_industries],
            key="industry_selector"
        )
        
        if selected_industry != "全部":
            # 找到选中行业的指数代码
            selected_industry_info = next((industry for industry in top_industries if industry['industry_name'] == selected_industry), None)
            if selected_industry_info:
                if st.button(f"🔍 筛选 {selected_industry} 行业股票", use_container_width=True):
                    st.session_state['selected_industry'] = selected_industry_info['index_code']
                    st.session_state['selected_industry_name'] = selected_industry
                    st.rerun()
    else:
        st.info("暂无行业数据，请先点击'🏷️ 更新行业标签'按钮")
except requests.exceptions.RequestException as e:
    st.error(f"网络请求失败: {e}")
except Exception as e:
    st.error(f"获取行业数据失败: {e}")

# 行业分布图表
st.subheader("行业分布")
try:
    # 使用与行业标签相同的数据源
    if industry_stats:
        # 取前10个行业，按成交量排序
        top_industries = industry_stats[:10]
        
        if top_industries:
            # 创建行业分布数据
            industry_data = []
            for industry in top_industries:
                industry_data.append({
                    "行业": industry['industry'],
                    "股票数量": industry['stock_count'],
                    "成交量": industry['total_volume']
                })
            
            industry_df = pd.DataFrame(industry_data)
            st.bar_chart(industry_df.set_index("行业")["股票数量"])
        else:
            st.info("暂无行业数据")
    else:
        st.info("暂无行业数据")
except Exception as e:
    st.error(f"获取行业数据失败: {e}")

# 最近活动
st.header("📋 最近活动")

# 最近选股结果
st.subheader("最近选股结果")
try:
    # 调用选股接口获取最近结果
    selection_payload = {
        "cfg": {},
        "start": "20240101",
        "end": "20241231",
        "codes": None
    }
    selection_resp = requests.post(f"{backend}/selection", json=selection_payload, timeout=30)
    selection_data = selection_resp.json()
    items = selection_data.get("items", [])
    
    if items:
        # 取前5个结果
        top_5 = items[:5]
        df_data = []
        for item in top_5:
            df_data.append({
                "代码": item.get("ts_code", ""),
                "名称": item.get("name", ""),
                "行业": item.get("industry", ""),
                "收盘价": f"{item.get('close', 0):.2f}" if item.get('close') else "-",
                "评分": f"{item.get('score', 0):.1f}"
            })
        
        if df_data:
            recent_selection = pd.DataFrame(df_data)
            st.dataframe(recent_selection, use_container_width=True)
        else:
            st.info("暂无选股结果")
    else:
        st.info("暂无选股结果")
except Exception as e:
    st.error(f"获取选股结果失败: {e}")

# 最近回测结果
st.subheader("最近回测结果")
try:
    # 调用回测接口获取最近结果
    backtest_payload = {
        "cfg": {},
        "start": "20240101",
        "end": "20241231",
        "codes": None,
        "lookback": 60,
        "forward_n": 5
    }
    backtest_resp = requests.post(f"{backend}/backtest", json=backtest_payload, timeout=60)
    backtest_data = backtest_resp.json()
    summary = backtest_data.get("summary", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        win_rate = summary.get("win_rate", 0)
        st.metric("胜率", f"{win_rate:.1f}%")
    with col2:
        avg_ret = summary.get("avg_ret", 0)
        st.metric("平均收益", f"{avg_ret:.1f}%")
    with col3:
        mdd = summary.get("mdd", 0)
        st.metric("最大回撤", f"{mdd:.1f}%")
    with col4:
        signals = summary.get("signals", 0)
        st.metric("信号数量", f"{signals}")
        
except Exception as e:
    st.error(f"获取回测结果失败: {e}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("胜率", "N/A")
    with col2:
        st.metric("平均收益", "N/A")
    with col3:
        st.metric("最大回撤", "N/A")
    with col4:
        st.metric("信号数量", "N/A")

# 系统状态
st.header("🔧 系统状态")
status_col1, status_col2 = st.columns(2)

with status_col1:
    st.subheader("数据库状态")
    if health_status == "✅ 正常":
        st.info("✅ SQLite 连接正常")
        st.info(f"📅 最新交易日: {latest_date}")
        st.info(f"📊 股票总数: {total_stocks:,d}")
    else:
        st.error("❌ 数据库连接异常")

with status_col2:
    st.subheader("服务状态")
    st.info(f"🔧 后端服务: {health_status}")
    st.info("✅ 前端界面正常")
    if running_tasks > 0:
        st.info(f"⚙️ 运行中任务: {running_tasks}")
    else:
        st.info("⚙️ 无运行中任务")

# 快速链接
st.header("🔗 快速导航")
nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)

with nav_col1:
    st.link_button("📈 选股分析", "/选股")
with nav_col2:
    st.link_button("📊 回测分析", "/回测")
with nav_col3:
    st.link_button("⚙️ 任务中心", "/任务中心")
with nav_col4:
    st.link_button("📋 系统日志", "#")

st.info("💡 提示：使用左侧导航栏可以快速访问各个功能模块")
