"""Evidence-driven opera identity review queue for Atlas diagnostics.

Reports unmatched official candidate work credits without changing catalog IDs,
creating aliases, or promoting performances. Safe on every workflow refresh.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from opera_atlas.work_identity import resolve_work, canonical_title
from scripts.publish_catalog_v2 import ROOT

EVIDENCE = ROOT / "data" / "candidate-detail-evidence.json"
REGISTRY = ROOT / "data" / "identity-registry.json"
OUTPUT = ROOT / "public" / "catalog" / "work-identity-review.json"
MAX_GROUPS = 500

def _clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""

def _safe_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    u = urlsplit(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return None
    return value

def _review_credit_hint(title: str, composer: str, works: list[dict]) -> dict | None:
    """Suggest a verified canonical record for obvious appended metadata.

    This is only diagnostic: never alter incoming composer/title or silently
    promote a performance based on a stripped suffix.
    """
    for work in works:
        if canonical_title(title, work["composer"]).casefold() != work["title"].casefold():
            continue
        original = work["composer"]
        if not composer.casefold().startswith(original.casefold() + " "):
            continue
        extra = composer[len(original):].strip()
        if not (re.fullmatch(r"(?:Opera|Tragedia|Melodramma)", extra, re.I)
                or re.fullmatch(r"\\(\\d{4}[–-]\\d{4}\\)", extra)):
            continue
        return {"work_id": work["id"], "title":work["title"],
                "composer":original, "reason":"metadata_after_composer"}
    return None


def evaluate(evidence: dict, registry: dict) -> dict:
    if evidence.get("schema_version") != 1 or not isinstance(evidence.get("evidence"), list):
        raise ValueError("invalid candidate evidence document")
    if registry.get("schema_version") != 1 or not isinstance(registry.get("works"), dict):
        raise ValueError("invalid canonical work registry")
    works = list(registry["works"].values())
    by_composer = {}
    for work in works:
        by_composer.setdefault(_clean(work.get("composer")).casefold(), []).append(work)
    groups: dict[tuple[str,str,str],dict] = {}
    candidate_count = 0
    fact_count = 0
    resolved_count = 0
    alias_count = 0
    no_facts = 0
    for candidate in evidence["evidence"]:
        if not isinstance(candidate, dict):
            raise ValueError("invalid evidence entry")
        if candidate.get("status") not in ("needs_editorial_review", "needs_program_review"):
            continue
        candidate_count += 1
        facts = candidate.get("event_facts") or []
        if not facts:
            no_facts += 1
            continue
        observed = set()
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            title, composer = _clean(fact.get("event_title")), _clean(fact.get("composer"))
            if not title:
                continue
            fact_count += 1
            match = resolve_work(registry, title, composer) if composer else None
            if match is not None:
                resolved_count += 1
                if canonical_title(title, composer) != title:
                    alias_count += 1
                continue
            category = ("missing_composer" if not composer else
                        "new_work_candidate" if composer.casefold() in by_composer else
                        "composer_credit_to_review")
            # A previously reviewed canonical title with a different credit
            # is NOT auto-corrected: it may be an homonym or bad source parser.
            candidates = by_composer.get(composer.casefold(), [])
            suggestion = [
                {"work_id":w["id"],"title":w["title"]}
                for w in candidates
                if w["title"].casefold() == title.casefold()
            ]
            hint = _review_credit_hint(title, composer, works) if composer else None
            key = (title.casefold(),composer.casefold(),category)
            if key not in groups:
                groups[key] = {"title":title,"composer":composer or None,"category":category,
                               "recite_observed":0,"sources":[],"candidate_ids":[],
                               "exact_title_matches":suggestion,
                               "possible_canonical_match":hint}
            entry = groups[key]
            entry["recite_observed"] += 1
            source = {"source_key":_clean(candidate.get("source_key")),
                      "url":_safe_url(candidate.get("source_url"))}
            if source not in entry["sources"] and len(entry["sources"]) < 12:
                entry["sources"].append(source)
            candidate_id = _clean(candidate.get("candidate_id"))
            if candidate_id and candidate_id not in entry["candidate_ids"] and len(entry["candidate_ids"]) < 40:
                entry["candidate_ids"].append(candidate_id)
            observed.add(key)
    values = sorted(groups.values(), key=lambda e:(-len(e["candidate_ids"]),-e["recite_observed"],
                                                    e["title"].casefold(),e["composer"] or ""))
    result = {
        "schema_version":1,
        "source":"candidate-detail-evidence",
        "checked_at":max((e.get("checked_at") or "" for e in evidence["evidence"]
                          if isinstance(e,dict)),default="") or None,
        "totals":{"candidates_checked":candidate_count,"candidates_without_facts":no_facts,
                  "facts_examined":fact_count,"facts_resolved":resolved_count,
                  "translated_facts_resolved":alias_count,
                  "unmatched_groups":len(values),
                  "unmatched_facts":sum(x["recite_observed"] for x in values)},
        "groups":values[:MAX_GROUPS],
        "truncated":len(values)>MAX_GROUPS,
        "note":"Identità da verificare: nessuna associazione o pubblicazione automatica."
    }
    return result

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    report=evaluate(json.loads(EVIDENCE.read_text(encoding="utf-8")),
                    json.loads(REGISTRY.read_text(encoding="utf-8")))
    expected=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("work-identity-review snapshot out of date")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(expected,encoding="utf-8")

if __name__=="__main__":
    main()
