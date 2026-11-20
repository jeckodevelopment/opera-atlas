"""Curated repertoire registry: never infer canonical identity from a title alone.

This module supports verified work/alias mappings only. Data ingestion must
treat a missing or ambiguous result as a review item, not invent a composer.
"""
from __future__ import annotations

import sqlite3

from .db import add_work, normalize_title

# Editorial types. Non-operatic events are recognized, but must not be counted
# as operas by downstream publishing/metrics.
GENRES = frozenset(("opera", "operetta", "music_theatre", "concert", "ballet", "prose", "other"))


class AmbiguousWorkError(ValueError):
    """More than one canonical work matches the supplied verified facts."""


def register_work(
    conn: sqlite3.Connection,
    title: str,
    composer: str | None,
    *,
    genre: str = "opera",
) -> int:
    """Add a curated work, without merging homonyms or changing prior records."""
    if genre not in GENRES:
        raise ValueError("invalid genre")
    if composer is not None and not composer.strip():
        raise ValueError("empty composer is not a verified composer")
    if composer is not None:
        composer = composer.strip()
    work_id = add_work(conn, title, composer)
    if genre != "opera":
        conn.execute("UPDATE works SET genre=? WHERE id=?", (genre, work_id))
    return work_id


def register_alias(conn: sqlite3.Connection, work_id: int, alias: str) -> None:
    """Register a human-verified title alias for a known canonical work."""
    normalized = normalize_title(alias)
    if conn.execute("SELECT 1 FROM works WHERE id=?", (work_id,)).fetchone() is None:
        raise ValueError("unknown work")
    conn.execute(
        "INSERT OR IGNORE INTO work_aliases(work_id,alias,alias_normalized) VALUES (?,?,?)",
        (work_id, alias.strip(), normalized),
    )


def find_work(
    conn: sqlite3.Connection,
    title: str,
    *,
    composer: str | None,
    genre: str | None = None,
) -> int | None:
    """Find only an unambiguous canonical match; never guess missing composer.

    Both canonical titles and explicitly registered aliases are searched.
    Composer is required to avoid inferring identity from a homonymous title.
    """
    normalized = normalize_title(title)
    if composer is None or not composer.strip():
        return None
    if genre is not None and genre not in GENRES:
        raise ValueError("invalid genre")
    query = """SELECT DISTINCT w.id
               FROM works w LEFT JOIN work_aliases a ON a.work_id=w.id
               WHERE (w.title_normalized=? OR a.alias_normalized=?)
                 AND w.composer IS NOT NULL
                 AND lower(trim(w.composer))=lower(trim(?))"""
    values: list[str] = [normalized, normalized, composer]
    if genre is not None:
        query += " AND w.genre=?"
        values.append(genre)
    matches = [row["id"] for row in conn.execute(query, values)]
    if len(matches) > 1:
        raise AmbiguousWorkError("multiple curated works match the title and composer")
    return matches[0] if matches else None


def opera_only_clause(alias: str = "w") -> str:
    """SQL predicate for unambiguous opera statistics; trusted fixed alias only."""
    if alias != "w":
        raise ValueError("unsupported alias")
    return "w.genre = 'opera'"
