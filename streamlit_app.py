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
kagoshima_local_cities = {
    "Kagoshima City": {"lat": 31.5966, "lon": 130.5571},
    "Izumi": {"lat": 32.0906, "lon": 130.3521},
    "Ichikikushikino": {"lat": 31.7203, "lon": 130.2696},
    "Kirishima": {"lat": 31.7426, "lon": 130.7632},
    "Satsumasendai": {"lat": 31.8133, "lon": 130.3044},
    "Kanoya": {"lat": 31.3783, "lon": 130.8525},
    "Minamisatsuma": {"lat": 31.4167, "lon": 130.3167},
    "Shibushi": {"lat": 31.4769, "lon": 131.1036},
    "Tarumizu": {"lat": 31.4878, "lon": 130.6997},
    "Aira": {"lat": 31.7311, "lon": 130.6239},
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
def fetch_hourly_temperatures(cities_dict):
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    hourly_by_city = {}
    time_index = None

    for city, coords in cities_dict.items():
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

        times = data["hourly"]["time"]
        temps = data["hourly"]["temperature_2m"]

        if time_index is None:
            time_index = times

        hourly_by_city[city] = temps

    return time_index, hourly_by_city


# まず「都市の座標df」だけ作る（気温はスライダーで入れる）
df = pd.DataFrame([
    {"City": city, "lat": coords["lat"], "lon": coords["lon"]}
    for city, coords in kyushu_capitals.items()
])

with st.spinner("最新の気温データ（時間別）を取得中..."):
    time_list, kyushu_hourly = fetch_hourly_temperatures(kyushu_capitals)
    _, kagoshima_hourly = fetch_hourly_temperatures(kagoshima_local_cities)


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
df["Temperature"] = df["City"].map(lambda c: kyushu_hourly[c][selected_idx])
df["elevation"] = df["Temperature"] * 3000

df_kago = pd.DataFrame([
    {"City": city, "lat": coords["lat"], "lon": coords["lon"]}
    for city, coords in kagoshima_local_cities.items()
])

df_kago["Temperature"] = df_kago["City"].map(lambda c: kagoshima_hourly[c][selected_idx])
df_kago["elevation"] = df_kago["Temperature"] * 2000  # ローカルは少し低めで見やすく



# --- メインレイアウト ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("取得したデータ")
    st.dataframe(df[['City', 'Temperature']], use_container_width=True)

    st.subheader("鹿児島ローカル都市")
    st.dataframe(df_kago[["City", "Temperature"]], use_container_width=True)

    
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

    kago_layer = pdk.Layer(
    "ColumnLayer",
    data=df_kago,
    get_position='[lon, lat]',
    get_elevation='elevation',
    radius=12000,
    get_fill_color='[200, 50, 50, 180]',
    pickable=True,
    auto_highlight=True,
)

    # 描画
    st.pydeck_chart(pdk.Deck(
    layers=[layer, kago_layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>{City}</b><br>気温: {Temperature}°C<br>時刻: " + selected_time,
        "style": {"color": "white"}
    }
))
