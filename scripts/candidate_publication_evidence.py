"""Conservative candidate-to-public-catalog evidence cross-check.

Exact source URLs connect candidates to versioned canonical works, solo stagings
and scheduled recite records. A matching URL with more than one staging is
ambiguous rather than proof of one candidate's publication. This measures the
GitHub catalog release, NOT availability at opera.plus/atlas.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.publish_catalog_v2 import ROOT, payload

AUTOMATION = ROOT / "public/catalog/source-automation.json"
CANDIDATES = ROOT / "data/season-index-candidates.json"
CATALOG = ROOT / "public/catalog/v2"
PROGRAMS = ROOT / "public/catalog/programs.json"
OUTPUT = ROOT / "public/catalog/candidate-publication-evidence.json"


def evidence(automation: dict, candidates: dict, manifest: dict,
             works: dict, stagings: dict, performances: dict,
             programs: dict) -> dict:
    if manifest.get("schema_version") != 2 or candidates.get("schema_version") != 1:
        raise ValueError("unsupported catalog or candidate schema")
    owner = defaultdict(set)
    for venue in automation.get("venues", []):
        for source in venue.get("sources", []):
            if source.get("configured"):
                owner[source["source_key"]].add(venue["venue_id"])
    works_by_id = {x["id"]: x for x in works.get("works", [])}
    st_by_id = {x["id"]: x for x in stagings.get("stagings", [])}
    performances_by_staging = defaultdict(list)
    for item in performances.get("performances", []):
        performances_by_staging[item["staging_id"]].append(item["id"])
    by_url = defaultdict(list)
    for staging in st_by_id.values():
        by_url[staging["source_url"]].append(staging)
    programs_by_url = defaultdict(list)
    for program in programs.get("programs", []):
        programs_by_url[program["source_url"]].append(program)
    rows = []
    for candidate in candidates.get("candidates", []):
        state = candidate.get("status")
        source_url = candidate.get("official_url")
        targets = owner.get(candidate.get("source_key"), set())
        linked = by_url.get(source_url, [])
        composed = programs_by_url.get(source_url, [])
        result = "not_applicable"
        evidence_links = []
        if state == "already_catalogued":
            if len(linked) == 1 and not composed:
                staging = linked[0]
                work = works_by_id.get(staging.get("work_id"))
                recite_ids = performances_by_staging.get(staging["id"], [])
                if work and recite_ids:
                    result = "linked_solo_in_repository"
                    evidence_links = [{
                        "work_id": work["id"], "staging_id": staging["id"],
                        "performance_count": len(recite_ids),
                        "staging_route": staging.get("url"),
                    }]
                else:
                    result = "incomplete_repository_link"
            elif len(composed) == 1 and not linked:
                program = composed[0]
                components = program.get("components", [])
                recites = program.get("performances", [])
                if components and all(x.get("work_id") in works_by_id for x in components) and recites:
                    result = "linked_program_in_repository"
                    evidence_links = [{
                        "program_id": program["id"],
                        "work_ids": sorted({x["work_id"] for x in components}),
                        "performance_count": len(recites),
                    }]
                else:
                    result = "incomplete_repository_link"
            elif len(linked) > 1 or len(composed) > 1 or (linked and composed):
                result = "ambiguous_source_url"
            else:
                result = "no_direct_repository_link"
        rows.append({
            "candidate_id": candidate["id"],
            "source_key": candidate.get("source_key"),
            "official_url": source_url,
            "candidate_status": state,
            "venue_id": next(iter(targets)) if len(targets) == 1 else None,
            "evidence_status": result,
            "catalog_evidence": evidence_links,
        })
    counts = Counter(x["evidence_status"] for x in rows)
    return {
        "schema_version": 1,
        "catalog_release_sha256": manifest["files"]["stagings"]["sha256"],
        "scope": "repository_catalog_evidence_not_live_web_verification",
        "definition": "Direct verified URL link to versioned catalog work/staging/recite or program; ambiguous and indirect source matches are unproven, not publication failures.",
        "totals": dict(sorted(counts.items())),
        "candidates": rows,
    }


def publish(check: bool = False) -> dict:
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))
    manifest = load(CATALOG / "manifest.json")
    names = {k: CATALOG / v["path"] for k, v in manifest["files"].items()}
    result = evidence(
        load(AUTOMATION), load(CANDIDATES), manifest,
        load(names["works"]), load(names["stagings"]),
        load(names["performances"]), load(PROGRAMS),
    )
    encoded = payload(result)
    if check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != encoded:
            raise ValueError("candidate publication evidence out of sync")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    result = publish(check=options.check)
    print(json.dumps(result["totals"]))


if __name__ == "__main__":
    main()
