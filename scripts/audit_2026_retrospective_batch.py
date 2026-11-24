"""Independent retrospective 2025/26 and 2026 official archive discovery.

Bounded network scan with the approved Atlas robots-gated fetcher. It does NOT
write the public catalog, canonical source candidates, or approved historical
evidence. Historical *leads* are not proof of a complete calendar.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from scripts.audit_2026_mass_scan import fetch, valid_official_url, clean_facts
from scripts.collect_candidate_details import parse_event_facts
from scripts.discover_season_indexes import validate_config, excluded_nonopera

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/season-index-config.json"
VENUES = ROOT / "data/venue-directory.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-retrospective-batch.json"
MAX_WORKERS = 5
MAX_INDEX_PAGES = 240
MAX_DETAIL_PAGES = 750
MAX_DETAIL_PER_HOST = 25

# Search only for explicit historical year references on *official* pages.
# We deliberately do not fabricate season URLs from a future season pattern.
HISTORY_RE = re.compile(
    r"(?i)(?:2025\s*[/\-–]\s*2026|2025\s*[/\-–]\s*26|"
    r"2025-2026|2025-26|2025/26|2026|stagion[ei]|archivi[oi]|"
    r"repertori[oi]|opera|liric[ao]|calendari[oi])"
)
YEAR_RE = re.compile(r"(?i)(?:2025\s*[/\-–]\s*(?:2026|26)|2026)")
HISTORIC_PATH_RE = re.compile(r"(?i)(?:2025|2026|archivio|archiv[ei]|stagion[ei]|calendari[oi])")
NON_EVENT_RE = re.compile(
    r"(?i)(?:privacy|cookie|contatt|staff|sponsor|donazion|login|"
    r"registrazion|biglietteria|abbonamenti|newsletter|facebook|instagram|"
    r"youtube|linkedin|whatsapp|tel:|mailto:)"
)


# Independently checked first-party festival page; these are event-local wall
# clocks, not inferred UTC offsets. Never extrapolate to other dates or sources.
MODENA_2026_OFFICIAL_CLOCKS = {
    ("2026-09-16", "Il cambiamento era incessante"): "20:30",
    ("2026-09-25", "La costanza trionfante"): "20:30",
    ("2026-09-26", "Kammermusik n. 1"): "17:00",
    ("2026-09-26", "Voci inaudite"): "21:30",
    ("2026-09-27", "Kattivissimi and friends… all’Opera"): "17:30",
    ("2026-09-27", "Letteralmente Verdi"): "20:30",
    ("2026-09-30", "Ma l’amor mio non muore!"): "21:00",
    ("2026-10-02", "Viva Verdi"): "20:30",
    ("2026-10-03", "Kammermusik n. 2"): "17:00",
    ("2026-10-04", "Concerto di Gala"): "20:30",
    ("2026-10-09", "A casa Bononcini"): "20:30",
    ("2026-10-10", "Messa da Requiem"): "20:30",
    ("2026-10-11", "Dalla Boemia al Ducato di Modena"): "17:00",
    ("2026-10-12", "Mamma: tributo a Luciano Pavarotti e Henry Mancini"): "20:30",
    ("2026-10-13", "Filarmonie Future"): "20:30",
    ("2026-10-17", "La preghiera nell’opera lirica"): "18:00",
    ("2026-10-17", "Le maschere allo specchio"): "20:30",
    ("2026-11-12", "Caterina Barbieri e Fontanamix ensemble"): "20:30",
}
MODENA_2026_CLOCK_SOURCE = "https://www.teatrocomunalemodena.it/modena-belcanto-festival/"


def reconcile_verified_modena_clocks(facts, source, page_url):
    """Annotate scoped source-time errors without destroying the raw JSON-LD."""
    if (source.get("key") != "modena-teatro-opera-2026-27"
            or urlsplit(page_url).hostname != "www.teatrocomunalemodena.it"):
        return facts
    from scripts.audit_2026_retrospective_reconciliation import norm
    verified = {(day, norm(title)): hour
                for (day, title), hour in MODENA_2026_OFFICIAL_CLOCKS.items()}
    for fact in facts:
        key = (fact.get("date"), norm(unescape(fact.get("event_title") or "")))
        hour = verified.get(key)
        if hour is None or not isinstance(fact.get("starts_at"), str):
            continue
        old = fact["starts_at"]
        try:
            original = datetime.fromisoformat(old.replace("Z", "+00:00"))
            if original.tzinfo is None or original.utcoffset() is None:
                continue
            local = datetime.fromisoformat(f'{key[0]}T{hour}:00').replace(
                tzinfo=ZoneInfo("Europe/Rome"))
        except (ValueError, TypeError):
            continue
        if old != local.isoformat(timespec="seconds"):
            fact["source_original_starts_at"] = old
            fact["starts_at"] = local.isoformat(timespec="seconds")
            fact["official_clock_evidence_url"] = MODENA_2026_CLOCK_SOURCE
            fact["official_clock_correction"] = "verified_local_wall_clock"
    return facts


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.href = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.rows.append((self.href, " ".join("".join(self.parts).split())))
            self.href = None
            self.parts = []


def approved_hosts(config):
    """Group existing approvals by exact hostname; never guess a new domain."""
    groups = defaultdict(list)
    for source in validate_config(config):
        if source["access_status"] == "approved":
            groups[urlsplit(source["official_url"]).hostname].append(source)
    return dict(sorted(groups.items()))


def index_seeds(config, *, max_pages=MAX_INDEX_PAGES):
    """Current indexes plus official origin homepages; deduplicate each host."""
    seen = set()
    seeds = []
    for host, sources in approved_hosts(config).items():
        for source in sources:
            # Reuse approved hosts only, not user-provided or inferred URLs.
            for url in (source["url"], source["official_url"]):
                key = (host, url)
                if key not in seen and valid_official_url(url, source["official_url"]):
                    seen.add(key)
                    seeds.append((source, url))
    if len(seeds) > max_pages:
        raise ValueError("too many approved starting pages; no silent truncation")
    return sorted(seeds, key=lambda s: (urlsplit(s[1]).hostname, s[1]))


def candidate_links(html, page_url, official_url):
    parser = Anchors()
    parser.feed(html)
    out = {}
    for href, label in parser.rows:
        if not isinstance(href, str):
            continue
        url = urljoin(page_url, href).split("#", 1)[0]
        if not valid_official_url(url, official_url):
            continue
        if NON_EVENT_RE.search(urlsplit(url).path):
            continue
        if not HISTORY_RE.search(url + " " + label):
            continue
        if url == page_url:
            continue
        # Link label may identify a season, even if its URL is opaque.
        explicit = bool(YEAR_RE.search(url + " " + label))
        category = "historical_year" if explicit else (
            "archive_or_season_lead" if HISTORIC_PATH_RE.search(url) else "generic_opera_lead"
        )
        if url not in out or (explicit and out[url]["category"] != "historical_year"):
            out[url] = {"url": url, "label": label[:180], "category": category}
    return sorted(out.values(), key=lambda row: (row["category"] != "historical_year", row["url"]))


def first_pass(config, *, fetch_page=fetch, workers=MAX_WORKERS):
    seeds = index_seeds(config)
    def scan(seed):
        source, url = seed
        row = {"source_key": source["key"], "seed_url": url,
               "official_url": source["official_url"]}
        try:
            html = fetch_page(source, url)
            row.update(status="scanned",
                       links=candidate_links(html, url, source["official_url"]))
        except Exception as exc:
            if not isinstance(exc, (ValueError, OSError, RuntimeError)):
                raise
            row.update(status="unverified", failure=type(exc).__name__, links=[])
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(scan, seeds))


def queue_historical_indexes(seeds, *, limit=MAX_INDEX_PAGES, offset=0):
    if offset < 0 or limit < 1:
        raise ValueError('invalid archive pagination')
    """Prioritize explicit years, then archive paths; never flood a host."""
    priorities = {}
    for row in seeds:
        for candidate in row["links"]:
            if candidate["category"] == "generic_opera_lead":
                continue
            url = candidate["url"]
            host = urlsplit(url).hostname
            # First prioritize the missing Jan-Jun 2026 season, ahead of
            # 2026/27 pages that the ordinary live scanner already knows.
            rank = (0 if re.search(r"2025[^0-9]{0,5}(?:2026|26)", url)
                    else 1 if candidate["category"] == "historical_year" else 2)
            old = priorities.get(url)
            if old is None or rank < old[0]:
                priorities[url] = (rank, row["source_key"],
                                   {"key": row["source_key"],
                                    "official_url": row["official_url"],
                                    "access_status": "approved"})
    ordered = [(source, url, rank, key) for url, (rank, key, source)
               in sorted(priorities.items(), key=lambda kv: (kv[1][0], kv[0]))]
    return ordered[offset:offset + limit], max(0, len(ordered) - offset - limit)


def second_pass(queue, *, fetch_page=fetch, workers=MAX_WORKERS):
    def scan(task):
        source, url, rank, key = task
        row = {"source_key": key, "archive_url": url, "rank": rank}
        try:
            html = fetch_page(source, url)
            links = candidate_links(html, url, source["official_url"])
            # Only the lead collection, never certify the archive as complete.
            row.update(status="scanned", links=links,
                       event_facts=reconcile_verified_modena_clocks(
                           clean_facts(parse_event_facts(html)),source,url))
        except Exception as exc:
            if not isinstance(exc, (ValueError, OSError, RuntimeError)):
                raise
            row.update(status="unverified", failure=type(exc).__name__,
                       links=[], event_facts=[])
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(scan, queue))


def queue_details(seed_rows, archive_rows, config, *, limit=MAX_DETAIL_PAGES,
                  host_offset=0):
    if host_offset < 0 or limit < 1:
        raise ValueError('invalid detail pagination')
    by_host = {urlsplit(s["official_url"]).hostname:s
               for sources in approved_hosts(config).values() for s in sources}
    # Restrict to links discovered in a 2025/26 or 2026 archive page.
    # Generic 'opera' links from unrelated current season pages stay out.
    candidates = {}
    for row in archive_rows:
        if row["status"] != "scanned":
            continue
        for link in row["links"]:
            url = link["url"]
            host = urlsplit(url).hostname
            source = by_host.get(host)
            if source is None or not valid_official_url(url, source["official_url"]):
                continue
            if excluded_nonopera(row["source_key"], url):
                continue
            if link["category"] == "generic_opera_lead" or YEAR_RE.search(url):
                candidates.setdefault(url, (source, url, row["archive_url"]))
    for row in seed_rows:
        for link in row["links"]:
            if link["category"] != "historical_year":
                continue
            url = link["url"]
            host = urlsplit(url).hostname
            source = by_host.get(host)
            if source and not excluded_nonopera(row["source_key"], url):
                candidates.setdefault(url, (source, url, row["seed_url"]))
    counts=defaultdict(int)
    selected=[]
    deferred_host=defaultdict(int)
    for source,url,discovered_from in sorted(candidates.values(), key=lambda x:x[1]):
        host=urlsplit(url).hostname
        counts[host]+=1
        if counts[host] <= host_offset:
            continue
        if counts[host] > host_offset + MAX_DETAIL_PER_HOST:
            deferred_host[host]+=1
            continue
        selected.append((source,url,discovered_from))
    overflow = {"per_host":dict(sorted(deferred_host.items())),
                "global":max(0,len(selected)-limit)}
    return selected[:limit], overflow


def details_batch(queue, *, fetch_page=fetch, workers=MAX_WORKERS):
    def scan(task):
        source,url,from_url=task
        row={"source_url":url,"source_key":source["key"],"discovered_from":from_url}
        try:
            html=fetch_page(source,url)
            row.update(status="scanned",
                       facts=reconcile_verified_modena_clocks(
                           clean_facts(parse_event_facts(html)),source,url))
        except Exception as exc:
            if not isinstance(exc,(ValueError,OSError,RuntimeError)):
                raise
            row.update(status="unverified",failure=type(exc).__name__,facts=[])
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(scan,queue))


def create_report(config, venues, *, fetch_page=fetch, workers=MAX_WORKERS,
                  max_detail_pages=MAX_DETAIL_PAGES,
                  archive_offset=0, detail_host_offset=0):
    seeds=first_pass(config,fetch_page=fetch_page,workers=workers)
    archives_queue,archive_overflow=queue_historical_indexes(seeds,offset=archive_offset)
    archives=second_pass(archives_queue,fetch_page=fetch_page,workers=workers)
    details_queue,details_overflow=queue_details(seeds,archives,config,limit=max_detail_pages,
                                                host_offset=detail_host_offset)
    details=details_batch(details_queue,fetch_page=fetch_page,workers=workers)
    # Host association is tentative: multi-site venues and festivals are separate.
    source_hosts=set(approved_hosts(config))
    venue_rows=[{"venue_id":v["id"],"venue":v["name"],"city":v.get("city"),
                 "official_host":urlsplit(v.get("website") or "").hostname,
                 "has_matching_approved_host":urlsplit(v.get("website") or "").hostname in source_hosts,
                 "complete_2026_calendar_verified":False}
                for v in venues.get("venues",[])]
    facts=[{"source_url":row["source_url"],"source_key":row["source_key"],
            "discovered_from":row["discovered_from"],**fact}
           for row in details for fact in row["facts"]]
    facts += [{"source_url":row["archive_url"],"source_key":row["source_key"],
               "discovered_from":row["archive_url"],**fact}
              for row in archives for fact in row["event_facts"]]
    return {
        "schema_version":1,"year":2026,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,"complete_seasons_certified":0,
        "archive_offset":archive_offset,"detail_host_offset":detail_host_offset,
        "approved_hosts":len(source_hosts),
        "seed_pages_attempted":len(seeds),
        "seed_pages_scanned":sum(r["status"]=="scanned" for r in seeds),
        "historical_archives_attempted":len(archives),
        "historical_archives_scanned":sum(r["status"]=="scanned" for r in archives),
        "detail_pages_attempted":len(details),
        "detail_pages_scanned":sum(r["status"]=="scanned" for r in details),
        "unverified_2026_facts":facts,
        "archive_queue_deferred":archive_overflow,"detail_queue_deferred":details_overflow,
        "venues":venue_rows,"seed_results":seeds,
        "archive_results":archives,"detail_results":details,
        "warning":"Archive discovery is not a verified annual denominator. Every fact needs public-audience, genre, venue and exact-time reconciliation; no automatic promotion.",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    parser.add_argument("--workers",type=int,default=MAX_WORKERS)
    parser.add_argument("--max-detail-pages",type=int,default=MAX_DETAIL_PAGES)
    parser.add_argument("--archive-offset",type=int,default=0)
    parser.add_argument("--detail-host-offset",type=int,default=0)
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    if not args.allow_network:
        parser.error("Explicit --allow-network required")
    if not 1 <= args.workers <= MAX_WORKERS or not 1 <= args.max_detail_pages <= MAX_DETAIL_PAGES or args.archive_offset < 0 or args.detail_host_offset < 0:
        parser.error("Limits exceeded")
    config=json.loads(SOURCES.read_text(encoding="utf-8"))
    venues=json.loads(VENUES.read_text(encoding="utf-8"))
    result=create_report(config,venues,workers=args.workers,
                         max_detail_pages=args.max_detail_pages,
                         archive_offset=args.archive_offset,
                         detail_host_offset=args.detail_host_offset)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("approved_hosts","seed_pages_scanned",
        "historical_archives_scanned","detail_pages_scanned","complete_seasons_certified")}))


if __name__=="__main__":
    main()
