"""Read-only triage of nationally reconciled 2026 archive observations.

Associations across differing source URLs are *diagnostic corroboration*, not
a transferred editorial decision. Nothing here can publish or exclude an event.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from scripts.audit_2026_retrospective_reconciliation import norm, url_key

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "public/diagnostics/atlas-2026-national-reconciliation-summary.json"
DECISIONS = ROOT / "data/retrospective-2026-source-specific-decisions.json"
PRIORITY = ROOT / "data/retrospective-2026-priority-reviews.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-editorial-triage.json"


def identity(row):
    # Source key is essential: independent companies may present the same title.
    return (row.get("source_key"), row.get("date"), row.get("time"),
            norm(row.get("event_title")), norm(row.get("venue")))


def classify(summary, decisions, priority):
    if (summary.get("year") != 2026 or summary.get("read_only") is not True
            or summary.get("catalog_updated") is not False
            or summary.get("complete_seasons_certified") != 0):
        raise ValueError("Invalid national source summary")
    queue = summary["review_queue"]
    if summary["review_queue_count"] != len(queue):
        raise ValueError("Incomplete national review queue")
    by_identity = defaultdict(list)
    for row in queue:
        if not row.get("source_key") or not row.get("date") or not norm(row.get("event_title")):
            raise ValueError("Untraceable review entry")
        by_identity[identity(row)].append(row)
    # Only *previous* editorial classifications under an exact first-party
    # URL and exact day, clock, venue and title can corroborate a second URL.
    prior = defaultdict(list)
    for decision in decisions.get("decisions", []):
        if (decision.get("decision") != "exclude_nonopera"
                or not url_key(decision.get("source_url"))
                or not decision.get("time") or not norm(decision.get("venue"))):
            continue
        k=(decision.get("date"), decision.get("time"),
           norm(decision.get("event_title")), norm(decision.get("venue")))
        prior[k].append(decision)
    official = {
        (r.get("date"), norm(r.get("event_title"))):r
        for r in priority.get("records", [])
        if r.get("classification", "").startswith("official_opera_candidate")
    }
    groups = []
    for key, rows in sorted(by_identity.items(), key=lambda pair: str(pair[0])):
        source, date, clock, title, venue = key
        urls = sorted({r["source_url"] for r in rows})
        candidate = official.get((date, title))
        if candidate and (not clock or not venue or not candidate.get("time")
                          or norm(candidate.get("venue")) != venue
                          or not any(urlsplit(u).hostname ==
                                     urlsplit(candidate.get("source_url") or "").hostname
                                     for u in urls)):
            candidate = None
        support = []
        if clock and venue:
            support = [
                d for d in prior.get((date, clock, title, venue), [])
                if url_key(d["source_url"]) and
                any(urlsplit(u).hostname == urlsplit(d["source_url"]).hostname
                    for u in urls)
                and d["source_url"] not in urls
            ]
        if candidate:
            bucket = "official_opera_candidate_needs_editorial_review"
        elif support:
            bucket = "previous_nonopera_decision_cross_url_corroboration"
        elif any(r["status"] == "possible_match_needs_venue_source_review" for r in rows):
            bucket = "possible_catalog_match_needs_confirmation"
        elif len(urls) > 1:
            bucket = "cross_index_duplicate_needs_genre_review"
        else:
            bucket = "unclassified_requires_source_review"
        groups.append({
            "source_key":source,"date":date,"time":clock,
            "event_title":rows[0]["event_title"],"venue":rows[0].get("venue"),
            "bucket":bucket,"observation_count":len(rows),
            "source_urls":urls,
            "original_statuses":sorted({r["status"] for r in rows}),
            "existing_editorial_evidence":[
                {"source_url":d["source_url"],"reason":d.get("reason"),
                 "decision":d["decision"]} for d in support
            ],
            "official_candidate_evidence":(
                {"official_detail_url":candidate.get("official_detail_url"),
                 "time":candidate.get("time"),"classification":candidate["classification"]}
                if candidate else None),
            "automatic_publication":False,
            "automatic_exclusion":False,
        })
    counts = dict(sorted(Counter(x["bucket"] for x in groups).items()))
    by_source = defaultdict(Counter)
    for g in groups:
        by_source[g["source_key"]][g["bucket"]] += 1
    return {
        "schema_version":1,"year":2026,
        "source_summary_generated_at":summary["generated_at"],
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,
        "complete_seasons_certified":0,
        "input_review_count":len(queue),
        "event_groups":len(groups),
        "cross_url_observations_consolidated":len(queue)-len(groups),
        "bucket_counts":counts,
        "by_source":{k:dict(sorted(v.items())) for k,v in sorted(by_source.items())},
        "review_groups":groups,
        "warning":"Cross-URL evidence and category guesses are diagnostic. No editorial decision transfers to a different URL, and no new opera is certified missing or published.",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    result=classify(json.loads(SUMMARY.read_text(encoding="utf-8")),
                    json.loads(DECISIONS.read_text(encoding="utf-8")),
                    json.loads(PRIORITY.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("EDITORIAL_TRIAGE_COUNTS "+json.dumps({
        "observations":result["input_review_count"],
        "groups":result["event_groups"],
        "cross_url_consolidated":result["cross_url_observations_consolidated"],
        "buckets":result["bucket_counts"],
    },ensure_ascii=False))
    for group in result["review_groups"]:
        if group["bucket"] in (
            "official_opera_candidate_needs_editorial_review",
            "cross_index_duplicate_needs_genre_review",
            "possible_catalog_match_needs_confirmation",
        ):
            print("EDITORIAL_TRIAGE_REVIEW "+json.dumps({
                "date":group["date"],"title":group["event_title"],
                "bucket":group["bucket"],"source":group["source_key"],
            },ensure_ascii=False))


if __name__=="__main__":
    main()
