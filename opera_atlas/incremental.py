"""Conservative comparison of consecutive production-page snapshots.

A missing timestamp is not proof of cancellation. When dated external IDs
disappear while others appear on the same page, treat the new dates as possible
reschedules: stage an unresolved delta, do NOT create a second canonical recita.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotDelta:
    missing: tuple[str, ...]
    added: tuple[str, ...]
    review_id: int | None


def compare_snapshot(
    conn: sqlite3.Connection, *, source_id: int, source_url: str,
    production_id: int, external_ids: list[str],
) -> SnapshotDelta:
    """Read existing identities for one source URL/production and stage uncertainty.

    This only detects changes in IDs; it cannot assert why a recita disappeared.
    The caller must only invoke this after parsing a *complete*, validated
    production page, never on an empty or partial/error response.
    """
    if not external_ids or len(external_ids) != len(set(external_ids)):
        raise ValueError("complete snapshot with unique identities required")
    existing = {
        row["external_id"] for row in conn.execute(
            """SELECT e.external_id FROM source_events e
               LEFT JOIN performances p ON p.id=e.performance_id
               WHERE e.source_id=? AND e.source_url=?
                 AND (p.production_id=? OR p.id IS NULL)""",
            (source_id, source_url, production_id),
        )
    }
    current = set(external_ids)
    missing = tuple(sorted(existing - current))
    added = tuple(sorted(current - existing))
    review_id = None
    if missing and added:
        old_json = json.dumps(missing, separators=(",", ":"))
        new_json = json.dumps(added, separators=(",", ":"))
        conn.execute(
            """INSERT OR IGNORE INTO source_snapshot_deltas
               (source_id,source_url,production_id,old_external_ids,new_external_ids)
               VALUES (?,?,?,?,?)""",
            (source_id,source_url,production_id,old_json,new_json),
        )
        review = conn.execute(
            """SELECT id FROM source_snapshot_deltas WHERE source_id=?
               AND source_url=? AND production_id=? AND
               old_external_ids=? AND new_external_ids=?""",
            (source_id,source_url,production_id,old_json,new_json),
        ).fetchone()
        review_id = int(review["id"])
    return SnapshotDelta(missing,added,review_id)


def acknowledge_delta(conn: sqlite3.Connection, delta_id: int, *, reason: str) -> None:
    """Mark an operator-reviewed discrepancy acknowledged; never mutate recite."""
    if not isinstance(reason,str) or not reason.strip():
        raise ValueError("operator explanation required")
    row = conn.execute(
        "SELECT state FROM source_snapshot_deltas WHERE id=?", (delta_id,)
    ).fetchone()
    if row is None or row["state"] != "open":
        raise ValueError("unknown or already acknowledged delta")
    conn.execute(
        """UPDATE source_snapshot_deltas SET state='acknowledged',
           acknowledged_at=CURRENT_TIMESTAMP WHERE id=?""",
        (delta_id,),
    )
