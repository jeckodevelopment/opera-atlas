"""Compare the independently reviewed Jan-Jun 2026 official recite with canonical Atlas.

This is a *bounded evidence audit*, not a nationwide coverage denominator.
It never inserts, changes or deletes catalog entries.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/historical-2026-official-evidence.json"
CATALOG = ROOT / "data/verified-launch-catalog.json"
VENUES = ROOT / "data/venue-directory.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-first-half-verified-gaps.json"


def canonical_index(catalog):
    index = defaultdict(list)
    for p in catalog.get("productions", []):
        for d in p.get("dates", []):
            if not isinstance(d, list) or not d or not isinstance(d[0], str):
                continue
            index[(p.get("municipality", "").casefold(),
                   p.get("title", "").casefold(), d[0])].append({
                "time": d[1] if len(d) > 1 else None,
                "venue": p.get("venue"),
                "source_url": p.get("source_url"),
            })
    return index


def audit(evidence, catalog, venues):
    if evidence.get("year") != 2026 or not isinstance(evidence.get("records"), list):
        raise ValueError("Expected approved 2026 historical evidence")
    index = canonical_index(catalog)
    rows, observed = [], set()
    for item in evidence["records"]:
        if item.get("source_type") != "official_event_detail" or item.get("audience") != "general_public":
            raise ValueError("Historic facts must be reviewed for public admission")
        url = item.get("source_url", "")
        if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            raise ValueError("Historical evidence lacks an official HTTPS source")
        for d in item.get("dates", []):
            day, clock = d.get("date"), d.get("time")
            try:
                parsed = date.fromisoformat(day)
            except (TypeError, ValueError):
                raise ValueError("Invalid historical performance date") from None
            if not (parsed.year == 2026 and parsed.month <= 6 and
                    isinstance(clock, str) and len(clock) == 5 and
                    clock[2] == ":" and clock[:2].isdigit() and clock[3:].isdigit() and
                    0 <= int(clock[:2]) <= 23 and 0 <= int(clock[3:]) <= 59):
                raise ValueError("Out-of-scope or invalid official performance")
            key = (item["city"].casefold(), item["title"].casefold(), day, clock)
            if key in observed:
                raise ValueError("Duplicate source-reviewed official performance")
            observed.add(key)
            matches = index.get(key[:3], [])
            exact = [m for m in matches if m["time"] == clock]
            status = ("catalog_exact_day_time" if exact else
                      "catalog_day_clock_conflict" if matches else
                      "verified_official_recita_absent_from_catalog")
            rows.append({
                "date": day, "time": clock, "opera": item["title"],
                "composer": item.get("composer"), "venue": item["venue"],
                "city": item["city"], "official_url": url, "status": status,
                "catalog_matches": matches,
                "editorial_publication_required": status == "verified_official_recita_absent_from_catalog",
                "automatically_published": False,
            })
    counts = dict(sorted(Counter(r["status"] for r in rows).items()))
    first_half = [
        (p, d) for p in catalog.get("productions", [])
        for d in p.get("dates", [])
        if isinstance(d, list) and d and isinstance(d[0], str)
        and "2026-01-01" <= d[0] <= "2026-06-30"
    ]
    months = dict(sorted(Counter(d[0][:7] for _, d in first_half).items()))
    cities = dict(sorted(Counter(p.get("municipality") or "unknown" for p, _ in first_half).items()))
    return {
        "schema_version": 1, "year": 2026,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only": True, "catalog_updated": False, "complete_seasons_certified": 0,
        "scope": "Only four individually reviewed first-semester official productions; NOT national calendar completeness",
        "reviewed_productions": len(evidence["records"]),
        "reviewed_official_performances": len(rows),
        "official_match_counts": counts,
        "catalog_first_half_performance_rows": len(first_half),
        "catalog_first_half_months": months,
        "catalog_first_half_cities": cities,
        "venue_directory_count": len(venues.get("venues", [])),
        "historical_reconciliation": sorted(rows, key=lambda x: (x["date"], x["time"], x["opera"])),
        "warning": "The verified gap may be considered for a separately reviewed catalog change; no automated promotion. Counts do not establish national 2026 coverage.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = audit(*(
        json.loads(p.read_text(encoding="utf-8")) for p in (EVIDENCE, CATALOG, VENUES)
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("FIRST_HALF_2026 " + json.dumps({
        "reviewed": result["reviewed_official_performances"],
        "counts": result["official_match_counts"],
        "catalog_first_half": result["catalog_first_half_performance_rows"],
        "months": result["catalog_first_half_months"],
        "cities": result["catalog_first_half_cities"],
    }, ensure_ascii=False))
    for row in result["historical_reconciliation"]:
        if row["editorial_publication_required"]:
            print("VERIFIED_MISSING_RECITA " + json.dumps(
                {"date": row["date"], "time": row["time"], "opera": row["opera"],
                 "city": row["city"], "official_url": row["official_url"]},
                ensure_ascii=False))


if __name__ == "__main__":
    main()
