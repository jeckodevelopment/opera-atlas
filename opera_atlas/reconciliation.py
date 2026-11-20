"""Deterministic reconciliation of independent official event observations.

A verified work_id, venue_id and UTC instant define a *candidate* recita.
Two distinct productions of the same work at a venue and instant are treated
as ambiguous if the catalog already contains more than one such candidate.
An existing source's external_id is never silently moved to another recita.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .db import add_performance, local_start


@dataclass(frozen=True)
class ReconcileResult:
    state: str  # linked | review
    performance_id: int | None
    review_id: int | None = None


def _check_source_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.netloc:
        raise ValueError("source URL must be an absolute http(s) URL")


def reconcile(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    external_id: str,
    source_url: str,
    production_id: int,
    venue_id: int,
    starts_at: datetime,
    payload: dict,
) -> ReconcileResult:
    """Link a scanned source record to exactly one canonical performance.

    Call in a single-writer ingestion pipeline. New source records with zero
    candidates create a recita. One candidate of the same canonical work,
    venue and instant gets the additional provenance. Multiple candidates
    and changed source identities enter human review (without mutating the
    existing canonical recita).
    """
    if not external_id.strip():
        raise ValueError("external_id is required")
    _check_source_url(source_url)
    stamp = local_start(starts_at)
    fingerprint = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    work = conn.execute(
        "SELECT work_id FROM productions WHERE id=?", (production_id,)
    ).fetchone()
    if work is None:
        raise ValueError("unknown production")
    if conn.execute("SELECT 1 FROM venues WHERE id=?", (venue_id,)).fetchone() is None:
        raise ValueError("unknown venue")
    if conn.execute("SELECT 1 FROM sources WHERE id=?", (source_id,)).fetchone() is None:
        raise ValueError("unknown source")

    instant = starts_at.astimezone(timezone.utc)
    existing = conn.execute(
        "SELECT id, performance_id FROM source_events WHERE source_id=? AND external_id=?",
        (source_id, external_id),
    ).fetchone()
    candidates = []
    for row in conn.execute(
        """SELECT p.id, p.starts_at
           FROM performances p JOIN productions pr ON pr.id=p.production_id
           WHERE pr.work_id=? AND p.venue_id=?""",
        (work["work_id"], venue_id),
    ):
        if datetime.fromisoformat(row["starts_at"]).astimezone(timezone.utc) == instant:
            candidates.append(row["id"])

    if existing is not None and existing["performance_id"] is not None:
        # Existing source identity must never migrate silently to another record.
        if existing["performance_id"] not in candidates:
            return _review(conn, existing["id"], "changed_identity",
                           production_id, venue_id, stamp, fingerprint)
        performance_id = existing["performance_id"]
    elif len(candidates) > 1:
        if existing is None:
            cursor = conn.execute(
                """INSERT INTO source_events
                   (source_id,external_id,last_fingerprint,state)
                   VALUES (?,?,?,'review')""",
                (source_id, external_id, fingerprint),
            )
            event_id = cursor.lastrowid
        else:
            event_id = existing["id"]
        return _review(conn, event_id, "ambiguous_match",
                       production_id, venue_id, stamp, fingerprint)
    elif candidates:
        performance_id = candidates[0]
    else:
        performance_id = add_performance(conn, production_id, venue_id, starts_at)

    if existing is None:
        conn.execute(
            """INSERT INTO source_events
               (source_id,external_id,performance_id,last_fingerprint,state)
               VALUES (?,?,?,?,'linked')""",
            (source_id, external_id, performance_id, fingerprint),
        )
    else:
        conn.execute(
            """UPDATE source_events SET performance_id=?,last_fingerprint=?,
               state='linked',last_seen_at=CURRENT_TIMESTAMP WHERE id=?""",
            (performance_id, fingerprint, existing["id"]),
        )
    conn.execute(
        """INSERT OR IGNORE INTO performance_sources
           (performance_id,source_id,source_url) VALUES (?,?,?)""",
        (performance_id, source_id, source_url),
    )
    return ReconcileResult("linked", performance_id)


def _review(conn: sqlite3.Connection, event_id: int, reason: str,
            production_id: int, venue_id: int, starts_at: str,
            fingerprint: str) -> ReconcileResult:
    conn.execute(
        """INSERT OR IGNORE INTO reconciliation_reviews
           (source_event_id,reason,proposed_production_id,proposed_venue_id,
            proposed_start,observed_fingerprint)
           VALUES (?,?,?,?,?,?)""",
        (event_id, reason, production_id, venue_id, starts_at, fingerprint),
    )
    conn.execute(
        "UPDATE source_events SET state='review',last_seen_at=CURRENT_TIMESTAMP WHERE id=?",
        (event_id,),
    )
    review = conn.execute(
        """SELECT id FROM reconciliation_reviews WHERE
           source_event_id=? AND observed_fingerprint=? AND
           proposed_production_id=? AND proposed_venue_id=? AND proposed_start=?""",
        (event_id, fingerprint, production_id, venue_id, starts_at),
    ).fetchone()
    current = conn.execute(
        "SELECT performance_id FROM source_events WHERE id=?", (event_id,)
    ).fetchone()
    return ReconcileResult("review", current["performance_id"], review["id"])
