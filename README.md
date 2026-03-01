# VARealignment

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Data-driven interactive mapping and analysis of Virginia political realignment at the county level (1980-2025).**

An interactive visualization tool for exploring Virginia's electoral shifts over four decades, featuring county-level analysis, multi-year trend tracking, and detailed research findings for statewide and regional patterns.

## 🌐 Live Demo
**[View Live Map](https://tenjin25.github.io/VARealignment/)** | [Repository](https://github.com/Tenjin25/VARealignment)

## ✨ Features

### Interactive Map
- **County-level visualization** of election results with color-coded competitiveness ratings
- **Click counties** to view detailed results, margins, vote breakdowns, and turnout
- **Dynamic year/contest selection** - Switch between Presidential, Gubernatorial, Senate, and other statewide races
- **Search functionality** - Find counties quickly with intelligent ranking
- **Responsive design** - Works on desktop, tablet, and mobile devices
- **Accessibility features** - High-contrast mode and keyboard navigation support

### Research Insights
- **Multi-year trend analysis** - Track margin shifts across multiple election cycles (2012-2024 or expand to 1980-2024)
- **Regional breakdowns** - Analysis for 7 Virginia regions (NoVA, Richmond Metro, Hampton Roads, Southwest VA, etc.)
- **County drilldowns** - Deep-dive analysis for specific counties with historical comparisons
- **Realignment tracking** - Identify counties with the largest partisan swings
- **Turnout analysis** - Track voter participation changes over time
- **Visual data boxes** - Styled metrics highlighting margins, percentages, and vote totals

### Data Processing
- **Automated aggregation** from OpenElections CSV sources
- **Data validation** tools to ensure consistency
- **Competitiveness rating** calculation based on margin thresholds
- **County geography** integration with Census shapefiles
- **JSON API** for easy integration with other tools

## 📑 Table of Contents
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
  - [Interactive Map](#interactive-map)
  - [Script Usage](#script-usage)
- [Data Sources](#-data-sources)
- [Project Structure](#-project-structure)
- [Scripts Documentation](#-scripts-documentation)
- [Data Structure](#-data-structure)
- [Development Workflow](#-development-workflow)
- [Recent Updates](#-recent-updates)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Installation

### Prerequisites
- **Python 3.11+** (required for scripts)
- **Git** (for cloning repository)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Setup
```powershell
# Clone the repository
git clone https://github.com/Tenjin25/VARealignment.git
cd VARealignment

# No additional dependencies required - Python uses standard library only
# Open index.html in your browser to view the map
```

## 🎯 Quick Start

### View the Map
Simply open `index.html` in your web browser:
```powershell
# Windows
start index.html

# Or just double-click index.html in File Explorer
```

### Generate Research Findings
```powershell
# Generate detailed findings for the last 4 election cycles
py Scripts/enrich_research_findings_detailed.py --years 4

# Add specific county analysis
py Scripts/enrich_research_findings_detailed.py --county "Loudoun County" --county "Fairfax County"

# Preview without modifying index.html
py Scripts/enrich_research_findings_detailed.py --dry-run
```

## 📖 Usage

### Interactive Map

**Basic Navigation:**
1. **Select Contest** - Choose from Presidential, Governor, Senate, etc. using the dropdown
2. **Select Year** - Pick an election year from the available data
3. **Click Counties** - View detailed results in the sidebar
4. **Search** - Use the search box to quickly find specific counties
5. **Toggle Accessibility** - Click the accessibility icon for high-contrast mode

**Sidebar Information:**
- Winner and margin
- Vote totals and percentages for Democratic, Republican, and Other candidates
- County competitiveness rating (Safe/Likely/Lean/Tossup)
- Turnout statistics
- Research findings (when generated)

### Script Usage

## 📚 Scripts Documentation

### 1. `enrich_research_findings_detailed.py`
**Purpose:** Generate comprehensive multi-year trend analysis with regional and county-specific insights.

**Features:**
- Multi-year presidential/gubernatorial/senate analysis (configurable from 2-12+ cycles)
- Regional analysis for 7 Virginia regions with contextual descriptions
- County-specific drilldowns with historical comparisons
- Top realigned counties identification
- Margin trends, turnout changes, and party flip tracking
- Styled data boxes for visual emphasis

**Usage:**
```powershell
# Basic usage (4 recent election cycles)
py Scripts/enrich_research_findings_detailed.py

# Analyze specific number of years
py Scripts/enrich_research_findings_detailed.py --years 6

# Add specific county analysis
py Scripts/enrich_research_findings_detailed.py --county "Loudoun County"

# Multiple counties
py Scripts/enrich_research_findings_detailed.py --county "Chesterfield County" --county "Virginia Beach city"

# Or use comma-separated
py Scripts/enrich_research_findings_detailed.py --counties "Loudoun County,Fairfax County,Prince William County"

# Change contest type
py Scripts/enrich_research_findings_detailed.py --contest Governor --years 3

# Show more/fewer realigned counties
py Scripts/enrich_research_findings_detailed.py --top-realigned 10

# Preview without writing to file
py Scripts/enrich_research_findings_detailed.py --dry-run
```

**Output:** Updates `index.html` with detailed findings section including:
- Statewide trend analysis
- Regional cards (NoVA, Richmond Metro, Hampton Roads, Southwest VA, Southside/Rural, Central VA, Shenandoah Valley)
- Top realigned counties with detailed metrics
- Selected county drilldowns with multi-year comparisons

---

### 2. `build_geojson_and_data_json.py`
**Purpose:** Aggregate OpenElections CSV files into clean JSON dataset and generate GeoJSON for mapping.

**Features:**
- Processes all Virginia election CSV files from OpenElections format
- Normalizes candidate names (e.g., "Willard M. Romney" → "Mitt Romney")
- Calculates margins, percentages, and competitiveness ratings
- Generates county geography GeoJSON from Census shapefiles
- Validates data consistency

**Usage:**
```powershell
# Build both data.json and GeoJSON
py Scripts/build_geojson_and_data_json.py

# Custom paths (if needed)
py Scripts/build_geojson_and_data_json.py --input-dir Data/openelections --output Data/custom_output.json
```

**Output:**
- `Data/va_county_aggregated_results.json` - Election data
- `Data/geo/va_counties_2020.geojson` - County boundaries

---

### 3. `validate_rating_colors.py`
**Purpose:** Validate and fix competitiveness rating assignments in the JSON data.

**Features:**
- Validates each county result has correct competitiveness category, party, code, and color
- Checks margin calculations
- Optional auto-fix mode to correct mismatches
- Detailed reporting of issues found

**Usage:**
```powershell
# Validate data (read-only)
py Scripts/validate_rating_colors.py

# Validate and auto-fix issues
py Scripts/validate_rating_colors.py --fix

# Validate specific JSON file
py Scripts/validate_rating_colors.py --json-path Data/custom_data.json
```

**Rating Thresholds:**
- **Safe**: >15% margin
- **Likely**: 10-15% margin
- **Lean**: 5-10% margin
- **Tossup**: <5% margin

---

### 4. `scan_va_election_json.py`
**Purpose:** Quick summary analysis of election data JSON.

**Features:**
- Lists all available years and contests
- Shows county count per contest
- Displays candidate names and vote totals
- Useful for data exploration and debugging

**Usage:**
```powershell
# Basic scan
py Scripts/scan_va_election_json.py

# Scan specific file
py Scripts/scan_va_election_json.py --json-path Data/va_county_aggregated_results.json
```

---

### 5. `enrich_research_findings.py`
**Purpose:** Simpler version of research findings generation (maintained for backward compatibility).

**Note:** `enrich_research_findings_detailed.py` is recommended for most use cases as it provides more comprehensive analysis.

**Usage:**
```powershell
py Scripts/enrich_research_findings.py
```

---

### 6. `convert_to_openelections.py`
**Purpose:** Convert Virginia Department of Elections CSV format to OpenElections format.

**Usage:**
```powershell
py Scripts/convert_to_openelections.py --input raw_data.csv --output Data/openelections/formatted.csv
```

## 📊 Data Structure

### JSON Data Format (`va_county_aggregated_results.json`)
```json
{
  "results_by_year": {
    "2024": {
      "President": {
        "Fairfax County": {
          "county_name": "Fairfax County",
          "dem_candidate": "Kamala Harris",
          "dem_votes": 450000,
          "rep_candidate": "Donald Trump",
          "rep_votes": 280000,
          "other_votes": 12000,
          "total_votes": 742000,
          "margin": 170000,
          "margin_pct": 22.91,
          "competitiveness": {
            "category": "Safe Democratic",
            "party": "DEM",
            "code": "SAFE_DEM",
            "color": "#1e3a8a"
          }
        }
      }
    }
  }
}
```

### GeoJSON Format (`va_counties_2020.geojson`)
Standard GeoJSON FeatureCollection with county polygons and properties including:
- `NAME`: County name
- `GEOID`: Census FIPS code
- Geometry coordinates for mapping

## 📁 Project Structure

```text
VARealignment/
├── Data/
│   ├── geo/
│   │   └── va_counties_2020.geojson         # County boundary polygons
│   ├── openelections/                        # Source CSV files from OpenElections
│   │   ├── Virginia_Elections_Database__1980_President_General_Election.csv
│   │   ├── Virginia_Elections_Database__1984_President_General_Election.csv
│   │   └── ...                               # More election CSVs
│   ├── tl_2020_51_county20/                  # Census shapefile data
│   ├── va_county_aggregated_results.json     # Primary dataset (generated)
│   └── Election Results_Nov_2025.csv         # Recent election data
├── Scripts/
│   ├── build_geojson_and_data_json.py        # Main data aggregation script
│   ├── enrich_research_findings_detailed.py  # Detailed findings generator
│   ├── enrich_research_findings.py           # Simple findings generator
│   ├── validate_rating_colors.py             # Data validation tool
│   ├── scan_va_election_json.py              # JSON explorer (Python)
│   ├── scan_va_election_json.js              # JSON explorer (Node.js)
│   └── convert_to_openelections.py           # Format converter
├── index.html                                 # Main interactive map application
├── MDMap.html                                 # Maryland comparison map
├── README.md                                  # This file
└── .gitignore                                 # Git ignore rules
```

## 🔄 Development Workflow

### Standard Development Cycle
1. **Update source data** - Add new election CSVs to `Data/openelections/`
2. **Rebuild aggregated data** - Run `build_geojson_and_data_json.py`
3. **Validate ratings** - Run `validate_rating_colors.py` (with `--fix` if needed)
4. **Generate findings** - Run `enrich_research_findings_detailed.py` with desired parameters
5. **Test in browser** - Open `index.html` and verify all functionality
6. **Commit changes** - Use git to track modifications

### Example Workflow
```powershell
# 1. Add new 2025 election data to Data/openelections/
# 2. Rebuild the dataset
py Scripts/build_geojson_and_data_json.py

# 3. Validate and fix any rating issues
py Scripts/validate_rating_colors.py --fix

# 4. Generate updated research findings
py Scripts/enrich_research_findings_detailed.py --years 4 --top-realigned 10

# 5. Test the map
start index.html

# 6. Commit if everything looks good
git add .
git commit -m "Add 2025 election data and updated findings"
git push
```

## 📈 Data Sources

### Primary Sources
- **[OpenElections Virginia](http://www.openelections.net/va/)** - County-level election results (1980-2020)
  - Presidential, Gubernatorial, Senate, and statewide office elections
  - Standardized CSV format
  - Public domain data
- **[Virginia Department of Elections](https://www.elections.virginia.gov/)** - Official state election results (2021-2025)
- **[US Census Bureau](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)** - County boundary shapefiles (2020 TIGER/Line)

### Data Coverage
- **Time Period**: 1980-2025 (45 years)
- **Geographic Level**: County and independent city
- **Contests**: President, Governor, US Senate, Lieutenant Governor, Attorney General
- **Counties/Cities**: 133 Virginia localities

### Data Processing Notes
- Candidate names are normalized for consistency
- Third-party and write-in votes are aggregated into "Other"
- Competitiveness ratings calculated using margin thresholds
- Special elections and primaries are not included

### Key Output Files
- `Data/va_county_aggregated_results.json` - Primary app dataset
- `Data/geo/va_counties_2020.geojson` - Map boundary source

## 🎨 Competitiveness Rating System

The map uses a color-coded system to show how competitive each county is:

### Democratic Advantage
- **Safe Democratic** (>15% margin) - Dark Blue `#1e3a8a`
- **Likely Democratic** (10-15% margin) - Medium Blue `#3b82f6`
- **Lean Democratic** (5-10% margin) - Light Blue `#93c5fd`
- **Tossup Democratic** (<5% margin) - Pale Blue `#dbeafe`

### Republican Advantage
- **Tossup Republican** (<5% margin) - Pale Red `#fee2e2`
- **Lean Republican** (5-10% margin) - Light Red `#fca5a5`
- **Likely Republican** (10-15% margin) - Medium Red `#ef4444`
- **Safe Republican** (>15% margin) - Dark Red `#991b1b`

### Special Cases
- **No Data** - Gray `#d1d5db`

### Rating Logic
- `margin_pct` in county records: based on **total votes**
- `competitiveness` category/color: based on **signed margin over total votes** (DEM vs REP)
- Both values are displayed/used consistently in the UI

## 🚀 Deployment

### GitHub Pages (Current)
The project is automatically deployed to GitHub Pages:
```
https://tenjin25.github.io/VARealignment/
```

### Manual Deployment
To deploy to any static hosting service:
1. Upload `index.html` to your web server
2. Upload `Data/` directory (must maintain structure)
3. Ensure CORS is enabled if serving JSON from different domain
4. No build process required - pure HTML/CSS/JavaScript

### Local Development Server
```powershell
# Python (simple HTTP server)
cd VARealignment
python -m http.server 8000

# Then open http://localhost:8000/index.html
```

## 🧪 Testing

### Browser Testing
Recommended browsers for testing:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

### Validation Checklist
- [ ] Map loads without errors
- [ ] County colors match competitiveness ratings
- [ ] Sidebar updates when clicking counties
- [ ] Contest/year selectors work correctly
- [ ] Search functionality returns correct results
- [ ] Research findings display properly
- [ ] Mobile responsive design works
- [ ] Accessibility mode functions correctly

## 📝 Recent Updates

### Enhanced Data Box Styling (Feb 2026)
- Updated data boxes to match Maryland map metric design
- Pill/badge style with rounded corners and subtle backgrounds
- Consistent 2-decimal precision for percentages and margins
- Party-color themed boxes (blue for Democratic, red for Republican)

### Expanded County Analysis (Feb 2026)
- Added Charles City County, Loudoun County, and Prince William County drilldowns
- Now featuring 8 counties with detailed multi-year analysis
- Long-term swing tracking (2012-2024)
- Turnout change percentages and party flip detection

### Comprehensive Research Findings (Feb 2026)
- Multi-year trend analysis spanning 4-12 election cycles
- Regional analysis for 7 Virginia regions with contextual descriptions
- Top realigned counties identification
- Styled data visualizations for better readability

### Previous Updates
1. **County search improvements** - Better suggestion ranking for partial searches
2. **Aggregation logic update** - `margin_pct` calculated as `(margin / total_votes) * 100`
3. **Candidate name normalization** - Standardized presidential tickets and candidate names
4. **Sidebar competitiveness alignment** - Consistent rating display between map and sidebar
5. **New validation script** - `validate_rating_colors.py` with optional `--fix` mode

## 🤝 Contributing

### How to Contribute
1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/YourFeature`)
3. **Make your changes** with clear commit messages
4. **Test thoroughly** - Verify map functionality and data accuracy
5. **Submit a pull request** with description of changes

### Contribution Ideas
- Add new election data (2026+)
- Improve data visualization
- Add new analysis features
- Enhance mobile experience
- Fix bugs or improve performance
- Update documentation
- Add unit tests

### Code Style
- Python: Follow PEP 8 guidelines
- JavaScript: Use consistent indentation (2 spaces)
- HTML/CSS: Semantic markup, clear class names
- Comments: Explain non-obvious logic

### Reporting Issues
When reporting bugs or issues, please include:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Browser/OS information
- Screenshots if applicable

## 🔮 Future Enhancements

### Planned Features
- [ ] Export map as PNG/SVG
- [ ] Share specific county/year/contest via URL parameters
- [ ] Comparison mode (side-by-side years)
- [ ] Turnout heatmap overlay
- [ ] Historical timeline slider
- [ ] Congressional district analysis
- [ ] Demographics overlay
- [ ] Scatter plot view (margin vs turnout)
- [ ] Data download functionality (CSV/JSON)
- [ ] Advanced filtering and sorting

### Wishlist
- API endpoint for programmatic access
- Embeddable widget for other sites
- Animated transition between years
- Mobile app version
- Real-time election night updates

## 📄 License
MIT License - See LICENSE file for details

## 👤 Authors
**Shamar Davis** - Project Lead & Developer
- GitHub: [@Tenjin25](https://github.com/Tenjin25)

## 🔗 Links
- **Repository**: [https://github.com/Tenjin25/VARealignment](https://github.com/Tenjin25/VARealignment)
- **Live Demo**: [https://tenjin25.github.io/VARealignment/](https://tenjin25.github.io/VARealignment/)
- **Issues**: [https://github.com/Tenjin25/VARealignment/issues](https://github.com/Tenjin25/VARealignment/issues)

## 🙏 Acknowledgments
- OpenElections for providing comprehensive Virginia election data
- US Census Bureau for county boundary shapefiles
- Virginia Department of Elections for official results
- All contributors and users of this project

---

**Made with ❤️ for Virginia political analysis**
