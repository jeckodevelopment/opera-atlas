"""Reviewed touring productions: one owner/identity, actual location per show."""
from __future__ import annotations
import copy
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

SOURCE=Path(__file__).resolve().parents[1]/"data/reviewed-itinerant-productions.json"

def _url(raw):
    if not isinstance(raw,str):return False
    p=urlsplit(raw)
    return (p.scheme=="https" and bool(p.hostname) and p.port is None
            and not any((p.username,p.password,p.query,p.fragment)))

def reviewed():
    doc=json.loads(SOURCE.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("productions"),list):
        raise ValueError("invalid reviewed touring registry")
    result={}
    for entry in doc["productions"]:
        p=entry["production"]
        if (p["key"] in result or p.get("performance_format")!="itinerante"
            or not all(isinstance(p.get(k),str) and p[k].strip()
                       for k in ("project_name","title","composer","venue","municipality","region"))
            or not _url(p.get("source_url"))):
            raise ValueError("invalid reviewed touring identity")
        days=[d for d,_ in p["dates"]]
        locations=p.get("performance_locations")
        if (not days or len(days)!=len(set(days)) or not isinstance(locations,dict)
            or set(days)!=set(locations)):
            raise ValueError("one verified location required for each touring date")
        for day,loc in locations.items():
            if (date.fromisoformat(day).isoformat()!=day
                or set(loc)!={"venue","municipality","region","source_url"}
                or not all(isinstance(loc[k],str) and loc[k].strip()
                           for k in ("venue","municipality","region"))
                or not _url(loc["source_url"])
                or urlsplit(loc["source_url"]).hostname!=urlsplit(p["source_url"]).hostname):
                raise ValueError("invalid touring location or provenance")
        result[p["key"]]=entry
    return result

def approved_urls(entries):
    return {u for e in entries.values() for p in [e["production"]]
            for u in [p["source_url"],*(x["source_url"] for x in p["performance_locations"].values())]}

def validate_production(p,entries):
    """The reviewed dataset is the authority, not a city or title guess."""
    entry=entries.get(p.get("key"))
    if entry:
        if p!=entry["production"]:
            raise ValueError("touring production differs from reviewed facts")
    elif ("project_name" in p or "performance_locations" in p
          or p.get("source_url") in approved_urls(entries)):
        raise ValueError("unreviewed touring production")

def promote(facts,registry,*,today,allocate):
    from scripts.publish_catalog_v2 import normalized
    from scripts.build_verified_catalog import replica_registry_key
    f,r=copy.deepcopy(facts),copy.deepcopy(registry)
    added=recite=0
    for key,entry in reviewed().items():
        p=entry["production"]
        existing=[x for x in f["productions"] if x["key"]==key]
        if existing:
            validate_production(existing[0],{key:entry})
            if len(existing)!=1:raise ValueError("duplicate touring production")
            continue
        if key in r["stagings"]:raise ValueError("touring identity collision")
        w=r["works"][normalized(p["title"])+"|"+normalized(p["composer"])]
        v=r["venues"][p["municipality"]+"|"+p["venue"]]
        if any(s["venue_id"]==v["id"] and s.get("route_slug",s["slug"])==entry["route_slug"]
               for s in r["stagings"].values()):
            raise ValueError("touring route collision")
        sid=allocate(r["stagings"],"oa-s-")
        r["stagings"][key]={"id":sid,"work_id":w["id"],"venue_id":v["id"],
            "slug":w["slug"],"route_slug":entry["route_slug"],"season":entry["season"],
            "source_url":p["source_url"],
            "supporting_source_urls":sorted({x["source_url"] for x in p["performance_locations"].values()})}
        for day,hour in p["dates"]:
            rk=replica_registry_key(p,day,hour)
            if rk in r["performances"]:raise ValueError("touring performance identity collision")
            r["performances"][rk]={"id":allocate(r["performances"],"oa-r-"),
                "staging_id":sid,"original_date":day,"source_url":p["source_url"]}
            recite+=1
        f["productions"].append(copy.deepcopy(p))
        added+=1
    if added:f["reviewed_on"]=today.isoformat()
    return f,r,added,recite
