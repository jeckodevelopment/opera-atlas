"""Explicit, auditable resolution of ambiguous or changed event identities."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .db import add_performance


def resolve_review(
    conn: sqlite3.Connection,
    review_id: int,
    *,
    action: str,
    selected_performance_id: int | None = None,
) -> int:
    """Resolve a queued review by linking a verified candidate or creating a recita.

    action='link' requires a specifically selected existing performance.
    action='create' uses the proposed production, venue and timezone-aware time.
    The caller is responsible for verifying the decision and committing.
    """
    if action not in ("link", "create"):
        raise ValueError("action must be 'link' or 'create'")
    review = conn.execute(
        """SELECT r.id,r.source_event_id,r.proposed_production_id,
                  r.proposed_venue_id,r.proposed_start,r.state,
                  e.source_id,e.performance_id AS previous_id,e.source_url
           FROM reconciliation_reviews r
           JOIN source_events e ON e.id=r.source_event_id WHERE r.id=?""",
        (review_id,),
    ).fetchone()
    if review is None or review["state"] != "open":
        raise ValueError("unknown or already resolved review")
    proposed_time = datetime.fromisoformat(review["proposed_start"])
    if proposed_time.tzinfo is None:
        raise ValueError("review lacks timezone")
    proposed_work = conn.execute(
        "SELECT work_id FROM productions WHERE id=?",
        (review["proposed_production_id"],),
    ).fetchone()["work_id"]

    if action == "create":
        if selected_performance_id is not None:
            raise ValueError("cannot select a performance for 'create'")
        target_id = add_performance(
            conn, review["proposed_production_id"],
            review["proposed_venue_id"], proposed_time,
        )
    else:
        if selected_performance_id is None:
            raise ValueError("select a target performance")
        target = conn.execute(
            """SELECT p.id,p.venue_id,p.starts_at,pr.work_id
               FROM performances p JOIN productions pr ON pr.id=p.production_id
               WHERE p.id=?""",
            (selected_performance_id,),
        ).fetchone()
        if target is None or target["venue_id"] != review["proposed_venue_id"] or target["work_id"] != proposed_work:
            raise ValueError("chosen performance differs from proposed work/venue")
        if datetime.fromisoformat(target["starts_at"]).astimezone(timezone.utc) != proposed_time.astimezone(timezone.utc):
            raise ValueError("chosen performance has a different instant")
        target_id = int(target["id"])

    # Keep review and source-event write consistent; never silently erase history.
    conn.execute(
        "UPDATE source_events SET performance_id=?,state='linked',last_seen_at=CURRENT_TIMESTAMP WHERE id=?",
        (target_id,review["source_event_id"]),
    )
    if review["source_url"]:
        conn.execute(
            """INSERT OR IGNORE INTO performance_sources
               (performance_id,source_id,source_url) VALUES (?,?,?)""",
            (target_id,review["source_id"],review["source_url"]),
        )
        previous_id = review["previous_id"]
        if previous_id is not None and previous_id != target_id:
            # Remove old provenance only if no source event still points to it.
            still_linked = conn.execute(
                """SELECT 1 FROM source_events WHERE source_id=?
                   AND performance_id=? AND id<>?""",
                (review["source_id"],previous_id,review["source_event_id"]),
            ).fetchone()
            if still_linked is None:
                conn.execute(
                    """DELETE FROM performance_sources WHERE performance_id=?
                       AND source_id=? AND source_url=?""",
                    (previous_id,review["source_id"],review["source_url"]),
                )
    conn.execute(
        """UPDATE reconciliation_reviews SET state='resolved',
           resolved_at=CURRENT_TIMESTAMP WHERE id=?""",
        (review_id,),
    )
    return target_id
