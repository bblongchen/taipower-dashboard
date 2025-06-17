
import streamlit as st
from prophet import Prophet
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

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

import pandas as pd
import numpy as np

def generate_fake_city_data(city_name, base_value=3600, noise_level=0.05):
    now = pd.Timestamp.now(tz='Asia/Taipei')
    ds_list = [now - pd.Timedelta(minutes=10 * i) for i in reversed(range(30))]
    y_list = [base_value * (1 + np.random.uniform(-noise_level, noise_level)) for _ in range(30)]
    df = pd.DataFrame({'ds': ds_list, 'y': y_list})
    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = pd.to_numeric(df['y'])
    return df

# 假設這是目前尖峰負載（從 Cloudflare proxy API 拿到的）
try:
    records = fetch_data()
    if not records or "curr_load" not in records[0]:
        raise ValueError("curr_load 欄位缺失")   
    curr_load = float(records[0].get("curr_load", 3600))
except Exception as e:
    st.error(f"⚠️ 無法載入即時負載資料：{e}")
    st.stop()
    st.subheader("🔎 即時電力資料記錄")
    st.json(records)

st.subheader("📈 AI 模擬尖峰負載預測")

try:
    hist_df = generate_fake_city_data(curr_load)
    m = Prophet()
    m.fit(hist_df)
    future = m.make_future_dataframe(periods=7)
    forecast = m.predict(future)
    forecast_display = forecast.set_index("ds")[["yhat", "yhat_upper", "yhat_lower"]].tail(14)
    st.line_chart(forecast_display)
except Exception as e:
    st.error(f"預測模型錯誤：{e}")

# 🔧 模擬城市歷史負載資料
def generate_fake_city_data(city_name, base_value, noise_level=0.05):
    now = pd.Timestamp.now(tz='Asia/Taipei')
    ds_list = [now - pd.Timedelta(minutes=10 * i) for i in reversed(range(30))]
    y_list = [base_value * (1 + np.random.uniform(-noise_level, noise_level)) for _ in range(30)]
    df = pd.DataFrame({'ds': ds_list, 'y': y_list})
    df['ds'] = pd.to_datetime(df['ds'])  # 確保時間格式
    df['y'] = pd.to_numeric(df['y'])     # 確保數值格式
    return df

# 🤖 預測未來負載
def forecast_city(df):
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=6, freq='H')
    forecast = model.predict(future)
    return forecast

st.subheader("🔮 六都 AI 電力負載預測")

city_name = st.selectbox("請選擇城市", ["台北", "新北", "桃園", "台中", "台南", "高雄"])
city_base_load = {
    "台北": 580,
    "新北": 740,
    "桃園": 620,
    "台中": 810,
    "台南": 430,
    "高雄": 770,
}

df_city = generate_fake_city_data(city_name, city_base_load[city_name])
forecast = forecast_city(df_city)

fig = px.line(forecast, x='ds', y='yhat', title=f"{city_name} 未來 6 小時 AI 預測電力負載", labels={'ds': '時間', 'yhat': '預測負載（MW）'})
st.plotly_chart(fig, use_container_width=True)
