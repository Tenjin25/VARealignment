# Script to scan va_county_aggregated_results.json and extract insights for research findings
# Usage: Run with your .venv Python (see below)
# Example: .venv/Scripts/python.exe scan_va_election_json.py

import json
import os
from collections import defaultdict

DATA_PATH = os.path.join('Data', 'va_county_aggregated_results.json')

# Helper to calculate margin
def get_margin(dem, rep):
    total = dem + rep
    if total == 0:
        return 0
    return ((dem - rep) / total) * 100

def scan_trends(election_data):
    results = {}
    by_year = election_data.get('results_by_year', {})
    years = sorted(by_year.keys())
    # Use correct contest keys as in JSON
    key_races = ['President', 'Governor', 'US Senate']
    if len(years) < 2:
        return results
    last_year = years[-1]
    prev_year = years[-2]
    results['largest_margins'] = {}
    results['biggest_swings'] = {}
    results['statewide_margins'] = {}
    results['flips'] = {}
    for race in key_races:
        last = by_year.get(last_year, {}).get(race, {})
        prev = by_year.get(prev_year, {}).get(race, {})
        max_dem = {'county': '', 'margin': float('-inf')}
        max_rep = {'county': '', 'margin': float('inf')}
        biggest_swing = {'county': '', 'swing': 0}
        for county, l in last.items():
            p = prev.get(county, {})
            margin_last = get_margin(l.get('dem_votes', 0), l.get('rep_votes', 0))
            margin_prev = get_margin(p.get('dem_votes', 0), p.get('rep_votes', 0))
            if margin_last > max_dem['margin']:
                max_dem = {'county': county, 'margin': margin_last}
            if margin_last < max_rep['margin']:
                max_rep = {'county': county, 'margin': margin_last}
            swing = margin_last - margin_prev
            if abs(swing) > abs(biggest_swing['swing']):
                biggest_swing = {'county': county, 'swing': swing}
        results['largest_margins'][race] = {'year': last_year, 'max_dem': max_dem, 'max_rep': max_rep}
        results['biggest_swings'][race] = {'year': last_year, 'biggest_swing': biggest_swing}
        # Statewide margin trend
        margins = []
        for year in years:
            race_data = by_year.get(year, {}).get(race, {})
            dem = sum(row.get('dem_votes', 0) for row in race_data.values())
            rep = sum(row.get('rep_votes', 0) for row in race_data.values())
            margins.append({'year': year, 'margin': get_margin(dem, rep)})
        results['statewide_margins'][race] = margins
        # Flips
        flips = []
        for county, l in last.items():
            p = prev.get(county, {})
            margin_last = get_margin(l.get('dem_votes', 0), l.get('rep_votes', 0))
            margin_prev = get_margin(p.get('dem_votes', 0), p.get('rep_votes', 0))
            if (margin_last > 0 and margin_prev < 0) or (margin_last < 0 and margin_prev > 0):
                flips.append({'county': county, 'from': 'Dem' if margin_prev > 0 else 'Rep', 'to': 'Dem' if margin_last > 0 else 'Rep'})
        results['flips'][race] = {'year': last_year, 'flips': flips}
    return results

def main():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    insights = scan_trends(data)
    print(json.dumps(insights, indent=2))

if __name__ == '__main__':
    main()
