"""Conservative, audited changes to already-known performances.

A missing event in a scan is never evidence of cancellation. An explicit
reviewed source and reason are required for each state transition.
"""
from __future__ import annotations

import sqlite3
from urllib.parse import urlsplit

STATUSES = frozenset(("announced", "confirmed", "postponed", "cancelled"))
TRANSITIONS = {
    "announced": frozenset(("confirmed", "postponed", "cancelled")),
    "confirmed": frozenset(("postponed", "cancelled")),
    "postponed": frozenset(("confirmed", "cancelled")),
    "cancelled": frozenset(("confirmed",)),
}


def set_performance_status(
    conn: sqlite3.Connection, *,
    performance_id: int,
    status: str,
    source_url: str,
    reason: str,
) -> bool:
    """Record one explicit, fact-checked status transition.

    If status is already current, no new history entry is created. Only
    sources already associated with this specific canonical performance
    may substantiate a change. Caller owns transaction/commit.
    """
    if status not in STATUSES:
        raise ValueError("invalid performance status")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("status change requires a reason")
    uri = urlsplit(source_url)
    if uri.scheme != "https" or not uri.hostname or uri.username or uri.password:
        raise ValueError("status evidence must be an absolute HTTPS URL")
    performance = conn.execute(
        "SELECT status FROM performances WHERE id=?", (performance_id,)
    ).fetchone()
    if performance is None:
        raise ValueError("unknown performance")
    old = performance["status"]
    if old == status:
        return False
    if status not in TRANSITIONS[old]:
        raise ValueError("invalid status transition")
    evidence = conn.execute(
        """SELECT 1 FROM performance_sources ps
           JOIN sources s ON s.id=ps.source_id
           WHERE ps.performance_id=? AND ps.source_url=?
             AND s.access_status='approved'""",
        (performance_id, source_url),
    ).fetchone()
    if evidence is None:
        raise ValueError("evidence must be an approved, linked source URL")
    updated = conn.execute(
        "UPDATE performances SET status=? WHERE id=? AND status=?",
        (status, performance_id, old),
    )
    if updated.rowcount != 1:
        raise ValueError("concurrent status change detected")
    conn.execute(
        """INSERT INTO performance_status_history
           (performance_id,previous_status,new_status,source_url,reason)
           VALUES (?,?,?,?,?)""",
        (performance_id,old,status,source_url,reason.strip()),
    )
    return True


def list_status_history(conn: sqlite3.Connection, performance_id: int) -> list[dict]:
    """Read change history without modifying archived evidence."""
    return [
        dict(row) for row in conn.execute(
            """SELECT previous_status,new_status,source_url,reason,decided_at
               FROM performance_status_history WHERE performance_id=?
               ORDER BY id""",
            (performance_id,),
        )
    ]
