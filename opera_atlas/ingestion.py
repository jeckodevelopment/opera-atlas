"""Offline, explicitly authorized import of verified source HTML."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .catalog import find_work
from .reconciliation import reconcile
from .regio_parser import parse_regio_detail
from .incremental import compare_snapshot


@dataclass(frozen=True)
class ImportSummary:
    discovered: int
    linked: int
    review: int


def import_regio_snapshot(
    conn: sqlite3.Connection, *,
    html: str,
    source_url: str,
    source_id: int,
    venue_id: int,
    production_id: int,
    expected_title: str,
    expected_composer: str,
) -> ImportSummary:
    """Import a single vetted saved HTML snapshot, no HTTP requests.

    All entities must have been curated and confirmed before import. Caller
    controls transaction/rollback. A source with status other than 'approved'
    cannot be imported.
    """
    src = conn.execute(
        "SELECT id,access_status,official_url FROM sources WHERE id=?", (source_id,)
    ).fetchone()
    if src is None or src["access_status"] != "approved":
        raise ValueError("source must be reviewed and approved before ingestion")
    if src["official_url"].rstrip("/") not in (
        "https://www.teatroregio.torino.it", "https://teatroregio.torino.it"
    ):
        raise ValueError("source is not Teatro Regio Torino")
    work_id = find_work(conn, expected_title, composer=expected_composer, genre="opera")
    production = conn.execute(
        """SELECT p.work_id FROM productions p WHERE p.id=?""", (production_id,)
    ).fetchone()
    if work_id is None or production is None or production["work_id"] != work_id:
        raise ValueError("production must reference a unique curated opera")
    venue = conn.execute("SELECT name,municipality FROM venues WHERE id=?", (venue_id,)).fetchone()
    if venue is None or venue["municipality"].casefold() != "torino" or "regio" not in venue["name"].casefold():
        raise ValueError("venue must be the reviewed Torino Teatro Regio")
    recite = parse_regio_detail(
        html, source_url=source_url, expected_title=expected_title,
        expected_composer=expected_composer,
    )
    if not recite:
        raise ValueError("no explicit recite: incomplete or unsupported page")
    delta = compare_snapshot(
        conn, source_id=source_id, source_url=source_url,
        production_id=production_id,
        external_ids=[fact.external_id for fact in recite],
    )
    linked = 0
    review = int(delta.review_id is not None)
    for fact in recite:
        if delta.review_id is not None and fact.external_id in delta.added:
            # A disappearance alongside a new timestamp may be a moved show.
            # Never create a second canonical performance automatically.
            continue
        res = reconcile(
            conn, source_id=source_id, external_id=fact.external_id,
            source_url=fact.source_url, production_id=production_id,
            venue_id=venue_id, starts_at=fact.starts_at,
            payload={"title":fact.title,"composer":fact.composer,
                     "starts_at":fact.starts_at.isoformat(),"source_url":fact.source_url},
        )
        linked += res.state == "linked"
        review += res.state == "review"
    return ImportSummary(len(recite), linked, review)


def export_public_catalog(conn: sqlite3.Connection, destination: str | Path) -> int:
    """Publish verified, non-cancelled operatic recite only, with provenance.

    Export is deliberately an explicit step; no unverified scan can silently
    become public. No artists' biographies, pictures or source HTML copied.
    """
    rows = conn.execute(
        """SELECT pf.id, pf.starts_at, pf.status, w.title, w.composer,
                  v.name AS venue, v.municipality, v.region,
                  v.latitude, v.longitude
           FROM performances pf
           JOIN productions p ON p.id=pf.production_id
           JOIN works w ON w.id=p.work_id
           JOIN venues v ON v.id=pf.venue_id
           WHERE w.genre='opera' AND pf.status IN ('announced','confirmed')
           AND EXISTS(SELECT 1 FROM performance_sources ps
                      JOIN sources s ON s.id=ps.source_id
                      WHERE ps.performance_id=pf.id AND s.access_status='approved')
           ORDER BY pf.starts_at,pf.id"""
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["sources"] = [
            x["source_url"] for x in conn.execute(
                """SELECT DISTINCT ps.source_url FROM performance_sources ps
                   JOIN sources s ON s.id=ps.source_id
                   WHERE ps.performance_id=? AND s.access_status='approved'
                   ORDER BY ps.source_url""", (row["id"],)
            )
        ]
        out.append(item)
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version":1,"performances":out},
                   ensure_ascii=False,indent=2) + "\n", encoding="utf-8",
    )
    return len(out)
