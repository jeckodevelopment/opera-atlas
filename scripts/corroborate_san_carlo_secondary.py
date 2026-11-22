"""Cross-check San Carlo secondary opera dates against an independent calendar.

No first-party evidence is fabricated: reports may enrich review, NEVER write
canonical candidates, verified facts or published recite. Differing clocks
remain explicitly conflicted. The official repertoire must be checked
separately before canonical promotion.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.controlled_fetch import fetch_official_html
from opera_atlas.db import connect, migrate
from scripts.daily_ingest import _write_atomic
from scripts.publish_catalog_v2 import ROOT

SOURCE = "https://www.enjoylive.travel/it/napoli-sancarlo-programma"
CANDIDATES = ROOT / "data/san-carlo-secondary-candidates.json"
REPORT = ROOT / "data/san-carlo-secondary-corroboration.json"
PUBLIC = ROOT / "public/catalog/san-carlo-secondary-corroboration.json"

MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
CLOCK = re.compile(r"(?<!\d)(\d{1,2})\s*\(\s*(\d{1,2})h(\d{2})\s*(am|pm)\b", re.I)
MONTH_ROW = re.compile(r"(?i)(?:^|\n)\s*(" + "|".join(MONTHS) + r")\s*:\s*([^\n]+)")
YEAR = re.compile(r"20\d{2}")
TITLE_NORMALIZE = re.compile(r"[^a-z0-9]+")


def key_of(value: str) -> str:
    import unicodedata
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(x for x in normalized if not unicodedata.combining(x))
    return TITLE_NORMALIZE.sub(" ", normalized).strip()


class Events(HTMLParser):
    """Collect only visible event headings and their bounded calendar text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self.heading = False
        self.heading_parts: list[str] = []
        self.skip = 0
        self.meta_parts: list[str] = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "noscript"):
            self.skip += 1
        elif not self.skip and tag == "h4":
            self.heading = True
            self.heading_parts = []

    def handle_data(self, data):
        if self.skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self.heading:
            self.heading_parts.append(text)
        elif self.current is not None:
            self.current["parts"].append(text)
        else:
            self.meta_parts.append(text)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript"):
            self.skip = max(self.skip - 1, 0)
            return
        if self.skip:
            return
        if tag == "h4" and self.heading:
            title = " ".join(self.heading_parts)
            self.current = {"title": title, "parts": []}
            self.blocks.append(self.current)
            self.heading = False
        elif tag in ("p", "h5", "h6", "li", "br"):
            if self.current is not None:
                self.current["parts"].append("\n")


def parse_independent(html: str, *, allowed_titles: set[str] | None = None) -> dict[str, dict]:
    page = Events()
    page.feed(html)
    meta = " ".join(page.meta_parts)
    if ("Napoli" not in meta or "San Carlo" not in meta
        or not re.search(r"2026\s*/\s*2027", meta)):
        raise ValueError("independent calendar has no matching venue and season")
    found = {}
    for block in page.blocks:
        title = key_of(block["title"])
        if not title or (allowed_titles is not None and title not in allowed_titles):
            continue
        text = " ".join(block["parts"]).replace(" \n ", "\n").replace("\n ", "\n")
        # This event block can include an h5 month/year heading. Choose
        # years from explicit context, never today's date.
        years = [int(y) for y in YEAR.findall(text)]
        if not years:
            continue
        if len(set(years)) != 1:
            # A compound month header can cross December/January.
            # Do not assign a year when multiple years appear.
            continue
        year = years[0]
        rows = {}
        for match in MONTH_ROW.finditer(text):
            month = MONTHS[match.group(1).casefold()]
            body = match.group(2)
            for d, h, minute, period in CLOCK.findall(body):
                hour = int(h)
                if not 1 <= hour <= 12:
                    raise ValueError("independent invalid 12-hour clock")
                hour = hour % 12 + (12 if period.casefold() == "pm" else 0)
                day = date(year, month, int(d)).isoformat()
                clock = f"{hour:02d}:{minute}"
                if day in rows and rows[day] != clock:
                    raise ValueError("conflicting independent showtimes for same day")
                rows[day] = clock
        if rows:
            if title in found:
                raise ValueError("duplicate independent event title")
            found[title] = {"title": block["title"], "dates": rows}
    if not found:
        raise ValueError("independent calendar has no dated events")
    return found


def compare(candidates: dict, observed: dict[str, dict]) -> dict:
    if (candidates.get("schema_version") != 1
        or candidates.get("source_key") != "napoli-san-carlo-rolling-opera"
        or candidates.get("source_role") != "secondary_unverified"
        or not isinstance(candidates.get("productions"), list)
        or not candidates["productions"]):
        raise ValueError("untrusted San Carlo candidate checkpoint")
    result = []
    seen = set()
    for p in candidates["productions"]:
        if (p.get("corroboration_status") != "pending_independent_event_verification"
            or p.get("venue") != "Teatro di San Carlo" or p.get("city") != "Napoli"):
            raise ValueError("invalid candidate provenance")
        title = key_of(p["title"])
        if title in seen:
            raise ValueError("duplicate candidate work")
        seen.add(title)
        source_dates = {r["date"]: r["time"] for r in p["performances"]}
        if len(source_dates) != len(p["performances"]):
            raise ValueError("duplicate candidate dates")
        counterpart = observed.get(title)
        match, conflict, missing = [], [], []
        if counterpart:
            reference = counterpart["dates"]
            for day, clock in sorted(source_dates.items()):
                other = reference.get(day)
                if other is None:
                    missing.append({"date": day, "candidate": clock})
                elif clock == other:
                    match.append({"date": day, "time": clock})
                else:
                    conflict.append({"date": day, "candidate": clock,
                                     "independent": other})
        else:
            missing = [{"date": day, "candidate": clock}
                       for day, clock in sorted(source_dates.items())]
        result.append({
            "title": p["title"], "composer": p["composer"],
            "candidate_count": len(source_dates),
            "confirmed_matching_clocks": match,
            "conflicting_clocks": conflict,
            "unmatched_clocks": missing,
            "status": ("all_clocks_match_second_source"
                       if len(match) == len(source_dates) else
                       "needs_date_review" if conflict else "incomplete_second_source"),
        })
    return {
        "schema_version": 1,
        "source_key": "napoli-san-carlo-rolling-opera",
        "first_source": candidates["source_url"],
        "second_source": SOURCE,
        "source_independence": "two_secondary_publishers_not_primary_official_evidence",
        "canonical_publication_authorized": False,
        "productions": result,
        "production_count": len(result),
        "matching_recite_count": sum(len(x["confirmed_matching_clocks"]) for x in result),
        "conflicting_recite_count": sum(len(x["conflicting_clocks"]) for x in result),
        "unmatched_recite_count": sum(len(x["unmatched_clocks"]) for x in result),
    }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--sync-review", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("--allow-network is required")
    doc = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    target = urlsplit(SOURCE)
    if target.scheme != "https" or target.hostname != "www.enjoylive.travel":
        raise ValueError("invalid second source")
    db = connect()
    try:
        migrate(db)
        origin = "https://www.enjoylive.travel/"
        db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')", (origin,))
        sid = db.execute("SELECT id FROM sources WHERE official_url=?", (origin,)).fetchone()["id"]
        response = fetch_official_html(db, source_id=sid, url=SOURCE, network_enabled=True)
    finally:
        db.close()
    allowed = {key_of(x["title"]) for x in doc["productions"]}
    result = compare(doc, parse_independent(response.html, allowed_titles=allowed))
    if args.sync_review:
        _write_atomic(REPORT, result)
        _write_atomic(PUBLIC, result)
    print(json.dumps({
        "dry_run": args.dry_run,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "matching_recite_count": result["matching_recite_count"],
        "conflicting_recite_count": result["conflicting_recite_count"],
        "unmatched_recite_count": result["unmatched_recite_count"],
        "canonical_publication_authorized": False,
        "conflicts": [dict(title=p["title"], conflicts=p["conflicting_clocks"])
                      for p in result["productions"] if p["conflicting_clocks"]],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
