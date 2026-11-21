"""Publish one source-verified ticket per multi-work program date.

Independent, immutable public companion feed. Existing v2 opera IDs and
performance counts remain untouched. No scraping, guessing or paid services.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from opera_atlas.programs import program_from_evidence
from scripts.auto_catalogue import VENUE_BY_SOURCE
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.discover_season_indexes import CONFIG,OUTPUT as CANDIDATES,validate_config,eligible
from scripts.publish_catalog_v2 import REGISTRY,ROOT,payload
from scripts.daily_ingest import _write_atomic

OUTPUT=ROOT/"public"/"catalog"/"programs.json"

def assemble_programs(candidates:dict,evidence:dict,registry:dict,
                      facts:dict,config:list[dict])->dict:
    approved={s["key"]:s for s in validate_config(config)
              if s["access_status"]=="approved"}
    candidates_by_id={c["id"]:c for c in candidates["candidates"]
                      if c.get("status")=="needs_review"}
    program_ids=set()
    performances=set()
    items=[]
    for item in sorted(evidence.get("evidence",[]),key=lambda x:x.get("candidate_id","")):
        if item.get("status")!="needs_program_review" or not item.get("program_heading"):
            continue
        key=item.get("source_key")
        source=approved.get(key)
        candidate=candidates_by_id.get(item.get("candidate_id"))
        url=item.get("source_url")
        if (not source or not candidate or key not in VENUE_BY_SOURCE
            or item.get("program_heading_source_url")!=url
            or not isinstance(url,str) or not eligible(key,url)
            or urlsplit(url).hostname!=urlsplit(source["official_url"]).hostname):
            raise ValueError("unverified source or heading for composite program")
        city,venue=VENUE_BY_SOURCE[key]
        # The venue is independently canonical and must not be invented.
        venue_entries=[x for x in registry["venues"].values()
                       if x.get("name")==venue and x.get("city")==city]
        # Resolve by canonical venue record, allowing legacy field names.
        if len(venue_entries)!=1:
            venue_entries=[x for x in registry["venues"].values()
                           if x.get("slug")==__import__("scripts.publish_catalog_v2",fromlist=["slugify"]).slugify(venue)
                           and x.get("city_slug")==__import__("scripts.publish_catalog_v2",fromlist=["slugify"]).slugify(city)]
        if len(venue_entries)!=1:raise ValueError("ambiguous or unknown program theatre")
        place=venue_entries[0]
        program=program_from_evidence(
            heading=item["program_heading"],source_key=key,source_url=url,
            candidate=candidate,detail=item,registry=registry,
            venue=venue,city=city,region=place["region"])
        if program["id"] in program_ids:raise ValueError("duplicate program identity")
        program_ids.add(program["id"])
        for date in program["performances"]:
            if date["id"] in performances:raise ValueError("duplicated program recita")
            performances.add(date["id"])
            if any(p["source_url"]==url and
                   date["local_date"] in {day for day,_ in p["dates"]}
                   for p in facts["productions"]):
                raise ValueError("composite program already published as solo work")
        items.append(program)
    return {"schema_version":1,"programs":items}

def publish(*,check:bool=False)->dict:
    read=lambda path:json.loads(path.read_text(encoding="utf-8"))
    result=assemble_programs(read(CANDIDATES),read(EVIDENCE),
                             read(REGISTRY),read(MANIFEST),read(CONFIG))
    if check:
        if not OUTPUT.exists() or OUTPUT.read_bytes()!=payload(result):
            raise ValueError("public program feed differs from verified source facts")
    else:
        _write_atomic(OUTPUT,result)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=publish(check=args.check)
    print(json.dumps({"published_programs":len(result["programs"]),
        "program_recite":sum(len(x["performances"]) for x in result["programs"])}))

if __name__=="__main__":
    main()
