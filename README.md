# VARealignment

Data-driven interactive mapping and analysis of Virginia political realignment at the county level (1980-2025).

## What This Project Does
- Displays county-level election outcomes on an interactive map (`index.html`)
- Shows county sidebar details (winner, margin, vote breakdown, competitiveness rating)
- Aggregates OpenElections county CSVs into a clean JSON dataset for visualization
- Supports quick research workflows through Python/JS scripts

## Recent Updates
This repository was recently updated with the following changes:

1. County search improvements in `index.html`
- Better suggestion ranking for partial searches (for example, typing `hampton` favors `City of Hampton` over unrelated substring matches like `Southampton`)
- Better handling of county/city aliases and display names

2. Aggregation logic update in `Scripts/build_geojson_and_data_json.py`
- `margin_pct` is now calculated as:
  - `margin / total_votes * 100`
- This keeps margin percentages aligned to total turnout

3. Candidate name normalization updates
- `Willard M. Romney` -> `Mitt Romney`
- `W. T. Bolling`, `William T. Bolling`, and `William Bill T. Bolling` -> `Bill Bolling`

4. Sidebar competitiveness alignment in `index.html`
- Sidebar rating label/color now uses the same `competitiveness` object used by map fill colors
- This removes mismatches where sidebar category/color could disagree with map coloring

5. New validation script
- Added `Scripts/validate_rating_colors.py`
- Validates that each county result has the expected competitiveness:
  - `category`
  - `party`
  - `code`
  - `color`
- Optional `--fix` mode auto-corrects mismatches in place

## Rating Logic (Important)
- `margin_pct` in county records: based on **total votes**
- `competitiveness` category/color: based on **signed margin over total votes** (DEM vs REP)

This is intentional, and both values are now displayed/used consistently in the UI.

## Data Sources
- OpenElections Virginia county-level CSVs (see `Data/openelections/`)
- County geography from Census county shapefile inputs in `Data/tl_2020_51_county20/`

## Key Output Files
- `Data/va_county_aggregated_results.json` (primary app dataset)
- `Data/geo/va_counties_2020.geojson` (map boundary source)

## Scripts
### Build/aggregate data
```powershell
py Scripts/build_geojson_and_data_json.py
```

### Validate competitiveness color/category assignments
```powershell
py Scripts/validate_rating_colors.py
```

### Validate and auto-fix competitiveness mismatches
```powershell
py Scripts/validate_rating_colors.py --fix
```

### Scan JSON for summary insights
```powershell
py Scripts/scan_va_election_json.py
```

## Usage
### Interactive map
Open `index.html` in a browser.

### Typical workflow
1. Update source files in `Data/openelections/` if needed
2. Rebuild data with `build_geojson_and_data_json.py`
3. Run `validate_rating_colors.py`
4. Open `index.html` and verify map/sidebar behavior

## Directory Snapshot
```text
VARealignment/
|- Data/
|  |- geo/
|  |  |- va_counties_2020.geojson
|  |- openelections/
|  |- va_county_aggregated_results.json
|- Scripts/
|  |- build_geojson_and_data_json.py
|  |- validate_rating_colors.py
|  |- scan_va_election_json.py
|  |- scan_va_election_json.js
|- index.html
|- README.md
```

## Development Notes
- Python 3.11+ recommended
- All data/code changes are tracked in git

## Contributing
Pull requests are welcome. Open an issue for bugs, data issues, or feature ideas.

## License
MIT License

## Authors
- Shamar Davis (project lead)

## Repository
https://github.com/Tenjin25/VARealignment
