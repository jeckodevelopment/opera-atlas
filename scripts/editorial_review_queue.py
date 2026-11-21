"""Deterministic, no-cost editorial queue for Opera Atlas work cards.

Never touches canonical cards. A separate chat/GitHub PR can improve a
flagged card only after validating title, composer and cited plot facts.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from scripts.publish_catalog_v2 import ROOT, payload
from scripts.publish_work_editorial import OUTPUT as EDITORIAL, validate_history

OUTPUT = ROOT / "data" / "editorial-review-queue.json"
TEMPLATE_SUFFIX = "Consulta le rappresentazioni verificate in programma nei teatri italiani."
MAX_QUEUE = 5000


def evaluate(catalog: dict) -> dict:
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("works"), list):
        raise ValueError("invalid work editorial feed")
    queue = []
    seen = set()
    for work in catalog["works"]:
        identity = work.get("work_id")
        if not isinstance(identity, str) or identity in seen:
            raise ValueError("invalid or duplicated work identity")
        seen.add(identity)
        title, composer, synopsis = (
            work.get("title"), work.get("composer"), work.get("synopsis"))
        if not all(isinstance(x, str) and x.strip() for x in (title, composer, synopsis)):
            raise ValueError("incomplete work editorial fields")
        reasons = []
        if synopsis.strip().endswith(TEMPLATE_SUFFIX):
            reasons.append("identity_only_introduction")
        if work.get("history") is None:
            reasons.append("historical_facts_missing")
        elif not validate_history(work["history"]):
            raise ValueError("invalid existing historical claims")
        if reasons:
            queue.append({
                "work_id": identity,
                "title": title,
                "composer": composer,
                "route_slug": work.get("route_slug", work.get("slug")),
                "reasons": reasons,
                "priority": "high" if "identity_only_introduction" in reasons else "normal",
                "current_synopsis": synopsis.strip(),
                "existing_history_sources": (
                    work["history"].get("sources",[]) if work.get("history") else []),
            })
    if len(queue) > MAX_QUEUE:
        raise ValueError("editorial review queue exceeds safety limit")
    queue.sort(key=lambda x: (x["priority"] != "high", x["title"].casefold(),
                               x["composer"].casefold(), x["work_id"]))
    return {
        "schema_version": 1,
        "purpose": "optional_editorial_improvement",
        "works": queue,
        "count": len(queue),
        "identity_only_count": sum("identity_only_introduction" in x["reasons"] for x in queue),
        "missing_history_count": sum("historical_facts_missing" in x["reasons"] for x in queue),
    }


def generate(*,check:bool=False)->dict:
    catalog=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    result=evaluate(catalog)
    encoded=payload(result)
    if check:
        if not OUTPUT.exists() or OUTPUT.read_bytes()!=encoded:
            raise ValueError("editorial queue snapshot differs from catalog")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_bytes(encoded)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=generate(check=args.check)
    print(json.dumps({key:result[key] for key in
          ("count","identity_only_count","missing_history_count")}))


if __name__=="__main__":
    main()
