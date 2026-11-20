"""Autonomous publication of unambiguous, official, already-known opera recite.

No manual reconciliation. A candidate is accepted only if its official production
URL, canonical work+composer, venue, and explicit dates agree with the already
verified sources. New unknown works cannot be misidentified by title alone.
"""
from __future__ import annotations
import copy
import hashlib
import json
from datetime import date
from urllib.parse import urlsplit
from scripts.build_verified_catalog import MANIFEST
from scripts.daily_ingest import _next_replica_id, _write_atomic
from scripts.publish_catalog_v2 import REGISTRY, assemble, normalized, slugify
from scripts.discover_season_indexes import CONFIG, validate_config, eligible, OUTPUT as INDEX
from scripts.collect_candidate_details import OUTPUT as DETAILS
from pathlib import Path

ROOT=MANIFEST.parents[1]
SOURCE_ALLOWLIST=ROOT/"data"/"auto-source-urls.json"
HEALTH=ROOT/"data"/"autonomous-catalogue-health.json"
VENUE_BY_SOURCE={
    "scala-season-2026-27":("Milano","Teatro alla Scala"),
    "arena-festival-2027":("Verona","Arena di Verona"),
}
def next_id(entries:dict,prefix:str)->str:
    numeric=[int(x["id"][len(prefix):]) for x in entries.values()
             if x["id"].startswith(prefix) and x["id"][len(prefix):].isdigit()]
    return prefix+f"{max(numeric,default=0)+1:06d}"

def promote(facts:dict, registry:dict, evidence:dict, candidates:dict,
            authorized_urls:list[str], *, today:date)->tuple[dict,dict,list[str],dict]:
    """Return all changes in memory; skip anomalies without publishing bad data."""
    next_facts=copy.deepcopy(facts)
    next_registry=copy.deepcopy(registry)
    approved=set(authorized_urls)
    indexes={x["id"]:x for x in candidates.get("candidates",[])
             if x.get("status")=="needs_review"}
    config={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
            if x["access_status"]=="approved"}
    issues=[]
    created_stagings=created_recite=0
    for item in sorted(evidence.get("evidence",[]),key=lambda x:x.get("candidate_id","")):
        cid=item.get("candidate_id")
        candidate=indexes.get(cid)
        if not candidate or item.get("status")!="needs_editorial_review":
            continue
        key=candidate["source_key"]
        source=config.get(key)
        url=candidate["official_url"]
        if (source is None or key not in VENUE_BY_SOURCE or item.get("source_url")!=url
            or item.get("source_key")!=key or not eligible(key,url)
            or urlsplit(url).hostname!=urlsplit(source["official_url"]).hostname):
            issues.append({"candidate_id":cid,"reason":"unsupported_or_untrusted_source"})
            continue
        # Both the explicitly named work and composer must be present in the
        # evidence; an Event title alone never establishes a canonical opera.
        rows=item.get("event_facts",[])
        if not rows or not all(isinstance(x,dict) and
               isinstance(x.get("composer"),str) and isinstance(x.get("event_title"),str)
               and isinstance(x.get("date"),str) and isinstance(x.get("starts_at"),str)
               for x in rows):
            issues.append({"candidate_id":cid,"reason":"incomplete_work_or_clock"})
            continue
        names={(normalized(x["event_title"]),normalized(x["composer"])) for x in rows}
        if len(names)!=1:
            issues.append({"candidate_id":cid,"reason":"multiple_work_identities"})
            continue
        title,composer=next(iter(names))
        matches=[w for w in next_registry["works"].values()
                 if normalized(w["title"])==title and normalized(w["composer"])==composer]
        if len(matches)!=1:
            issues.append({"candidate_id":cid,"reason":"unknown_work_needs_authority_data"})
            continue
        work=matches[0]
        city,venue=VENUE_BY_SOURCE[key]
        venues=[(vk,v) for vk,v in next_registry["venues"].items()
                if v["city"]==city and v["name"]==venue]
        if len(venues)!=1:
            issues.append({"candidate_id":cid,"reason":"unknown_venue"})
            continue
        vk,canonical_venue=venues[0]
        dates={}
        for row in rows:
            try:
                day=date.fromisoformat(row["date"]).isoformat()
                stamp=__import__("datetime").datetime.fromisoformat(row["starts_at"])
                if stamp.tzinfo is None or stamp.date().isoformat()!=day:
                    raise ValueError("missing timezone or conflicting day")
                from zoneinfo import ZoneInfo
                local=stamp.astimezone(ZoneInfo("Europe/Rome"))
                if local.date().isoformat()!=day:
                    raise ValueError("not Italian local day")
                hour=local.strftime("%H:%M")
                if day in dates and dates[day]!=hour:raise ValueError("ambiguous date")
                dates[day]=hour
            except (TypeError,ValueError):
                dates={}
                break
        if not dates:
            issues.append({"candidate_id":cid,"reason":"unreliable_event_dates"})
            continue
        # Production URL is an exact identity. A second staging of the same
        # opera at one theatre must not silently share an ambiguous route.
        colliding=[x for x in next_facts["productions"]
                   if x["municipality"]==city and x["venue"]==venue
                   and normalized(x["title"])==title and normalized(x["composer"])==composer]
        exact=[x for x in colliding if x["source_url"]==url]
        if colliding and not exact:
            issues.append({"candidate_id":cid,"reason":"venue_work_route_collision"})
            continue
        if len(exact)>1:
            issues.append({"candidate_id":cid,"reason":"ambiguous_existing_staging"})
            continue
        if exact:
            production=exact[0]
            if any(day in dict(production["dates"]) and dict(production["dates"])[day]!=hour
                   for day,hour in dates.items()):
                issues.append({"candidate_id":cid,"reason":"conflicting_existing_time"})
                continue
        else:
            staging_key="auto-"+hashlib.sha256((key+"|"+url).encode()).hexdigest()[:16]
            if staging_key in next_registry["stagings"]:
                issues.append({"candidate_id":cid,"reason":"identity_collision"})
                continue
            production={"key":staging_key,"title":work["title"],
                        "composer":work["composer"],"venue":venue,
                        "municipality":city,"region":canonical_venue["region"],
                        "source_url":url,"dates":[]}
            next_registry["stagings"][staging_key]={
                "id":next_id(next_registry["stagings"],"oa-s-"),
                "work_id":work["id"],"venue_id":canonical_venue["id"],
                "slug":work["slug"],"source_url":url,"season":"2026-2027"}
            next_facts["productions"].append(production)
            created_stagings+=1
        for day,hour in sorted(dates.items()):
            if day in dict(production["dates"]):continue
            pk=production["key"]+"|"+day
            if pk in next_registry["performances"]:
                issues.append({"candidate_id":cid,"reason":"recita_id_collision"})
                continue
            next_registry["performances"][pk]={
                "id":f"oa-r-{_next_replica_id(next_registry):06d}",
                "staging_id":next_registry["stagings"][production["key"]]["id"],
                "original_date":day,"source_url":url}
            production["dates"].append([day,hour])
            created_recite+=1
        production["dates"].sort(key=lambda x:x[0])
        approved.add(url)
    if created_recite:
        next_facts["reviewed_on"]=today.isoformat()
    return (next_facts,next_registry,sorted(approved),
            {"new_stagings":created_stagings,"new_recite":created_recite,
             "auto_skipped":issues})

def main():
    from datetime import date
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    evidence=json.loads(DETAILS.read_text(encoding="utf-8")) if DETAILS.exists() else {"evidence":[]}
    candidates=json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"candidates":[]}
    approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8")) if SOURCE_ALLOWLIST.exists() else {"schema_version":1,"urls":[]}
    next_facts,next_registry,urls,report=promote(
        facts,registry,evidence,candidates,approved["urls"],today=date.today())
    # Only write after the full canonical graph validates against the expanded
    # source allowlist; rollback-like behavior by pre-validating in memory.
    from scripts.build_verified_catalog import validate_auto_sources
    validate_auto_sources(urls)
    assemble(next_facts,next_registry,approved_extra=set(urls))
    if report["new_recite"]:
        _write_atomic(MANIFEST,next_facts)
        _write_atomic(REGISTRY,next_registry)
        _write_atomic(SOURCE_ALLOWLIST,{"schema_version":1,"urls":urls})
    _write_atomic(HEALTH,{"schema_version":1,**report})
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
