import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import branca.colormap as cm
import math

# --- App Configuration ---
st.set_page_config(page_title="USA Metropolitan Areas Map", layout="wide")
st.title("USA Metropolitan Areas: Households & High-Value Homes")
st.markdown("Bubble size represents **Total Households**, while color represents **% Houses >$1m** (Red = Lowest, Green = Highest).")

# --- 1. Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('SF_USA_Cities.csv')
    return df

df = load_data()

# --- 2. Geocoding Setup ---
geolocator = Nominatim(user_agent="streamlit_usa_map_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

@st.cache_data
def get_coordinates(city, state):
    """Fetches coordinates for a given city and state, cached to avoid repeated API calls."""
    query = f"{city}, {state}, USA"
    try:
        location = geolocator.geocode(query, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception:
        pass
    return None, None

# --- 3. Build the Map ---
# Center the map on the contiguous United States
m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles="CartoDB positron")

# Create a color scale (Red -> Yellow -> Green) for the % of homes > $1m
min_pct = df['% Houses >$1m'].min()
max_pct = df['% Houses >$1m'].max()
colormap = cm.LinearColormap(colors=['red', 'orange', 'green'], vmin=min_pct, vmax=max_pct)
colormap.caption = '% Houses over $1m'
colormap.add_to(m)

# Create a feature group for the city bubbles
city_group = folium.FeatureGroup(name="USA Cities")

for idx, row in df.iterrows():
    lat, lon = get_coordinates(row['City'], row['STATE'])
    
    if lat and lon:
        # Calculate bubble radius: square root used so area scales with households
        households = row['Total households']
        radius = max(3, math.sqrt(households) / 60) 
        
        # Determine color based on % Houses >$1m
        pct_high_value = row['% Houses >$1m']
        color = colormap(pct_high_value)
        
        popup_html = f"""
        <b>{row['Metropolitan Area']}</b><br>
        <b>City:</b> {row['City']}, {row['STATE']}<br>
        <b>Type:</b> {row['Metro / Micro']}<br>
        <b>Total Households:</b> {households:,}<br>
        <b>% Houses >$1m:</b> {pct_high_value:.2%}<br>
        <b>Median Value:</b> ${row['VALUE!!Median (dollars)']:,.0f}
        """
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['City']}, {row['STATE']}",
            color="#333333",  # Dark border
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(city_group)

city_group.add_to(m)
folium.LayerControl().add_to(m)

# --- 4. Render Map & Data Table ---
st_folium(m, width=1200, height=700)

st.caption("Note: Location geocoding is cached for speed. The map may take a moment to load the first time as it processes the city names.")

st.subheader("Underlying Data")
st.dataframe(df, use_container_width=True)