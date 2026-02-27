import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import requests
import time
import json

st.set_page_config(page_title="UK Interactive Map", layout="wide")
st.title("UK Interactive Map: Audiences, Sites, and Stores")

# --- 1. Load Data ---
@st.cache_data
def load_data():
    df_pop = pd.read_csv('PopulationSizing.csv')
    df_out = pd.read_csv('OutdoorSites.csv')
    df_av = pd.read_csv('AV.csv')
    df_stores = pd.read_csv('StoreLocations.csv')
    
    # Process AV Spend: Combine TV and VOD by Region
    df_av_grouped = df_av.groupby('Region')['Spend (CTC)'].sum().reset_index()
    
    return df_pop, df_out, df_av_grouped, df_stores

df_pop, df_out, df_av_grouped, df_stores = load_data()

# --- 2. Geocoding Setup (Converting Locations/Postcodes to Coordinates) ---
geolocator = Nominatim(user_agent="streamlit_uk_map_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

@st.cache_data
def get_coordinates(query):
    """Fetches coordinates for a given string, cached to avoid repeated API calls."""
    try:
        location = geolocator.geocode(query + ", UK", timeout=10)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None

# --- 3. Fetch UK GeoJSON for the Choropleth maps ---

@st.cache_data
def get_uk_geojson():
    try:
        with open('Regions_December_2024_Boundaries_EN_BFE_-8330052564508536532.geojson', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Could not load 'Regions_December_2024_Boundaries_EN_BFE_-8330052564508536532.geojson' from working folder: {e}")
        return {}

geojson_data = get_uk_geojson()

# --- 4. Build the Map ---
# Initialize the map centered around the UK
m = folium.Map(location=[54.5, -2.5], zoom_start=6, tiles="cartodbpositron")

# ==========================================
# LAYER 1: Total Population (Green Choropleth)
# ==========================================
layer_pop = folium.FeatureGroup(name='1. Total Population', show=False)
folium.Choropleth(
    geo_data=geojson_data,
    name='Total Population',
    data=df_pop,
    columns=['Region', 'Total Population'],
    key_on='feature.properties.NUTS112NM', # Standard property for NUTS1 region names
    fill_color='Greens',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Total Population'
).add_to(layer_pop)
layer_pop.add_to(m)

# ==========================================
# LAYER 2: Acquisition Audience (Blue Choropleth)
# ==========================================
layer_acq = folium.FeatureGroup(name='2. Acquisition Audience', show=False)
folium.Choropleth(
    geo_data=geojson_data,
    name='Acquisition Audience',
    data=df_pop,
    columns=['Region', 'Acquisition Audience'],
    key_on='feature.properties.NUTS112NM',
    fill_color='Blues',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Acquisition Audience'
).add_to(layer_acq)
layer_acq.add_to(m)

# ==========================================
# LAYER 3: Outdoor Sites (Symbols)
# ==========================================
layer_outdoor = folium.FeatureGroup(name='3. Outdoor Sites', show=True)

for _, row in df_out.iterrows():
    lat, lon = get_coordinates(row['Location'])
    if lat and lon:
        fmt = row['Format']
        
        # Formatting logic based on "Format"
        if fmt == "Transvision Screen":
            icon = folium.Icon(color='blue', icon='stop', prefix='fa')
            folium.Marker([lat, lon], popup=row['Location'], icon=icon).add_to(layer_outdoor)
            
        elif fmt == "Motion Waterloo":
            # Extra styling for large dark blue square using HTML DivIcon
            html = f"""<div style="background-color: darkblue; width: 15px; height: 15px;"></div>"""
            icon = folium.DivIcon(html=html)
            folium.Marker([lat, lon], popup=row['Location'], icon=icon).add_to(layer_outdoor)
            
        elif fmt == "Rail Digital 6 Sheet":
            folium.CircleMarker([lat, lon], popup=row['Location'], radius=5, 
                                color='green', fill=True, fill_color='green').add_to(layer_outdoor)
            
        elif fmt == "Road Digital 6 Sheet":
            folium.CircleMarker([lat, lon], popup=row['Location'], radius=5, 
                                color='darkgreen', fill=True, fill_color='darkgreen').add_to(layer_outdoor)

layer_outdoor.add_to(m)

# ==========================================
# LAYER 4: AV Spend Heatmap/Choropleth (Red)
# ==========================================
layer_av = folium.FeatureGroup(name='4. AV Spend (TV & VOD)', show=False)
folium.Choropleth(
    geo_data=geojson_data,
    name='AV Spend',
    data=df_av_grouped,
    columns=['Region', 'Spend (CTC)'],
    key_on='feature.properties.NUTS112NM',
    fill_color='Reds',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Spend (CTC)'
).add_to(layer_av)
layer_av.add_to(m)

# ==========================================
# LAYER 5: Store Locations (Icons)
# ==========================================
layer_stores = folium.FeatureGroup(name='5. Store Locations', show=True)

for _, row in df_stores.iterrows():
    lat, lon = get_coordinates(row['Postcode'])
    if lat and lon:
        store_type = row['Store Type']
        closing_year = str(row['Closing Year'])
        
        # Determine Color
        if 'Closed' in closing_year or closing_year.isdigit(): # Catching explicit 'Closed' or past years
            color = 'lightred'
        elif store_type == "House of Frasers":
            color = 'lightgray'
        elif store_type == "Frasers":
            color = 'pink'
        else:
            color = 'white'
            
        # Add a shopping cart icon marker
        icon = folium.Icon(color=color, icon='shopping-cart', prefix='fa')
        folium.Marker(
            [lat, lon], 
            popup=f"{row['Name']} - {store_type}", 
            icon=icon
        ).add_to(layer_stores)

layer_stores.add_to(m)

# --- 5. Add Layer Control and Render ---
# This adds the filter overlay allowing users to toggle layers on and off
folium.LayerControl(collapsed=False).add_to(m)

# Display the map in Streamlit
st_folium(m, width=1000, height=700)

st.caption("Note: Location geocoding is cached for speed, but the app may take a moment to load the first time it processes postcodes and station names.")