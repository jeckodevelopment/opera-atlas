"""Publish existing, fully verified known-work recite before slow live scans.

Offline-only: neither invents unknown works nor bypasses source verification.
Generated public JSON remains checked by the regular workflow before pushing.
"""
from __future__ import annotations
import json
from datetime import date
from scripts.auto_catalogue import (
    promote,enrich_existing_times,enrich_double_bill_times,SOURCE_ALLOWLIST
)
from scripts.build_verified_catalog import (
    MANIFEST,TIME_EVIDENCE,validate_auto_sources,validate_time_evidence
)
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.publish_work_editorial import EDITORIAL,HISTORY,build_editorial
from scripts.daily_ingest import _write_atomic

def prepare(facts,registry,evidence,candidates,authorized,verified_times,*,today):
    after,ids,urls,report=promote(
        facts,registry,evidence,candidates,authorized,today=today)
    updated_times,enriched=enrich_existing_times(
        after,evidence,candidates,verified_times)
    updated_times,double=enrich_double_bill_times(
        after,evidence,candidates,updated_times)
    validate_auto_sources(urls)
    validate_time_evidence(after,updated_times)
    assemble(after,ids,approved_extra=set(urls))
    editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    history=json.loads(HISTORY.read_text(encoding="utf-8"))
    build_editorial(after,ids,editorial,
                    approved_extra=set(urls),history=history)
    report["enriched_recite_times"]=enriched+double
    return after,ids,urls,updated_times,report

def main():
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates=json.loads(INDEX.read_text(encoding="utf-8"))
    evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
    allowlist=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))
    old_times=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
    after,ids,urls,times,report=prepare(
        facts,registry,evidence,candidates,allowlist["urls"],old_times,
        today=date.today())
    if report["new_recite"]:
        _write_atomic(MANIFEST,after)
        _write_atomic(REGISTRY,ids)
        _write_atomic(SOURCE_ALLOWLIST,{"schema_version":1,"urls":urls})
    if report["enriched_recite_times"]:
        _write_atomic(TIME_EVIDENCE,times)
    print(json.dumps({"cached_verified":report},ensure_ascii=False))

if __name__=="__main__":
    main()
