import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'Data'
GEO_DIR = DATA_DIR / 'geo'
OUT_DIR = DATA_DIR / 'processed'
OPENELECTIONS_DIR = DATA_DIR / 'openelections'
GEO_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

SHAPE_PATH = DATA_DIR / 'tl_2020_51_county20' / 'tl_2020_51_county20.shp'
GEOJSON_PATH = GEO_DIR / 'va_counties_2020.geojson'
JSON_PATH = DATA_DIR / 'va_county_aggregated_results.json'

COMPETITIVENESS_SCALE = {
    'Republican': [
        {'category': 'Annihilation', 'range': 'R+40%+', 'color': '#67000d'},
        {'category': 'Dominant', 'range': 'R+30.00-39.99%', 'color': '#a50f15'},
        {'category': 'Stronghold', 'range': 'R+20.00-29.99%', 'color': '#cb181d'},
        {'category': 'Safe', 'range': 'R+10.00-19.99%', 'color': '#ef3b2c'},
        {'category': 'Likely', 'range': 'R+5.50-9.99%', 'color': '#fb6a4a'},
        {'category': 'Lean', 'range': 'R+1.00-5.49%', 'color': '#fcae91'},
        {'category': 'Tilt', 'range': 'R+0.50-0.99%', 'color': '#fee8c8'},
    ],
    'Tossup': [
        {'category': 'Tossup', 'range': '<0.5%', 'color': '#f7f7f7'},
    ],
    'Democratic': [
        {'category': 'Tilt', 'range': 'D+0.50-0.99%', 'color': '#e1f5fe'},
        {'category': 'Lean', 'range': 'D+1.00-5.49%', 'color': '#c6dbef'},
        {'category': 'Likely', 'range': 'D+5.50-9.99%', 'color': '#9ecae1'},
        {'category': 'Safe', 'range': 'D+10.00-19.99%', 'color': '#6baed6'},
        {'category': 'Stronghold', 'range': 'D+20.00-29.99%', 'color': '#3182bd'},
        {'category': 'Dominant', 'range': 'D+30.00-39.99%', 'color': '#08519c'},
        {'category': 'Annihilation', 'range': 'D+40%+', 'color': '#08306b'},
    ],
}

PARTY_CODE_MAP = {
    'DEMOCRATIC': 'DEM',
    'REPUBLICAN': 'REP',
    'LIBERTARIAN': 'LIB',
    'GREEN': 'GRN',
    'INDEPENDENT': 'IND',
    'FORWARD': 'FWD',
    'OTHER': 'OTH',
    'WRITE-IN': 'WRI',
    'WRITE IN': 'WRI',
    '': 'OTH',
}

ALLOWED_CONTESTS = {
    'President',
    'U.S. Senate',
    'Governor',
    'Lieutenant Governor',
    'Attorney General',
}

HISTORICAL_TO_CURRENT = {
    'BEDFORD CITY': 'BEDFORD COUNTY',
    'CLIFTON FORGE CITY': 'ALLEGHANY COUNTY',
    'S BOSTON CITY': 'HALIFAX COUNTY',
    'SOUTH BOSTON CITY': 'HALIFAX COUNTY',
    'MANASSAS COUNTY': 'MANASSAS CITY',
}

CANDIDATE_NAME_OVERRIDES = {
    'A. Donald McEachin': 'Aston Donald McEachin',
    'C. S. Robb': 'Charles S. Robb',
    'Charies S. Robb': 'Charles S. Robb',
    'D. S. Beyer, Jr': 'Donald S. Beyer, Jr',
    'G. F. Allen': 'George F. Allen',
    'J. H. Hager': 'John H. Hager',
    'J. H. Webb, Jr': 'James H. Webb, Jr',
    'J. K. Katzen': 'Jay K. Katzen',
    'J. Marshall Coleman': 'John Marshall Coleman',
    'J. S. Gilmore, III': 'James S. Gilmore, III',
    'J. W. Kilgore': 'Jerry W. Kilgore',
    'James Jim S. Gilmore, III': 'James S. Gilmore, III',
    'J. W. Warner': 'John W. Warner',
    'L. F. Payne, Jr': 'Lewis F. Payne, Jr',
    'L. L. Byrne': 'Leslie L. Byrne',
    'M. L. Earley': 'Mark L. Earley',
    'M. R. Warner': 'Mark R. Warner',
    'T. M. Kaine': 'Timothy M. Kaine',
    'W. B. Redpath': 'William B. Redpath',
    "W. R. O'Brien": "William R. O'Brien",
    'W. T. Bolling': 'William T. Bolling',
    'William Bill T. Bolling': 'William T. Bolling',
}


def normalize_county(name: str) -> str:
    s = (name or '').strip().upper()
    s = s.replace('&', 'AND')
    s = s.replace('.', '')
    s = re.sub(r'\s+', ' ', s)
    return s


def clean_county_for_matching(name: str) -> str:
    s = (name or '').strip()
    # Older files sometimes append congressional-district tags to locality labels.
    s = re.sub(r'\s*\(CD\s*0*\d+\)\s*$', '', s, flags=re.IGNORECASE)
    return s


def parse_votes(value: str) -> int:
    s = str(value or '').replace(',', '').strip()
    if not s:
        return 0
    return int(float(s))


def party_code(party_name: str) -> str:
    p = (party_name or '').strip().upper()
    return PARTY_CODE_MAP.get(p, p[:3] if p else 'OTH')


def canonical_candidate_name(name: str) -> str:
    n = (name or '').strip()
    return CANDIDATE_NAME_OVERRIDES.get(n, n)


def classify_office_type(contest: str) -> str:
    c = contest.lower()
    if any(x in c for x in ['president', 'senate', 'house of representatives', 'u.s.', 'us senate', 'congress']):
        return 'Federal'
    if any(x in c for x in ['judge', 'judicial', 'justice']):
        return 'Judicial'
    if any(x in c for x in ['governor', 'attorney general', 'lieutenant governor', 'house of delegates']):
        return 'State'
    return 'Other'


def contest_rank(contest: str) -> int:
    c = contest.lower()
    if c == 'president':
        return 1
    if c in {'u.s. senate', 'us senate'}:
        return 2
    if c == 'governor':
        return 3
    if c == 'lieutenant governor':
        return 4
    if c == 'attorney general':
        return 5
    return 99


def canonical_contest(contest: str) -> str:
    c = (contest or '').strip()
    if c.lower() == 'us senate':
        return 'U.S. Senate'
    return c


def year_from_filename(path: Path) -> str:
    m = re.match(r'^(\d{4})\d{4}__', path.name)
    if m:
        return m.group(1)
    return 'unknown'


def write_geojson_and_counties():
    gdf = gpd.read_file(SHAPE_PATH)
    keep_cols = ['GEOID20', 'NAME20', 'NAMELSAD20', 'ALAND20', 'AWATER20', 'geometry']
    gdf = gdf[keep_cols].copy()
    gdf = gdf.rename(
        columns={
            'GEOID20': 'geoid',
            'NAME20': 'name',
            'NAMELSAD20': 'namelsad',
            'ALAND20': 'aland',
            'AWATER20': 'awater',
        }
    )
    gdf.to_file(GEOJSON_PATH, driver='GeoJSON')

    county_map = {}
    county_info = {}
    for _, row in gdf.iterrows():
        key = normalize_county(row['namelsad'])
        geoid = str(row['geoid'])
        county_map[key] = geoid
        county_info[geoid] = {
            'county': str(row['namelsad']),
            'county_label': str(row['namelsad']),
            'fips': geoid,
        }
    return county_map, county_info


def competitiveness_from_margin(signed_margin_pct: float):
    abs_margin = abs(signed_margin_pct)
    if abs_margin < 0.5:
        return {'category': 'Tossup', 'party': 'Tossup', 'code': 'TOSSUP', 'color': '#f7f7f7'}

    if signed_margin_pct > 0:
        side = 'Democratic'
        prefix = 'D'
        colors = {
            'Tilt': '#e1f5fe',
            'Lean': '#c6dbef',
            'Likely': '#9ecae1',
            'Safe': '#6baed6',
            'Stronghold': '#3182bd',
            'Dominant': '#08519c',
            'Annihilation': '#08306b',
        }
    else:
        side = 'Republican'
        prefix = 'R'
        colors = {
            'Tilt': '#fee8c8',
            'Lean': '#fcae91',
            'Likely': '#fb6a4a',
            'Safe': '#ef3b2c',
            'Stronghold': '#cb181d',
            'Dominant': '#a50f15',
            'Annihilation': '#67000d',
        }

    if abs_margin < 1:
        category = 'Tilt'
    elif abs_margin < 5.5:
        category = 'Lean'
    elif abs_margin < 10:
        category = 'Likely'
    elif abs_margin < 20:
        category = 'Safe'
    elif abs_margin < 30:
        category = 'Stronghold'
    elif abs_margin < 40:
        category = 'Dominant'
    else:
        category = 'Annihilation'

    return {
        'category': category,
        'party': side,
        'code': f'{prefix}_{category.upper()}',
        'color': colors[category],
    }


def build_county_record(year: str, contest: str, county_label: str, fips: str, party_rows: list[dict]):
    total_votes = sum(r['votes'] for r in party_rows)

    dem_rows = [r for r in party_rows if r['party_code'] == 'DEM']
    rep_rows = [r for r in party_rows if r['party_code'] == 'REP']

    dem_votes = sum(r['votes'] for r in dem_rows)
    rep_votes = sum(r['votes'] for r in rep_rows)

    dem_candidate = max(dem_rows, key=lambda r: r['votes'])['candidate'] if dem_rows else ''
    rep_candidate = max(rep_rows, key=lambda r: r['votes'])['candidate'] if rep_rows else ''

    two_party_total = dem_votes + rep_votes
    margin = abs(dem_votes - rep_votes)

    # Keep competitiveness behavior the same (two-party signed margin),
    # but compute margin_pct using total votes as requested.
    if two_party_total > 0:
        signed_margin_pct = ((dem_votes - rep_votes) / two_party_total) * 100.0
    else:
        signed_margin_pct = 0.0

    if total_votes > 0:
        margin_pct = (margin / total_votes) * 100.0
    else:
        # Fallback when no votes are present: compare top two overall candidates.
        sorted_rows = sorted(party_rows, key=lambda x: x['votes'], reverse=True)
        top1 = sorted_rows[0]['votes'] if len(sorted_rows) > 0 else 0
        top2 = sorted_rows[1]['votes'] if len(sorted_rows) > 1 else 0
        margin = abs(top1 - top2)
        margin_pct = 0.0

    if dem_votes > rep_votes:
        winner = 'DEM'
    elif rep_votes > dem_votes:
        winner = 'REP'
    else:
        winner = max(party_rows, key=lambda r: r['votes'])['party_code'] if party_rows else 'TIE'

    other_votes = total_votes - dem_votes - rep_votes

    all_parties = defaultdict(int)
    for r in party_rows:
        all_parties[r['party_code']] += r['votes']

    return {
        'county': county_label,
        'county_fips': fips,
        'contest': contest,
        'year': year,
        'office_type': classify_office_type(contest),
        'office_rank': contest_rank(contest),
        'dem_candidate': dem_candidate,
        'rep_candidate': rep_candidate,
        'dem_votes': dem_votes,
        'rep_votes': rep_votes,
        'dem_pct': round((dem_votes / total_votes * 100.0), 2) if total_votes else 0.0,
        'rep_pct': round((rep_votes / total_votes * 100.0), 2) if total_votes else 0.0,
        'other_votes': other_votes,
        'total_votes': total_votes,
        'two_party_total': two_party_total,
        'margin': margin,
        'margin_pct': f'{margin_pct:.2f}',
        'winner': winner,
        'competitiveness': competitiveness_from_margin(signed_margin_pct),
        'all_parties': dict(sorted(all_parties.items())),
    }


def load_all_rows():
    rows = []
    source_files = []
    for path in sorted(OPENELECTIONS_DIR.glob('*.csv')):
        year = year_from_filename(path)
        with path.open('r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            required = {'county', 'office', 'party', 'candidate', 'votes'}
            if not required.issubset(set(reader.fieldnames or [])):
                continue
            for row in reader:
                county = (row.get('county') or '').strip()
                if not county:
                    continue
                county_clean = clean_county_for_matching(county)
                norm = normalize_county(county_clean)
                if norm in {'TOTAL', 'TOTALS', 'VIRGINIA', 'COMMONWEALTH OF VIRGINIA'}:
                    continue

                contest = canonical_contest((row.get('office') or '').strip())
                if not contest:
                    continue
                if contest not in ALLOWED_CONTESTS:
                    continue

                rows.append(
                    {
                        'source_file': path.name,
                        'year': year,
                        'contest': contest,
                        'county_raw': county,
                        'county_clean': county_clean,
                        'county_norm': norm,
                        'candidate': canonical_candidate_name((row.get('candidate') or '').strip()),
                        'party': (row.get('party') or '').strip(),
                        'party_code': party_code(row.get('party') or ''),
                        'votes': parse_votes(row.get('votes', '0')),
                    }
                )
        source_files.append(path.name)
    return rows, source_files


def main():
    county_map, county_info = write_geojson_and_counties()

    all_rows, source_files = load_all_rows()

    grouped = defaultdict(list)
    unmatched = defaultdict(set)

    for r in all_rows:
        county_norm = HISTORICAL_TO_CURRENT.get(r['county_norm'], r['county_norm'])
        geoid = county_map.get(county_norm)
        if not geoid:
            unmatched[r['year']].add(r['county_raw'])
            continue
        grouped[(r['year'], r['contest'], geoid)].append(r)

    results_by_year = defaultdict(dict)
    total_county_results = 0

    for (year, contest, geoid), party_rows in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        county_label = county_info[geoid]['county']
        county_record = build_county_record(year, contest, county_label, geoid, party_rows)

        if contest not in results_by_year[year]:
            results_by_year[year][contest] = {}
        results_by_year[year][contest][county_label] = county_record
        total_county_results += 1

    years_covered = sorted([y for y in results_by_year.keys() if y != 'unknown'])
    all_contests = sorted({contest for y in results_by_year.values() for contest in y.keys()})

    payload = {
        'focus': 'Clean geographic political patterns',
        'processed_date': str(date.today()),
        'categorization_system': {
            'competitiveness_scale': COMPETITIVENESS_SCALE,
            'office_types': ['Federal', 'State', 'Judicial', 'Other'],
            'enhanced_features': [
                'Competitiveness categorization for each county',
                'Contest type classification (Federal/State/Judicial)',
                'Office ranking system for analysis prioritization',
                'Color coding compatible with political geography visualization',
            ],
        },
        'summary': {
            'total_years': len(years_covered),
            'total_contests': len(all_contests),
            'total_county_results': total_county_results,
            'years_covered': years_covered,
        },
        'source_openelections_files': source_files,
        'unmatched_counties': {k: sorted(v) for k, v in unmatched.items()},
        'results_by_year': dict(results_by_year),
    }

    with JSON_PATH.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)

    print(f'Wrote {GEOJSON_PATH}')
    print(f'Wrote {JSON_PATH}')
    print(f'Source files: {len(source_files)}')
    print(f'Years: {years_covered[0]}-{years_covered[-1]} ({len(years_covered)} years)')
    print(f'Contests: {len(all_contests)}')
    print(f'Total county results: {total_county_results}')
    print(f'Unmatched counties: {sum(len(v) for v in unmatched.values())}')


if __name__ == '__main__':
    main()
