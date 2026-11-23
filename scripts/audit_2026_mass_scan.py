"""Massive, bounded, read-only official 2026 archive discovery.

Scans all approved configured source indexes and bounded official detail pages
using Atlas' robots-gated controlled_fetch. Outputs *diagnostics only*.
Does not import the candidate publishers, write Atlas DB/catalog or auto-promote.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from opera_atlas.controlled_fetch import AccessDenied, FetchUnavailable, fetch_official_html
from opera_atlas.db import connect, migrate
from scripts.discover_season_indexes import extract, validate_config, eligible
from scripts.collect_candidate_details import parse_event_facts

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/season-index-config.json"
CANDIDATES = ROOT / "data/season-index-candidates.json"
MAX_INDEXES = 120
MAX_DETAILS = 750
MAX_PER_SOURCE = 15
WORKERS = 5
HOST_GAP_SECONDS = 1.0
_lock = threading.Lock()
_host_locks = defaultdict(threading.Lock)
_last_by_host = {}


def valid_official_url(url, official):
    """Never follow cross-domain links, HTTP, credentialed URLs or exotic ports."""
    try:
        a, b = urlsplit(url), urlsplit(official)
        return (a.scheme == b.scheme == "https" and a.hostname == b.hostname
                and a.hostname and not a.username and not a.password
                and a.port is None and b.port is None)
    except ValueError:
        return False


def fetch(item, url, *, fetcher=fetch_official_html, sleep=time.sleep):
    """A distinct in-memory SQLite approval context per worker."""
    if not valid_official_url(url, item["official_url"]):
        raise AccessDenied("URL outside the approved official hostname")
    host = urlsplit(url).hostname
    # Serialize requests to each host; parallelize only across independent hosts.
    with _host_locks[host]:
        with _lock:
            remaining = max(0., HOST_GAP_SECONDS - (time.monotonic() - _last_by_host.get(host, 0.)))
        if remaining:
            sleep(remaining)
        db = connect()
        try:
            migrate(db)
            db.execute("INSERT OR IGNORE INTO sources(official_url, access_status) VALUES (?, 'approved')",
                       (item["official_url"],))
            source_id = db.execute("SELECT id FROM sources WHERE official_url=?",
                                   (item["official_url"],)).fetchone()["id"]
            page = fetcher(db, source_id=source_id, url=url, network_enabled=True)
            return page.html
        finally:
            db.close()
            with _lock:
                _last_by_host[host] = time.monotonic()


def clean_facts(facts):
    """Only explicitly dated 2026 event facts; audience/genre require review."""
    out = []
    for f in facts:
        day = f.get("date")
        if not isinstance(day, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", day):
            continue
        title = f.get("event_title")
        if not isinstance(title, str) or not title.strip():
            continue
        out.append({
            "date": day, "starts_at": f.get("starts_at"),
            "event_title": title.strip(), "composer": f.get("composer"),
            "venue": f.get("venue"), "audience": "not_verified",
            "genre": "not_verified", "review_status": "needs_independent_validation",
        })
    return out


def index_batch(config, *, fetch_page=fetch, workers=WORKERS):
    entries = [s for s in validate_config(config) if s["access_status"] == "approved"]
    if len(entries) > MAX_INDEXES:
        raise ValueError("approved index count exceeds configured safety limit")
    def scan(s):
        row = {"source_key": s["key"], "index_url": s["url"]}
        try:
            html = fetch_page(s, s["url"])
            links = extract(s["key"], s["url"], html, s["min_links"])
            links = sorted({u for u in links
                            if valid_official_url(u, s["official_url"]) and eligible(s["key"], u)})
            row.update(status="scanned", candidate_urls=links, candidate_count=len(links))
        except (AccessDenied, FetchUnavailable, ValueError, OSError) as exc:
            row.update(status="unverified", reason=type(exc).__name__,
                       candidate_urls=[], candidate_count=0)
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return sorted(pool.map(scan, entries), key=lambda r: r["source_key"])


def detail_queue(config, indexes, cached, *, max_pages=MAX_DETAILS):
    """Reuse existing candidate URLs plus live index leads; source-scoped."""
    approved = {s["key"]: s for s in validate_config(config)
                if s["access_status"] == "approved"}
    links = defaultdict(set)
    for row in indexes:
        for u in row["candidate_urls"]:
            links[row["source_key"]].add(u)
    for row in cached.get("candidates", []):
        key, url = row.get("source_key"), row.get("official_url")
        if (key in approved and isinstance(url, str)
                and row.get("status") != "excluded_nonopera"):
            links[key].add(url)
    queue = []
    overflow = []
    for key in sorted(links):
        source = approved[key]
        approved_urls = sorted(u for u in links[key]
                               if valid_official_url(u, source["official_url"])
                               and eligible(key, u))
        for u in approved_urls[:MAX_PER_SOURCE]:
            queue.append((source, u))
        if len(approved_urls) > MAX_PER_SOURCE:
            overflow.append({"source_key": key,
                             "deferred_due_to_per_source_limit": len(approved_urls) - MAX_PER_SOURCE})
    if len(queue) > max_pages:
        overflow.append({"global_deferred": len(queue) - max_pages})
    return queue[:max_pages], overflow


def detail_batch(queue, *, fetch_page=fetch, workers=WORKERS):
    def scan(task):
        source, url = task
        result = {"source_key": source["key"], "source_url": url}
        try:
            html = fetch_page(source, url)
            facts = clean_facts(parse_event_facts(html))
            result.update(status="evidence_found" if facts else "no_structured_2026_evidence",
                          facts=facts)
        except (AccessDenied, FetchUnavailable, ValueError, OSError) as exc:
            result.update(status="unverified", reason=type(exc).__name__, facts=[])
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return sorted(pool.map(scan, queue),
                      key=lambda r: (r["source_key"], r["source_url"]))


def make_report(config, cached, *, fetch_page=fetch, workers=WORKERS, max_pages=MAX_DETAILS):
    indexes = index_batch(config, fetch_page=fetch_page, workers=workers)
    queue, overflow = detail_queue(config, indexes, cached, max_pages=max_pages)
    details = detail_batch(queue, fetch_page=fetch_page, workers=workers)
    return {
        "schema_version": 1, "year": 2026,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "official source discovery only; not season coverage certification",
        "read_only": True, "catalog_updated": False,
        "source_indexes_configured": len(config.get("sources", [])),
        "source_indexes_scanned": sum(x["status"] == "scanned" for x in indexes),
        "detail_pages_scanned": sum(x["status"] != "unverified" for x in details),
        "observations_needing_review": sum(len(x["facts"]) for x in details),
        "overflow": overflow, "index_results": indexes, "detail_results": details,
        "warning": "Candidate facts need opera, audience, venue and calendar-completeness review. Missing structured facts do not mean no recite.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--max-detail-pages", type=int, default=MAX_DETAILS)
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("Mass scan requires explicit --allow-network")
    if not 1 <= args.workers <= WORKERS or not 1 <= args.max_detail_pages <= MAX_DETAILS:
        parser.error("worker/page limits exceeded")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cached = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    report = make_report(config, cached, workers=args.workers, max_pages=args.max_detail_pages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "source_indexes_configured", "source_indexes_scanned",
        "detail_pages_scanned", "observations_needing_review", "read_only")}))


if __name__ == "__main__":
    main()
