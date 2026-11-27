"""Discover future San Carlo seasons through independent calendars, review only.

A secondary event URL is never authority to publish a performance. This probe
does not alter the historical 2026/27 checkpoint or canonical registries.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
from urllib.parse import urljoin

from opera_atlas.controlled_fetch import AccessDenied, FetchUnavailable, fetch_official_html
from opera_atlas.db import connect, migrate
from scripts.daily_ingest import _write_atomic
from scripts.publish_catalog_v2 import ROOT
from scripts.scan_san_carlo_secondary import (
    parse, season_years, build_secondary_checkpoint,
)
from scripts.corroborate_san_carlo_secondary import SOURCE, key_of, parse_independent, compare

INDEX = "https://www.classicalive.it/it/luoghi/campania/napoli/napoli/teatro-di-san-carlo/"
OUT = ROOT / "data/san-carlo-future-review.json"
PUBLIC = ROOT / "public/catalog/san-carlo-future-review.json"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.add(urljoin(INDEX, href))

def discover(html, *, today):
    page = Links()
    page.feed(html)
    found = []
    for url in sorted(page.links):
        try:
            start, end = season_years(url)
        except ValueError:
            continue
        # Rolling two-edition horizon; the legacy edition remains governed
        # by its separately verified canonical bridge.
        if max(2027, today.year - 1) <= start <= today.year + 1 and end >= today.year:
            found.append(url)
    return found

def review_seasons(fetch, *, today, checked_at, previous=None):
    report = {"schema_version": 1, "checked_at": checked_at,
              "index_url": INDEX, "canonical_publication_authorized": False,
              "seasons": [], "status": "not_verified"}
    old = {r["source_url"]: r for r in (previous or {}).get("seasons", [])
           if r.get("checkpoint")}
    try:
        urls = discover(fetch(INDEX), today=today)
    except (AccessDenied, FetchUnavailable, ValueError):
        report["status"] = "index_unavailable"
        report["seasons"] = [dict(r, status="stale_index_unavailable") for r in old.values()]
        return report
    report["status"] = "review_only" if urls else "no_future_edition_verified"
    independent = None
    if urls:
        try:
            independent = fetch(SOURCE)
        except (AccessDenied, FetchUnavailable, ValueError):
            pass
    for url in urls:
        start, end = season_years(url)
        row = {"source_url": url, "season": f"{start}/{end}", "status": "unverified"}
        try:
            skipped = []
            records = parse(fetch(url), url=url, diagnostics=skipped)
            checkpoint, health = build_secondary_checkpoint(
                records, checked_at=checked_at, incomplete=skipped, url=url)
        except (AccessDenied, FetchUnavailable, ValueError):
            report["seasons"].append(dict(old.get(url, row), status="season_unavailable"))
            continue
        row.update(checkpoint=checkpoint, health=health, status="awaiting_independent_calendar",
                   primary_repertoire_required=True, canonical_publication_authorized=False)
        if independent is not None:
            try:
                allowed = {key_of(p["title"]) for p in records}
                observed = parse_independent(independent, allowed_titles=allowed, season=(start,end))
                row["comparison"] = compare(checkpoint, observed)
                row["status"] = "awaiting_primary_repertoire"
            except ValueError:
                row["status"] = "independent_edition_unverified"
        report["seasons"].append(row)
    # Keep earlier successful checkpoints visible, but never claim freshness.
    for url, row in old.items():
        if url not in urls and season_years(url)[1] >= today.year:
            report["seasons"].append(dict(row, status="stale_not_listed"))
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("--allow-network required")
    db = connect()
    try:
        migrate(db)
        ids = {}
        for origin in ("https://www.classicalive.it/", "https://www.enjoylive.travel/"):
            db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')", (origin,))
            ids[origin] = db.execute("SELECT id FROM sources WHERE official_url=?", (origin,)).fetchone()["id"]
        def fetch(url):
            origin = "https://www.enjoylive.travel/" if url == SOURCE else "https://www.classicalive.it/"
            return fetch_official_html(db,source_id=ids[origin],url=url,network_enabled=True).html
        now = datetime.now(timezone.utc)
        previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
        report = review_seasons(fetch,today=now.date(),checked_at=now.isoformat(timespec="seconds"),previous=previous)
    finally:
        db.close()
    for path in (OUT,PUBLIC):
        _write_atomic(path,report)
    print(json.dumps({"status":report["status"],"seasons":len(report["seasons"]),
                      "canonical_publication_authorized":False}))

if __name__ == "__main__":
    main()
