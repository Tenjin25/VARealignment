# VARealignment

A data-driven, interactive visualization and analysis project for Virginia's political realignment at the county level (1980–2025).

## Features
- Interactive map of Virginia counties with political color coding
- Sidebar with county-level and statewide election analysis
- Research findings highlighting key trends and realignment patterns
- Scripts for extracting insights from election data
- Data files for presidential, gubernatorial, and senate elections

## Data Sources
- OpenElections Virginia county-level CSVs (see Data/)
- Aggregated and processed into `Data/va_county_aggregated_results.json`

## Directory Structure
```
VARealignment/
├── Data/
│   ├── va_county_aggregated_results.json
│   └── ... (raw CSVs)
├── Scripts/
│   └── scan_va_election_json.py
├── index.html
├── README.md
└── ...
```

## Usage
### Interactive Map
Open `index.html` in your browser. The map and sidebar provide:
- County-level results and trends
- Statewide contest selection
- Research findings (editable in HTML)

### Data Analysis Scripts
Python (via `.venv`):
```sh
.venv/Scripts/python.exe Scripts/scan_va_election_json.py
```
This script scans the nested JSON and outputs:
- Counties with largest Dem/Rep margins
- Biggest swings
- Statewide margin trends
- Counties that flipped party

### Development
- Requires Python 3.11+ (see `.venv`)
- Node.js script also available for similar analysis
- All code and data are version controlled with git

## Contributing
Pull requests welcome! Please open issues for bugs or suggestions.

## License
MIT License

## Authors
- Shamar Davis (project lead)

## Repository
https://github.com/Tenjin25/VARealignment
