"""Measure published vs independently observed official showtimes by venue.

The denominator is *observed to date*, not proof of an exhaustive season.
Source production URLs alone are never counted as performances.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import ROOT, payload

EVIDENCE = ROOT / "data/candidate-detail-evidence.json"
OUT = ROOT / "public/catalog/recite-coverage.json"
PROGRAMS = ROOT / "public/catalog/programs.json"

# Explicit aliases only: never confuse Teatro Regio Torino with Regio Parma.
ALIASES = {
    "teatro regio": "teatro regio torino",
    "teatro regio di torino": "teatro regio torino",
    "teatro comunale": "teatro comunale di bologna",
    "teatro comunale bologna": "teatro comunale di bologna",
}


def canonical(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return ALIASES.get(value, value)


def normalized_url(value: str) -> str:
    parsed = urlsplit(value)
    return (parsed.hostname or "").lower().removeprefix("www.") + parsed.path.rstrip("/").lower()


def detect(published: dict, observations: dict, programs: dict | None = None) -> dict:
    # Only confirmed official dates with an identified physical venue qualify.
    # Index candidate count is NOT a performance count.
    state = defaultdict(lambda: {"published": set(), "observed": set(),
                                 "name": "", "city": "", "region": "",
                                 "independent_evidence": 0,
                                 "ambiguous": 0})
    for p in published["productions"]:
        venue = canonical(p["venue"])
        s = state[venue]
        s["name"], s["city"], s["region"] = p["venue"], p["municipality"], p["region"]
        for day, hour in p["dates"]:
            token = (day, hour or "")
            s["published"].add(token)
    # Composite programmes are one ticketed performance, not one per work.
    # Include already-published programme dates in the coverage numerator.
    for program in (programs or {}).get("programs", []):
        venue = program.get("venue")
        if not venue:
            continue
        s = state[canonical(venue)]
        if not s["name"]:
            s["name"] = venue
            s["city"] = program.get("municipality", "")
            s["region"] = program.get("region", "")
        for performance in program.get("performances", []):
            day = performance.get("local_date")
            stamp = performance.get("starts_at")
            if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                continue
            hour = stamp[11:16] if isinstance(stamp, str) and stamp.startswith(day + "T") else ""
            dated = {(d, h) for d, h in s["published"] if d == day}
            if (day, hour) in dated:
                continue
            if len(dated) == 1 and ((day, "") in dated or not hour):
                s["published"].difference_update(dated)
            s["published"].add((day, hour))
    # The same official performance can be found more than once or in a
    # multi-work programme: key by venue/date/time, not work title.
    for page in observations.get("evidence", []):
        if page.get("status") in {"excluded_nonopera", "invalid_source"}:
            continue
        seen = set()
        for fact in page.get("event_facts", []):
            venue, day = fact.get("venue"), fact.get("date")
            timestamp = fact.get("starts_at")
            if not venue or not day or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                continue
            if timestamp and not timestamp.startswith(day + "T"):
                continue
            key = canonical(venue)
            s = state[key]
            if not s["name"]:
                s["name"] = venue
            hour = timestamp[11:16] if timestamp else ""
            token = (day, hour)
            if token in seen:
                continue
            seen.add(token)
            s["observed"].add(token)
            s["independent_evidence"] += 1
    rows = []
    for key, s in state.items():
        published_dates = s["published"]
        remaining = set(s["observed"])
        # Same exact showtime is definitively the same recita. If the
        # published record lacks time and there is exactly one candidate
        # on that day, it can safely be reconciled by date.
        for day, hour in sorted(published_dates):
            if (day, hour) in remaining:
                remaining.remove((day, hour))
                continue
            options = [v for v in remaining if v[0] == day]
            if not hour and len(options) == 1:
                remaining.remove(options[0])
            elif hour and (day, "") in remaining:
                remaining.remove((day, ""))
        found = len(published_dates) + len(remaining)
        posted = len(published_dates)
        if not found:
            continue
        rows.append({
            "venue_key": key,
            "venue": s["name"],
            "city": s["city"] or None,
            "region": s["region"] or None,
            "published": posted,
            "found": found,
            "missing": len(remaining),
            "percent": round(100 * posted / found, 1),
            "independent_observations": len(s["observed"]),
            "scope": "observed_official_dates_not_full_season",
            "source_evidence": "official_candidate_detail_and_published",
        })
    rows.sort(key=lambda row: (row["city"] or "zz", row["venue"]))
    return {
        "schema_version": 1,
        "reviewed_on": published["reviewed_on"],
        "definition": "Published / distinct official showtimes found so far. Not a guarantee of complete season coverage.",
        "venues": rows,
    }


def publish(check: bool = False) -> dict:
    published = json.loads(MANIFEST.read_text(encoding="utf-8"))
    observations = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    programs = json.loads(PROGRAMS.read_text(encoding="utf-8"))
    report = detect(published, observations, programs)
    expected = payload(report)
    if check:
        if not OUT.exists() or OUT.read_bytes() != expected:
            raise ValueError("Recite coverage feed is out of sync")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(expected)
    return report


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--check", action="store_true")
    opts = args.parse_args()
    report = publish(check=opts.check)
    print(json.dumps({"venues": len(report["venues"]),
                      "published": sum(x["published"] for x in report["venues"]),
                      "found": sum(x["found"] for x in report["venues"])}))


if __name__ == "__main__":
    main()
