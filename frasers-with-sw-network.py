import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import base64
from geopy.extra.rate_limiter import RateLimiter
import requests
import time
import json

st.set_page_config(page_title="UK Interactive Map", layout="wide")
st.image("https://images.squarespace-cdn.com/content/5c9e3048523958515c382443/2129c340-d177-48e6-8b14-3c8b01a94ec7/CreamLogo-EMAILSIGNATURE.png?content-type=image%2Fpng", width=100)
st.text("")
st.title("Frasers Interactive Map: Audiences, Sites, and Stores")

# --- 1. Load Data ---
@st.cache_data
def load_data():
    df_pop = pd.read_csv('PopulationSizing.csv')
    df_out = pd.read_csv('OutdoorSites.csv')
    df_av = pd.read_csv('AV.csv')
    df_stores = pd.read_csv('StoreLocations.csv')
    
    # Clean Population Data
    for col in ['Total Population', 'Acquisition Audience']:
        if df_pop[col].dtype == 'object':
             df_pop[col] = df_pop[col].astype(str).str.replace(',', '').astype(float)

    # Clean AV Spend Data
    if df_av['Spend (CTC)'].dtype == 'object':
        df_av['Spend (CTC)'] = df_av['Spend (CTC)'].astype(str).str.replace('£', '').str.replace(',', '').astype(float)

    # Process AV Spend: Combine TV and VOD by Region
    df_av_grouped = df_av.groupby('Region')['Spend (CTC)'].sum().reset_index()
    
    return df_pop, df_out, df_av_grouped, df_stores

df_pop, df_out, df_av_grouped, df_stores = load_data()

# --- 2. Geocoding Setup (Converting Locations/Postcodes to Coordinates) ---
# Static coordinates to ensure markers appear without relying solely on live geocoding
outdoor_sites_coords = {
    'Cannon Street Station': (51.5089, -0.0847),
    'Barking Station': (51.5369, 0.0764),
    'Camden Sattion': (51.5355, -0.1425),
    'Camden Station': (51.5355, -0.1425),
    'Kings Cross Station': (51.5308, -0.1187),
    'Kings Cross St Pancras Station': (51.5308, -0.1187),
    'Liverpool Street Station': (51.5179, -0.0818),
    'Lverpool Street Station': (51.5179, -0.0818),
    'Fenchurch Street Station': (51.5055, -0.0756),
    'London Bridge Station': (51.5055, -0.0862),
    'Waterloo Station': (51.5031, -0.1123),
    'Victoria Station': (51.4938, -0.1447),
    'Charing Cross Station': (51.5051, -0.1247),
    'Blackfriars Station': (51.5076, -0.1048),
    'Reading Station': (51.3339, -0.9733),
    'Liverpool Lime Street Station': (53.4065, -2.9769),
    'Manchhester Victoria Station': (53.4858, -2.2338),
    'Manchester Picadilly Station': (53.4782, -2.2309),
    'Manchester Victoria Station': (53.4858, -2.2338),
    'Bedford Station': (52.1342, -0.4663),
    'Cambridge Station': (52.1279, 0.1438),
    'Chelmsford Station': (51.8904, 0.4749),
    'Colchester Station': (51.8916, 0.8969),
    'Ely Station': (52.3974, 0.2634),
    'Hitchin Station': (51.9563, -0.2808),
    'Ipswich Station': (52.0532, 1.1467),
    'Milton Keynes Central Station': (52.0431, -0.7698),
    'Northampton Station': (52.2300, -0.8832),
    'Birkenhead Hamilton Square Station': (53.3893, -3.0212),
    'Blackburn Station': (53.7476, -2.4919),
    'Crewe Station': (53.0919, -2.4164),
    'Liverpool Central Station': (53.4061, -2.9799),
    'Liverpool Moorfields Station': (53.4041, -2.9789),
    'Manchester Piccadilly Station': (53.4782, -2.2309),
    'Preston Station': (53.7481, -2.7327),
    'Southport Station': (53.6425, -3.0134),
    'St Helens Central Station': (53.4502, -2.7173),
    'Stalybridge Station': (53.4889, -2.0636),
    'Stockport Station': (53.4075, -2.1577),
    'Wigan Wallgate Station': (53.5450, -2.6295),
    'Braintree': (51.8688, 0.5542),
    'Cambridge': (52.2053, 0.1218),
    'Ipswich': (52.0599, 1.1439),
    'Norwich': (52.6289, 1.2974),
    'Peterborough': (52.5687, -0.2426),
    'Blackpool': (53.8142, -3.0566),
    'Bolton': (53.5761, -2.4291),
    'Liverpool': (53.4084, -2.9916),
    'Macclesfield': (53.2595, -2.1426),
    'Manchester': (53.4808, -2.2426),
    'Newton-le-Willows': (53.4461, -2.6361),
    'St Helens': (53.4502, -2.7173),
    'Warrington': (53.3900, -2.5982),
}

postcode_coords = {
    'HP20 2SP': (51.8076, -0.8107), 'BT1 4QG': (54.5973, -5.9301), 'B2 5JS': (52.5095, -1.8846),
    'CR0 1TY': (51.3764, -0.0976), 'G1 3HL': (55.8642, -4.2588), 'NN10 6FG': (52.1279, -0.6429),
    'G83 8QL': (56.0496, -4.5994), 'M3 2QG': (53.4839, -2.2446), 'NR2 1SH': (52.6262, 1.2974),
    'B72 1PB': (52.5671, -1.8261), 'TF3 4BS': (52.6892, -2.4480), 'WV1 3NN': (52.5851, -2.1243),
    'BT48 6AP': (54.9974, -7.1696), 'T12 X7HK': (51.8961, -8.4856), 'W12 H660': (53.177543, -6.7976511),
    'ME14 1QP': (51.2691, 0.5267), 'DE1 2PL': (52.9234, -1.4726), 'DD1 1UQ': (56.4576, -2.9773),
    'PE1 1QA': (52.5696, -0.2412), 'S9 1EL': (53.41469, -1.40932), 'FY1 4HU': (53.8099, -3.0554),
    'HP11 2DQ': (551.62941, -0.75379), 'CF10 1TT': (51.4826, -3.1798), 'GU15 3GP': (51.3299, -0.7543),
    'B91 3AT': (52.4108, -1.8208), 'GU1 3GH': (51.2364, -0.5850), 'RG1 2AG': (51.4560, -0.9736),
    'CA3 8HU': (54.8927, -2.9335), 'BS1 3BD': (51.4508, -2.5965), 'BA1 1DD': (51.3797, -2.3619),
    'LN5 7EA': (53.2283, -0.5414), 'WR1 3LD': (52.1905, -2.2165), 'DA9 9SW': (51.4879, 0.2894),
    'GL50 1HP': (51.8969, -1.8932), 'DN1 1NR': (53.5659, -0.7662), 'RM20 2ZP': (51.5080, 0.4237),
    'NG1 3HF': (52.9535, -1.1491),
}

geolocator = Nominatim(user_agent="streamlit_uk_map_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

@st.cache_data
def get_coordinates(query):
    """Fetches coordinates for a given string, cached to avoid repeated API calls."""
    # Check static dictionaries first
    if query in outdoor_sites_coords:
        return outdoor_sites_coords[query]
    if query in postcode_coords:
        return postcode_coords[query]
    # Fuzzy match for outdoor sites
    for k, v in outdoor_sites_coords.items():
        if k.lower() == str(query).lower():
            return v
            
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
        with open('uk_regions.geojson', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Could not load 'uk_regions.geojson' from working folder: {e}")
        return {}

geojson_data = get_uk_geojson()

@st.cache_data
def get_sw_gemini_geojson():
    try:
        with open('sw_gemini.geojson', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Could not load 'sw_gemini.geojson' from working folder: {e}")
        return {}

sw_gemini_geo = get_sw_gemini_geojson()

def get_icon(filename):
    try:
        with open(filename, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return folium.CustomIcon(f"data:image/png;base64,{encoded}", icon_size=(30, 30))
    except Exception:
        return folium.Icon(color='gray', icon='info-sign')

# --- 4. Build the Map ---
# Initialize the map centered around the UK
m = folium.Map(location=[54.5, -2.5], zoom_start=6, tiles="OpenStreetMap")

# ==========================================
# LAYER 1: Total Population (Green Choropleth)
# ==========================================
cp1 = folium.Choropleth(
    geo_data=geojson_data,
    name='1. Total Population',
    data=df_pop,
    columns=['Region', 'Total Population'],
    key_on='feature.properties.rgn19nm', # Standard property for NUTS1 region names
    fill_color='Greens',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Total Population',
    show=False
)
cp1.geojson.layer_name = '1. Total Population'
cp1.geojson.show = False
cp1.geojson.add_to(m)

# ==========================================
# LAYER 2: Acquisition Audience (Blue Choropleth)
# ==========================================
cp2 = folium.Choropleth(
    geo_data=geojson_data,
    name='2. Acquisition Audience',
    data=df_pop,
    columns=['Region', 'Acquisition Audience'],
    key_on='feature.properties.rgn19nm',
    fill_color='Blues',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Acquisition Audience',
    show=False
)
cp2.geojson.layer_name = '2. Acquisition Audience'
cp2.geojson.show = False
cp2.geojson.add_to(m)

# ==========================================
# LAYER 3: Outdoor Sites (Symbols)
# ==========================================
layer_outdoor = folium.FeatureGroup(name='3. Outdoor Sites', show=False)

for _, row in df_out.iterrows():
    lat, lon = get_coordinates(row['Location'])
    if lat and lon:
        fmt = row['Format']
        
        # Formatting logic based on "Format"
        if fmt == "Transvision Screen":
            # Extra styling for large blue square using HTML DivIcon
            html = f"""<div style="background-color: black; width: 12px; height: 12px;"></div>"""
            icon = folium.DivIcon(html=html)
            folium.Marker([lat, lon], popup=f"{fmt} - {row['Location']}", icon=icon).add_to(layer_outdoor)
            
        elif fmt == "Motion Waterloo":
            # Extra styling for large dark blue square using HTML DivIcon
            html = f"""<div style="background-color: black; width: 12px; height: 12px;"></div>"""
            icon = folium.DivIcon(html=html)
            folium.Marker([lat, lon], popup=f"{fmt} - {row['Location']}", icon=icon).add_to(layer_outdoor)
            
        elif fmt == "Rail Digital 6 Sheet":
            folium.CircleMarker([lat, lon], popup=f"{fmt} - {row['Location']}", radius=6, 
                                color='black', fill=True, fill_opacity=0.95).add_to(layer_outdoor)
            
        elif fmt == "Road Digital 6 Sheet":
            folium.CircleMarker([lat, lon], popup=f"{fmt} - {row['Location']}", radius=6, 
                                color='black', fill=True, fill_opacity=0.95).add_to(layer_outdoor)

layer_outdoor.add_to(m)

# ==========================================
# LAYER 4: AV Spend Heatmap/Choropleth (Red)
# ==========================================
cp4 = folium.Choropleth(
    geo_data=geojson_data,
    name='4. AV Spend (TV+VOD)',
    data=df_av_grouped,
    columns=['Region', 'Spend (CTC)'],
    key_on='feature.properties.rgn19nm',
    fill_color='Reds',
    fill_opacity=0.7,
    line_opacity=0.2,
    nan_fill_color='lightgray',
    nan_fill_opacity=0.4,
    legend_name='AV Spend (TV+VOD)',
    bins=[0, 10000, 20000, 30000, 40000, 50000, 60000],
    show=False
)
cp4.geojson.layer_name = '4. AV Spend (TV+VOD)'
cp4.geojson.show = False
cp4.geojson.add_to(m)

# ==========================================
# LAYER 5: Frasers Stores (Open)
# ==========================================
layer_frasers = folium.FeatureGroup(name='5. Frasers Stores (Open)', show=False)

for _, row in df_stores.iterrows():
    if row['Store Type'] == 'Frasers' and str(row['Closing Year']) == 'Open':
        lat, lon = get_coordinates(row['Postcode'])
        if lat and lon:
            folium.Marker(
                [lat, lon], 
                popup=f"{row['Name']} - Frasers", 
                icon=get_icon("Frasers_Capital_Logo.png")
            ).add_to(layer_frasers)
layer_frasers.add_to(m)

# ==========================================
# LAYER 6: House of Frasers (Open)
# ==========================================
layer_hof = folium.FeatureGroup(name='6. House of Frasers (Open)', show=False)

for _, row in df_stores.iterrows():
    if row['Store Type'] == 'House of Frasers' and str(row['Closing Year']) == 'Open':
        lat, lon = get_coordinates(row['Postcode'])
        if lat and lon:
            folium.Marker(
                [lat, lon], 
                popup=f"{row['Name']} - House of Frasers", 
                icon=get_icon("HoF_Capital_Logo.png")
            ).add_to(layer_hof)
layer_hof.add_to(m)

# ==========================================
# LAYER 7: Closed Stores
# ==========================================
layer_closed = folium.FeatureGroup(name='7. Closed Stores', show=False)

for _, row in df_stores.iterrows():
    closing_year = str(row['Closing Year'])
    if 'Closed' in closing_year or closing_year.isdigit():
        lat, lon = get_coordinates(row['Postcode'])
        if lat and lon:
            folium.Marker(
                [lat, lon], 
                popup=f"{row['Name']} - Closed ({closing_year})", 
                icon=get_icon("Closed_Store.png")
            ).add_to(layer_closed)
layer_closed.add_to(m)

# ==========================================
# LAYER 8: SW Gemini Network
# ==========================================
if sw_gemini_geo:
    folium.GeoJson(
        sw_gemini_geo,
        name='8. SW Gemini Network',
        style_function=lambda x: {'color': 'black', 'weight': 2},
        show=False
    ).add_to(m)

# --- Custom Legend (Top Left, White Box) ---
# Calculate min/max for legend labels
pop_min = int(df_pop['Total Population'].min())
pop_max = int(df_pop['Total Population'].max())
acq_min = int(df_pop['Acquisition Audience'].min())
acq_max = int(df_pop['Acquisition Audience'].max())
spend_min = int(0)
spend_max = int(df_av_grouped['Spend (CTC)'].max())

legend_html = f"""
<div style="
    position: fixed; 
    top: 10px; left: 50px; width: 160px; 
    border: 2px solid grey; z-index:9999; font-size:12px;
    background-color:white; opacity: 0.9;
    padding: 10px; border-radius: 5px;
    ">
    <b>Legend</b><br>
    <div style="margin-top: 5px;">
        <span style="font-size:10px">1. Total Population</span><br>
        <div style="width: 100%; height: 8px; background: linear-gradient(to right, #f7fcf5, #00441b);"></div>
        <div style="display: flex; justify-content: space-between; font-size: 10px;">
            <span>{pop_min:,}</span><span>{pop_max:,}</span>
        </div>
    </div>
    <div style="margin-top: 5px;">
        <span style="font-size:10px">2. Acquisition Audience</span><br>
        <div style="width: 100%; height: 8px; background: linear-gradient(to right, #f7fbff, #08306b);"></div>
        <div style="display: flex; justify-content: space-between; font-size: 10px;">
            <span>{acq_min:,}</span><span>{acq_max:,}</span>
        </div>
    </div>
    <div style="margin-top: 5px;">
        <span style="font-size:10px">4. AV Spend (TV+VOD)</span><br>
        <div style="width: 100%; height: 8px; background: linear-gradient(to right, #fff5f0, #67000d);"></div>
        <div style="display: flex; justify-content: space-between; font-size: 10px;">
            <span>£{spend_min:,}</span><span>£{spend_max:,}</span>
        </div>
    </div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# --- 5. Add Layer Control and Render ---
# This adds the filter overlay allowing users to toggle layers on and off
folium.LayerControl(collapsed=False).add_to(m)

# Display the map in Streamlit
st_folium(m, width=1000, height=700)

st.caption("Note: Location geocoding is cached for speed, but the app may take a moment to load the first time it processes postcodes and station names.")

# --- 6. Data Tables ---
st.subheader("Population Data by Region")

# Prepare display dataframe with required columns and calculations
df_table = df_pop.copy()

# Ensure expected columns exist
if 'Core Audience' not in df_table.columns:
    df_table['Core Audience'] = 0
if 'Acquisition Audience' not in df_table.columns:
    df_table['Acquisition Audience'] = 0

total_pop = df_table['Total Population'].sum() if df_table['Total Population'].sum() != 0 else 1
total_core = df_table['Core Audience'].sum() if df_table['Core Audience'].sum() != 0 else 1
total_acq = df_table['Acquisition Audience'].sum() if df_table['Acquisition Audience'].sum() != 0 else 1

# Percentage shares (rounded to 0 decimal places for display)
df_table['Total %'] = (df_table['Total Population'] / total_pop * 100).round(0)
df_table['Core %'] = (df_table['Core Audience'] / total_core * 100).round(0)
df_table['Audience %'] = (df_table['Acquisition Audience'] / total_acq * 100).round(0)

# Indexes: (share of audience / share of population) * 100, rounded to 2 decimals
df_table['Core Index'] = (((df_table['Core Audience'] / total_core) / (df_table['Total Population'] / total_pop)) * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)
df_table['Acquisition Index'] = (((df_table['Acquisition Audience'] / total_acq) / (df_table['Total Population'] / total_pop)) * 100).replace([float('inf'), -float('inf')], 0).fillna(0).round(2)

# Select and order columns as requested
display_cols = [
    'Region',
    'Total Population',
    'Total %',
    'Core Audience',
    'Core %',
    'Core Index',
    'Acquisition Audience',
    'Audience %',
    'Acquisition Index'
]

df_display = df_table.loc[:, display_cols]

st.dataframe(
    df_display,
    column_config={
        'Total Population': st.column_config.NumberColumn(format="%d"),
        'Total %': st.column_config.NumberColumn(format="%d%%"),
        'Core Audience': st.column_config.NumberColumn(format="%d"),
        'Core %': st.column_config.NumberColumn(format="%d%%"),
        'Core Index': st.column_config.NumberColumn(format="%.2f"),
        'Acquisition Audience': st.column_config.NumberColumn(format="%d"),
        'Audience %': st.column_config.NumberColumn(format="%d%%"),
        'Acquisition Index': st.column_config.NumberColumn(format="%.2f"),
    },
    hide_index=True,
    use_container_width=True
)
