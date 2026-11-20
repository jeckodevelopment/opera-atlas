"""One-page controlled scan, including audit metadata and source reconciliation.

Nothing is scheduled. Database changes are committed by the CLI/operator only.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .controlled_fetch import (
    AccessDenied, FetchUnavailable, fetch_official_html, record_source_check,
)
from .ingestion import ImportSummary, import_regio_snapshot


@dataclass(frozen=True)
class ScanResult:
    outcome: str
    discovered: int = 0
    linked: int = 0
    review: int = 0


def scan_regio_detail(
    conn: sqlite3.Connection, *,
    url: str,
    source_id: int,
    venue_id: int,
    production_id: int,
    title: str,
    composer: str,
    network_enabled: bool = False,
    opener=None,
) -> ScanResult:
    """Fetch one approved detail page and reconcile recite; no commits.

    For denied/unavailable robots do not fetch the target URL. All failures
    are reported as audit metadata. Caller must commit/rollback explicitly.
    """
    try:
        page = fetch_official_html(
            conn, source_id=source_id, url=url,
            network_enabled=network_enabled, opener=opener,
        )
    except (AccessDenied, FetchUnavailable) as exc:
        reason = str(exc)
        outcome = (
            "robots_unavailable" if "robots.txt unavailable" in reason
            else "robots_blocked" if "robots.txt denies" in reason
            else "fetch_error" if isinstance(exc, FetchUnavailable)
            else "invalid_content"
        )
        record_source_check(
            conn, source_id=source_id, url=url, outcome=outcome,
            message=reason,
        )
        return ScanResult(outcome)

    try:
        summary = import_regio_snapshot(
            conn, html=page.html, source_url=url, source_id=source_id,
            venue_id=venue_id, production_id=production_id,
            expected_title=title, expected_composer=composer,
        )
    except (ValueError, sqlite3.Error) as exc:
        # The caller must rollback on unexpected failures: do not risk a
        # half-imported event being committed along with an error record.
        raise ValueError("scan import rejected; rollback required") from exc

    record_source_check(
        conn, source_id=source_id, url=url, outcome="success",
        content_sha256=page.sha256, byte_count=page.byte_count,
        observed_count=summary.discovered,
    )
    return ScanResult("success", summary.discovered, summary.linked, summary.review)
