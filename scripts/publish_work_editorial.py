"""Publish brief verified work cards independently from static SFTP pages.

A new canonical work may not go live without a checked editorial synopsis.
Editorial facts are original brief descriptions, not scraped production copy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from scripts.publish_catalog_v2 import ROOT, REGISTRY, MANIFEST, assemble, payload, slugify

EDITORIAL = ROOT / "site" / "work-synopses.json"
HISTORY = ROOT / "site" / "work-history.json"
OUTPUT = ROOT / "public" / "catalog" / "work-editorial.json"


def validate_history(entry: object) -> bool:
    """Fail closed if a new opera lacks sourced historic facts."""
    if not isinstance(entry, dict):return False
    for field in ("librettist","premiere_venue","premiere_city"):
        if not isinstance(entry.get(field),str) or not 3 <= len(entry[field].strip()) <= 180:
            return False
    year=entry.get("premiere_year")
    if type(year) is not int or not 1600 <= year <= 2100:return False
    composition=entry.get("composition_year")
    if composition is not None and (type(composition) is not int or
                                    not 1500 <= composition <= year):
        return False
    sources=entry.get("sources")
    return isinstance(sources,list) and bool(sources) and all(
        isinstance(url,str) and url.startswith("https://") and len(url)<=500
        for url in sources)


def build_editorial(facts: dict, registry: dict, editorial: dict, *,
                    approved_extra: set[str] | None = None,
                    history: dict | None = None) -> dict:
    if (editorial.get("schema_version") != 1 or editorial.get("language") != "it"
            or not isinstance(editorial.get("synopses"), dict)):
        raise ValueError("invalid editorial work source")
    graph = assemble(facts, registry, approved_extra=approved_extra)
    works = graph["works"]
    if history is None:history=json.loads(HISTORY.read_text(encoding="utf-8"))
    if history.get("schema_version")!=1 or not isinstance(history.get("works"),dict):
        raise ValueError("invalid historical work registry")
    reserved_ids={x["id"] for x in registry.get("reserved_works",{}).values()}
    expected = {w["slug"] for w in works if w["id"] not in reserved_ids}
    provided = set(editorial["synopses"])
    if not expected.issubset(provided):
        raise ValueError("missing verified work synopsis: " +
                         ", ".join(sorted(expected - provided)))
    same_slug={}
    for w in works:
        same_slug.setdefault(w["slug"], []).append(w["id"])
    synopses_by_id=editorial.get("synopses_by_id",{})
    history_by_id=history.get("works_by_id",{})
    if not isinstance(synopses_by_id,dict) or not isinstance(history_by_id,dict):
        raise ValueError("work-specific editorial data must be dictionaries")
    entries = []
    for work in works:
        if work["id"] in reserved_ids:
            continue
        summary = synopses_by_id.get(work["id"], editorial["synopses"][work["slug"]])
        if len(same_slug[work["slug"]])>1 and work["id"] not in synopses_by_id:
            raise ValueError("ambiguous synopsis needs work ID: "+work["id"])
        if not isinstance(summary, str) or not 35 <= len(summary.strip()) <= 300:
            raise ValueError("invalid short synopsis: " + work["slug"])
        # A generic identity sentence is not a synopsis. The catalogue
        # is a theatre guide, but each published work needs a concise plot.
        if summary.strip().endswith(
                "Consulta le rappresentazioni verificate in programma nei teatri italiani."):
            raise ValueError("identity-only text is not a plot synopsis: " + work["id"])
        historical=history_by_id.get(work["id"],history["works"].get(work["slug"]))
        official_url=work.get("authority_url")
        # Source-agnostic verified first-party identity. A source must be
        # officially approved, its production URL eligible, and a canonical
        # staging for this very work must point to that exact document.
        from urllib.parse import urlsplit
        from scripts.discover_season_indexes import CONFIG,validate_config,eligible
        configured={x["key"]:x for x in validate_config(json.loads(
            CONFIG.read_text(encoding="utf-8")))
            if x["access_status"]=="approved"}
        has_first_party_authority=(
            isinstance(official_url,str) and
            any(eligible(key,official_url)
                and urlsplit(source["official_url"]).hostname==urlsplit(official_url).hostname
                for key,source in configured.items()) and
            any(stage["work_id"]==work["id"] and stage["source_url"]==official_url
                for stage in graph["stagings"]))
        has_verified_authority=(
            (isinstance(work.get("wikidata_id"),str)
             and bool(__import__("re").fullmatch(
                r"Q[1-9][0-9]*",work["wikidata_id"])))
            or has_first_party_authority)
        if len(same_slug[work["slug"]])>1 and work["id"] not in history_by_id:
            if not has_verified_authority:
                raise ValueError("ambiguous history needs work ID: "+work["id"])
            historical=None
        if not validate_history(historical):
            # Verified work identity is necessary, but never a substitute for
            # a documented libretto and premiere in a public editorial card.
            raise ValueError("missing complete sourced work history: "+work["slug"])
        entries.append({"work_id":work["id"], "slug":work["slug"],
                        "title":work["title"],"composer":work["composer"],
                        "route_slug":work.get("route_slug",work["slug"]),
                        "synopsis":summary.strip(),"history":historical})
    # Program-only works receive complete cards from the reviewed profile
    # registry; their absence from solo productions must not hide the opera.
    reviewed=json.loads((ROOT/"data"/"reviewed-program-work-editorials.json").read_text(encoding="utf-8"))
    profiles={(x["title"].casefold(),x["composer"].casefold()):x for x in reviewed["works"]}
    for work in works:
        if work["id"] not in reserved_ids:
            continue
        profile=profiles.get((work["title"].casefold(),work["composer"].casefold()))
        if not profile or not validate_history(profile.get("history")):
            raise ValueError("missing complete sourced work history: "+work["slug"])
        summary=profile.get("synopsis")
        if not isinstance(summary,str) or not 35<=len(summary.strip())<=300:
            raise ValueError("invalid short synopsis: "+work["slug"])
        entries.append({"work_id":work["id"],"slug":work["slug"],
                        "title":work["title"],"composer":work["composer"],
                        "route_slug":work.get("route_slug",work["slug"]),
                        "synopsis":summary.strip(),"history":profile["history"]})
    return {"schema_version":1,"language":"it",
            "works":sorted(entries,key=lambda v:v["work_id"])}


def publish(check: bool=False) -> dict:
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    history=json.loads(HISTORY.read_text(encoding="utf-8"))
    result=build_editorial(facts,registry,editorial,history=history)
    data=payload(result)
    if check:
        if not OUTPUT.exists() or OUTPUT.read_bytes()!=data:
            raise ValueError("public work editorial feed differs from verified catalog")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_bytes(data)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=publish(check=args.check)
    print(json.dumps({"published_work_cards":len(result["works"])}))


if __name__=="__main__":
    main()
