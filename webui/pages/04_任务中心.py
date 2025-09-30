# TODO
# - 列表展示后台任务，查看状态与取消
# - 订阅WebSocket进度推送占位

import streamlit as st
import requests

st.header("任务中心")

backend = st.session_state.get("backend_url", "http://localhost:8000")
st.text_input("后端地址", value=backend, key="backend_url")

job_id = st.text_input("Job ID", value="")
col1, col2 = st.columns(2)
with col1:
    if st.button("查询状态") and job_id.strip():
        try:
            url = f"{st.session_state['backend_url'].rstrip('/')}/jobs/{job_id.strip()}"
            resp = requests.get(url, timeout=30)
            st.json(resp.json())
        except Exception as e:
            st.error(f"查询失败: {e}")
with col2:
    if st.button("取消任务") and job_id.strip():
        try:
            url = f"{st.session_state['backend_url'].rstrip('/')}/jobs/{job_id.strip()}/cancel"
            resp = requests.post(url, timeout=30)
            st.json(resp.json())
        except Exception as e:
            st.error(f"取消失败: {e}")
