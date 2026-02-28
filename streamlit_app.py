import streamlit as st
import googlemaps
import folium
import streamlit.components.v1 as components

# --- 0. カウンター機能（認証欲求・モチベーション維持用） ---
@st.cache_resource
def get_counter():
    # アプリ起動中の累計回数を保持する簡易カウンター
    return {"count": 0}

counter = get_counter()

# --- 1. セキュリティ設定 ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("合言葉を入力してください", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("合言葉が違います。再入力してください", type="password", on_change=password_entered, key="password")
        return False
    return True

# --- 2. 経路算出ロジック（複数経由地対応・V字防止） ---
def find_jun_goal_no_detour(gmaps, start_point, waypoints, target_km, mode="bicycling"):
    active_waypoints = [w for w in waypoints if w.strip()]
    if not start_point.strip():
        return None, None, "出発地を入力してください。"
    if not active_waypoints:
        return None, None, "経由地を少なくとも1つ入力してください。"
    
    dest = active_waypoints[-1]
    via = active_waypoints[:-1]

    directions = gmaps.directions(
        origin=start_point,
        destination=dest,
        waypoints=via,
        mode=mode,
        region="jp",
        language="ja"
    )

    if not directions and mode == "bicycling":
        directions = gmaps.directions(
            origin=start_point,
            destination=dest,
            waypoints=via,
            mode="driving",
            avoid=["tolls", "highways", "ferries"],
            region="jp"
        )

    if not directions:
        return None, None, "指定された経由地を結ぶルートが見つかりませんでした。"

    target_meters = target_km * 1000 
    accumulated_meters = 0
    route = directions[0]
    start_coords = route['legs'][0]['start_location']
    
    for leg in route['legs']:
        for step in leg['steps']:
            step_dist = step['distance']['value']
            if accumulated_meters + step_dist >= target_meters:
                return step['end_location'], start_coords, None
            accumulated_meters += step_dist
            
    return route['legs'][-1]['end_location'], start_coords, f"※{target_km}kmに届かず、{accumulated_meters/1000:.1f}km地点を表示します。"

# --- 3. 一括消去用関数 ---
def clear_text():
    st.session_state["start_node"] = ""
    st.session_state["w1"] = ""
    st.session_state["w2"] = ""
    st.session_state["w3"] = ""

# --- 4. メイン UI ---
def main():
    st.set_page_config(page_title="日本一周NAVI v1.1", layout="centered")
    st.title("🚲 日本一周・ルートビルダー v1.1")
    
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])

    # セッション状態の初期化
    if "start_node" not in st.session_state:
        st.session_state["start_node"] = ""
    if "w1" not in st.session_state:
        st.session_state["w1"] = ""
    if "w2" not in st.session_state:
        st.session_state["w2"] = ""
    if "w3" not in st.session_state:
        st.session_state["w3"] = ""

    with st.sidebar:
        st.header("旅の現在地")
        start_node = st.text_input("出発地", key="start_node")
        
        st.write("---")
        target_km = st.number_input("本日の走行予定距離 (km)", min_value=1, max_value=300, value=80)
        
        st.write("---")
        st.header("経由地（進む順に）")
        w1 = st.text_input("経由地1", key="w1")
        w2 = st.text_input("経由地2", key="w2")
        w3 = st.text_input("最終目的地方面", key="w3")
        
        st.write("---")
        st.button("入力内容をすべて消去", on_click=clear_text)
        
        st.write("---")
        run_btn = st.button(f"今日の{target_km}km地点を計算")

    if run_btn:
        if not start_node:
            st.error("出発地を入力してください。")
        else:
            with st.spinner(f"道なりの{target_km}km地点を特定中..."):
                waypoints = [w1, w2, w3]
                goal_coords, start_coords, error = find_jun_goal_no_detour(gmaps, start_node, waypoints, target_km)
                
                if goal_coords:
                    # 計算成功時にカウンターを +1 する
                    counter["count"] += 1
                    
                    rev = gmaps.reverse_geocode((goal_coords['lat'], goal_coords['lng']), language='ja')
                    address = rev[0]['formatted_address'] if rev else "住所不明"
                    
                    st.success(f"✨ {target_km}km地点を特定しました！")
                    
                    d_lat, d_lng = goal_coords['lat'], goal_coords['lng']
                    
                    maps_url = (
                        f"https://www.google.com/maps/dir/?api=1&?origin={start_node}&destination={d_lat},{d_lng}&travelmode=bicycling"
                    )
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**本日の到達地点の目安:**\n{address}")
                    with col2:
                        st.link_button("🚀 マップでナビ", maps_url)

                    m = folium.Map(location=[d_lat, d_lng], zoom_start=11)
                    folium.Marker([start_coords['lat'], start_coords['lng']], tooltip="出発地", icon=folium.Icon(color='red')).add_to(m)
                    folium.Marker([d_lat, d_lng], tooltip=f"{target_km}km地点", icon=folium.Icon(color='blue', icon='bicycle', prefix='fa')).add_to(m)
                    components.html(m._repr_html_(), height=500)
                else:
                    st.error(error)

    # --- フッター（カウンター表示） ---
    st.write("---")
    st.caption(f"🏁 これまでの累計ルート算出回数: {counter['count']} 回")
    st.caption("※このカウンターはアプリの起動期間中の累計を表示しています。")

if check_password():
    main()
