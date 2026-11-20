"""Opera Atlas data storage: stdlib-only SQLite foundation."""
from __future__ import annotations

import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_V2_PATH = Path(__file__).resolve().parent / "schema_v2.sql"
SCHEMA_V3_PATH = Path(__file__).resolve().parent / "schema_v3.sql"
SCHEMA_V4_PATH = Path(__file__).resolve().parent / "schema_v4.sql"
SCHEMA_V5_PATH = Path(__file__).resolve().parent / "schema_v5.sql"
SCHEMA_V6_PATH = Path(__file__).resolve().parent / "schema_v6.sql"
ITALY = ZoneInfo("Europe/Rome")


def connect(database: str | Path = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    """Apply the idempotent baseline schema in a transaction."""
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations(version) VALUES (1)"
    )
    if connection.execute("SELECT 1 FROM schema_migrations WHERE version=2").fetchone() is None:
        connection.executescript(SCHEMA_V2_PATH.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations(version) VALUES (2)")
    if connection.execute("SELECT 1 FROM schema_migrations WHERE version=3").fetchone() is None:
        connection.executescript(SCHEMA_V3_PATH.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations(version) VALUES (3)")
    if connection.execute("SELECT 1 FROM schema_migrations WHERE version=4").fetchone() is None:
        connection.executescript(SCHEMA_V4_PATH.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations(version) VALUES (4)")
    if connection.execute("SELECT 1 FROM schema_migrations WHERE version=5").fetchone() is None:
        connection.executescript(SCHEMA_V5_PATH.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations(version) VALUES (5)")
    if connection.execute("SELECT 1 FROM schema_migrations WHERE version=6").fetchone() is None:
        connection.executescript(SCHEMA_V6_PATH.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations(version) VALUES (6)")
    connection.commit()


def normalize_title(value: str) -> str:
    """Normalize Unicode/case/whitespace, not editorially distinct titles."""
    if not value or not value.strip():
        raise ValueError("work title must not be empty")
    return " ".join(
        unicodedata.normalize("NFKC", value).casefold().split()
    )


def local_start(value: datetime) -> str:
    """Return an ISO timestamp with explicit offset, rejecting naive input.

    Use timezone-aware datetimes. In particular, do not guess the offset
    during DST transitions by attaching Europe/Rome to a naive datetime.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("performance start requires timezone information")
    return value.astimezone(ITALY).isoformat(timespec="seconds")


def add_work(
    connection: sqlite3.Connection, title: str, composer: str | None = None
) -> int:
    """Never merge homonymous works automatically; return a new work ID."""
    cursor = connection.execute(
        "INSERT INTO works(title, composer, title_normalized) VALUES (?, ?, ?)",
        (title.strip(), composer, normalize_title(title)),
    )
    return int(cursor.lastrowid)


def add_performance(
    connection: sqlite3.Connection,
    production_id: int,
    venue_id: int,
    starts_at: datetime,
    status: str = "announced",
) -> int:
    """Idempotent insert for exactly identical canonical performances.

    Cross-production matching is intentionally deferred to a reviewed
    reconciliation workflow (#3); do not guess those identities.
    """
    timestamp = local_start(starts_at)
    cursor = connection.execute(
        """INSERT OR IGNORE INTO performances
           (production_id, venue_id, starts_at, status)
           VALUES (?, ?, ?, ?)""",
        (production_id, venue_id, timestamp, status),
    )
    if cursor.rowcount == 1:
        return int(cursor.lastrowid)
    existing = connection.execute(
        """SELECT id FROM performances
           WHERE production_id=? AND venue_id=? AND starts_at=?""",
        (production_id, venue_id, timestamp),
    ).fetchone()
    if existing is None:
        raise ValueError("performance rejected: invalid or conflicting fields")
    return int(existing["id"])
