"""Validated, opt-in official source seed loader (never fetches web pages)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "data" / "sources.json"
REQUIRED = {"key", "name", "official_url", "calendar_url", "region", "city", "kind", "access_status"}
KINDS = {"theatre", "foundation", "festival", "circuit", "other"}


def read_registry(path: str | Path = DEFAULT_REGISTRY) -> list[dict]:
    """Validate a machine-readable seed file before writing anything."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema_version") != 1 or not isinstance(doc.get("sources"), list):
        raise ValueError("unsupported source registry")
    seen = set()
    urls = set()
    output = []
    for source in doc["sources"]:
        if not isinstance(source, dict) or set(source) != REQUIRED:
            raise ValueError("invalid source fields")
        for name in ("key", "name", "official_url", "calendar_url", "region"):
            if not isinstance(source[name], str) or not source[name].strip():
                raise ValueError(f"invalid {name}")
        if source["city"] is not None and (
            not isinstance(source["city"], str) or not source["city"].strip()
        ):
            raise ValueError("invalid city")
        if source["kind"] not in KINDS or source["access_status"] != "pending":
            raise ValueError("seed sources must await access permission checks")
        for field in ("official_url", "calendar_url"):
            parts = urlsplit(source[field])
            if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
                raise ValueError("only public HTTPS URLs are accepted")
        if source["key"] in seen or source["official_url"] in urls:
            raise ValueError("duplicate source")
        seen.add(source["key"])
        urls.add(source["official_url"])
        output.append(source)
    return output


def seed_sources(connection: sqlite3.Connection, path: str | Path = DEFAULT_REGISTRY) -> int:
    """Register vetted official entry points without enabling a crawler.

    Leaves existing access decisions unchanged. Does not commit: caller owns
    the transaction. Returns count of newly inserted source rows.
    """
    sources = read_registry(path)
    inserted = 0
    for s in sources:
        existing = connection.execute(
            "SELECT id FROM sources WHERE official_url=?", (s["official_url"],)
        ).fetchone()
        if existing is not None:
            continue
        organization = connection.execute(
            "SELECT id FROM organizations WHERE name=? AND kind=?",
            (s["name"], s["kind"]),
        ).fetchone()
        if organization is None:
            org_id = connection.execute(
                "INSERT INTO organizations(name,kind,official_url) VALUES (?,?,?)",
                (s["name"], s["kind"], s["official_url"]),
            ).lastrowid
        else:
            org_id = organization["id"]
        connection.execute(
            """INSERT INTO sources(organization_id,official_url,calendar_url,
                                   source_kind,access_status,checked_at)
               VALUES (?, ?, ?, 'html', 'pending', ?)""",
            (org_id, s["official_url"], s["calendar_url"], "2026-11-20"),
        )
        inserted += 1
    return inserted
