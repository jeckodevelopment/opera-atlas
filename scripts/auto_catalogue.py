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
    "fenice-opera-2026-27":("Venezia","Teatro La Fenice"),
    "parma-opera-2027":("Parma","Teatro Regio di Parma"),
    "massimo-season-2026-27":("Palermo","Teatro Massimo"),
}
def season_from_source(source_key:str,url:str,days)->str:
    """Use the exact official season URL or observed dates, never 2026-27."""
    import re
    path=urlsplit(url).path
    if source_key=="scala-season-2026-27":
        match=re.search(r"/it/stagione/(20\d{2})-(20\d{2})/opera/",path)
        if match and int(match[2])==int(match[1])+1:
            return match[1]+"-"+match[2]
    if source_key in ("fenice-opera-2026-27","massimo-season-2026-27"):
        source=next((x for x in validate_config(json.loads(
            CONFIG.read_text(encoding="utf-8"))) if x["key"]==source_key),None)
        if source:
            start=re.search(r"(20\d{2})-(\d{2})",source["url"])
            if start and int(start[2])==(int(start[1])+1)%100:
                return str(int(start[1]))+"-"+str(int(start[1])+1)
    if days:
        y=int(min(days)[:4])
        return str(y)
    raise ValueError("cannot determine official source season")

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
        # Distinct official productions of the same opera in the same
        # theatre are legitimate (e.g. two different Aida stagings at
        # Verona). Preserve the original route and assign an edition URL
        # for the new staging, within the existing three-segment contract.
        edition_slug=None
        if colliding and not exact:
            from urllib.parse import unquote
            edition=slugify(unquote(urlsplit(url).path.rstrip("/").split("/")[-1]
                                       .removesuffix(".html")))
            edition_slug=(edition if edition.startswith(work["slug"]+"-")
                          else work["slug"]+"-"+edition)
            existing_routes={
                x.get("route_slug",x["slug"])
                for key2,x in next_registry["stagings"].items()
                if x["venue_id"]==canonical_venue["id"]}
            if edition_slug in existing_routes:
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
                "slug":work["slug"],"source_url":url,
                "season":season_from_source(key,url,dates),
                **({"route_slug":edition_slug} if edition_slug else {})}
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

def promote_calendar(facts:dict,registry:dict,health:dict,*,today:date):
    """Automatically onboard date-only OperaLombardia stagings of known operas.

    Never infer composer if the same title maps to multiple canonical works.
    The calendar's exact venue and city must already be verified in Atlas.
    """
    next_facts=copy.deepcopy(facts)
    next_registry=copy.deepcopy(registry)
    accepted=0
    created=0
    skipped=[]
    from scripts.daily_ingest import CONFIG as DAILY_CONFIG, validate_source_config
    sources={x["key"]:x for x in validate_source_config(json.loads(
        DAILY_CONFIG.read_text(encoding="utf-8")))}
    source=sources.get("opera-lombardia-calendar-2026-27")
    if source is None or source["access_status"]!="approved":
        return next_facts,next_registry,{"new_stagings":0,"new_recite":0,"auto_skipped":[]}
    for scan in health.get("sources",[]):
        if scan.get("key")!="opera-lombardia-calendar-2026-27" or scan.get("outcome")!="review_required":
            continue
        for row in scan.get("candidates",[]):
            title,city,venue,day=(row.get(k) for k in ("title","city","venue","date"))
            if not all(isinstance(v,str) and v.strip() for v in (title,city,venue,day)):
                continue
            if row.get("time") is not None:continue
            try:date.fromisoformat(day)
            except ValueError:continue
            works=[w for w in next_registry["works"].values()
                   if normalized(w["title"])==normalized(title)]
            venue_key=city+"|"+venue
            canonical_venue=next_registry["venues"].get(venue_key)
            if len(works)!=1 or canonical_venue is None:
                skipped.append({"title":title,"city":city,"reason":"identity_requires_more_evidence"})
                continue
            work=works[0]
            collisions=[x for x in next_facts["productions"]
                        if x["municipality"]==city and x["venue"]==venue
                        and normalized(x["title"])==normalized(work["title"])
                        and normalized(x["composer"])==normalized(work["composer"])]
            exact=[x for x in collisions if x["source_url"]==source["url"]]
            if (len(exact)>1 or (collisions and not exact)):
                skipped.append({"title":title,"city":city,"reason":"venue_work_route_collision"})
                continue
            if exact:
                production=exact[0]
            else:
                key="auto-lombardia-"+hashlib.sha256(
                    (source["key"]+"|"+work["id"]+"|"+venue_key).encode()).hexdigest()[:16]
                if key in next_registry["stagings"]:continue
                production={"key":key,"title":work["title"],
                            "composer":work["composer"],"venue":venue,
                            "municipality":city,"region":canonical_venue["region"],
                            "source_url":source["url"],"dates":[]}
                next_registry["stagings"][key]={
                    "id":next_id(next_registry["stagings"],"oa-s-"),
                    "work_id":work["id"],"venue_id":canonical_venue["id"],
                    "slug":work["slug"],"source_url":source["url"],
                    "season":season_from_source(source["key"],source["url"],[day])}
                next_facts["productions"].append(production)
                created+=1
            if day in dict(production["dates"]):
                if dict(production["dates"])[day] is not None:
                    continue
                continue
            recita_key=production["key"]+"|"+day
            if recita_key in next_registry["performances"]:
                continue
            next_registry["performances"][recita_key]={
                "id":f"oa-r-{_next_replica_id(next_registry):06d}",
                "staging_id":next_registry["stagings"][production["key"]]["id"],
                "original_date":day,"source_url":source["url"]}
            production["dates"].append([day,None])
            production["dates"].sort(key=lambda x:x[0])
            accepted+=1
    if accepted:
        next_facts["reviewed_on"]=today.isoformat()
    return next_facts,next_registry,{"new_stagings":created,
                                     "new_recite":accepted,"auto_skipped":skipped}

def promote_new_works(facts:dict,registry:dict,evidence:dict,candidates:dict,
                      intelligence:dict,editorial:dict,approved_urls:list[str],*,
                      today:date, history:dict|None=None):
    """One unattended all-or-nothing work+history+staging+recita transaction."""
    next_facts=copy.deepcopy(facts)
    next_registry=copy.deepcopy(registry)
    next_editorial=copy.deepcopy(editorial)
    next_history=copy.deepcopy(history) if history is not None else None
    allowed=set(approved_urls)
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
             if x["access_status"]=="approved"}
    candidates_by_id={x["id"]:x for x in candidates.get("candidates",[])
                      if x.get("status")=="needs_review"}
    event_by_id={x["candidate_id"]:x for x in evidence.get("evidence",[])
                 if x.get("status")=="needs_editorial_review"}
    result={"new_works":0,"new_stagings":0,"new_recite":0,"auto_skipped":[]}
    if next_editorial.get("schema_version")!=1 or not isinstance(
            next_editorial.get("synopses"),dict):
        raise ValueError("invalid original editorial synopsis registry")
    for item in sorted(intelligence.get("works",[]),key=lambda x:x.get("candidate_id","")):
        cid=item.get("candidate_id")
        candidate=candidates_by_id.get(cid)
        detail=event_by_id.get(cid)
        if not candidate or not detail:continue
        source_key=item.get("source_key")
        url=item.get("source_url")
        source=sources.get(source_key)
        if (source_key not in VENUE_BY_SOURCE or source is None
            or not isinstance(url,str) or not eligible(source_key,url)
            or urlsplit(url).hostname!=urlsplit(source["official_url"]).hostname
            or candidate.get("official_url")!=url or candidate.get("source_key")!=source_key
            or detail.get("source_url")!=url or detail.get("source_key")!=source_key):
            continue
        title,composer,summary=(item.get(k) for k in ("title","composer","synopsis"))
        if not all(isinstance(x,str) and x.strip() for x in (title,composer,summary)):
            continue
        summary=summary.strip()
        if not 45<=len(summary)<=300:continue
        historical=item.get("history")
        if next_history is not None:
            from scripts.publish_work_editorial import validate_history
            if not validate_history(historical):
                result["auto_skipped"].append({"candidate_id":cid,"reason":"incomplete_historical_profile"})
                continue
        if not isinstance(item.get("wikidata_id"),str) or not __import__("re").fullmatch(
                r"Q[1-9][0-9]*",item["wikidata_id"]):continue
        work_key=normalized(title)+"|"+normalized(composer)
        slug=slugify(title)
        if (work_key in next_registry["works"] or
            any(x["slug"]==slug for x in next_registry["works"].values())):
            continue
        city,venue=VENUE_BY_SOURCE[source_key]
        venue_key=city+"|"+venue
        canonical_venue=next_registry["venues"].get(venue_key)
        if canonical_venue is None:continue
        rows=detail.get("event_facts",[])
        if not isinstance(rows,list) or not rows:continue
        date_rows={}
        invalid=False
        for row in rows:
            if (not isinstance(row,dict) or normalized(row.get("event_title",""))!=normalized(title)
                or normalized(row.get("composer",""))!=normalized(composer)
                or row.get("venue")!=venue):invalid=True;break
            try:
                local_day=date.fromisoformat(row["date"]).isoformat()
                stamp=__import__("datetime").datetime.fromisoformat(row["starts_at"])
                from zoneinfo import ZoneInfo
                if stamp.tzinfo is None or stamp.utcoffset() is None:raise ValueError
                local=stamp.astimezone(ZoneInfo("Europe/Rome"))
                if local.date().isoformat()!=local_day:raise ValueError
                hour=local.strftime("%H:%M")
                if local_day in date_rows and date_rows[local_day]!=hour:raise ValueError
                date_rows[local_day]=hour
            except (KeyError,TypeError,ValueError):invalid=True;break
        if invalid or not date_rows:continue
        # The canonical work route must remain unique; no title-based
        # overwrites and no guessing which composer an old URL identifies.
        staging_key="auto-"+hashlib.sha256((source_key+"|"+url).encode()).hexdigest()[:16]
        if staging_key in next_registry["stagings"]:continue
        work_id=next_id(next_registry["works"],"oa-w-")
        stage_id=next_id(next_registry["stagings"],"oa-s-")
        next_registry["works"][work_key]={
            "id":work_id,"slug":slug,"title":title,"composer":composer}
        next_editorial["synopses"][slug]=summary
        if next_history is not None:next_history["works"][slug]=historical
        next_registry["stagings"][staging_key]={
            "id":stage_id,"work_id":work_id,"venue_id":canonical_venue["id"],
            "slug":slug,"source_url":url,
            "season":season_from_source(source_key,url,date_rows)}
        next_facts["productions"].append({
            "key":staging_key,"title":title,"composer":composer,"venue":venue,
            "municipality":city,"region":canonical_venue["region"],
            "source_url":url,
            "dates":[[day,hour] for day,hour in sorted(date_rows.items())]})
        for day in sorted(date_rows):
            next_registry["performances"][staging_key+"|"+day]={
                "id":f"oa-r-{_next_replica_id(next_registry):06d}",
                "staging_id":stage_id,"original_date":day,"source_url":url}
        allowed.add(url)
        result["new_works"]+=1
        result["new_stagings"]+=1
        result["new_recite"]+=len(date_rows)
    if result["new_recite"]:next_facts["reviewed_on"]=today.isoformat()
    if next_history is not None:
        return next_facts,next_registry,sorted(allowed),next_editorial,next_history,result
    return next_facts,next_registry,sorted(allowed),next_editorial,result

def main():
    from datetime import date
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    evidence=json.loads(DETAILS.read_text(encoding="utf-8")) if DETAILS.exists() else {"evidence":[]}
    candidates=json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"candidates":[]}
    approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8")) if SOURCE_ALLOWLIST.exists() else {"schema_version":1,"urls":[]}
    next_facts,next_registry,urls,report=promote(
        facts,registry,evidence,candidates,approved["urls"],today=date.today())
    from scripts.daily_ingest import HEALTH as DAILY_HEALTH
    health=json.loads(DAILY_HEALTH.read_text(encoding="utf-8")) if DAILY_HEALTH.exists() else {"sources":[]}
    next_facts,next_registry,calendar=promote_calendar(
        next_facts,next_registry,health,today=date.today())
    report["new_stagings"]+=calendar["new_stagings"]
    report["new_recite"]+=calendar["new_recite"]
    report["auto_skipped"]+=calendar["auto_skipped"]
    from scripts.auto_work_research import OUT as RESEARCH
    from scripts.publish_work_editorial import EDITORIAL, build_editorial
    intelligence=(json.loads(RESEARCH.read_text(encoding="utf-8"))
                  if RESEARCH.exists() else {"schema_version":1,"works":[]})
    editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    from scripts.publish_work_editorial import HISTORY, validate_history
    historical=json.loads(HISTORY.read_text(encoding="utf-8"))
    next_facts,next_registry,urls,next_editorial,next_history,newworks=promote_new_works(
        next_facts,next_registry,evidence,candidates,intelligence,editorial,urls,
        today=date.today(),history=historical)
    report["new_works"]=newworks["new_works"]
    report["new_stagings"]+=newworks["new_stagings"]
    report["new_recite"]+=newworks["new_recite"]
    # Only write after the full canonical graph validates against the expanded
    # source allowlist; rollback-like behavior by pre-validating in memory.
    from scripts.build_verified_catalog import validate_auto_sources
    validate_auto_sources(urls)
    assemble(next_facts,next_registry,approved_extra=set(urls))
    build_editorial(next_facts,next_registry,next_editorial,approved_extra=set(urls),
                   history=next_history)
    if report["new_recite"]:
        _write_atomic(MANIFEST,next_facts)
        _write_atomic(REGISTRY,next_registry)
        _write_atomic(SOURCE_ALLOWLIST,{"schema_version":1,"urls":urls})
        if report["new_works"]:
            _write_atomic(EDITORIAL,next_editorial)
            _write_atomic(HISTORY,next_history)
    _write_atomic(HEALTH,{"schema_version":1,**report})
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
