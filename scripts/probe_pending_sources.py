"""Read-only live readiness probe for specifically inventoried Scala/Arena pages.

The probe is deliberately separate from the canonical ingestion job: it
checks fresh robots.txt for each URL, then compares live parsed recite with
the reviewed catalog without writing new events or changing approval state.
The user authorized conditional robots-respecting checks on official pages.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime,timezone
from opera_atlas.controlled_fetch import AccessDenied, FetchUnavailable,fetch_official_html
from opera_atlas.db import connect,migrate
from scripts.build_verified_catalog import MANIFEST
from scripts.daily_ingest import CONFIG, _parse,validate_source_config

SUPPORTED={"scala","arena"}


def evaluate(config: dict, facts: dict, *, fetcher=fetch_official_html) -> dict:
    sources=[s for s in validate_source_config(config) if s["adapter"] in SUPPORTED]
    if not sources:
        raise ValueError("No explicitly inventoried sources for probe")
    reports=[]
    db=connect()
    try:
        migrate(db)
        for source in sources:
            if source["access_status"] == "blocked":
                reports.append({"key":source["key"],"status":"blocked_by_registry"})
                continue
            # Temporary approval is ONLY permission to test robots.txt, not a
            # persistent promotion of source access_status.
            db.execute(
                "INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?,'approved')",
                (source["official_url"],)
            )
            sid=db.execute(
                "SELECT id FROM sources WHERE official_url=?", (source["official_url"],)
            ).fetchone()["id"]
            try:
                response=fetcher(db,source_id=sid,url=source["url"],network_enabled=True)
                parsed=_parse(source,response.html)
                expected=[
                    (p["venue"],p["municipality"],day,hour)
                    for p in facts["productions"]
                    if p["key"]==source["key"]
                    for day,hour in p["dates"]
                ]
                observed=set(parsed)
                if not parsed or len(observed)!=len(parsed):
                    raise ValueError("empty or duplicated parsed schedule")
                if set(expected)==observed:
                    status="matched_official_calendar"
                else:
                    status="review_required"
                reports.append({"key":source["key"],"status":status,
                                "observed":len(parsed),"expected":len(expected),
                                "new_rows":len(observed-set(expected)),
                                "missing_rows":len(set(expected)-observed)})
            except (AccessDenied,FetchUnavailable,ValueError,sqlite3.Error) as exc:
                reports.append({"key":source["key"],"status":"not_verified",
                                "reason":type(exc).__name__})
    finally:
        db.close()
    return {"checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reports":reports}


def main():
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    result=evaluate(config,facts)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    # Probe cannot declare success if any permitted page was blocked or changed.
    if any(x["status"]!="matched_official_calendar" for x in result["reports"]):
        raise SystemExit("At least one source requires access or editorial review")


if __name__=="__main__":
    main()
