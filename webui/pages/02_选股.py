import streamlit as st
import pandas as pd
import requests

st.header("选股")

backend = st.session_state.get("backend_url", "http://localhost:8000")
st.text_input("后端地址", value=backend, key="backend_url")

# 检查是否有选中的行业
if 'selected_industry' in st.session_state:
    st.info(f"当前筛选行业: {st.session_state['selected_industry_name']}")
    if st.button("清除行业筛选"):
        del st.session_state['selected_industry']
        del st.session_state['selected_industry_name']
        st.rerun()

# 参数面板
col1, col2 = st.columns(2)
with col1:
    start = st.text_input("开始日期(yyyyMMdd)", value="20230101")
with col2:
    end = st.text_input("结束日期(yyyyMMdd)", value="20231231")

codes_csv = st.text_area("可选：指定代码(逗号分隔)", value="")

# 行业选择
try:
    # 获取最新交易日
    stats_resp = requests.get(f"{backend}/stocks/stats", timeout=5)
    latest_date = stats_resp.json().get("latest_trade_date", "20231231")
    
    # 获取行业统计数据
    industry_stats_resp = requests.get(f"{backend}/stocks/industries/stats-real?trade_date={latest_date}", timeout=10)
    industry_stats = industry_stats_resp.json()
    
    if industry_stats:
        industry_names = [ind['industry'] for ind in industry_stats]
        selected_industry = st.selectbox("选择行业", ["全部"] + industry_names)
    else:
        selected_industry = "全部"
        st.info("暂无行业数据，请先在首页点击'🏷️ 更新行业标签'按钮")
except Exception as e:
    selected_industry = "全部"
    st.warning(f"获取行业列表失败: {e}")

# 排序选项
sort_options = {
    "成交量": "volume",
    "成交额": "amount", 
    "涨幅": "pct_chg",
    "换手率": "turnover_rate"
}
sort_by = st.selectbox("排序方式", list(sort_options.keys()))

if st.button("运行选股"):
    try:
        codes = [c.strip() for c in codes_csv.split(',') if c.strip()] if codes_csv.strip() else None
        
        # 如果选择了特定行业，获取该行业的股票
        if selected_industry != "全部":
            industry_stocks_resp = requests.get(
                f"{backend}/stocks/industries/{selected_industry}/stocks-real",
                params={"limit": 1000},
                timeout=30
            )
            industry_stocks = industry_stocks_resp.json()
            if industry_stocks:
                codes = [stock['ts_code'] for stock in industry_stocks]
        
        payload = {"cfg": {}, "start": start, "end": end, "codes": codes}
        url = f"{st.session_state['backend_url'].rstrip('/')}/selection"
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        
        if not items:
            st.info("没有返回结果")
        else:
            df = pd.DataFrame(items)
            # 按选择的排序方式排序
            if sort_by in ["成交量", "成交额", "涨幅", "换手率"]:
                sort_field = sort_options[sort_by]
                if sort_field in df.columns:
                    df = df.sort_values(sort_field, ascending=False)
            
            st.dataframe(df, use_container_width=True)
            
            # 导出功能
            if st.button("导出结果"):
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载CSV",
                    data=csv,
                    file_name=f"选股结果_{start}_{end}.csv",
                    mime="text/csv"
                )
    except Exception as e:
        st.error(f"请求失败: {e}")
