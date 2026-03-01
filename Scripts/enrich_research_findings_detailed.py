#!/usr/bin/env python3
"""Generate highly detailed research findings from election JSON with multi-year trends.

Usage:
  py Scripts/enrich_research_findings_detailed.py
  py Scripts/enrich_research_findings_detailed.py --dry-run
  py Scripts/enrich_research_findings_detailed.py --contest Governor
  py Scripts/enrich_research_findings_detailed.py --top-realigned 10
  py Scripts/enrich_research_findings_detailed.py --county "Loudoun County"
  py Scripts/enrich_research_findings_detailed.py --years 3
"""

import argparse
import html
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from statistics import mean, median

DEFAULT_JSON_PATH = Path("Data/va_county_aggregated_results.json")
DEFAULT_INDEX_PATH = Path("index.html")

# Regional classification of Virginia counties
NOVA_COUNTIES = {
    "Arlington County", "Fairfax County", "Loudoun County", "Prince William County",
    "Alexandria city", "Fairfax city", "Falls Church city", "Manassas city", "Manassas Park city",
}

RICHMOND_METRO = {
    "Richmond city", "Henrico County", "Chesterfield County", "Hanover County",
}

HAMPTON_ROADS = {
    "Norfolk city", "Portsmouth city", "Newport News city", "Hampton city",
    "Virginia Beach city", "Chesapeake city", "Suffolk city",
}

SOUTHWEST_VA = {
    "Buchanan County", "Dickenson County", "Lee County", "Russell County",
    "Scott County", "Tazewell County", "Wise County", "Smyth County",
    "Washington County", "Grayson County", "Wythe County",
    "Bristol city", "Galax city", "Norton city",
}

SOUTHSIDE_RURAL = {
    "Brunswick County", "Charlotte County", "Halifax County", "Lunenburg County",
    "Mecklenburg County", "Pittsylvania County", "Patrick County", "Henry County",
    "Franklin County", "Nottoway County", "Amelia County", "Cumberland County",
    "Dinwiddie County", "Greensville County", "Prince Edward County",
}

CENTRAL_VA = {
    "Albemarle County", "Charlottesville city", "Fluvanna County", "Greene County",
    "Nelson County", "Orange County", "Madison County", "Culpeper County",
}

SHENANDOAH_VALLEY = {
    "Augusta County", "Rockingham County", "Shenandoah County", "Frederick County",
    "Clarke County", "Warren County", "Page County", "Rockbridge County",
    "Harrisonburg city", "Staunton city", "Waynesboro city", "Winchester city",
}


def safe_margin(dem_votes: float, rep_votes: float) -> float:
    """Calculate Democratic margin as percentage."""
    total = dem_votes + rep_votes
    if total <= 0:
        return 0.0
    return ((dem_votes - rep_votes) / total) * 100.0


def safe_percentage(votes: float, total: float) -> float:
    """Calculate vote percentage."""
    if total <= 0:
        return 0.0
    return (votes / total) * 100.0


def fmt_margin(value: float) -> str:
    """Format margin with party prefix."""
    party = "D" if value >= 0 else "R"
    return f"{party}+{abs(value):.1f}%"


def fmt_pct(value: float) -> str:
    """Format percentage."""
    return f"{value:.1f}%"


def contest_years(results_by_year: Dict, contest: str) -> List[str]:
    """Get available years for a contest."""
    years = []
    for year in sorted(results_by_year.keys()):
        if contest in results_by_year.get(year, {}):
            years.append(year)
    return years


def aggregate_region(results: Dict[str, Dict], counties: set) -> Dict[str, float]:
    """Aggregate results for a region."""
    dem = rep = other = total = 0
    for county in counties:
        row = results.get(county)
        if not row:
            continue
        d = row.get("dem_votes", 0) or 0
        r = row.get("rep_votes", 0) or 0
        t = row.get("total_votes", 0) or 0
        dem += d
        rep += r
        total += t
        other += max(0, t - d - r)
    
    two_party = dem + rep
    return {
        "dem_votes": dem,
        "rep_votes": rep,
        "other_votes": other,
        "total_votes": total,
        "margin": safe_margin(dem, rep),
        "dem_pct": safe_percentage(dem, two_party),
        "rep_pct": safe_percentage(rep, two_party),
        "other_pct": safe_percentage(other, total),
    }


def statewide_summary(results: Dict[str, Dict]) -> Dict[str, float]:
    """Calculate statewide summary statistics."""
    dem = sum((r.get("dem_votes", 0) or 0) for r in results.values())
    rep = sum((r.get("rep_votes", 0) or 0) for r in results.values())
    other = 0
    total = sum((r.get("total_votes", 0) or 0) for r in results.values())
    other = max(0, total - dem - rep)
    
    two_party = dem + rep
    return {
        "dem_votes": dem,
        "rep_votes": rep,
        "other_votes": other,
        "total_votes": total,
        "margin": safe_margin(dem, rep),
        "dem_pct": safe_percentage(dem, two_party),
        "rep_pct": safe_percentage(rep, two_party),
        "other_pct": safe_percentage(other, total),
    }


def multi_year_trend(
    results_by_year: Dict,
    contest: str,
    counties: set,
    years: List[str]
) -> List[Dict]:
    """Calculate trends over multiple years for a region."""
    trend = []
    for year in years:
        if year not in results_by_year or contest not in results_by_year[year]:
            continue
        agg = aggregate_region(results_by_year[year][contest], counties)
        trend.append({
            'year': year,
            'margin': agg['margin'],
            'dem_pct': agg['dem_pct'],
            'rep_pct': agg['rep_pct'],
            'turnout': agg['total_votes'],
        })
    return trend


def format_trend(trend: List[Dict], metric: str = 'margin') -> str:
    """Format a trend line for display."""
    if not trend:
        return "No data"
    items = []
    for t in trend:
        year = t['year']
        if metric == 'margin':
            items.append(f"{year}: {fmt_margin(t['margin'])}")
        elif metric == 'turnout':
            items.append(f"{year}: {t['turnout']:,}")
        elif metric == 'dem_pct':
            items.append(f"{year}: {fmt_pct(t['dem_pct'])}")
    return " → ".join(items)


def calculate_swing(trend: List[Dict], metric: str = 'margin') -> Optional[float]:
    """Calculate total swing over time."""
    if len(trend) < 2:
        return None
    return trend[-1][metric] - trend[0][metric]


def county_swings(curr: Dict[str, Dict], prev: Dict[str, Dict]) -> List[Tuple[str, float, float, float]]:
    """Calculate county swings between two elections."""
    swings = []
    for county, c_row in curr.items():
        p_row = prev.get(county)
        if not p_row:
            continue
        curr_margin = safe_margin(c_row.get("dem_votes", 0) or 0, c_row.get("rep_votes", 0) or 0)
        prev_margin = safe_margin(p_row.get("dem_votes", 0) or 0, p_row.get("rep_votes", 0) or 0)
        swings.append((county, curr_margin - prev_margin, curr_margin, prev_margin))
    swings.sort(key=lambda x: abs(x[1]), reverse=True)
    return swings


def multi_year_county_swing(
    results_by_year: Dict,
    contest: str,
    county: str,
    years: List[str]
) -> List[Dict]:
    """Get multi-year data for a county."""
    data = []
    for year in years:
        if year not in results_by_year or contest not in results_by_year[year]:
            continue
        results = results_by_year[year][contest]
        if county not in results:
            continue
        row = results[county]
        dem = row.get("dem_votes", 0) or 0
        rep = row.get("rep_votes", 0) or 0
        total = row.get("total_votes", 0) or 0
        margin = safe_margin(dem, rep)
        two_party = dem + rep
        data.append({
            'year': year,
            'margin': margin,
            'dem_pct': safe_percentage(dem, two_party),
            'rep_pct': safe_percentage(rep, two_party),
            'turnout': total,
            'dem_votes': dem,
            'rep_votes': rep,
        })
    return data


def flips(curr: Dict[str, Dict], prev: Dict[str, Dict]) -> List[Tuple[str, str, str]]:
    """Find counties that flipped parties."""
    out = []
    for county, c_row in curr.items():
        p_row = prev.get(county)
        if not p_row:
            continue
        curr_margin = safe_margin(c_row.get("dem_votes", 0) or 0, c_row.get("rep_votes", 0) or 0)
        prev_margin = safe_margin(p_row.get("dem_votes", 0) or 0, p_row.get("rep_votes", 0) or 0)
        if curr_margin == 0 or prev_margin == 0:
            continue
        curr_party = "Democratic" if curr_margin > 0 else "Republican"
        prev_party = "Democratic" if prev_margin > 0 else "Republican"
        if curr_party != prev_party:
            out.append((county, prev_party, curr_party))
    out.sort(key=lambda x: x[0])
    return out


def top_turnout(results: Dict[str, Dict], n: int = 5) -> List[Tuple[str, int]]:
    """Get top turnout counties."""
    pairs = [(county, int(row.get("total_votes", 0) or 0)) for county, row in results.items()]
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:n]


def turnout_change(curr: Dict[str, Dict], prev: Dict[str, Dict]) -> List[Tuple[str, float, int, int]]:
    """Calculate turnout changes between elections."""
    changes = []
    for county, c_row in curr.items():
        p_row = prev.get(county)
        if not p_row:
            continue
        curr_turnout = c_row.get("total_votes", 0) or 0
        prev_turnout = p_row.get("total_votes", 0) or 0
        if prev_turnout == 0:
            continue
        pct_change = ((curr_turnout - prev_turnout) / prev_turnout) * 100
        changes.append((county, pct_change, curr_turnout, prev_turnout))
    changes.sort(key=lambda x: abs(x[1]), reverse=True)
    return changes


def get_regional_classification(county: str) -> str:
    """Classify county by region."""
    if county in NOVA_COUNTIES:
        return "Northern Virginia"
    elif county in RICHMOND_METRO:
        return "Richmond Metro"
    elif county in HAMPTON_ROADS:
        return "Hampton Roads"
    elif county in SOUTHWEST_VA:
        return "Southwest Virginia"
    elif county in SOUTHSIDE_RURAL:
        return "Southside/Rural"
    elif county in CENTRAL_VA:
        return "Central Virginia"
    elif county in SHENANDOAH_VALLEY:
        return "Shenandoah Valley"
    else:
        return "Other"


def normalize(s: str) -> str:
    """Normalize string for matching."""
    return " ".join(s.strip().lower().split())


def resolve_counties(requested: List[str], available: List[str]) -> List[str]:
    """Resolve county names from user input."""
    if not requested:
        return []

    avail_norm = {normalize(c): c for c in available}
    out = []

    for raw in requested:
        query = normalize(raw)
        if not query:
            continue

        if query in avail_norm:
            out.append(avail_norm[query])
            continue

        partials = sorted({name for key, name in avail_norm.items() if query in key})
        if len(partials) == 1:
            out.append(partials[0])
            continue
        if not partials:
            raise RuntimeError(f"County '{raw}' not found in selected contest/year data")

        raise RuntimeError(f"County '{raw}' is ambiguous. Matches: {', '.join(partials[:8])}")

    deduped = []
    seen = set()
    for county in out:
        if county in seen:
            continue
        seen.add(county)
        deduped.append(county)
    return deduped


def build_regional_card_detailed(
    region_name: str,
    counties: set,
    results_by_year: Dict,
    contest: str,
    years: List[str],
    emoji: str = "📍",
    description: str = ""
) -> str:
    """Build a detailed regional analysis card with multi-year trends."""
    trend = multi_year_trend(results_by_year, contest, counties, years)
    if len(trend) < 2:
        return ""
    
    latest = trend[-1]
    previous = trend[-2]
    first = trend[0]
    
    margin_trend = format_trend(trend, 'margin')
    turnout_trend = format_trend(trend, 'turnout')
    
    swing_recent = latest['margin'] - previous['margin']
    swing_total = latest['margin'] - first['margin'] if len(trend) > 2 else swing_recent
    
    direction = "Democratic" if swing_recent > 0 else "Republican"
    total_direction = "Democratic" if swing_total > 0 else "Republican"
    
    turnout_change_pct = ((latest['turnout'] - previous['turnout']) / previous['turnout'] * 100) if previous['turnout'] > 0 else 0
    
    desc_paragraph = f"<p style='margin-bottom:12px;color:#4b5563;'>{html.escape(description)}</p>" if description else ""
    
    return f'''          <div class="finding-card">
            <h5>{emoji} {html.escape(region_name)}</h5>
            {desc_paragraph}
            <p><strong>Margin Trend:</strong> {margin_trend}</p>
            <p><strong>Recent Swing ({previous['year']} → {latest['year']}):</strong> {abs(swing_recent):.2f} pts toward {direction}</p>
            {f'<p><strong>Long-term Swing ({first["year"]} → {latest["year"]}):</strong> {abs(swing_total):.2f} pts toward {total_direction}</p>' if len(trend) > 2 else ''}
            <p><strong>Turnout Trend:</strong> {turnout_trend} ({'+' if turnout_change_pct > 0 else ''}{turnout_change_pct:.1f}% vs {previous['year']})</p>
            <p><strong>Latest ({latest['year']}) Two-Party Split:</strong> DEM {fmt_pct(latest['dem_pct'])} | REP {fmt_pct(latest['rep_pct'])}</p>
          </div>'''


def build_realigned_county_cards_detailed(
    swings: List[Tuple[str, float, float, float]],
    results_by_year: Dict,
    contest: str,
    years: List[str],
    top_n: int,
) -> str:
    """Build detailed cards for most realigned counties."""
    cards = []
    latest_year = years[-1]
    previous_year = years[-2]
    
    for county, swing, curr_margin, prev_margin in swings[:top_n]:
        # Get multi-year data for this county
        county_trend = multi_year_county_swing(results_by_year, contest, county, years)
        if len(county_trend) < 2:
            continue
        
        latest = county_trend[-1]
        previous = county_trend[-2]
        
        prev_party = "Democratic" if prev_margin > 0 else "Republican"
        curr_party = "Democratic" if curr_margin > 0 else "Republican"
        flipped = prev_party != curr_party
        flip_text = f"<strong style='color: #d97706;'>Flip: {prev_party} → {curr_party}</strong>" if flipped else "No party flip"
        direction = "Democratic" if swing > 0 else "Republican"
        
        region = get_regional_classification(county)
        
        # Calculate turnout change
        turnout_change_pct = ((latest['turnout'] - previous['turnout']) / previous['turnout'] * 100) if previous['turnout'] > 0 else 0
        
        # Multi-year trend if available
        trend_line = ""
        if len(county_trend) >= 3:
            first = county_trend[0]
            long_swing = latest['margin'] - first['margin']
            long_direction = "Democratic" if long_swing > 0 else "Republican"
            trend_line = f"<p><strong>Long-term Trend ({first['year']} → {latest_year}):</strong> {abs(long_swing):.2f} pts toward {long_direction}</p>"
        
        cards.append(
            f'''          <div class="finding-card">
            <h5>{html.escape(county)}: {abs(swing):.2f}-Point Realignment</h5>
            <p><strong>Region:</strong> {region}</p>
            <p><strong>Margin Change:</strong> <span class="metric">{previous_year}: {fmt_margin(prev_margin)}</span> → <span class="metric">{latest_year}: {fmt_margin(curr_margin)}</span></p>
            <p><strong>Swing Direction:</strong> {abs(swing):.2f} pts toward {direction}</p>
            {trend_line}
            <p><strong>{latest_year} Results:</strong> DEM {fmt_pct(latest['dem_pct'])} ({latest['dem_votes']:,}) | REP {fmt_pct(latest['rep_pct'])} ({latest['rep_votes']:,}) | Total {latest['turnout']:,}</p>
            <p><strong>{previous_year} Results:</strong> DEM {fmt_pct(previous['dem_pct'])} ({previous['dem_votes']:,}) | REP {fmt_pct(previous['rep_pct'])} ({previous['rep_votes']:,}) | Total {previous['turnout']:,}</p>
            <p><strong>Turnout Change:</strong> {'+' if turnout_change_pct > 0 else ''}{turnout_change_pct:.1f}%</p>
            <p>{flip_text}</p>
          </div>'''
        )

    return "\n".join(cards)


def build_selected_county_card_detailed(
    selected_counties: List[str],
    results_by_year: Dict,
    contest: str,
    years: List[str],
) -> str:
    """Build detailed cards for user-selected counties."""
    if not selected_counties or len(years) < 2:
        return ""

    cards = []
    for county in selected_counties:
        county_trend = multi_year_county_swing(results_by_year, contest, county, years)
        if len(county_trend) < 2:
            continue
        
        latest = county_trend[-1]
        previous = county_trend[-2]
        first = county_trend[0]
        
        region = get_regional_classification(county)
        
        # Recent swing
        recent_swing = latest['margin'] - previous['margin']
        recent_direction = "Democratic" if recent_swing > 0 else "Republican"
        
        # Long-term swing
        long_swing = latest['margin'] - first['margin']
        long_direction = "Democratic" if long_swing > 0 else "Republican"
        
        # Turnout change
        turnout_change_pct = ((latest['turnout'] - previous['turnout']) / previous['turnout'] * 100) if previous['turnout'] > 0 else 0
        
        # Check for party flip
        prev_party = "Democratic" if previous['margin'] > 0 else "Republican"
        curr_party = "Democratic" if latest['margin'] > 0 else "Republican"
        flipped = prev_party != curr_party
        flip_text = f"<strong style='color: #d97706;'>Party Flip: {prev_party} → {curr_party}</strong>" if flipped else "No party flip"
        
        # Build trend line
        margin_trend = format_trend(county_trend, 'margin')
        
        cards.append(
            f'''          <div class="finding-card">
            <h5>📌 {html.escape(county)} - Detailed Analysis</h5>
            <p><strong>Region:</strong> {region}</p>
            <p><strong>Margin Trend:</strong> {margin_trend}</p>
            <p><strong>Recent Swing ({previous['year']} → {latest['year']}):</strong> {abs(recent_swing):.2f} pts toward {recent_direction}</p>
            {f'<p><strong>Long-term Swing ({first["year"]} → {latest["year"]}):</strong> {abs(long_swing):.2f} pts toward {long_direction}</p>' if len(county_trend) > 2 else ''}
            <p><strong>{latest['year']} Results:</strong> DEM {fmt_pct(latest['dem_pct'])} ({latest['dem_votes']:,}) | REP {fmt_pct(latest['rep_pct'])} ({latest['rep_votes']:,}) | Total {latest['turnout']:,}</p>
            <p><strong>{previous['year']} Results:</strong> DEM {fmt_pct(previous['dem_pct'])} ({previous['dem_votes']:,}) | REP {fmt_pct(previous['rep_pct'])} ({previous['rep_votes']:,}) | Total {previous['turnout']:,}</p>
            <p><strong>Turnout Change:</strong> {'+' if turnout_change_pct > 0 else ''}{turnout_change_pct:.1f}%</p>
            <p>{flip_text}</p>
          </div>'''
        )

    return "\n".join(cards)


def build_statewide_card_detailed(
    results_by_year: Dict,
    contest: str,
    years: List[str],
) -> str:
    """Build detailed statewide analysis card."""
    trend = []
    for year in years:
        if year not in results_by_year or contest not in results_by_year[year]:
            continue
        results = results_by_year[year][contest]
        summary = statewide_summary(results)
        trend.append({
            'year': year,
            'margin': summary['margin'],
            'dem_pct': summary['dem_pct'],
            'rep_pct': summary['rep_pct'],
            'turnout': summary['total_votes'],
            'other_pct': summary['other_pct'],
        })
    
    if len(trend) < 2:
        return ""
    
    latest = trend[-1]
    previous = trend[-2]
    first = trend[0]
    
    margin_trend = format_trend(trend, 'margin')
    turnout_trend = format_trend(trend, 'turnout')
    
    swing_recent = latest['margin'] - previous['margin']
    swing_total = latest['margin'] - first['margin'] if len(trend) > 2 else swing_recent
    
    direction = "Democratic" if swing_recent > 0 else "Republican"
    total_direction = "Democratic" if swing_total > 0 else "Republican"
    
    turnout_change_pct = ((latest['turnout'] - previous['turnout']) / previous['turnout'] * 100) if previous['turnout'] > 0 else 0
    
    # Get top turnout counties
    latest_results = results_by_year[latest['year']][contest]
    top_counties = top_turnout(latest_results, n=5)
    turnout_line = ", ".join(f"{html.escape(c)} ({v:,})" for c, v in top_counties)
    
    # Get biggest swings
    latest_results = results_by_year[latest['year']][contest]
    previous_results = results_by_year[previous['year']][contest]
    swings = county_swings(latest_results, previous_results)
    swing_line = ", ".join(
        f"{html.escape(c)} ({'D' if s > 0 else 'R'}+{abs(s):.1f})"
        for c, s, _, _ in swings[:5]
    )
    
    # Get flips
    county_flips = flips(latest_results, previous_results)
    flip_line = ", ".join(f"{html.escape(c)} ({p[0]} → {n[0]})" for c, p, n in county_flips[:10])
    if not flip_line:
        flip_line = "No county flips"
    
    # Turnout changes
    turnout_changes = turnout_change(latest_results, previous_results)
    top_turnout_gains = [t for t in turnout_changes if t[1] > 0][:5]
    turnout_gain_line = ", ".join(f"{html.escape(c)} (+{pct:.1f}%)" for c, pct, _, _ in top_turnout_gains)
    if not turnout_gain_line:
        turnout_gain_line = "No significant gains"
    
    return f'''          <div class="finding-card">
            <h5>🏛️ Statewide Analysis - {html.escape(contest)}</h5>
            <p style='margin-bottom:12px;color:#4b5563;'>Comprehensive statewide trends showing Virginia's evolution across all counties, including voting patterns, turnout changes, and partisan realignment.</p>
            <p><strong>Margin Trend:</strong> {margin_trend}</p>
            <p><strong>Recent Swing ({previous['year']} → {latest['year']}):</strong> {abs(swing_recent):.2f} pts toward {direction}</p>
            {f'<p><strong>Long-term Swing ({first["year"]} → {latest["year"]}):</strong> {abs(swing_total):.2f} pts toward {total_direction}</p>' if len(trend) > 2 else ''}
            <p><strong>Turnout Trend:</strong> {turnout_trend} ({'+' if turnout_change_pct > 0 else ''}{turnout_change_pct:.1f}% vs {previous['year']})</p>
            <p><strong>Latest ({latest['year']}) Results:</strong> DEM {fmt_pct(latest['dem_pct'])} | REP {fmt_pct(latest['rep_pct'])} | Other {fmt_pct(latest['other_pct'])}</p>
            <p><strong>Top Turnout Counties ({latest['year']}):</strong></p>
            <p style='word-wrap:break-word;margin-left:20px;'>{turnout_line}</p>
            <p><strong>Largest County Swings ({previous['year']} → {latest['year']}):</strong></p>
            <p style='word-wrap:break-word;margin-left:20px;'>{swing_line}</p>
            <p><strong>Top Turnout Gains ({previous['year']} → {latest['year']}):</strong></p>
            <p style='word-wrap:break-word;margin-left:20px;'>{turnout_gain_line}</p>
            <p><strong>County Flips:</strong> {flip_line}</p>
          </div>'''


def build_findings_html_detailed(
    contest: str,
    results_by_year: Dict,
    years: List[str],
    selected_counties: Optional[List[str]] = None,
    top_realigned: int = 8,
) -> str:
    """Build comprehensive detailed findings HTML."""
    selected_counties = selected_counties or []
    
    if len(years) < 2:
        return '<div class="findings-section"><p>Insufficient data for analysis.</p></div>'
    
    latest_year = years[-1]
    previous_year = years[-2]
    
    # Build regional cards
    nova_card = build_regional_card_detailed(
        "Northern Virginia", NOVA_COUNTIES, results_by_year, contest, years, "🏙️",
        "Virginia's most populous region and DC's Virginia suburbs, including Fairfax, Loudoun, Prince William, and Arlington. Like neighboring Maryland suburbs, NoVA's politics are shaped by federal government employment, high education levels, and growing diversity. Once a Republican stronghold, it has become Virginia's Democratic anchor."
    )
    
    richmond_card = build_regional_card_detailed(
        "Richmond Metro", RICHMOND_METRO, results_by_year, contest, years, "🏛️",
        "The state capital region including Richmond city and suburbs like Henrico and Chesterfield. A competitive battleground where urban Democratic strength meets suburban swing counties."
    )
    
    hampton_card = build_regional_card_detailed(
        "Hampton Roads", HAMPTON_ROADS, results_by_year, contest, years, "⚓",
        "Virginia's southeastern coastal region and military hub. Includes Norfolk, Virginia Beach, Chesapeake, and Newport News. Leans Democratic in urban cores with competitive suburbs."
    )
    
    sw_card = build_regional_card_detailed(
        "Southwest Virginia", SOUTHWEST_VA, results_by_year, contest, years, "⛰️",
        "Appalachian Virginia's coal and mountain country. Once Democratic union territory, now among Virginia's most Republican regions, mirroring trends across Appalachia."
    )
    
    southside_card = build_regional_card_detailed(
        "Southside/Rural Virginia", SOUTHSIDE_RURAL, results_by_year, contest, years, "🌾",
        "Rural counties south of Richmond with agricultural and manufacturing economies. Historically Democratic, now reliably Republican as rural realignment continues statewide."
    )
    
    central_card = build_regional_card_detailed(
        "Central Virginia", CENTRAL_VA, results_by_year, contest, years, "🎓",
        "College town region centered on Charlottesville and UVA. More Democratic than surrounding rural areas due to education sector influence and university populations."
    )
    
    valley_card = build_regional_card_detailed(
        "Shenandoah Valley", SHENANDOAH_VALLEY, results_by_year, contest, years, "🏞️",
        "The scenic valley corridor between the Blue Ridge and Allegheny mountains. Traditionally conservative region with agricultural communities and small towns."
    )
    
    # Build statewide card
    statewide_card = build_statewide_card_detailed(results_by_year, contest, years)
    
    # Build selected county cards
    selected_card = build_selected_county_card_detailed(
        selected_counties, results_by_year, contest, years
    )
    selected_block = f"\n{selected_card}" if selected_card else ""
    
    # Build realigned county cards
    latest_results = results_by_year[latest_year][contest]
    previous_results = results_by_year[previous_year][contest]
    swings = county_swings(latest_results, previous_results)
    
    realigned_cards = build_realigned_county_cards_detailed(
        swings, results_by_year, contest, years, top_realigned
    )
    
    year_range = f"{years[0]}-{years[-1]}" if len(years) > 2 else f"{previous_year}-{latest_year}"
    
    return f'''        <div class="findings-section">
          <h4>🔍 Detailed Research Findings - {html.escape(contest)} ({year_range})</h4>
          <div class="finding-card">
            <h5>📊 Analysis Overview</h5>
            <p>This analysis examines <strong>{len(years)} election cycles</strong> from <strong>{years[0]}</strong> to <strong>{years[-1]}</strong>, 
            tracking margins, turnout trends, vote shares, and partisan realignment across Virginia's counties and regions.</p>
          </div>
{statewide_card}
{nova_card}
{richmond_card}
{hampton_card}
{central_card}
{valley_card}
{sw_card}
{southside_card}{selected_block}
          <div class="finding-card">
            <h5>🔄 Most Realigned Counties ({previous_year} → {latest_year})</h5>
            <p>Counties ranked by absolute margin swing. Includes multi-year trends, turnout changes, and party control shifts.</p>
          </div>
{realigned_cards}
        </div>'''


def replace_findings_section(index_html: str, findings_block: str) -> str:
    """Replace findings section in index.html."""
    start = index_html.find('<div class="findings-section">')
    if start == -1:
        raise RuntimeError("Could not find findings section start token in index.html")

    footer = index_html.find('<div class="sidebar-footer"', start)
    if footer == -1:
        raise RuntimeError("Could not find sidebar footer after findings section")

    replacement = findings_block + "\n      "
    return index_html[:start] + replacement + index_html[footer:]


def choose_contest(results_by_year: Dict, requested: str) -> str:
    """Resolve contest name from user input."""
    normalized = requested.strip().lower()
    available = set()
    for year_data in results_by_year.values():
        available.update(year_data.keys())

    direct = [c for c in available if c.lower() == normalized]
    if direct:
        return sorted(direct)[0]

    aliases = {
        "president": "President",
        "governor": "Governor",
        "us senate": "US Senate",
        "senate": "US Senate",
        "attorney general": "Attorney General",
        "lieutenant governor": "Lieutenant Governor",
    }

    if normalized in aliases and aliases[normalized] in available:
        return aliases[normalized]

    raise RuntimeError(
        f"Contest '{requested}' not found. Available contests: {', '.join(sorted(available))}"
    )


def parse_requested_counties(county_args: List[str], counties_csv: Optional[str]) -> List[str]:
    """Parse county names from arguments."""
    out = []
    out.extend(county_args or [])
    if counties_csv:
        out.extend([x.strip() for x in counties_csv.split(",") if x.strip()])
    return out


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate highly detailed research findings with multi-year trends.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py Scripts/enrich_research_findings_detailed.py
  py Scripts/enrich_research_findings_detailed.py --contest Governor --years 3
  py Scripts/enrich_research_findings_detailed.py --top-realigned 10
  py Scripts/enrich_research_findings_detailed.py --county "Loudoun County" --county "Fairfax County"
  py Scripts/enrich_research_findings_detailed.py --dry-run
        """
    )
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH), help="Path to election JSON")
    parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH), help="Path to index.html")
    parser.add_argument("--contest", default="President", help="Contest to analyze")
    parser.add_argument("--years", type=int, default=None, help="Number of years to analyze (default: all available)")
    parser.add_argument("--top-realigned", type=int, default=8, help="Number of top realigned counties to include")
    parser.add_argument("--county", action="append", default=[], help="County/city to include in drilldown (repeatable)")
    parser.add_argument("--counties", default=None, help="Comma-separated counties/cities to include in drilldown")
    parser.add_argument("--dry-run", action="store_true", help="Print findings HTML instead of writing index.html")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    index_path = Path(args.index_path)

    if not json_path.exists():
        raise FileNotFoundError(f"JSON not found: {json_path}")
    if not index_path.exists():
        raise FileNotFoundError(f"index file not found: {index_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    results_by_year = data.get("results_by_year")
    if not isinstance(results_by_year, dict):
        raise RuntimeError("JSON missing results_by_year")

    contest = choose_contest(results_by_year, args.contest)
    all_years = contest_years(results_by_year, contest)
    
    if len(all_years) < 2:
        raise RuntimeError(f"Need at least two years for contest '{contest}', found: {all_years}")

    # Limit years if specified
    if args.years and args.years > 0:
        years = all_years[-args.years:]
    else:
        years = all_years
    
    # Get available counties from latest year
    latest_results = results_by_year[years[-1]][contest]
    
    requested_counties = parse_requested_counties(args.county, args.counties)
    selected_counties = resolve_counties(requested_counties, sorted(latest_results.keys()))

    findings_block = build_findings_html_detailed(
        contest,
        results_by_year,
        years,
        selected_counties=selected_counties,
        top_realigned=max(1, args.top_realigned),
    )

    if args.dry_run:
        print(findings_block)
        if selected_counties:
            print("\n" + "="*60)
            print(f"Selected counties: {', '.join(selected_counties)}")
        print(f"Years analyzed: {', '.join(years)}")
        return

    index_html = index_path.read_text(encoding="utf-8")
    updated = replace_findings_section(index_html, findings_block)
    index_path.write_text(updated, encoding="utf-8")

    year_range = f"{years[0]}-{years[-1]}" if len(years) > 2 else f"{years[-2]}-{years[-1]}"
    suffix = f"; selected counties: {', '.join(selected_counties)}" if selected_counties else ""
    print(
        f"✓ Updated research findings in {index_path}\n"
        f"  Contest: {contest}\n"
        f"  Years: {year_range} ({len(years)} cycles)\n"
        f"  Top realigned: {max(1, args.top_realigned)}{suffix}"
    )


if __name__ == "__main__":
    main()
