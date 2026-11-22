"""Opt-in official page retrieval honoring explicit robots prohibitions and bounded HTTP.

No scheduling, no recursive crawling, no storage of copyrighted HTML by default.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

MAX_BYTES = 2_000_000
USER_AGENT = "OperaAtlasResearch/0.1 (+https://github.com/jeckodevelopment/opera-atlas)"
TIMEOUT = 12


class AccessDenied(ValueError):
    pass


class FetchUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResult:
    url: str
    html: str
    sha256: str
    byte_count: int


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AccessDenied("redirect blocked; verify destination explicitly")


def _official_target(url: str, official_url: str) -> None:
    target = urlsplit(url)
    official = urlsplit(official_url)
    if (target.scheme != "https" or official.scheme != "https"
            or target.username or target.password
            or target.port is not None
            or target.hostname != official.hostname
            or not target.hostname):
        raise AccessDenied("HTTPS URL must have exactly the approved official hostname")


def fetch_official_html(
    conn: sqlite3.Connection, *,
    source_id: int, url: str, network_enabled: bool = False,
    opener=None,
) -> FetchResult:
    """Fetch one explicitly selected official URL, honoring explicit robots disallow.

    Unavailable, absent or malformed robots.txt is not a Disallow directive.
    User must opt in; no retry or follow links. Source and destination HTTP
    controls remain independent; a blocked destination stays blocked.
    """
    if not network_enabled:
        raise AccessDenied("network disabled unless explicitly enabled")
    source = conn.execute(
        "SELECT official_url,access_status FROM sources WHERE id=?", (source_id,)
    ).fetchone()
    if source is None or source["access_status"] != "approved":
        raise AccessDenied("source must be approved in SQLite")
    _official_target(url, source["official_url"])
    client = opener or build_opener(_NoRedirects())
    robots_url = urljoin(source["official_url"].rstrip("/") + "/", "robots.txt")
    # Atlas policy: only an *explicit applicable* robots.txt Disallow stops
    # acquisition. A missing/unreachable file is not such a directive.
    # Never override a destination's HTTP denial or follow redirects.
    robots = None
    try:
        with client.open(Request(robots_url, headers={"User-Agent": USER_AGENT}),
                         timeout=TIMEOUT) as response:
            if response.status == 200:
                raw_robots = response.read(256_001)
                if len(raw_robots) <= 256_000:
                    robots = raw_robots.decode("utf-8", errors="replace")
    except (HTTPError, URLError, OSError, TimeoutError):
        # robots.txt cannot be read; leave the explicit-disallow set empty.
        pass
    if robots is not None:
        rules = robots.splitlines()
        # HTML placeholders and malformed content have no valid directives.
        # Only actual user-agent groups containing Disallow or Allow are
        # interpreted as REP rules.
        if any(line.strip().casefold().startswith("user-agent:") for line in rules):
            parser = RobotFileParser()
            parser.parse(rules)
            if not parser.can_fetch(USER_AGENT, url):
                raise AccessDenied("robots.txt explicitly denies access")
    try:
        with client.open(Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "text/html"
        }), timeout=TIMEOUT) as response:
            if response.status != 200:
                raise FetchUnavailable("unexpected HTTP status")
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                raise FetchUnavailable("not an HTML page")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise FetchUnavailable("HTML response too large")
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise FetchUnavailable("page unavailable") from exc
    return FetchResult(url, body.decode("utf-8", errors="replace"),
                       hashlib.sha256(body).hexdigest(), len(body))


def record_source_check(
    conn: sqlite3.Connection, *, source_id: int, url: str,
    outcome: str, status_code: int | None = None,
    content_sha256: str | None = None, byte_count: int | None = None,
    observed_count: int | None = None, message: str | None = None,
) -> int:
    """Store operational metadata only; never a full page or credentials."""
    cur = conn.execute(
        """INSERT INTO source_checks
           (source_id,url,outcome,status_code,content_sha256,bytes_received,
            observed_count,message) VALUES (?,?,?,?,?,?,?,?)""",
        (source_id,url,outcome,status_code,content_sha256,byte_count,
         observed_count,(message or "")[:250]),
    )
    return int(cur.lastrowid)
