import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "Data" / "va_county_aggregated_results.json"


def to_scale_map(payload: dict) -> dict:
    scale = payload["categorization_system"]["competitiveness_scale"]
    out = {}
    for party, entries in scale.items():
        out[party] = {entry["category"]: entry["color"] for entry in entries}
    return out


def expected_competitiveness(dem_votes: int, rep_votes: int, total_votes: int, scale_map: dict) -> dict:
    signed_margin_pct = round(((dem_votes - rep_votes) / total_votes * 100.0), 2) if total_votes > 0 else 0.0
    abs_margin = abs(signed_margin_pct)

    if abs_margin < 0.5:
        return {
            "category": "Tossup",
            "party": "Tossup",
            "code": "TOSSUP",
            "color": scale_map["Tossup"]["Tossup"],
        }

    if signed_margin_pct > 0:
        party = "Democratic"
        prefix = "D"
    else:
        party = "Republican"
        prefix = "R"

    if abs_margin < 1:
        category = "Tilt"
    elif abs_margin < 5.5:
        category = "Lean"
    elif abs_margin < 10:
        category = "Likely"
    elif abs_margin < 20:
        category = "Safe"
    elif abs_margin < 30:
        category = "Stronghold"
    elif abs_margin < 40:
        category = "Dominant"
    else:
        category = "Annihilation"

    return {
        "category": category,
        "party": party,
        "code": f"{prefix}_{category.upper()}",
        "color": scale_map[party][category],
    }


def validate_or_fix(path: Path, fix: bool = False, max_print: int = 25) -> int:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    scale_map = to_scale_map(payload)
    mismatches = []
    total = 0

    results = payload.get("results_by_year", {})
    for year, contests in results.items():
        for contest, counties in contests.items():
            for county, rec in counties.items():
                total += 1
                dem_votes = int(rec.get("dem_votes", 0) or 0)
                rep_votes = int(rec.get("rep_votes", 0) or 0)
                total_votes = int(rec.get("total_votes", 0) or 0)
                expected = expected_competitiveness(dem_votes, rep_votes, total_votes, scale_map)
                actual = rec.get("competitiveness") or {}

                diffs = []
                for key in ("category", "party", "code", "color"):
                    if actual.get(key) != expected[key]:
                        diffs.append((key, actual.get(key), expected[key]))

                if diffs:
                    mismatches.append((year, contest, county, diffs))
                    if fix:
                        rec["competitiveness"] = expected

    if fix and mismatches:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
            f.write("\n")

    print(f"Checked {total} county results in {path}")
    if not mismatches:
        print("OK: all competitiveness ratings have the expected category/code/color.")
        return 0

    mode = "fixed" if fix else "found"
    print(f"{mode.upper()}: {len(mismatches)} mismatches.")
    for year, contest, county, diffs in mismatches[:max_print]:
        detail = "; ".join([f"{k}: {a!r} -> {e!r}" for k, a, e in diffs])
        print(f"- {year} | {contest} | {county}: {detail}")
    if len(mismatches) > max_print:
        print(f"... and {len(mismatches) - max_print} more")

    return 0 if fix else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that competitiveness rating colors/categories/codes match the rating rules."
    )
    parser.add_argument("--fix", action="store_true", help="Auto-correct mismatched competitiveness blocks in place.")
    parser.add_argument("--file", type=Path, default=DATA_PATH, help=f"Path to aggregated JSON (default: {DATA_PATH})")
    parser.add_argument("--max-print", type=int, default=25, help="Max mismatch lines to print.")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"File not found: {args.file}")
        return 2

    return validate_or_fix(args.file, fix=args.fix, max_print=args.max_print)


if __name__ == "__main__":
    sys.exit(main())
