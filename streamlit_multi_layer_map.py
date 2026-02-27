import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import pgeocode
import io

st.set_page_config(layout="wide", page_title="UK Multi-layer Map")

@st.cache_data
def load_csv(name):
    return pd.read_csv(name)

@st.cache_data
def fetch_regions_geojson(url=None):
    # Try a known GitHub raw URL; user can override with their own URL if needed
    if url is None:
        url = "https://raw.githubusercontent.com/martinjc/UK-GeoJSON/master/json/administrative/gb/regions.json"
    try:
        gdf = gpd.read_file(url)
        return gdf
    except Exception as e:
        st.error(f"Failed to fetch regions GeoJSON: {e}")
        return None

@st.cache_data
def geocode_postcodes(postcodes):
    nomi = pgeocode.Nominatim('GB')
    res = nomi.query_postal_code(postcodes)
    return res

def find_latlon_cols(df):
    lat_cols = [c for c in df.columns if c.lower() in ['lat','latitude','y','y_coord','latd']]
    lon_cols = [c for c in df.columns if c.lower() in ['lon','lng','longitude','x','x_coord','long']]
    if lat_cols and lon_cols:
        return lat_cols[0], lon_cols[0]
    return None, None

# Load data files (assumes they are in the same folder)
st.sidebar.header('Data files')
pop_file = st.sidebar.text_input('PopulationSizing CSV', 'PopulationSizing.csv')
av_file = st.sidebar.text_input('AV CSV', 'AV.csv')
outdoor_file = st.sidebar.text_input('OutdoorSites CSV', 'OutdoorSites.csv')
stores_file = st.sidebar.text_input('StoreLocations CSV', 'StoreLocations.csv')

# Load CSVs
try:
    pop_df = load_csv(pop_file)
    av_df = load_csv(av_file)
    outdoor_df = load_csv(outdoor_file)
    stores_df = load_csv(stores_file)
except Exception as e:
    st.error(f"Error loading CSVs: {e}")
    st.stop()

# Fetch UK regions geojson
st.sidebar.header('GeoJSON')
geo_url = st.sidebar.text_input('Regions GeoJSON URL (optional)', '')
regions_gdf = fetch_regions_geojson(geo_url if geo_url.strip() else None)
if regions_gdf is None:
    st.stop()

# Normalize region name column in regions_gdf
regions_gdf['region_name'] = regions_gdf.columns[0]  # fallback
# try common properties
for col in ['name','region','NAME','lad19nm','rgn19nm','rgn19nm']:
    if col in regions_gdf.columns:
        regions_gdf['region_name'] = regions_gdf[col]
        break

# Prepare Population layers
# Try to find reasonable column names or positions
def get_col_by_candidates(df, candidates, fallback_index=None):
    for cand in candidates:
        if cand in df.columns:
            return cand
    if fallback_index is not None and fallback_index < len(df.columns):
        return df.columns[fallback_index]
    return None

pop_region_col = get_col_by_candidates(pop_df, ['Region','region','Unnamed: 0','REGION'], 0)
pop_total_col = get_col_by_candidates(pop_df, ['Total Population','Total_Population','TotalPopulation','Population','Population Total'], 1)
pop_acq_col = get_col_by_candidates(pop_df, ['Acquisition Audience','Acquisition_Audience','AcquisitionAudience','Acquisition'], 4)

if pop_region_col is None or pop_total_col is None or pop_acq_col is None:
    st.warning('Could not auto-detect some PopulationSizing columns; check column names in the CSV.')

# Merge population into regions geo
pop_merge = pop_df[[pop_region_col, pop_total_col, pop_acq_col]].copy()
pop_merge.columns = ['Region', 'TotalPopulation', 'AcquisitionAudience']
# Normalize region names for merge
pop_merge['Region_norm'] = pop_merge['Region'].str.strip().str.lower()
regions_gdf['region_norm'] = regions_gdf['region_name'].astype(str).str.strip().str.lower()
regions_pop = regions_gdf.merge(pop_merge, left_on='region_norm', right_on='Region_norm', how='left')

# Prepare AV spends by region (sum across channels)
av_region_col = get_col_by_candidates(av_df, ['Region','region','REGION'], 0)
av_channel_col = get_col_by_candidates(av_df, ['Channel','Chanel','channel'], 1)
av_spend_col = get_col_by_candidates(av_df, ['Spend (CTC)','Spend','Spend_CTC','Spend (ctc)'], 4)
if av_region_col is None or av_spend_col is None:
    st.warning('Could not auto-detect some AV.csv columns; check column names in the CSV.')

av_sum = av_df.groupby(av_region_col)[av_spend_col].sum().reset_index()
av_sum.columns = ['Region', 'SpendCTC']
av_sum['Region_norm'] = av_sum['Region'].astype(str).str.strip().str.lower()
regions_av = regions_gdf.merge(av_sum, left_on='region_norm', right_on='Region_norm', how='left')

# Outdoor sites: expect lat/lon present
latcol, loncol = find_latlon_cols(outdoor_df)

# Store geocoding using Postcode
stores_postcodes = stores_df.iloc[:,4].astype(str).str.replace(' ','') if stores_df.shape[1] > 4 else pd.Series([])
stores_geo = None
if len(stores_postcodes) > 0:
    geocoded = geocode_postcodes(stores_postcodes.values)
    stores_geo = geocoded

# Streamlit UI toggles
st.sidebar.header('Map Layers')
show_pop_total = st.sidebar.checkbox('Population: Total Population (Green choropleth)', True)
show_pop_acq = st.sidebar.checkbox('Population: Acquisition Audience (Blue choropleth)', False)
show_outdoor = st.sidebar.checkbox('Outdoor Sites (symbols)', True)
show_av_heat = st.sidebar.checkbox('AV Spend heatmap (red)', True)
show_stores = st.sidebar.checkbox('Store locations (shop icons)', True)

# Create folium map
m = folium.Map(location=[54.0, -2.0], zoom_start=5, tiles='cartodbpositron')

# Add base tile layers
folium.TileLayer('Stamen Terrain').add_to(m)
folium.TileLayer('OpenStreetMap').add_to(m)

# Population Total choropleth (Greens)
if show_pop_total:
    fg_pop_total = folium.FeatureGroup(name='Total Population (Greens)')
    # We will add choropleth
    try:
        folium.Choropleth(
            geo_data=regions_pop.to_json(),
            data=regions_pop,
            columns=['region_name', 'TotalPopulation'],
            key_on='feature.properties.region_name',
            fill_color='Greens',
            fill_opacity=0.7,
            line_opacity=0.3,
            legend_name='Total Population'
        ).add_to(fg_pop_total)
        fg_pop_total.add_to(m)
    except Exception as e:
        st.warning(f'Failed to add Total Population choropleth: {e}')

# Population Acquisition Audience choropleth (Blues)
if show_pop_acq:
    fg_pop_acq = folium.FeatureGroup(name='Acquisition Audience (Blues)')
    try:
        folium.Choropleth(
            geo_data=regions_pop.to_json(),
            data=regions_pop,
            columns=['region_name', 'AcquisitionAudience'],
            key_on='feature.properties.region_name',
            fill_color='Blues',
            fill_opacity=0.7,
            line_opacity=0.3,
            legend_name='Acquisition Audience'
        ).add_to(fg_pop_acq)
        fg_pop_acq.add_to(m)
    except Exception as e:
        st.warning(f'Failed to add Acquisition Audience choropleth: {e}')

# AV spend heatmap: place centroid points weighted by spend
if show_av_heat:
    fg_av = folium.FeatureGroup(name='AV Spend Heatmap (Reds)')
    try:
        # compute centroids
        centroids = regions_av.copy()
        centroids['centroid'] = centroids.geometry.centroid
        centroids['lon'] = centroids.centroid.x
        centroids['lat'] = centroids.centroid.y
        heat_data = centroids[['lat','lon','SpendCTC']].dropna().values.tolist()
        # Normalize weights a bit
        weights = [[r[0], r[1], float(r[2])] for r in heat_data]
        HeatMap(weights, min_opacity=0.4, radius=40, blur=25, max_zoom=6).add_to(fg_av)
        fg_av.add_to(m)
    except Exception as e:
        st.warning(f'Failed to add AV heatmap: {e}')

# Outdoor sites markers
if show_outdoor:
    fg_out = folium.FeatureGroup(name='Outdoor Sites')
    if latcol and loncol:
        for _, row in outdoor_df.iterrows():
            try:
                lat = float(row[latcol])
                lon = float(row[loncol])
            except Exception:
                continue
            fmt = str(row.iloc[1]) if len(row.index) > 1 else ''
            # default marker
            icon = folium.Icon(color='blue', icon='square', prefix='fa')
            # Map formats to styles
            if 'transvision' in fmt.lower():
                icon = folium.Icon(color='lightblue', icon='stop', prefix='fa')
            elif 'motion waterloo' in fmt.lower():
                icon = folium.Icon(color='darkblue', icon='stop', prefix='fa')
            elif 'rail digital' in fmt.lower():
                icon = folium.Icon(color='green', icon='circle', prefix='fa')
            elif 'road digital' in fmt.lower():
                icon = folium.Icon(color='darkgreen', icon='circle', prefix='fa')
            folium.Marker(location=[lat, lon], popup=str(row.iloc[0]), icon=icon).add_to(fg_out)
        fg_out.add_to(m)
    else:
        st.warning('No latitude/longitude columns detected in OutdoorSites.csv; outdoor markers not added.')

# Store locations markers (geocode by postcode)
if show_stores:
    fg_stores = folium.FeatureGroup(name='Store Locations')
    if stores_geo is not None and not stores_geo.empty:
        for idx, row in stores_df.iterrows():
            try:
                geo = stores_geo.iloc[idx]
                lat = float(geo.latitude)
                lon = float(geo.longitude)
            except Exception:
                continue
            store_name = row.iloc[1] if row.shape[0] > 1 else ''
            store_type = row.iloc[2] if row.shape[0] > 2 else ''
            closing = str(row.iloc[3]) if row.shape[0] > 3 else ''
            if pd.notna(closing) and closing.strip().lower() not in ['', 'nan'] and closing.strip().lower() != 'nan':
                # closed store -> light red
                icon = folium.Icon(color='lightred', icon='shopping-cart', prefix='fa')
            else:
                if 'house of frasers' in str(store_type).lower():
                    icon = folium.Icon(color='gray', icon='shopping-bag', prefix='fa')
                elif 'frasers' in str(store_type).lower():
                    icon = folium.Icon(color='pink', icon='shopping-bag', prefix='fa')
                else:
                    icon = folium.Icon(color='cadetblue', icon='shopping-cart', prefix='fa')
            folium.Marker(location=[lat, lon], popup=store_name, icon=icon).add_to(fg_stores)
        fg_stores.add_to(m)
    else:
        st.warning('Store postcodes could not be geocoded; check Postcode column (5th column) in StoreLocations.csv.')

# Add LayerControl
folium.LayerControl().add_to(m)

# Display map in Streamlit
st.title('UK Multi-Layer Interactive Map')
st.markdown('Toggle layers in the sidebar. Data files can be adjusted in the sidebar inputs.')

st_data = st_folium(m, width=1200, height=800)

# Footer: show unmatched regions for debugging
with st.expander('Debug: unmatched regions and sample data'):
    st.write('Regions Geo DataFrame sample:')
    st.write(regions_gdf.head())
    st.write('Population data sample:')
    st.write(pop_df.head())
    st.write('AV data sample:')
    st.write(av_df.head())
    st.write('Outdoor data sample:')
    st.write(outdoor_df.head())
    st.write('Store data sample:')
    st.write(stores_df.head())


# End of file
