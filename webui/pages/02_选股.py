# TODO
# - 参数面板：策略配置、时间区间、代码过滤
# - 触发后端选股，并显示结果表格与导出

import streamlit as st
import pandas as pd
import requests

st.header("选股")

backend = st.session_state.get("backend_url", "http://localhost:8000")
st.text_input("后端地址", value=backend, key="backend_url")

col1, col2 = st.columns(2)
with col1:
    start = st.text_input("开始日期(yyyyMMdd)", value="20230101")
with col2:
    end = st.text_input("结束日期(yyyyMMdd)", value="20231231")

codes_csv = st.text_area("可选：指定代码(逗号分隔)", value="")

if st.button("运行选股"):
    try:
        codes = [c.strip() for c in codes_csv.split(',') if c.strip()] if codes_csv.strip() else None
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
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"请求失败: {e}")
