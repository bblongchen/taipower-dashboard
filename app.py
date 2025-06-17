import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

def fetch_taipower_data():
    url = "https://restless-sunset-f1b0.bblong-chen.workers.dev/"
    res = requests.get(url)
    res.raise_for_status()
    records = res.json().get("records", [])

    if not records or "curr_load" not in records[0]:
        raise ValueError("無法從資料中解析 curr_load 欄位")

    data = records[0]
    curr_load = float(data["curr_load"])
    util_rate = float(data["curr_util_rate"])

    df = pd.DataFrame([
        {"key": "目前尖峰負載(MW)", "value": curr_load},
        {"key": "目前備轉容量(MW)", "value": round(curr_load * util_rate / 100, 2)},
        {"key": "備轉率(%)", "value": util_rate},
        {"key": "更新時間", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ])
    return df

def simulate_city_load(df):
    load = float(df[df["key"] == "目前尖峰負載(MW)"]["value"].values[0])
    city_ratio = {
        "台北市": 0.15,
        "新北市": 0.12,
        "高雄市": 0.10,
        "台中市": 0.10
    }
    return {city: round(ratio * load, 2) for city, ratio in city_ratio.items()}

st.set_page_config(page_title="台電電力資訊儀表板", layout="centered")
st.title("🔌 台電電力資訊儀表板")
st_autorefresh(interval=600000, key="data_refresh")  # 每10分鐘刷新

try:
    df = fetch_taipower_data()
    st.success("資料載入成功 ✅")
    st.dataframe(df, use_container_width=True)

    st.subheader("🏙 城市模擬用電（估算）")
    city_load = simulate_city_load(df)
    st.json(city_load)

except Exception as e:
    st.error(f"資料載入錯誤：{e}")
