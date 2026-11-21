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
    expected = {w["slug"] for w in works}
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
        summary = synopses_by_id.get(work["id"], editorial["synopses"][work["slug"]])
        if len(same_slug[work["slug"]])>1 and work["id"] not in synopses_by_id:
            raise ValueError("ambiguous synopsis needs work ID: "+work["id"])
        if not isinstance(summary, str) or not 35 <= len(summary.strip()) <= 300:
            raise ValueError("invalid short synopsis: " + work["slug"])
        historical=history_by_id.get(work["id"],history["works"].get(work["slug"]))
        official_url=work.get("authority_url")
        has_first_party_authority=(
            isinstance(official_url,str) and
            bool(__import__("re").fullmatch(
                r"https://www\\.tcbo\\.it/evento/opera/[a-z0-9-]+-20\\d{2}/",
                official_url)) and
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
        if historical is None and has_verified_authority:
            # A verifiable opera identity is enough for an Atlas listing.
            # Missing archival facts must stay absent, never fabricated.
            pass
        elif not validate_history(historical):
            raise ValueError("missing complete sourced work history: "+work["slug"])
        entries.append({"work_id":work["id"], "slug":work["slug"],
                        "title":work["title"],"composer":work["composer"],
                        "route_slug":work.get("route_slug",work["slug"]),
                        "synopsis":summary.strip(),"history":historical})
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
