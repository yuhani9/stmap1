import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

# --- ページ設定 ---
st.set_page_config(page_title="九州気温 3D Map", layout="wide")
st.title("九州主要都市の現在の気温 3Dカラムマップ")

# 九州7県のデータ
kyushu_capitals = {
    'Fukuoka':    {'lat': 33.5904, 'lon': 130.4017},
    'Saga':       {'lat': 33.2494, 'lon': 130.2974},
    'Nagasaki':   {'lat': 32.7450, 'lon': 129.8739},
    'Kumamoto':   {'lat': 32.7900, 'lon': 130.7420},
    'Oita':       {'lat': 33.2381, 'lon': 131.6119},
    'Miyazaki':   {'lat': 31.9110, 'lon': 131.4240},
    'Kagoshima':  {'lat': 31.5600, 'lon': 130.5580}
}

# --- データ取得関数 ---
@st.cache_data(ttl=600)
def fetch_hourly_temperatures():
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    hourly_by_city = {}
    time_index = None

    for city, coords in kyushu_capitals.items():
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "hourly": "temperature_2m",
            "timezone": "Asia/Tokyo",
            "forecast_days": 2
        }
        r = requests.get(BASE_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        times = data["hourly"]["time"]                 # 例: "2026-01-16T18:00"
        temps = data["hourly"]["temperature_2m"]       # 同じ長さの配列

        if time_index is None:
            time_index = times  # 都市間で同じ想定（Open-Meteoは通常揃う）

        hourly_by_city[city] = temps

    return time_index, hourly_by_city

@st.cache_data(ttl=600)
def fetch_weather_data():
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    
    for city, coords in kyushu_capitals.items():
        params = {
            'latitude':  coords['lat'],
            'longitude': coords['lon'],
            'current': 'temperature_2m'
        }
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            weather_info.append({
                'City': city,
                'lat': coords['lat'],
                'lon': coords['lon'],
                'Temperature': data['current']['temperature_2m']
            })
        except Exception as e:
            st.error(f"Error fetching {city}: {e}")
            
    return pd.DataFrame(weather_info)

# まず「都市の座標df」だけ作る（気温はスライダーで入れる）
df = pd.DataFrame([
    {"City": city, "lat": coords["lat"], "lon": coords["lon"]}
    for city, coords in kyushu_capitals.items()
])

with st.spinner("最新の気温データ（時間別）を取得中..."):
    time_list, hourly_by_city = fetch_hourly_temperatures()

# スライダー（時刻選択）
# ここでは「インデックススライダー」にして、表示だけ時刻文字列にする
selected_idx = st.slider(
    "表示する時刻（JST）",
    min_value=0,
    max_value=len(time_list) - 1,
    value=0
)

selected_time = time_list[selected_idx]
st.caption(f"選択中: {selected_time} (JST)")

# 選択時刻の気温をdfに流し込む
df["Temperature"] = df["City"].map(lambda c: hourly_by_city[c][selected_idx])

# 高さに変換
df["elevation"] = df["Temperature"] * 3000


# --- メインレイアウト ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("取得したデータ")
    st.dataframe(df[['City', 'Temperature']], use_container_width=True)
    
    if st.button('データを更新'):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.subheader("3D カラムマップ")

    # Pydeck の設定
    view_state = pdk.ViewState(
        latitude=32.7,
        longitude=131.0,
        zoom=6.2,
        pitch=45,  # 地図を傾ける
        bearing=0
    )

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='elevation',
        radius=12000,        # 柱の太さ
        get_fill_color='[100, 100, 0, 180]', # 柱の色（オレンジ系）
        pickable=True,       # ホバーを有効に
        auto_highlight=True,
    )

    # 描画
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
    "html": "<b>{City}</b><br>気温: {Temperature}°C<br>時刻: " + selected_time,
    "style": {"color": "white"}
}
    ))
