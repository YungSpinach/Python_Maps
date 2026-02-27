import streamlit as st
import pandas as pd
import folium
from folium import plugins
import requests
import json
from streamlit_folium import st_folium
import numpy as np

# Page configuration
st.set_page_config(page_title="UK Multi-Layer Map", layout="wide")
st.title("Interactive UK Map - Multi-Layer Dashboard")

# ==================== DATA LOADING ====================
@st.cache_data
def load_data():
    population_df = pd.read_csv('PopulationSizing.csv', encoding='latin-1')
    outdoor_df = pd.read_csv('OutdoorSites.csv', encoding='latin-1')
    av_df = pd.read_csv('AV.csv', encoding='latin-1')
    stores_df = pd.read_csv('StoreLocations.csv', encoding='latin-1')
    return population_df, outdoor_df, av_df, stores_df

population_df, outdoor_df, av_df, stores_df = load_data()

# ==================== UK REGION COORDINATES ====================
# UK regions with their centroids for mapping
uk_regions_coords = {
    'Inner London': (51.5074, -0.1278),
    'East of England': (52.2314, 0.5629),
    'Outer London': (51.6309, -0.0931),
    'North West': (53.4808, -2.2426),
    'South East': (51.3198, 0.5034),
    'Scotland': (56.4907, -4.2026),
    'Yorkshire and the Humber': (53.9583, -1.5582),
    'East Midlands': (52.6368, -0.9822),
    'West Midlands': (52.6089, -1.8149),
    'South West': (50.7184, -3.5339),
    'Northern Ireland': (54.3781, -6.2592),
    'Wales': (52.1307, -3.7837),
}

# Outdoor sites location coordinates (UK stations)
outdoor_sites_coords = {
    'Cannon Street Station': (51.5089, -0.0847),
    'Barking Station': (51.5369, 0.0764),
    'Camden Sattion': (51.5355, -0.1425),  # Note: typo in CSV
    'Camden Station': (51.5355, -0.1425),
    'Kings Cross Station': (51.5308, -0.1187),
    'Kings Cross St Pancras Station': (51.5308, -0.1187),
    'Liverpool Street Station': (51.5179, -0.0818),
    'Lverpool Street Station': (51.5179, -0.0818),  # Typo variant
    'Fenchurch Street Station': (51.5055, -0.0756),
    'London Bridge Station': (51.5055, -0.0862),
    'Waterloo Station': (51.5031, -0.1123),
    'Victoria Station': (51.4938, -0.1447),
    'Charing Cross Station': (51.5051, -0.1247),
    'Blackfriars Station': (51.5076, -0.1048),
    'Reading Station': (51.3339, -0.9733),
    'Liverpool Lime Street Station': (53.4065, -2.9769),
    'Manchhester Victoria Station': (53.4858, -2.2338),  # Typo variant
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

# Postcode coordinates for stores
postcode_coords = {
    'HP20 2SP': (51.8076, -0.8107),   # Aylesbury
    'BT1 4QG': (54.5973, -5.9301),    # Belfast
    'B2 5JS': (52.5095, -1.8846),     # Birmingham
    'CR0 1TY': (51.3764, -0.0976),    # Croydon
    'G1 3HL': (55.8642, -4.2588),     # Glasgow
    'NN10 6FG': (52.1279, -0.6429),   # Rushden Lakes
    'G83 8QL': (56.0496, -4.5994),    # Loch Lomond
    'M3 2QG': (53.4839, -2.2446),     # Manchester
    'NR2 1SH': (52.6262, 1.2974),     # Norwich
    'B72 1PB': (52.5671, -1.8261),    # Sutton Coldfield
    'TF3 4BS': (52.6892, -2.4480),    # Telford
    'WV1 3NN': (52.5851, -2.1243),    # Wolverhampton
    'BT48 6AP': (54.9974, -7.1696),   # Derry
    'T12 X7HK': (51.8961, -8.4856),   # Cork (Ireland)
    'W12 H660': (53.5000, -6.7000),   # Newbridge (Ireland)
    'ME14 1QP': (51.2691, 0.5267),    # Maidstone
    'DE1 2PL': (52.9234, -1.4726),    # Derby
    'DD1 1UQ': (56.4576, -2.9773),    # Dundee
    'PE1 1QA': (52.5696, -0.2412),    # Peterborough
    'S9 1EL': (53.3773, -1.4012),     # Meadowhall
    'FY1 4HU': (53.8099, -3.0554),    # Blackpool
    'HP11 2DQ': (51.5747, -0.7501),   # High Wycombe
    'CF10 1TT': (51.4826, -3.1798),   # Cardiff
    'GU15 3GP': (51.3299, -0.7543),   # Camberley
    'B91 3AT': (52.4108, -1.8208),    # Solihull
    'GU1 3GH': (51.2364, -0.5850),    # Guildford
    'RG1 2AG': (51.4560, -0.9736),    # Reading
    'CA3 8HU': (54.8927, -2.9335),    # Carlisle
    'BS1 3BD': (51.4508, -2.5965),    # Bristol
    'BA1 1DD': (51.3797, -2.3619),    # Bath
    'LN5 7EA': (53.2283, -0.5414),    # Lincoln
    'WR1 3LD': (52.1905, -2.2165),    # Worcester
    'DA9 9SW': (51.4879, 0.2894),     # Bluewater
    'GL50 1HP': (51.8969, -1.8932),   # Cheltenham
    'DN1 1NR': (53.5659, -0.7662),    # Doncaster
    'RM20 2ZP': (51.5080, 0.4237),    # Lakeside
    'NG1 3HF': (52.9535, -1.1491),    # Nottingham
}

# ==================== DATA PROCESSING ====================

# Clean and prepare AV spend data
av_df['Spend (CTC)'] = av_df['Spend (CTC)'].astype(str).str.replace('£', '').str.replace(',', '').astype(float)
av_spend = av_df.groupby('Region')['Spend (CTC)'].sum().reset_index()

# Prepare outdoor sites data
outdoor_df['Location'] = outdoor_df['Location'].astype(str).str.strip()

# ==================== SIDEBAR CONTROLS ====================
st.sidebar.header("Layer Controls")

show_population = st.sidebar.checkbox("Population Heatmap (Green)", value=True)
show_acquisition = st.sidebar.checkbox("Acquisition Audience Heatmap (Blue)", value=True)
show_av_spend = st.sidebar.checkbox("AV Spend Heatmap (Red)", value=True)
show_outdoor = st.sidebar.checkbox("Outdoor Sites", value=True)
show_stores = st.sidebar.checkbox("Store Locations", value=True)

# ==================== MAP CREATION ====================

# Create base map centered on UK
center_lat = 54.5
center_lng = -3.5
m = folium.Map(
    location=[center_lat, center_lng],
    zoom_start=6,
    tiles='CartoDB positron'
)

# ==================== LAYER 1: POPULATION CHOROPLETH (GREEN) ====================
if show_population:
    # Prepare population data for choropleth
    pop_for_choropleth = population_df[['Region', 'Total Population']].copy()
    pop_for_choropleth['Total Population'] = pop_for_choropleth['Total Population'].astype(str).str.replace(',', '').astype(float)
    
    # Create a feature collection GeoJSON for UK regions
    uk_geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": "Inner London"}, "geometry": {"type": "Point", "coordinates": [-0.1278, 51.5074]}},
            {"type": "Feature", "properties": {"name": "East of England"}, "geometry": {"type": "Point", "coordinates": [0.5629, 52.2314]}},
            {"type": "Feature", "properties": {"name": "Outer London"}, "geometry": {"type": "Point", "coordinates": [-0.0931, 51.6309]}},
            {"type": "Feature", "properties": {"name": "North West"}, "geometry": {"type": "Point", "coordinates": [-2.2426, 53.4808]}},
            {"type": "Feature", "properties": {"name": "South East"}, "geometry": {"type": "Point", "coordinates": [0.5034, 51.3198]}},
            {"type": "Feature", "properties": {"name": "Scotland"}, "geometry": {"type": "Point", "coordinates": [-4.2026, 56.4907]}},
            {"type": "Feature", "properties": {"name": "Yorkshire and the Humber"}, "geometry": {"type": "Point", "coordinates": [-1.5582, 53.9583]}},
            {"type": "Feature", "properties": {"name": "East Midlands"}, "geometry": {"type": "Point", "coordinates": [-0.9822, 52.6368]}},
            {"type": "Feature", "properties": {"name": "West Midlands"}, "geometry": {"type": "Point", "coordinates": [-1.8149, 52.6089]}},
            {"type": "Feature", "properties": {"name": "South West"}, "geometry": {"type": "Point", "coordinates": [-3.5339, 50.7184]}},
            {"type": "Feature", "properties": {"name": "Northern Ireland"}, "geometry": {"type": "Point", "coordinates": [-6.2592, 54.3781]}},
            {"type": "Feature", "properties": {"name": "Wales"}, "geometry": {"type": "Point", "coordinates": [-3.7837, 52.1307]}}
        ]
    }
    
    # Add population circles with green color scale
    for idx, row in pop_for_choropleth.iterrows():
        region = row['Region']
        pop = row['Total Population']
        
        if region in uk_regions_coords:
            lat, lng = uk_regions_coords[region]
            # Normalize for color intensity
            intensity = pop / pop_for_choropleth['Total Population'].max()
            # Green color scale: lighter to darker
            green_value = int(50 + (intensity * 150))
            color = f'#{0:02x}{green_value:02x}{0:02x}'
            
            folium.CircleMarker(
                location=[lat, lng],
                radius=35,
                popup=f"<b>{region}</b><br>Population: {pop:,.0f}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7 + (intensity * 0.3),
                weight=2,
            ).add_to(m)

# ==================== LAYER 2: ACQUISITION AUDIENCE CHOROPLETH (BLUE) ====================
if show_acquisition:
    # Prepare acquisition audience data for choropleth
    acq_for_choropleth = population_df[['Region', 'Acquisition Audience']].copy()
    acq_for_choropleth['Acquisition Audience'] = acq_for_choropleth['Acquisition Audience'].astype(str).str.replace(',', '').astype(float)
    
    # Add acquisition circles with blue color scale
    for idx, row in acq_for_choropleth.iterrows():
        region = row['Region']
        acq = row['Acquisition Audience']
        
        if region in uk_regions_coords:
            lat, lng = uk_regions_coords[region]
            # Normalize for color intensity
            intensity = acq / acq_for_choropleth['Acquisition Audience'].max()
            # Blue color scale: lighter to darker
            blue_value = int(50 + (intensity * 150))
            color = f'#{0:02x}{0:02x}{blue_value:02x}'
            
            folium.CircleMarker(
                location=[lat, lng],
                radius=32,
                popup=f"<b>{region}</b><br>Acquisition Audience: {acq:,.0f}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7 + (intensity * 0.3),
                weight=2,
            ).add_to(m)

# ==================== LAYER 3: AV SPEND CHOROPLETH (RED) ====================
if show_av_spend:
    # Map AV regions to population regions
    region_mapping = {
        'London': 'Inner London',
        'Anglia ': 'East of England',  # Note: "Anglia " has trailing space in CSV
        'Anglia': 'East of England',
        'North West': 'North West',
        'South East': 'South East',
    }
    
    # Prepare spend data with mapped regions
    spend_for_choropleth = av_spend.copy()
    spend_for_choropleth['MappedRegion'] = spend_for_choropleth['Region'].map(region_mapping)
    # Fill unmapped regions with themselves
    spend_for_choropleth['MappedRegion'] = spend_for_choropleth['MappedRegion'].fillna(spend_for_choropleth['Region'])
    
    # Add spend circles with red color scale
    for idx, row in spend_for_choropleth.iterrows():
        region = row['MappedRegion']
        spend = row['Spend (CTC)']
        
        if region in uk_regions_coords:
            lat, lng = uk_regions_coords[region]
            # Normalize for color intensity
            intensity = spend / spend_for_choropleth['Spend (CTC)'].max()
            # Red color scale: lighter to darker
            red_value = int(100 + (intensity * 150))
            color = f'#{red_value:02x}{0:02x}{0:02x}'
            
            folium.CircleMarker(
                location=[lat, lng],
                radius=30,
                popup=f"<b>{region}</b><br>AV Spend: £{spend:,.2f}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7 + (intensity * 0.3),
                weight=2,
            ).add_to(m)

# ==================== LAYER 4: OUTDOOR SITES ====================
if show_outdoor:
    # Format to symbol mapping
    format_symbols = {
        'Transvision Screen': {'color': '#0080FF', 'icon': 'square'},
        'Motion Waterloo': {'color': '#00008B', 'icon': 'square'},
        'Rail Digital 6 Sheet': {'color': '#00AA00', 'icon': 'circle'},
        'Road Digital 6 Sheet': {'color': '#006400', 'icon': 'circle'},
    }
    
    for idx, row in outdoor_df.iterrows():
        location = row['Location'].strip()
        fmt = row['Format'].strip()
        
        # Try to find coordinates, handling name variations
        coords = outdoor_sites_coords.get(location)
        
        # If not found, try to find a similar match
        if not coords:
            for key in outdoor_sites_coords:
                if key.lower() == location.lower():
                    coords = outdoor_sites_coords[key]
                    break
        
        if coords:
            lat, lng = coords
            symbol_info = format_symbols.get(fmt, {'color': '#808080', 'icon': 'info'})
            
            # Create popup
            popup_text = f"<b>{location}</b><br>Format: {fmt}"
            
            if fmt == 'Motion Waterloo':
                # Large dark blue square for Motion Waterloo
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=12,
                    popup=popup_text,
                    color='#00008B',
                    fill=True,
                    fillColor='#00008B',
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(m)
            elif fmt == 'Transvision Screen':
                # Blue circle for Transvision Screen
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=8,
                    popup=popup_text,
                    color='#0080FF',
                    fill=True,
                    fillColor='#0080FF',
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(m)
            elif 'Rail Digital' in fmt:
                # Green dot for Rail Digital
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=6,
                    popup=popup_text,
                    color='#00AA00',
                    fill=True,
                    fillColor='#00AA00',
                    fillOpacity=0.8,
                    weight=1,
                ).add_to(m)
            elif 'Road Digital' in fmt:
                # Dark green dot for Road Digital
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=6,
                    popup=popup_text,
                    color='#006400',
                    fill=True,
                    fillColor='#006400',
                    fillOpacity=0.8,
                    weight=1,
                ).add_to(m)

# ==================== LAYER 5: STORE LOCATIONS ====================
if show_stores:
    store_icons = {
        'House of Frasers': {'color': 'gray', 'icon': 'shopping-bag'},
        'Frasers': {'color': 'pink', 'icon': 'shopping-bag'},
    }
    
    for idx, row in stores_df.iterrows():
        name = row['Name']
        store_type = row['Store Type']
        postcode = row['Postcode'].strip()
        closing_year = row['Closing Year']
        
        if postcode in postcode_coords:
            lat, lng = postcode_coords[postcode]
            
            # Determine icon color based on store type and closing status
            if closing_year != 'Open':
                icon_color = '#FF6666'  # Light red for closed
                popup_text = f"<b>{name}</b> ({store_type})<br>Closed: {closing_year}"
            else:
                if store_type == 'House of Frasers':
                    icon_color = '#808080'  # Grey
                else:
                    icon_color = '#FFB6C1'  # Pink
                popup_text = f"<b>{name}</b> ({store_type})<br>Status: Open"
            
            folium.Marker(
                location=[lat, lng],
                popup=folium.Popup(popup_text, max_width=200),
                icon=folium.Icon(color=icon_color, icon='shopping-bag', prefix='fa'),
            ).add_to(m)

# ==================== LEGEND ====================
# Note: Choropleth-style maps with dynamic color scaling
# Darker shades indicate higher values in each layer

# ==================== LAYER CONTROL ====================
folium.LayerControl().add_to(m)

# Display the map
st_folium(m, width=1400, height=800)

# ==================== INFO PANEL ====================
st.sidebar.header("Map Information")
st.sidebar.info("""
### Layer Colors:
- **Green**: Population density by region
- **Blue**: Acquisition audience by region
- **Red**: AV spend (VOD + TV combined) by region
- **Outdoor Sites**: Transportation hubs
  - Blue squares: Transvision Screen
  - Dark blue squares: Motion Waterloo
  - Green dots: Rail Digital
  - Dark green dots: Road Digital
- **Store Locations**: Frasers stores
  - Grey: House of Frasers (Open)
  - Pink: Frasers (Open)
  - Light red: Closed stores
""")
