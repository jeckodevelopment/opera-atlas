"""Reproducible city coverage audit. Never infer a percentage from missing official data."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CITIES = ("Torino", "Milano", "Roma", "Genova", "Bari", "Palermo")
SOURCE_KEYS = {
    "Torino": "regio-torino",
    "Milano": "scala-season-2026-27",
    "Roma": "opera-roma-season-2026-27",
    "Genova": "carlo-felice-season-2026-27",
    "Bari": "petruzzelli-opera-2026",
    "Palermo": "massimo-season-2026-27",
}


def audit(performances: list, stagings: list, venues: list, season_health: dict,
          candidate_health: dict, start: date, days: int = 30) -> dict:
    if days < 1 or days > 366:
        raise ValueError("days must be between 1 and 366")
    end = start + timedelta(days=days - 1)
    by_staging = {row["id"]: row["venue_id"] for row in stagings}
    by_venue = {row["id"]: row["city"] for row in venues}
    counts = Counter()
    unique = set()
    for row in performances:
        day = date.fromisoformat(row["local_date"])
        if not start <= day <= end or row.get("status") == "cancelled":
            continue
        city = by_venue.get(by_staging.get(row["staging_id"]))
        if city in CITIES:
            # Count each canonical performance once; never count multiple works
            # from a mixed evening as separate performances.
            identifier = row["id"]
            if identifier not in unique:
                unique.add(identifier)
                counts[city] += 1
    sources = {row["key"]: row for row in season_health.get("sources", [])}
    # Candidate outcomes alone do not prove which city's official season is
    # fully enumerated. Do not use them as a denominator.
    blocked = Counter(row.get("reason", "unknown") for row in
                      candidate_health.get("outcomes", [])
                      if row.get("outcome") != "facts_found")
    rows = []
    for city in CITIES:
        source = sources.get(SOURCE_KEYS[city], {})
        rows.append({
            "city": city,
            "published_recite_in_window": counts[city],
            "source_key": SOURCE_KEYS[city],
            "season_index_scan": source.get("status", "not_reported"),
            "official_production_links_seen": source.get("links") if source else None,
            "official_total_recite": None,
            "coverage_percent": None,
            "coverage_status": "unmeasured_official_denominator",
            "attention": "high" if counts[city] == 0 and source.get("links", 0) > 0 else "normal",
        })
    return {
        "schema_version": 1,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "definition": "Published canonical recite by city; official total and coverage unknown until complete official date-level enumeration.",
        "cities": rows,
        "candidate_failure_reasons_all_sources": dict(sorted(blocked.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=date.today().isoformat(),
                        help="First local date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("city-coverage-audit.json"))
    args = parser.parse_args()
    root = ROOT / "public/catalog/v2"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    arrays = {}
    for kind in ("performances", "stagings", "venues"):
        filename = manifest["files"][kind]["path"]
        if not filename.startswith("data/") or ".." in Path(filename).parts:
            raise ValueError("unsafe manifest path")
        arrays[kind] = json.loads((root / filename).read_text(encoding="utf-8"))[kind]
    season = json.loads((ROOT / "data/season-index-health.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "data/candidate-detail-health.json").read_text(encoding="utf-8"))
    report = audit(arrays["performances"], arrays["stagings"], arrays["venues"],
                   season, details, date.fromisoformat(args.start), args.days)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"window": [report["window_start"], report["window_end"]],
                      "cities": {x["city"]: x["published_recite_in_window"]
                                 for x in report["cities"]}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
