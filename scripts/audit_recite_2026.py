"""Read-only 2026 venue/month evidence audit; never certify season completeness.

Uses the existing approved catalog and official candidate detail evidence.
This is a baseline, NOT a historical source crawl or complete season denominator.
No production pipeline, catalog or connector is changed.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/venue-directory.json"
CATALOG = ROOT / "data/verified-launch-catalog.json"
EVIDENCE = ROOT / "data/candidate-detail-evidence.json"
PROGRAMS = ROOT / "public/catalog/programs.json"


def norm(value):
    value = unicodedata.normalize("NFKD", (value or "").casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(
        c for c in value if not unicodedata.combining(c))).strip()


def date_2026(value):
    return isinstance(value, str) and re.fullmatch(r"2026-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])", value) is not None


def token(day, hour=None):
    if not date_2026(day):
        return None
    return (day, hour or "")


def build(directory, catalog, evidence, programs):
    venues = directory["venues"]
    lookup = defaultdict(list)
    for v in venues:
        lookup[(norm(v.get("city")), norm(v["name"]))].append(v["id"])
        if v.get("profile_key") and "|" in v["profile_key"]:
            city, name = v["profile_key"].split("|", 1)
            lookup[(norm(city), norm(name))].append(v["id"])

    by_id = {v["id"]: v for v in venues}
    published = defaultdict(set)
    observed = defaultdict(set)
    unassigned = []

    def resolve(name, city):
        candidates = set(lookup.get((norm(city), norm(name)), []))
        return next(iter(candidates)) if len(candidates) == 1 else None

    for p in catalog.get("productions", []):
        venue_id = resolve(p.get("venue"), p.get("municipality"))
        for day, hour in p.get("dates", []):
            t = token(day, hour)
            if not t:
                continue
            if venue_id:
                published[venue_id].add(t)
            else:
                unassigned.append({"kind": "published", "venue": p.get("venue"),
                                   "city": p.get("municipality"), "date": day})

    for p in programs.get("programs", []):
        venue_id = resolve(p.get("venue"), p.get("municipality"))
        for performance in p.get("performances", []):
            day = performance.get("local_date")
            stamp = performance.get("starts_at")
            hour = stamp[11:16] if isinstance(stamp, str) and stamp.startswith(str(day) + "T") else ""
            t = token(day, hour)
            if t:
                if venue_id:
                    published[venue_id].add(t)
                else:
                    unassigned.append({"kind": "program", "venue": p.get("venue"),
                                       "city": p.get("municipality"), "date": day})

    # Official detail evidence often lacks a city. Never guess a venue from
    # an identical name elsewhere; only resolve names unique in the directory.
    names = defaultdict(set)
    for v in venues:
        names[norm(v["name"])].add(v["id"])
        if v.get("profile_key") and "|" in v["profile_key"]:
            names[norm(v["profile_key"].split("|", 1)[1])].add(v["id"])
    for page in evidence.get("evidence", []):
        if page.get("status") in ("excluded_nonopera", "invalid_source"):
            continue
        for fact in page.get("event_facts", []):
            day = fact.get("date")
            stamp = fact.get("starts_at")
            if stamp and not stamp.startswith(str(day) + "T"):
                continue
            hour = stamp[11:16] if stamp else ""
            t = token(day, hour)
            if not t:
                continue
            name = fact.get("venue")
            city = fact.get("city") or fact.get("municipality")
            venue_id = resolve(name, city) if city else None
            if not venue_id:
                options = names.get(norm(name), set())
                if len(options) == 1:
                    venue_id = next(iter(options))
            if venue_id:
                observed[venue_id].add(t)
            else:
                unassigned.append({"kind": "official_observation",
                                   "venue": name, "city": city, "date": day})

    result = []
    for venue in venues:
        vid = venue["id"]
        months = []
        for m in range(1, 13):
            prefix = f"2026-{m:02d}-"
            pub = {t for t in published[vid] if t[0].startswith(prefix)}
            obs = {t for t in observed[vid] if t[0].startswith(prefix)}
            remaining = set(obs)
            for day, hour in pub:
                if (day, hour) in remaining:
                    remaining.remove((day, hour))
                elif (day, "") in remaining:
                    remaining.remove((day, ""))
                elif not hour:
                    options = [t for t in remaining if t[0] == day]
                    if len(options) == 1:
                        remaining.remove(options[0])
            months.append({
                "month": f"2026-{m:02d}",
                "published_known": len(pub),
                "independently_observed": len(obs),
                "observed_not_published": len(remaining),
                "status": "known_gap" if remaining else "not_verified_complete",
                "official_full_calendar_checked": False,
            })
        result.append({
            "venue_id": vid, "venue": venue["name"], "city": venue.get("city"),
            "months": months,
            "year_status": "known_gap" if any(m["observed_not_published"] for m in months)
                           else "not_verified_complete",
        })
    return {
        "schema_version": 1, "year": 2026,
        "scope": "Existing approved catalog and official detail observations only",
        "complete_seasons_certified": 0,
        "warning": "NOT a full-calendar audit. No historical official calendar denominator has been verified.",
        "venues": result,
        "unassigned_evidence": unassigned,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional report path; omitted means stdout only")
    args = parser.parse_args()
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    result = build(read(DIRECTORY), read(CATALOG), read(EVIDENCE), read(PROGRAMS))
    body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(body, encoding="utf-8")
        print(f"Report written: {args.output}")
    else:
        print(body, end="")


if __name__ == "__main__":
    main()
