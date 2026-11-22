"""Apply an explicitly reviewed, bounded cross-source decision to live registries.

Unlike a network scan, this does not pretend to fetch an inaccessible primary
event page. The dated editorial decision and its disclosed secondary sources
are immutable inputs, not a second publisher. Canonical ID allocation and
duplicate checks remain in scripts.auto_catalogue.promote.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime,timezone

from scripts.publish_catalog_v2 import ROOT
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import OUTPUT as CANDIDATES,PUBLIC as PUBLIC_CANDIDATES
from scripts.collect_candidate_details import OUTPUT as DETAILS,PUBLIC as PUBLIC_DETAILS
from scripts.corroborate_performances import CONFIG as SOURCE_CONFIG,validate_case,EXPECTED
from scripts.build_verified_catalog import official_local_time

CONFIG=ROOT/"data/reviewed-performance-decisions.json"

def apply(decisions:dict,sources:dict,candidates:dict,details:dict,*,now:str):
    if (decisions.get("schema_version")!=1
        or not isinstance(decisions.get("decisions"),list)
        or len(decisions["decisions"])!=1):
        raise ValueError("expected one specifically reviewed editorial decision")
    if (sources.get("schema_version")!=1
        or not isinstance(sources.get("cases"),list)):
        raise ValueError("invalid source corroboration configuration")
    by_case={x["id"]:x for x in sources["cases"]}
    cand={x["id"]:dict(x) for x in candidates["candidates"]}
    evid={x["candidate_id"]:dict(x) for x in details["evidence"]}
    result=[]
    for decision in decisions["decisions"]:
        case=by_case.get(decision.get("case_id"))
        if case is None:
            raise ValueError("unregistered editorial review case")
        validate_case(case)
        if (decision.get("reviewed_on")!="2026-11-22"
            or decision.get("decision")!="approved_for_canonical_reconciliation"
            or decision.get("source_policy")!="issuer_repertoire_plus_secondary_performance_cross_checks"
            or decision.get("official_event_page_retrieved") is not False
            or decision.get("excluded_school_date")!=case["school_date"]
            or not isinstance(decision.get("independence_note"),str)
            or not decision["independence_note"].strip()):
            raise ValueError("incomplete or modified editorial evidence decision")
        rows=decision.get("public_recite")
        if (not isinstance(rows,list)
            or len(rows)!=2
            or not all(isinstance(x,dict) and set(x)=={"date","time"} for x in rows)
            or {x["date"]:x["time"] for x in rows}!=EXPECTED):
            raise ValueError("unapproved or ambiguous editorial performance clocks")
        key=case["source_key"]
        url=case["official_event_url"]
        cid="oa-index-"+hashlib.sha256((key+"|"+url).encode()).hexdigest()[:20]
        old_candidate=cand.get(cid)
        if old_candidate and (old_candidate.get("official_url")!=url or
                              old_candidate.get("source_key")!=key):
            raise ValueError("existing candidate conflicts with reviewed event")
        if old_candidate and old_candidate["status"]!="needs_review":
            result.append({"case_id":case["id"],"status":"already_processed"})
            continue
        old_evidence=evid.get(cid)
        if old_evidence and old_evidence.get("status")=="needs_editorial_review":
            # Stronger live-verified evidence takes precedence over reviewed
            # secondary evidence, even when another scan is in progress.
            result.append({"case_id":case["id"],"status":"existing_evidence_preserved"})
            continue
        if old_evidence and (old_evidence.get("source_key")!=key or
                             old_evidence.get("source_url")!=url):
            raise ValueError("conflicting candidate evidence origin")
        cand[cid]=(old_candidate or {
            "id":cid,"source_key":key,"official_url":url,
            "status":"needs_review","first_seen":now,"last_seen":now
        })
        canonical=json.dumps(decision,sort_keys=True,ensure_ascii=False,
                             separators=(",",":"))
        evid[cid]={
            "candidate_id":cid,"source_key":key,"source_url":url,
            "content_sha256":hashlib.sha256(canonical.encode()).hexdigest(),
            "content_hash_scope":"editorial_decision_not_primary_html",
            "reviewed_on":decision["reviewed_on"],
            "status":"needs_editorial_review",
            "event_facts":[{
                "event_title":case["title"],"composer":case["composer"],
                "venue":case["venue"],"date":r["date"],
                "starts_at":official_local_time(r["date"],r["time"])
            } for r in sorted(rows,key=lambda x:x["date"])],
            "corroboration":{
                "method":"manual_editorial_review_of_secondary_public_sources",
                "official_event_page_retrieved":False,
                "issuer_url":case["issuer_repertoire_url"],
                "publisher_urls":[r["url"] for r in case["publisher_events"]],
                "cross_check_url":case["independent_event_url"],
                "excluded_school_date":case["school_date"],
                "source_independence_note":decision["independence_note"],
                "reviewed_on":decision["reviewed_on"]
            }
        }
        result.append({"case_id":case["id"],"status":"reviewed_candidate_added"})
    return ({"schema_version":1,
             "candidates":sorted(cand.values(),key=lambda x:x["id"])},
            {"schema_version":1,
             "evidence":sorted(evid.values(),key=lambda x:x["candidate_id"])},
            result)

def main():
    reviews=json.loads(CONFIG.read_text(encoding="utf-8"))
    sources=json.loads(SOURCE_CONFIG.read_text(encoding="utf-8"))
    candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
    details=json.loads(DETAILS.read_text(encoding="utf-8"))
    new_candidates,new_details,outcomes=apply(
        reviews,sources,candidates,details,
        now=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _write_atomic(CANDIDATES,new_candidates)
    _write_atomic(PUBLIC_CANDIDATES,new_candidates)
    _write_atomic(DETAILS,new_details)
    _write_atomic(PUBLIC_DETAILS,new_details)
    print(json.dumps({"reviewed_evidence":outcomes},ensure_ascii=False))

if __name__=="__main__":
    main()
