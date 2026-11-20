"""Bounded multi-production orchestration for already curated Teatro Regio mappings.

No discovery, recurring schedule or autonomous approval. Every page is named
explicitly by an operator in a small JSON manifest, validated in full before
the first network request. Failed records have their own SQLite savepoint.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from .controlled_fetch import record_source_check
from .scan import scan_regio_detail, ScanResult

MAX_BATCH = 20
FIELDS = frozenset(("url", "source_id", "venue_id", "production_id", "title", "composer"))


@dataclass(frozen=True)
class BatchSummary:
    total: int
    succeeded: int
    failed: int
    discovered: int
    linked: int
    reviews: int


def load_manifest(path: str | Path) -> list[dict]:
    """Reject unknown fields, duplicates and unbounded source batches."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"schema_version", "productions"}:
        raise ValueError("manifest requires schema_version and productions")
    entries = value["productions"]
    if value["schema_version"] != 1 or not isinstance(entries, list) or not 1 <= len(entries) <= MAX_BATCH:
        raise ValueError("unsupported or empty/oversized batch")
    seen = set()
    results = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ValueError("invalid manifest entry fields")
        for key in ("source_id", "venue_id", "production_id"):
            if type(entry[key]) is not int or entry[key] < 1:
                raise ValueError(f"invalid {key}")
        for key in ("title", "composer", "url"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise ValueError(f"invalid {key}")
        url = urlsplit(entry["url"])
        if (url.scheme != "https" or url.hostname not in
            ("www.teatroregio.torino.it", "teatroregio.torino.it")
            or url.username or url.password or url.port is not None
            or not url.path.startswith("/opera-e-balletto-")
            or url.fragment):
            raise ValueError("manifest contains a noncanonical Regio detail URL")
        identity = (entry["source_id"], entry["url"])
        if identity in seen:
            raise ValueError("duplicate source and detail URL")
        seen.add(identity)
        results.append(entry)
    return results


def run_batch(
    conn: sqlite3.Connection,
    entries: list[dict],
    *,
    network_enabled: bool = False,
    opener=None,
    scan: Callable = scan_regio_detail,
) -> BatchSummary:
    """Run a prevalidated bounded batch and keep audit of individual failures.

    A successful page is imported atomically with its source check; a failed
    page has all its partial changes rolled back, then an import_error audit
    is added. Caller decides whether to commit the entire batch.
    """
    if not network_enabled:
        raise ValueError("network requires explicit opt-in")
    if not 1 <= len(entries) <= MAX_BATCH:
        raise ValueError("invalid batch size")
    # Do not attempt any URL before the corresponding source and canonical
    # production have been confirmed by the curator/operator.
    for entry in entries:
        source = conn.execute(
            "SELECT access_status,official_url FROM sources WHERE id=?",
            (entry["source_id"],),
        ).fetchone()
        if source is None or source["access_status"] != "approved":
            raise ValueError("all manifest sources must be approved before starting")
        if urlsplit(source["official_url"]).hostname != urlsplit(entry["url"]).hostname:
            raise ValueError("manifest target does not match approved source hostname")
        production = conn.execute(
            "SELECT 1 FROM productions WHERE id=?", (entry["production_id"],)
        ).fetchone()
        venue = conn.execute(
            "SELECT 1 FROM venues WHERE id=?", (entry["venue_id"],)
        ).fetchone()
        if production is None or venue is None:
            raise ValueError("unrecognized production or venue")
    successes = failures = discovered = linked = reviews = 0
    for entry in entries:
        conn.execute("SAVEPOINT atlas_page")
        try:
            result: ScanResult = scan(
                conn, url=entry["url"], source_id=entry["source_id"],
                venue_id=entry["venue_id"], production_id=entry["production_id"],
                title=entry["title"], composer=entry["composer"],
                network_enabled=True, opener=opener,
            )
            conn.execute("RELEASE SAVEPOINT atlas_page")
        except (ValueError, sqlite3.Error) as exc:
            conn.execute("ROLLBACK TO SAVEPOINT atlas_page")
            conn.execute("RELEASE SAVEPOINT atlas_page")
            # Record a concise outcome, never persist raw HTML/exception text.
            record_source_check(
                conn, source_id=entry["source_id"], url=entry["url"],
                outcome="import_error", message=type(exc).__name__,
            )
            failures += 1
            continue
        if result.outcome == "success":
            successes += 1
            discovered += result.discovered
            linked += result.linked
            reviews += result.review
        else:
            failures += 1
    return BatchSummary(len(entries), successes, failures, discovered, linked, reviews)
