import streamlit as st
import googlemaps
import folium
import pandas as pd
import streamlit.components.v1 as components

@st.cache_resource
def get_counter():
    return {"count": 0}

counter = get_counter()

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

def get_elevation_info(gmaps, path_coords, total_dist_meters):
    if not path_coords or total_dist_meters <= 0:
        return [0], 0, 0, 0, 0
    try:
        samples = 30
        elevation_data = gmaps.elevation_along_path(path_coords, samples)
        elevations = [item['elevation'] for item in elevation_data]
        total_ascent = 0
        slopes = []
        dist_step = total_dist_meters / (len(elevations) - 1)
        for i in range(len(elevations) - 1):
            diff = elevations[i+1] - elevations[i]
            if diff > 0:
                total_ascent += diff
                s = (diff / dist_step) * 100
                slopes.append(s)
        max_elev = max(elevations)
        avg_slope = (total_ascent / total_dist_meters) * 100
        max_slope = max(slopes) if slopes else 0
        return elevations, round(total_ascent), round(max_elev), round(avg_slope, 1), round(max_slope, 1)
    except:
        return [0], 0, 0, 0, 0

def find_jun_goal_no_detour(gmaps, start_point, waypoints, target_km, mode="bicycling"):
    active_waypoints = [w for w in waypoints if w.strip()]
    if not start_point.strip():
        return None, None, [0], 0, 0, 0, 0, 0, "出発地を入力してください。"
    dest = active_waypoints[-1] if active_waypoints else start_point
    via = active_waypoints[:-1] if active_waypoints else []
    try:
        directions = gmaps.directions(origin=start_point, destination=dest, waypoints=via, mode=mode, region="jp", language="ja")
        if not directions and mode == "bicycling":
            directions = gmaps.directions(origin=start_point, destination=dest, waypoints=via, mode="driving", avoid=["tolls", "highways", "ferries"], region="jp")
    except Exception as e:
        return None, None, [0], 0, 0, 0, 0, 0, f"API Error: {str(e)}"
    if not directions:
        return None, None, [0], 0, 0, 0, 0, 0, "No Route Found"
    target_meters = target_km * 1000 
    acc_meters = 0
    route = directions[0]
    start_coords = route['legs'][0]['start_location']
    path_coords = []
    found_goal = None
    real_dist = 0
    for leg in route['legs']:
        for step in leg['steps']:
            step_dist = step['distance']['value']
            path_coords.append(step['start_location'])
