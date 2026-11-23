"""Read-only source triage for the 2026 historical performance audit.

Hostname matches are *leads*, never proof that a source covers a venue or
contains an exhaustive historic calendar. No network requests are performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def host(url):
    try:
        return (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def source_leads(directory, config, health):
    health_by_key = {s["key"]: s for s in health.get("sources", [])
                     if isinstance(s, dict) and s.get("key")}
    sources = config.get("sources", [])
    rows = []
    for venue in directory.get("venues", []):
        website_host = host(venue.get("website"))
        leads = []
        for source in sources:
            official_host = host(source.get("official_url"))
            # Exact hostname only: never infer that two venues sharing an
            # organization domain belong to the same actual performance.
            if not website_host or website_host != official_host:
                continue
            url = source.get("url") or ""
            status = health_by_key.get(source.get("key"), {})
            leads.append({
                "source_key": source.get("key"),
                "calendar_url": url,
                "last_scan_status": status.get("status", "unknown"),
                "last_attempt_at": status.get("last_attempt_at"),
                "year_2026_mentioned": "2026" in url,
                "association": "hostname_candidate_not_verified",
                "full_2026_calendar_verified": False,
            })
        rows.append({
            "venue_id": venue["id"],
            "venue": venue["name"],
            "city": venue.get("city"),
            "official_website": venue.get("website"),
            "source_leads": leads,
            "source_review_status": "candidate_sources_to_review" if leads else "no_exact_host_candidate",
            "2026_complete": None,
        })
    return {
        "schema_version": 1,
        "year": 2026,
        "method": "exact official-website hostname match; unverified candidates only",
        "warning": "Neither a successful current scan nor a matching hostname proves historical 2026 coverage.",
        "inventory_venues": len(rows),
        "configured_source_indexes": len(sources),
        "venues": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    def load(name):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    report = source_leads(load("data/venue-directory.json"),
                          load("data/season-index-config.json"),
                          load("data/season-index-health.json"))
    body = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(body, encoding="utf-8")
        print(f"Report written: {args.output}")
    else:
        print(body, end="")


if __name__ == "__main__":
    main()
