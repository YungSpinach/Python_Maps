# UK Multi-Layer Interactive Map

An interactive Streamlit application that displays multiple data layers on a UK map with toggleable filters.

## Features

Five interactive data layers that can be toggled on/off:

1. **Population Heatmap (Green)** - Shows Total Population by UK region with darker green indicating higher population
2. **Acquisition Audience Heatmap (Blue)** - Shows Acquisition Audience by UK region with darker blue for higher values
3. **AV Spend Heatmap (Red)** - Shows combined VOD + TV advertising spend by region with darker red for higher spend
4. **Outdoor Sites** - Transportation hubs with symbols based on format:
   - Blue squares: Transvision Screen
   - Large dark blue squares: Motion Waterloo
   - Green dots: Rail Digital 6 Sheet
   - Dark green dots: Road Digital 6 Sheet
5. **Store Locations** - Frasers store locations with icons based on store type and status:
   - Grey icons: House of Frasers (Open)
   - Pink icons: Frasers (Open)
   - Light red icons: Closed stores

## Installation

1. Install Python 3.7 or higher

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

Run the Streamlit application:
```bash
streamlit run streamlit_uk_map.py
```

The app will open in your default browser at `http://localhost:8501`

## Data Files Required

Ensure the following CSV files are in the same directory as the script:
- `PopulationSizing.csv` - UK regions with population and acquisition audience data
- `OutdoorSites.csv` - Outdoor advertising sites with location names and formats
- `AV.csv` - Advertising spend data by region and channel (VOD/TV)
- `StoreLocations.csv` - Store locations with postcodes and status information

## Layer Controls

Use the checkboxes in the left sidebar to show/hide each data layer. All layers are enabled by default.

## Notes

- The map is centered on the UK and shows latitude/longitude coordinates
- Hover over or click on map elements to see popup information
- Store locations use a postcode-to-coordinate mapping (predefined for common postcodes)
- For outdoor sites, some location names with typos in the CSV are handled with fuzzy matching
