"""Queue verified Rome archive URLs without bypassing official date/authority gates."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from opera_atlas.roma_detail_parser import HISTORICAL_URLS

ROOT=Path(__file__).resolve().parents[1]
SOURCE="opera-roma-season-2026-27"

def seed(candidates,evidence,known_urls,*,timestamp):
    rows={row["id"]:row.copy() for row in candidates["candidates"]}
    details={row["candidate_id"]:row.copy() for row in evidence["evidence"]}
    for url in sorted(HISTORICAL_URLS):
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+url).encode()).hexdigest()[:20]
        if url in known_urls:
            continue
        if cid not in rows:
            rows[cid]={"id":cid,"source_key":SOURCE,"official_url":url,
                       "status":"needs_review","first_seen":timestamp,"last_seen":timestamp}
        row=rows[cid]
        proof=details.get(cid,{})
        if (row["status"]=="not_in_official_season"
            and proof.get("status")=="out_of_monitored_season"
            and proof.get("official_season")=="2025/2026"
            and proof.get("source_url")==url and proof.get("source_key")==SOURCE):
            row["status"]="needs_review"
            details.pop(cid)
    return ({**candidates,"candidates":sorted(rows.values(),key=lambda row:row["id"])},
            {**evidence,"evidence":sorted(details.values(),key=lambda row:row["candidate_id"])})

def main():
    from scripts.discover_season_indexes import reviewed_source_urls
    from scripts.collect_candidate_details import _write_atomic
    index=ROOT/"data/season-index-candidates.json"
    detail=ROOT/"data/candidate-detail-evidence.json"
    candidates,evidence=seed(json.loads(index.read_text(encoding="utf-8")),
        json.loads(detail.read_text(encoding="utf-8")),reviewed_source_urls(),
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    for path,doc in ((index,candidates),(detail,evidence),
        (ROOT/"public/catalog/season-index-candidates.json",candidates),
        (ROOT/"public/catalog/candidate-detail-evidence.json",evidence)):
        _write_atomic(path,doc)

if __name__=="__main__":
    main()
