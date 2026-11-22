"""Promote reviewed San Carlo cross-source evidence into the canonical candidate gate.

This does not publish directly. An original San Carlo press release, exact
official production link, and ALL the same dated clocks on two external
publishers are mandatory. An incomplete or conflicting production stays in
review as a whole; existing first-party facts always win.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from opera_atlas.napoli_san_carlo import eligible_detail
from scripts.build_verified_catalog import official_local_time
from scripts.corroborate_san_carlo_secondary import SOURCE as SECOND, key_of
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import OUTPUT as CANDIDATES, PUBLIC as PUBLIC_CANDIDATES
from scripts.collect_candidate_details import OUTPUT as DETAILS, PUBLIC as PUBLIC_DETAILS
from scripts.publish_catalog_v2 import ROOT

SOURCE_KEY = "napoli-san-carlo-rolling-opera"
FIRST = "https://www.classicalive.it/it/rassegne/teatro-di-san-carlo/stagione-dopera-2026-2027/"
OFFICIAL_PRESS_RELEASE = (
    "https://www.unina.it/documents/d/guest/stagione-teatro-san-carlo-2026-2027_c-pdf"
)
CHECKPOINT = ROOT / "data/san-carlo-secondary-candidates.json"
CORROBORATION = ROOT / "data/san-carlo-secondary-corroboration.json"
HEALTH = ROOT / "data/san-carlo-canonical-review-health.json"

# The original 2026/27 San Carlo press release confirms repertoire
# and the respective composers; this is an explicit edition-specific
# editorial attestation, NOT a recurring guess or official clock source.
APPROVED_REPERTOIRE = {
    "Luisa Miller": "Giuseppe Verdi",
    "Madama Butterfly": "Giacomo Puccini",
    "Aida": "Giuseppe Verdi",
    "Pagliacci": "Ruggero Leoncavallo",
    "Otto mesi in due ore o sia Gli esiliati in Siberia": "Gaetano Donizetti",
    "Nina o sia La pazza per amore": "Giovanni Paisiello",
    "Peter Grimes": "Benjamin Britten",
    "Il barbiere di Siviglia": "Gioacchino Rossini",
    "La damnation de Faust": "Hector Berlioz",
    "La chute de la maison Usher": "Claude Debussy / Alessandro Solbiati",
}
REPERTOIRE = {key_of(k): key_of(v) for k, v in APPROVED_REPERTOIRE.items()}


def apply(checkpoint: dict, comparison: dict, candidates: dict,
          details: dict, *, checked_at: str):
    if (checkpoint.get("schema_version") != 1
        or checkpoint.get("source_key") != SOURCE_KEY
        or checkpoint.get("source_role") != "secondary_unverified"
        or checkpoint.get("source_url") != FIRST
        or not isinstance(checkpoint.get("productions"), list)
        or not checkpoint["productions"]):
        raise ValueError("invalid first publisher checkpoint")
    if (comparison.get("schema_version") != 1
        or comparison.get("source_key") != SOURCE_KEY
        or comparison.get("first_source") != FIRST
        or comparison.get("second_source") != SECOND
        or comparison.get("source_independence") !=
           "two_secondary_publishers_not_primary_official_evidence"
        or comparison.get("canonical_publication_authorized") is not False
        or not isinstance(comparison.get("productions"), list)):
        raise ValueError("untrusted second publisher comparison")
    if (candidates.get("schema_version") != 1
        or details.get("schema_version") != 1):
        raise ValueError("invalid canonical registries")
    canonical = {r["id"]: dict(r) for r in candidates["candidates"]}
    evidence = {r["candidate_id"]: dict(r) for r in details["evidence"]}
    reviewed = {key_of(x["title"]): x for x in comparison["productions"]}
    if len(reviewed) != len(comparison["productions"]):
        raise ValueError("duplicate reviewed production")
    if len(reviewed) != len(checkpoint["productions"]):
        raise ValueError("cross-publisher production mismatch")
    outcomes = []
    seen_routes = set()
    for p in checkpoint["productions"]:
        title, composer = p["title"], p["composer"]
        identity = key_of(title)
        route = p.get("official_event_url")
        if (identity not in REPERTOIRE
            or REPERTOIRE[identity] != key_of(composer)
            or p.get("venue") != "Teatro di San Carlo"
            or p.get("city") != "Napoli"
            or p.get("secondary_source") != FIRST
            or p.get("corroboration_status") !=
               "pending_independent_event_verification"
            or not isinstance(route, str) or not eligible_detail(route)
            or route in seen_routes):
            raise ValueError("untrusted repertoire, source or official event identity")
        seen_routes.add(route)
        result = reviewed.get(identity)
        if not result or result.get("composer") != composer:
            raise ValueError("independent counterpart identity changed")
        dates = p["performances"]
        matching = result.get("confirmed_matching_clocks", [])
        conflicting = result.get("conflicting_clocks", [])
        missing = result.get("unmatched_clocks", [])
        if (not isinstance(dates, list)
            or not all(isinstance(r, dict) and set(r) == {"date", "time"} for r in dates)
            or not isinstance(matching, list)
            or not isinstance(conflicting, list) or not isinstance(missing, list)
            or len({(r["date"], r["time"]) for r in dates}) != len(dates)):
            raise ValueError("malformed cross-source recite evidence")
        expected = {(x["date"], x["time"]) for x in dates}
        confirmed = {(x["date"], x["time"]) for x in matching}
        if not confirmed.issubset(expected):
            raise ValueError("independent source claims unobserved recite")
        if len(confirmed) + len(conflicting) + len(missing) != len(dates):
            raise ValueError("inconsistent cross-source comparison totals")
        if (not expected or expected != confirmed
            or conflicting or missing
            or result.get("candidate_count") != len(dates)
            or result.get("status") != "all_clocks_match_second_source"):
            outcomes.append({"title": title, "status": "recite_conflict_or_incomplete",
                             "matching": len(matching), "expected": len(dates)})
            continue
        candidate_id = "oa-index-" + hashlib.sha256(
            (SOURCE_KEY + "|" + route).encode()
        ).hexdigest()[:20]
        prior = canonical.get(candidate_id)
        if prior and (prior.get("source_key") != SOURCE_KEY
                      or prior.get("official_url") != route):
            raise ValueError("canonical candidate ID collision")
        if prior and prior.get("status") != "needs_review":
            outcomes.append({"title": title, "status": "already_processed"})
            continue
        old = evidence.get(candidate_id)
        if old and (old.get("source_key") != SOURCE_KEY or
                    old.get("source_url") != route):
            raise ValueError("canonical source evidence collision")
        if old and old.get("status") == "needs_editorial_review" and not old.get("corroboration"):
            outcomes.append({"title": title, "status": "stronger_primary_preserved"})
            continue
        canonical[candidate_id] = {
            "id": candidate_id, "source_key": SOURCE_KEY,
            "official_url": route, "status": "needs_review",
            "first_seen": prior.get("first_seen", checked_at) if prior else checked_at,
            "last_seen": checked_at,
        }
        claims = [
            {"event_title": title, "composer": composer,
             "venue": "Teatro di San Carlo", "date": date_str,
             "starts_at": official_local_time(date_str, clock)}
            for date_str, clock in sorted(confirmed)
        ]
        digest = hashlib.sha256(json.dumps(
            {"source": FIRST, "official_url": route, "clocks": claims},
            sort_keys=True, ensure_ascii=False,
        ).encode()).hexdigest()
        evidence[candidate_id] = {
            "candidate_id": candidate_id, "source_key": SOURCE_KEY,
            "source_url": route, "content_sha256": digest,
            "content_hash_scope": "cross_source_review_not_primary_html",
            "checked_at": checked_at, "status": "needs_editorial_review",
            "event_facts": claims,
            "corroboration": {
                "method": "issuer_press_repertoire_plus_two_secondary_clocks",
                "official_event_page_retrieved": False,
                "issuer_press_url": OFFICIAL_PRESS_RELEASE,
                "publisher_urls": [FIRST, SECOND],
                "repertoire_edition": "2026/27",
                "showtimes_confirmed": len(claims),
                "source_independence_note":
                    "Two different secondary publishers may share original schedule inputs; no direct primary event page fetch",
            }
        }
        outcomes.append({"title": title, "status": "canonical_candidate_evidence_ready",
                         "recite": len(claims)})
    return (
        {"schema_version": 1,
         "candidates": sorted(canonical.values(), key=lambda r: r["id"])},
        {"schema_version": 1,
         "evidence": sorted(evidence.values(), key=lambda r: r["candidate_id"])},
        outcomes,
    )


def main():
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    review = json.loads(CORROBORATION.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    details = json.loads(DETAILS.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_candidates, new_details, outcomes = apply(
        checkpoint, review, candidates, details, checked_at=now
    )
    _write_atomic(CANDIDATES, new_candidates)
    _write_atomic(PUBLIC_CANDIDATES, new_candidates)
    _write_atomic(DETAILS, new_details)
    _write_atomic(PUBLIC_DETAILS, new_details)
    _write_atomic(HEALTH, {
        "schema_version": 1, "checked_at": now, "productions": outcomes,
    })
    print(json.dumps({"san_carlo_reconciliation": outcomes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
