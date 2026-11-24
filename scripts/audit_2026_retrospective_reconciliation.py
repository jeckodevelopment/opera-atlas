"""Reconcile national 2026 retrospective observations, diagnostics only.

Never infer a missing public recita from an unmatched fact. A match must be
traceable to the exact source URL and date, or independently corroborated by
canonical work, venue and clock. Archive/index generic Event JSON-LD is
insufficient to establish operatic genre, audience or absence.
"""
from __future__ import annotations

import argparse
import json
import html
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from scripts.discover_season_indexes import excluded_nonopera

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "public/diagnostics/atlas-2026-retrospective-batch.json"
CATALOG = ROOT / "data/verified-launch-catalog.json"
PROGRAMS = ROOT / "public/catalog/programs.json"
HISTORICAL = ROOT / "data/historical-2026-official-evidence.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-retrospective-reconciliation.json"
PRIORITY = ROOT / "data/retrospective-2026-priority-reviews.json"

def norm(value):
    value = unicodedata.normalize("NFKD", html.unescape(str(value or "")).casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(
        c for c in value if not unicodedata.combining(c))).strip()

def url_key(url):
    try:
        p = urlsplit(url or "")
        if p.scheme != "https" or not p.hostname:
            return None
        path = p.path.rstrip("/")
        # Locale-specific links for one verified bilingual official festival.
        # No generic locale stripping across other organizations.
        if p.hostname.lower() == "www.festivaldellavalleditria.it" and path.startswith("/en/spettacolo/"):
            path = path[3:]
        return (p.hostname.lower(), path)
    except (TypeError, ValueError):
        return None

def clock(value, day):
    if not isinstance(value, str) or not value.startswith(day + "T"):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return value[11:16]
    except ValueError:
        return None

def catalog_rows(catalog, programs, historical):
    rows = []
    for p in catalog.get("productions", []):
        for item in p.get("dates", []):
            if not isinstance(item, list) or not item or not isinstance(item[0], str):
                continue
            day = item[0]
            if not day.startswith("2026-"):
                continue
            rows.append({"source_url":p.get("source_url"),
                         "title":p.get("title"), "composer":p.get("composer"),
                         "venue":p.get("venue"), "city":p.get("municipality"),
                         "date":day, "time":item[1] if len(item)>1 else None,
                         "origin":"verified_catalog"})
    for p in programs.get("programs", []):
        for item in p.get("performances", []):
            day = item.get("local_date")
            if not isinstance(day,str) or not day.startswith("2026-"):
                continue
            rows.append({"source_url":p.get("source_url"),
                         "title":p.get("title"),"composer":None,
                         "venue":p.get("venue"),"city":p.get("municipality"),
                         "date":day,"time":clock(item.get("starts_at"),day),
                         "origin":"published_program"})
    for p in historical.get("records", []):
        for item in p.get("dates",[]):
            day=item.get("date")
            if not isinstance(day,str) or not day.startswith("2026-"):
                continue
            rows.append({"source_url":p.get("source_url"),"title":p.get("title"),
                         "composer":p.get("composer"),"venue":p.get("venue"),
                         "city":p.get("city"),"date":day,"time":item.get("time"),
                         "origin":"official_archive_diagnostic"})
    return rows

def same_time(fact_hour, published_hour):
    # Time missing is not evidence of an exact showtime match.
    return fact_hour is not None and published_hour is not None and fact_hour == published_hour

def reconcile(report, catalog, programs, historical, priority=None):
    if report.get("year") != 2026 or report.get("read_only") is not True:
        raise ValueError("invalid 2026 retrospective input")
    rows=catalog_rows(catalog,programs,historical)
    reviews={(url_key(p.get("source_url")),p.get("date"),norm(p.get("event_title"))):p
             for p in (priority or {}).get("records",[])}
    by_url_day=defaultdict(list)
    by_title_day=defaultdict(list)
    for row in rows:
        if url_key(row["source_url"]):
            by_url_day[(url_key(row["source_url"]),row["date"])].append(row)
        if norm(row["title"]):
            by_title_day[(norm(row["title"]),row["date"])].append(row)

    occurrences=defaultdict(list)
    for fact in report.get("unverified_2026_facts",[]):
        day=fact.get("date")
        if not isinstance(day,str) or not re.fullmatch(r"2026-\d{2}-\d{2}",day):
            continue
        try:
            date.fromisoformat(day)
        except ValueError:
            continue
        source=fact.get("source_url")
        if not url_key(source):
            continue
        title=norm(fact.get("event_title"))
        if not title:
            continue
        # Exact duplicate emitted from archive pass and detail pass is one
        # observation, retaining all paths through which it was discovered.
        itemkey=(url_key(source),day,title,fact.get("starts_at") or "",
                 norm(fact.get("venue")))
        occurrences[itemkey].append(fact)

    output=[]
    for (_,day,title,stamp,venue), copies in sorted(occurrences.items(),
            key=lambda kv: (kv[0][1],kv[0][2],kv[0][0])):
        fact=copies[0]
        source=fact["source_url"]
        source_key=fact.get("source_key") or ""
        hour=clock(fact.get("starts_at"),day)
        direct=by_url_day.get((url_key(source),day),[])
        candidates=by_title_day.get((title,day),[])
        reviewed=reviews.get((url_key(source),day,title))
        if excluded_nonopera(source_key,source):
            status="excluded_by_approved_policy"
            matched=[]
        elif reviewed:
            # The official independently checked event page may disagree with
            # a generic festival index JSON-LD timestamp; preserve the
            # candidate and surface the discrepancy for manual verification.
            status=(reviewed["classification"] if hour is None or hour == reviewed["time"]
                    else reviewed["classification"] + "_time_conflict")
            matched=[]
        elif direct and any(norm(m["title"])==title and
                (hour is None or same_time(hour,m["time"])) for m in direct):
            matched=[m for m in direct if norm(m["title"])==title and
                     (hour is None or same_time(hour,m["time"]))]
            origins={m["origin"] for m in matched}
            status=("already_published_exact_source_day_work" if
                    origins & {"verified_catalog","published_program"} else
                    "official_archive_already_documented")
        elif direct:
            # A multi-work evening may be represented by a canonical component
            # in the catalog. Keep it partial rather than calling it a conflict.
            if any(norm(m["title"]) in title and norm(m["title"]) != title
                   and (hour is None or same_time(hour,m["time"])) for m in direct):
                status="partial_multiwork_catalogued_needs_review"
            else:
                status="same_source_day_identity_or_time_conflict"
            matched=direct
        elif candidates:
            # Same title/day across cities or sources is not sufficient to
            # merge. Expose as an ambiguity for an editor.
            status="possible_match_needs_venue_source_review"
            matched=candidates
        else:
            status="unmatched_requires_official_review"
            matched=[]
        output.append({
            "date":day,"time":hour,"event_title":fact.get("event_title"),
            "source_url":source,"source_key":source_key,"venue":fact.get("venue"),
            "composer":fact.get("composer"),"status":status,
            "duplicate_observations_collapsed":len(copies)-1,
            "official_review_evidence":({
                "official_detail_url":reviewed["official_detail_url"],
                "composer":reviewed["composer"],
                "time":reviewed["time"],
                "venue":reviewed["venue"],
                "evidence":reviewed["evidence"],
            } if reviewed else None),
            "discovered_from":sorted({x.get("discovered_from") or source for x in copies}),
            "matched_catalog":[{"title":m["title"],"venue":m["venue"],
                                "city":m["city"],"time":m["time"],
                                "origin":m["origin"],"source_url":m["source_url"]}
                               for m in matched[:12]],
        })
    counts=dict(sorted(Counter(x["status"] for x in output).items()))
    by_month=defaultdict(lambda:Counter())
    for item in output:
        by_month[item["date"][:7]][item["status"]]+=1
    failures={
        phase:{"attempted":len(report.get(key,[])),
               "failed":sum(x.get("status")=="unverified" for x in report.get(key,[])),
               "reason_counts":dict(sorted(Counter(x.get("failure","unknown")
                    for x in report.get(key,[]) if x.get("status")=="unverified").items()))}
        for phase,key in (("seed","seed_results"),("archive","archive_results"),
                          ("detail","detail_results"))
    }
    return {
        "schema_version":1,"year":2026,"source_checked_at":report.get("checked_at"),
        "read_only":True,"catalog_updated":False,"complete_seasons_certified":0,
        "raw_observation_count":len(report.get("unverified_2026_facts",[])),
        "unique_observation_count":len(output),
        "duplicate_observations_collapsed":sum(x["duplicate_observations_collapsed"] for x in output),
        "observation_counts":counts,
        "monthly_counts":{month:dict(sorted(c.items())) for month,c in sorted(by_month.items())},
        "scan_failures":failures,
        "archives_checked":report.get("historical_archives_scanned"),
        "details_checked":report.get("detail_pages_scanned"),
        "observations":output,
        "warning":"Unmatched observations are not verified missing recite. In particular, generic event/season JSON-LD cannot certify opera, general audience, exact venue, or complete calendar. No automatic publication.",
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    result=reconcile(read(INPUT),read(CATALOG),read(PROGRAMS),read(HISTORICAL),
                     read(PRIORITY))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({"raw":result["raw_observation_count"],
                      "unique":result["unique_observation_count"],
                      "counts":result["observation_counts"],
                      "failures":result["scan_failures"]},ensure_ascii=False))
    # Review queue is deliberately readable directly from the job logs,
    # even when the full JSON is too large for an API content preview.
    for row in result["observations"]:
        if row["status"] not in ("already_published_exact_source_day_work",
                                 "excluded_by_approved_policy",
                                 "official_archive_already_documented",
                                 "official_opera_candidate_needs_publication_review",
                                 "semistaged_abbreviated_opera_needs_scope_review"):
            print("REVIEW " + json.dumps({
                "date":row["date"],"title":row["event_title"],
                "venue":row["venue"],"status":row["status"],
                "url":row["source_url"]},ensure_ascii=False))

if __name__=="__main__":
    main()
