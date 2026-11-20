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
    works = assemble(facts, registry, approved_extra=approved_extra)["works"]
    if history is None:history=json.loads(HISTORY.read_text(encoding="utf-8"))
    if history.get("schema_version")!=1 or not isinstance(history.get("works"),dict):
        raise ValueError("invalid historical work registry")
    expected = {w["slug"] for w in works}
    provided = set(editorial["synopses"])
    if not expected.issubset(provided):
        raise ValueError("missing verified work synopsis: " +
                         ", ".join(sorted(expected - provided)))
    entries = []
    for work in works:
        summary = editorial["synopses"][work["slug"]]
        if not isinstance(summary, str) or not 35 <= len(summary.strip()) <= 300:
            raise ValueError("invalid short synopsis: " + work["slug"])
        historical=history["works"].get(work["slug"])
        if not validate_history(historical):
            raise ValueError("missing complete sourced work history: "+work["slug"])
        entries.append({"work_id":work["id"], "slug":work["slug"],
                        "title":work["title"],"composer":work["composer"],
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
