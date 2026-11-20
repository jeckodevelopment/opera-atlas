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
OUTPUT = ROOT / "public" / "catalog" / "work-editorial.json"


def build_editorial(facts: dict, registry: dict, editorial: dict, *,
                    approved_extra: set[str] | None = None) -> dict:
    if (editorial.get("schema_version") != 1 or editorial.get("language") != "it"
            or not isinstance(editorial.get("synopses"), dict)):
        raise ValueError("invalid editorial work source")
    works = assemble(facts, registry, approved_extra=approved_extra)["works"]
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
        entries.append({"work_id":work["id"], "slug":work["slug"],
                        "title":work["title"],"composer":work["composer"],
                        "synopsis":summary.strip()})
    return {"schema_version":1,"language":"it",
            "works":sorted(entries,key=lambda v:v["work_id"])}


def publish(check: bool=False) -> dict:
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    result=build_editorial(facts,registry,editorial)
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
