
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from prophet import Prophet

@st.cache_data(ttl=600)  # 每10分鐘快取更新
def fetch_data():
    url = "https://restless-sunset-f1b0.bblong-chen.workers.dev/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("records", [])
    except Exception as e:
        st.error(f"❌ 無法載入即時電力資料：{e}")
        return []

st.set_page_config(page_title="城市級電力調度模擬", layout="wide")

st.title("🏙️ 城市級電力調度模擬")

# 自動刷新每 10 分鐘 (600000 ms)
st_autorefresh(interval=600000, key="refresh")

@st.cache_data(ttl=600)
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
        {"key": "更新時間", "value": (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")}
    ])
    return df, curr_load

df, total_load = fetch_taipower_data()

st.subheader("🔌 台電今日電力資訊：全國即時電力數據")
st.dataframe(df, use_container_width=True)

# 城市模擬
st.subheader("🔢 城市級電力調度模擬：六都")
city_ratios = {
    "台北市": 0.18,
    "新北市": 0.22,
    "桃園市": 0.15,
    "台中市": 0.20,
    "台南市": 0.12,
    "高雄市": 0.13
}

city_data = {
    "城市": [],
    "尖峰負載(MW)": [],
    "模擬備轉容量(MW)": []
}

util_rate = df[df["key"] == "備轉率(%)"]["value"].values[0]
for city, ratio in city_ratios.items():
    load = round(total_load * ratio, 2)
    reserve = round(load * util_rate / 100, 2)
    city_data["城市"].append(city)
    city_data["尖峰負載(MW)"].append(load)
    city_data["模擬備轉容量(MW)"].append(reserve)

city_df = pd.DataFrame(city_data)
st.dataframe(city_df, use_container_width=True)

# 圖表呈現
st.subheader("📊 城市電力負載與備轉容量")
st.bar_chart(city_df.set_index("城市")[["尖峰負載(MW)", "模擬備轉容量(MW)"]])

def generate_fake_city_data(city_name, base_value=3600, noise_level=0.03):
    import numpy as np
    import pandas as pd

    now = pd.Timestamp.now().tz_localize(None)  # 拿掉時區
    ds_list = [now - pd.Timedelta(minutes=10 * i) for i in reversed(range(48))]
    y_list = [base_value * (1 + np.random.uniform(-noise_level, noise_level)) for _ in range(48)]
    df = pd.DataFrame({'ds': ds_list, 'y': y_list})
    return df

def forecast_city(df):
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)  # 移除時區
    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=6, freq='10min')  # 預測下一小時
    forecast = model.predict(future)

    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

import streamlit as st
import plotly.graph_objects as go

st.subheader("🔮 六都 AI 用電預測")

cities = {
    "台北市": 3700,
    "新北市": 3800,
    "桃園市": 3600,
    "台中市": 3900,
    "台南市": 3500,
    "高雄市": 4100,
}

for city, base in cities.items():
    df_city = generate_fake_city_data(city, base)
    forecast = forecast_city(df_city)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_city['ds'], y=df_city['y'], mode='lines+markers', name='歷史用電'))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='預測用電'))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='預測上限', line=dict(dash='dot')))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='預測下限', line=dict(dash='dot')))

    st.markdown(f"**{city} 用電預測圖表**")
    st.plotly_chart(fig, use_container_width=True)
