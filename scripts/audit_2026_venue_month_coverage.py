"""2026 national venue × month coverage matrix, diagnostics only.

An observed performance is not a complete season. Only individually
attributable source-credited recite qualify as observations; generic index
events and non-opera screening never count toward a venue's opera denominator.
Never mutate published catalog, registry, official sources or editorial data.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VENUES = ROOT / "data/venue-directory.json"
REGISTRY = ROOT / "data/identity-registry.json"
MANIFEST = ROOT / "data/verified-launch-catalog.json"
PROGRAMS = ROOT / "public/catalog/programs.json"
HISTORICAL = ROOT / "data/historical-2026-official-evidence.json"
H1 = ROOT / "public/diagnostics/atlas-2026-jan-jun-official-archive.json"
H1_RECONCILIATION = ROOT / "public/diagnostics/atlas-2026-jan-jun-reconciliation.json"
H2 = ROOT / "public/diagnostics/atlas-2026-retrospective-reconciliation.json"
SEEDS = ROOT / "data/official-2026-retrospective-season-seeds.json"
SEED_SCAN = ROOT / "public/diagnostics/atlas-2026-jan-jun-official-archive.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-venue-month-coverage.json"


def canonical(text):
    text = unicodedata.normalize("NFKD", str(text or "").casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(
        c for c in text if not unicodedata.combining(c))).strip()


def url_identity(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return None
        return parsed.hostname.lower().removeprefix("www."), parsed.path.rstrip("/")
    except ValueError:
        return None


def source_slot(entry):
    day = entry.get("date")
    hour = entry.get("time")
    if not isinstance(day, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", day):
        return None
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    if not isinstance(hour, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", hour):
        return None
    return day, hour


def build_matrix(venues, registry, manifest, programs, historical, h1, h2,
                 seeds, seed_scan):
    venue_rows = venues.get("venues", [])
    if len(venue_rows) != 72 or len({v["id"] for v in venue_rows}) != len(venue_rows):
        raise ValueError("expected 72 distinct reviewed venue IDs")
    by_id = {v["id"]: v for v in venue_rows}
    registry_venues = registry["venues"]
    registry_to_directory = {}
    unlinked_registry = []
    for rv in registry_venues.values():
        target = next((v for v in venue_rows
                       if v["id"] == rv["id"] or v.get("canonical_venue_id") == rv["id"]), None)
        if target is None:
            matches = [v for v in venue_rows if
                       canonical(v["city"]) == canonical(rv["city"]) and
                       canonical(v["name"]) == canonical(rv["name"])]
            if len(matches) == 1:
                target = matches[0]
        if target is not None:
            registry_to_directory[rv["id"]] = target["id"]
        else:
            unlinked_registry.append({"venue_id": rv["id"], "name": rv["name"],
                                      "city": rv["city"]})
    # A physical venue and its exact local calendar slot are the primary
    # units; multiple sources/works can share a single double-bill performance.
    published = defaultdict(lambda: defaultdict(set))
    published_sources = defaultdict(set)
    unresolved_published = []
    for production in manifest.get("productions", []):
        staging = registry["stagings"].get(production.get("key"))
        vid = (registry_to_directory.get(staging["venue_id"])
               if isinstance(staging, dict) else None)
        if vid is None:
            unresolved_published.append({
                "source_url": production.get("source_url"),
                "title": production.get("title"), "venue": production.get("venue"),
                "city": production.get("municipality")})
            continue
        for item in production.get("dates", []):
            if not isinstance(item, list) or len(item) != 2:
                continue
            slot = source_slot({"date": item[0], "time": item[1]})
            if slot:
                published[vid][slot[0][:7]].add(slot)
                published_sources[(vid, slot)].add(url_identity(production["source_url"]))
    # Programmes: no double counting with standard productions.
    unlinked_programs = []
    for p in programs.get("programs", []):
        matches = [v for v in venue_rows if
                   canonical(v["city"]) == canonical(p.get("municipality")) and
                   canonical(v["name"]) == canonical(p.get("venue"))]
        if len(matches) != 1:
            unlinked_programs.append({"venue": p.get("venue"),
                                      "city": p.get("municipality")})
            continue
        vid = matches[0]["id"]
        for item in p.get("performances", []):
            stamp = item.get("starts_at")
            day = item.get("local_date")
            hour = stamp[11:16] if isinstance(stamp, str) and stamp.startswith(str(day)+"T") else None
            slot = source_slot({"date": day, "time": hour})
            if slot:
                published[vid][day[:7]].add(slot)
                published_sources[(vid, slot)].add(url_identity(p.get("source_url")))
    historic = defaultdict(lambda: defaultdict(set))
    for record in historical.get("records", []):
        vid = record.get("venue_id")
        if vid not in by_id or record.get("audience") != "general_public":
            continue
        for item in record.get("dates", []):
            slot = source_slot(item)
            if slot:
                historic[vid][slot[0][:7]].add(slot)

    # H1 has explicit source-credited opera/composer/venue and clocks.
    # The historical audit's old 'unpublished' classification becomes stale
    # when later catalogue PRs merge; always compare CURRENT canonical slots.
    observed = defaultdict(lambda: defaultdict(set))
    observation_details = defaultdict(dict)
    ambiguous_source_facts = []
    review_formats = {"il piccolo principe",
                      "piccolo orso e la montagna di ghiaccio"}
    for fact in h1.get("observations", []):
        candidate_vid = fact.get("venue_id_candidate")
        # The source-index belongs to the Fenice institution, but individual
        # performance pages may explicitly identify Teatro Malibran, a
        # separate canonical physical venue. The original matrix wrongly
        # counted those as Fenice performances.
        explicit = [v for v in venue_rows
                    if canonical(v.get("name")) == canonical(fact.get("venue"))
                    and candidate_vid in by_id
                    and canonical(v.get("city")) == canonical(by_id[candidate_vid]["city"])]
        vid = explicit[0]["id"] if len(explicit)==1 else candidate_vid
        slot = source_slot({"date": fact.get("date"),
                            "time": (fact.get("starts_at") or "")[11:16]})
        if vid not in by_id or not slot or slot[0] >= "2026-07-01":
            continue
        if canonical(fact.get("event_title")) in review_formats:
            ambiguous_source_facts.append({"venue_id": vid, "date": slot[0],
                                           "title": fact.get("event_title"),
                                           "reason": "family_or_school_scope_review"})
            continue
        month = slot[0][:7]
        observed[vid][month].add(slot)
        observation_details[(vid,slot)] = {
            "source_url": fact.get("official_url"),
            "title": fact.get("event_title"),
            "composer": fact.get("composer"),
        }
    for vid, month_slots in historic.items():
        for month, slots in month_slots.items():
            observed[vid][month].update(slots)
    # The broader Jul-Dec scan is a mixture of concerts and other genres:
    # DO NOT add 64 scanned observations to an opera denominator.
    # Report them by state in a separate, explicitly unverified summary.
    h2_counts = dict(Counter(x.get("status", "unknown")
                             for x in h2.get("observations", [])))
    sources_by_venue = defaultdict(list)
    scan_rows = {r["key"]:r for r in seed_scan.get("seed_results", [])}
    for seed in seeds.get("seeds", []):
        vid = seed.get("venue_id")
        if vid not in by_id:
            continue
        scan = scan_rows.get(seed.get("key"), {})
        sources_by_venue[vid].append({
            "source_key": seed["key"], "season": seed["season"],
            "official_url": seed["url"],
            "fetch_status": scan.get("status", "not_attempted"),
            "failure": scan.get("failure"),
            "detail_links_discovered": len(scan.get("links", [])),
            "scope": ("historical_2025_26" if seed["season"]=="2025/26"
                      else "2026_calendar"),
            "source_exhaustiveness_verified": False,
        })
    rows = []
    counts = Counter()
    for v in venue_rows:
        vid = v["id"]
        for m in range(1, 13):
            month = f"2026-{m:02d}"
            pub = published[vid][month]
            obs = observed[vid][month]
            missing = sorted(obs - pub)
            # 'no observations' can mean access denied, historical pages
            # removed, no opera on that month, or simply a missing parser.
            if missing:
                status = "official_observations_require_reconciliation"
            elif pub:
                status = "published_dates_not_exhaustively_verified"
            elif obs:
                status = "source_dates_without_publication"
            else:
                status = "coverage_not_established"
            counts[status] += 1
            rows.append({
                "venue_id":vid, "venue":v["name"],"city":v["city"],
                "region":v.get("region"),"month":month,
                "published_showtimes":len(pub),
                "source_observed_opera_showtimes":len(obs),
                "observed_already_published":len(obs & pub),
                "observed_not_in_publication":len(missing),
                "observed_unpublished_dates":[{"date":d,"time":h}
                                              for d,h in missing],
                "historical_sources_checked":sources_by_venue[vid] if m<=6 else [],
                "source_exhaustiveness_verified":False,
                "complete_month_verified":False,
                "status":status,
            })
    return {
        "schema_version":1, "year":2026,
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,
        "venue_count":len(venue_rows),"months_per_venue":12,
        "cell_count":len(rows),
        "complete_venue_months":0,"complete_annual_venues":0,
        "status_counts":dict(sorted(counts.items())),
        "published_2026_showtimes":sum(x["published_showtimes"] for x in rows),
        "observed_2026_opera_showtimes":sum(x["source_observed_opera_showtimes"] for x in rows),
        "unmatched_source_showtimes":sum(x["observed_not_in_publication"] for x in rows),
        "h1_scope_review":ambiguous_source_facts,
        "h2_mixed_genre_observation_counts":h2_counts,
        "unlinked_registry_venues":unlinked_registry,
        "unlinked_published_productions":unresolved_published,
        "unlinked_programs":unlinked_programs,
        "rows":rows,
        "warning":"Counts are source-observed and published showtimes, never exhaustive official calendars. Zero does not imply no scheduled performances. Only an independently validated complete season can certify a venue-month.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args=ap.parse_args()
    def load(path): return json.loads(path.read_text(encoding="utf-8"))
    report=build_matrix(*(load(p) for p in (
        VENUES,REGISTRY,MANIFEST,PROGRAMS,HISTORICAL,H1,H2,SEEDS,SEED_SCAN)))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({
        "venue_count":report["venue_count"],"cell_count":report["cell_count"],
        "published":report["published_2026_showtimes"],
        "observed":report["observed_2026_opera_showtimes"],
        "unmatched":report["unmatched_source_showtimes"],
        "states":report["status_counts"]},ensure_ascii=False))


if __name__=="__main__":
    main()
