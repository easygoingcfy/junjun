# TODO
# - 参数面板：窗口、前瞻、费用、规则
# - 触发后端回测，展示summary与资金曲线/明细

import streamlit as st
import requests
import pandas as pd

st.header("回测")

backend = st.session_state.get("backend_url", "http://localhost:8000")
st.text_input("后端地址", value=backend, key="backend_url")

col1, col2, col3 = st.columns(3)
with col1:
    start = st.text_input("开始日期(yyyyMMdd)", value="20230101")
with col2:
    end = st.text_input("结束日期(yyyyMMdd)", value="20231231")
with col3:
    lookback = st.number_input("回看窗口N", value=60, min_value=5, max_value=300, step=1)

forward_n = st.number_input("前瞻天数", value=5, min_value=1, max_value=60, step=1)
codes_csv = st.text_area("可选：指定代码(逗号分隔)", value="")

if st.button("运行回测"):
    try:
        codes = [c.strip() for c in codes_csv.split(',') if c.strip()] if codes_csv.strip() else None
        payload = {"cfg": {}, "start": start, "end": end, "codes": codes, "lookback": lookback, "forward_n": forward_n}
        url = f"{st.session_state['backend_url'].rstrip('/')}/backtest"
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        st.subheader("Summary")
        st.json(data.get("summary", {}))
        sig = data.get("signals", [])
        if sig:
            st.subheader("Signals")
            df = pd.DataFrame(sig)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无信号明细(占位)")
    except Exception as e:
        st.error(f"请求失败: {e}")
