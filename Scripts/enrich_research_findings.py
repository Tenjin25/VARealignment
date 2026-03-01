#!/usr/bin/env python3
"""Generate detailed research findings from election JSON and update index.html.

Usage:
  py Scripts/enrich_research_findings.py
  py Scripts/enrich_research_findings.py --dry-run
  py Scripts/enrich_research_findings.py --contest Governor
  py Scripts/enrich_research_findings.py --top-realigned 8
  py Scripts/enrich_research_findings.py --county "Loudoun County" --county "Chesterfield County"
  py Scripts/enrich_research_findings.py --counties "Fairfax County,Arlington County"
"""

import argparse
import html
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_JSON_PATH = Path("Data/va_county_aggregated_results.json")
DEFAULT_INDEX_PATH = Path("index.html")

NOVA_COUNTIES = {
    "Arlington County",
    "Fairfax County",
    "Loudoun County",
    "Prince William County",
    "Alexandria city",
    "Fairfax city",
    "Falls Church city",
    "Manassas city",
    "Manassas Park city",
}

RICHMOND_HAMPTON_ROADS = {
    "Richmond city",
    "Henrico County",
    "Chesterfield County",
    "Norfolk city",
    "Portsmouth city",
    "Newport News city",
    "Hampton city",
    "Virginia Beach city",
    "Chesapeake city",
    "Suffolk city",
}

SOUTHWEST_VA = {
    "Buchanan County",
    "Dickenson County",
    "Lee County",
    "Russell County",
    "Scott County",
    "Tazewell County",
    "Wise County",
    "Smyth County",
    "Washington County",
    "Grayson County",
    "Wythe County",
    "Bristol city",
    "Galax city",
    "Norton city",
}

SOUTHSIDE_RURAL = {
    "Brunswick County",
    "Charlotte County",
    "Halifax County",
    "Lunenburg County",
    "Mecklenburg County",
    "Pittsylvania County",
    "Patrick County",
    "Henry County",
    "Franklin County",
    "Nottoway County",
    "Amelia County",
    "Cumberland County",
    "Dinwiddie County",
    "Greensville County",
    "Prince Edward County",
}


def safe_margin(dem_votes: float, rep_votes: float) -> float:
    total = dem_votes + rep_votes
    if total <= 0:
        return 0.0
    return ((dem_votes - rep_votes) / total) * 100.0


def fmt_margin(value: float) -> str:
    party = "D" if value >= 0 else "R"
    return f"{party}+{abs(value):.2f}%"


def contest_years(results_by_year: Dict, contest: str) -> List[str]:
    years = []
    for year in sorted(results_by_year.keys()):
        if contest in results_by_year.get(year, {}):
            years.append(year)
    return years


def aggregate_region(results: Dict[str, Dict], counties: set) -> Dict[str, float]:
    dem = rep = total = 0
    for county in counties:
        row = results.get(county)
        if not row:
            continue
        dem += row.get("dem_votes", 0) or 0
        rep += row.get("rep_votes", 0) or 0
        total += row.get("total_votes", 0) or 0
    return {
        "dem_votes": dem,
        "rep_votes": rep,
        "total_votes": total,
        "margin": safe_margin(dem, rep),
    }


def statewide_summary(results: Dict[str, Dict]) -> Dict[str, float]:
    dem = sum((r.get("dem_votes", 0) or 0) for r in results.values())
    rep = sum((r.get("rep_votes", 0) or 0) for r in results.values())
    total = sum((r.get("total_votes", 0) or 0) for r in results.values())
    return {
        "dem_votes": dem,
        "rep_votes": rep,
        "total_votes": total,
        "margin": safe_margin(dem, rep),
    }


def county_swings(curr: Dict[str, Dict], prev: Dict[str, Dict]) -> List[Tuple[str, float, float, float]]:
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


def flips(curr: Dict[str, Dict], prev: Dict[str, Dict]) -> List[Tuple[str, str, str]]:
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
    pairs = [(county, int(row.get("total_votes", 0) or 0)) for county, row in results.items()]
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:n]


def normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def resolve_counties(requested: List[str], available: List[str]) -> List[str]:
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


def build_selected_county_card(
    selected_counties: List[str],
    latest_year: str,
    previous_year: str,
    latest_results: Dict[str, Dict],
    previous_results: Dict[str, Dict],
) -> str:
    if not selected_counties:
        return ""

    lines = []
    for county in selected_counties:
        curr = latest_results.get(county)
        prev = previous_results.get(county)
        if not curr or not prev:
            continue

        curr_margin = safe_margin(curr.get("dem_votes", 0) or 0, curr.get("rep_votes", 0) or 0)
        prev_margin = safe_margin(prev.get("dem_votes", 0) or 0, prev.get("rep_votes", 0) or 0)
        swing = curr_margin - prev_margin
        direction = "toward D" if swing > 0 else "toward R"

        lines.append(
            "            <p><strong>{county}:</strong> {latest} {latest_margin} vs {previous} {previous_margin}; "
            "swing {swing_abs:.2f} pts ({direction}); {latest} DEM {dem:,} | REP {rep:,} | Total {total:,}</p>".format(
                county=html.escape(county),
                latest=latest_year,
                latest_margin=fmt_margin(curr_margin),
                previous=previous_year,
                previous_margin=fmt_margin(prev_margin),
                swing_abs=abs(swing),
                direction=direction,
                dem=int(curr.get("dem_votes", 0) or 0),
                rep=int(curr.get("rep_votes", 0) or 0),
                total=int(curr.get("total_votes", 0) or 0),
            )
        )

    if not lines:
        return ""

    return (
        "          <div class=\"finding-card\">\n"
        "            <h5>Selected County Drilldown</h5>\n"
        + "\n".join(lines)
        + "\n          </div>"
    )


def build_realigned_county_cards(
    swings: List[Tuple[str, float, float, float]],
    latest_results: Dict[str, Dict],
    previous_results: Dict[str, Dict],
    latest_year: str,
    previous_year: str,
    top_n: int,
) -> str:
    cards = []
    for county, swing, curr_margin, prev_margin in swings[:top_n]:
        curr = latest_results.get(county, {})
        prev = previous_results.get(county, {})

        prev_party = "Democratic" if prev_margin > 0 else "Republican"
        curr_party = "Democratic" if curr_margin > 0 else "Republican"
        flipped = prev_party != curr_party
        flip_text = f"Flip: {prev_party} -> {curr_party}" if flipped else "No party flip"
        direction = "toward Democratic" if swing > 0 else "toward Republican"

        cards.append(
            f'''          <div class="finding-card">
            <h5>{html.escape(county)}: {abs(swing):.2f}-Point Realignment</h5>
            <p><strong>Margin Change:</strong> <span class="metric">{previous_year}: {fmt_margin(prev_margin)}</span> -> <span class="metric">{latest_year}: {fmt_margin(curr_margin)}</span></p>
            <p><strong>Swing Direction:</strong> {direction}</p>
            <p><strong>{latest_year} Votes:</strong> DEM {int(curr.get("dem_votes", 0) or 0):,} | REP {int(curr.get("rep_votes", 0) or 0):,} | Total {int(curr.get("total_votes", 0) or 0):,}</p>
            <p><strong>{previous_year} Votes:</strong> DEM {int(prev.get("dem_votes", 0) or 0):,} | REP {int(prev.get("rep_votes", 0) or 0):,} | Total {int(prev.get("total_votes", 0) or 0):,}</p>
            <p><strong>Party Control Shift:</strong> {flip_text}</p>
          </div>'''
        )

    return "\n".join(cards)


def build_findings_html(
    contest: str,
    latest_year: str,
    previous_year: str,
    latest_results: Dict[str, Dict],
    previous_results: Dict[str, Dict],
    selected_counties: Optional[List[str]] = None,
    top_realigned: int = 6,
) -> str:
    selected_counties = selected_counties or []

    nova_now = aggregate_region(latest_results, NOVA_COUNTIES)
    nova_prev = aggregate_region(previous_results, NOVA_COUNTIES)

    rh_now = aggregate_region(latest_results, RICHMOND_HAMPTON_ROADS)
    rh_prev = aggregate_region(previous_results, RICHMOND_HAMPTON_ROADS)

    sw_now = aggregate_region(latest_results, SOUTHWEST_VA)
    sw_prev = aggregate_region(previous_results, SOUTHWEST_VA)

    ss_now = aggregate_region(latest_results, SOUTHSIDE_RURAL)
    ss_prev = aggregate_region(previous_results, SOUTHSIDE_RURAL)

    state_now = statewide_summary(latest_results)
    state_prev = statewide_summary(previous_results)

    swings = county_swings(latest_results, previous_results)
    county_flips = flips(latest_results, previous_results)

    turnout = top_turnout(latest_results, n=5)
    turnout_line = ", ".join(f"{html.escape(c)} ({v:,})" for c, v in turnout)

    swing_line = ", ".join(
        f"{html.escape(c)} ({'toward D' if s > 0 else 'toward R'} {abs(s):.2f} pts)"
        for c, s, _, _ in swings[:5]
    )
    if not swing_line:
        swing_line = "No county swing data available."

    flip_line = ", ".join(f"{html.escape(c)} ({p} -> {n})" for c, p, n in county_flips[:10])
    if not flip_line:
        flip_line = "No county party flips between the two most recent cycles."

    selected_card = build_selected_county_card(
        selected_counties,
        latest_year,
        previous_year,
        latest_results,
        previous_results,
    )
    selected_block = f"\n{selected_card}" if selected_card else ""

    realigned_cards = build_realigned_county_cards(
        swings,
        latest_results,
        previous_results,
        latest_year,
        previous_year,
        top_realigned,
    )

    return f'''        <div class="findings-section">
          <h4>Research Findings ({html.escape(contest)} {latest_year} vs {previous_year})</h4>
          <div class="finding-card">
            <h5>Northern Virginia: High-Volume Democratic Core</h5>
            <p><strong>Regional Margin:</strong> <span class="metric">{latest_year}: {fmt_margin(nova_now['margin'])}</span> vs <span class="metric">{previous_year}: {fmt_margin(nova_prev['margin'])}</span></p>
            <p><strong>Two-Party Votes ({latest_year}):</strong> DEM {int(nova_now['dem_votes']):,} | REP {int(nova_now['rep_votes']):,}</p>
          </div>
          <div class="finding-card">
            <h5>Richmond + Hampton Roads: Urban/Suburban Democratic Anchor</h5>
            <p><strong>Regional Margin:</strong> <span class="metric">{latest_year}: {fmt_margin(rh_now['margin'])}</span> vs <span class="metric">{previous_year}: {fmt_margin(rh_prev['margin'])}</span></p>
            <p><strong>Two-Party Votes ({latest_year}):</strong> DEM {int(rh_now['dem_votes']):,} | REP {int(rh_now['rep_votes']):,}</p>
          </div>
          <div class="finding-card">
            <h5>Southwest Virginia: Durable Republican Strength</h5>
            <p><strong>Regional Margin:</strong> <span class="metric">{latest_year}: {fmt_margin(sw_now['margin'])}</span> vs <span class="metric">{previous_year}: {fmt_margin(sw_prev['margin'])}</span></p>
            <p><strong>Two-Party Votes ({latest_year}):</strong> DEM {int(sw_now['dem_votes']):,} | REP {int(sw_now['rep_votes']):,}</p>
          </div>
          <div class="finding-card">
            <h5>Southside/Rural Virginia: Republican Consolidation</h5>
            <p><strong>Regional Margin:</strong> <span class="metric">{latest_year}: {fmt_margin(ss_now['margin'])}</span> vs <span class="metric">{previous_year}: {fmt_margin(ss_prev['margin'])}</span></p>
            <p><strong>Two-Party Votes ({latest_year}):</strong> DEM {int(ss_now['dem_votes']):,} | REP {int(ss_now['rep_votes']):,}</p>
          </div>{selected_block}
          <div class="finding-card">
            <h5>Statewide Snapshot</h5>
            <p><strong>Statewide Margin:</strong> <span class="metric">{latest_year}: {fmt_margin(state_now['margin'])}</span> vs <span class="metric">{previous_year}: {fmt_margin(state_prev['margin'])}</span></p>
            <p><strong>Top Turnout Counties ({latest_year}):</strong> {turnout_line}</p>
            <p><strong>Largest County Swings ({previous_year} -> {latest_year}):</strong> {swing_line}</p>
            <p><strong>County Flips:</strong> {flip_line}</p>
          </div>
          <div class="finding-card">
            <h5>Most Realigned Counties ({previous_year} -> {latest_year})</h5>
            <p>Counties below are ranked by absolute margin swing in the selected contest.</p>
          </div>
{realigned_cards}
        </div>'''


def replace_findings_section(index_html: str, findings_block: str) -> str:
    start = index_html.find('<div class="findings-section">')
    if start == -1:
        raise RuntimeError("Could not find findings section start token in index.html")

    footer = index_html.find('<div class="sidebar-footer"', start)
    if footer == -1:
        raise RuntimeError("Could not find sidebar footer after findings section")

    old_section = index_html[start:footer]
    if "Research Findings" not in old_section:
        raise RuntimeError("Found findings-section block, but it does not contain the expected heading")

    replacement = findings_block + "\n      "
    return index_html[:start] + replacement + index_html[footer:]


def choose_contest(results_by_year: Dict, requested: str) -> str:
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
    out = []
    out.extend(county_args or [])
    if counties_csv:
        out.extend([x.strip() for x in counties_csv.split(",") if x.strip()])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate richer research findings from election JSON.")
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH), help="Path to election JSON")
    parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH), help="Path to index.html")
    parser.add_argument("--contest", default="President", help="Contest to analyze")
    parser.add_argument("--top-realigned", type=int, default=6, help="Number of top realigned counties to include")
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
    years = contest_years(results_by_year, contest)
    if len(years) < 2:
        raise RuntimeError(f"Need at least two years for contest '{contest}', found: {years}")

    latest_year = years[-1]
    previous_year = years[-2]
    latest_results = results_by_year[latest_year][contest]
    previous_results = results_by_year[previous_year][contest]

    requested_counties = parse_requested_counties(args.county, args.counties)
    selected_counties = resolve_counties(requested_counties, sorted(latest_results.keys()))

    findings_block = build_findings_html(
        contest,
        latest_year,
        previous_year,
        latest_results,
        previous_results,
        selected_counties=selected_counties,
        top_realigned=max(1, args.top_realigned),
    )

    if args.dry_run:
        print(findings_block)
        if selected_counties:
            print("\nSelected counties:", ", ".join(selected_counties))
        return

    index_html = index_path.read_text(encoding="utf-8")
    updated = replace_findings_section(index_html, findings_block)
    index_path.write_text(updated, encoding="utf-8")

    suffix = f"; counties: {', '.join(selected_counties)}" if selected_counties else ""
    print(
        f"Updated research findings in {index_path} using {contest} ({previous_year} -> {latest_year}) from {json_path}; top_realigned={max(1, args.top_realigned)}{suffix}"
    )


if __name__ == "__main__":
    main()
