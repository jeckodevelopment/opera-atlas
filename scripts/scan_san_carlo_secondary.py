"""Read-only secondary season discovery for Napoli San Carlo.

ClassicaLive is a secondary calendar, NEVER proof sufficient to publish recite.
This probe is isolated from the national discovery and catalog workflows.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from opera_atlas.napoli_san_carlo import eligible_detail

from opera_atlas.controlled_fetch import fetch_official_html
from opera_atlas.db import connect, migrate
from scripts.publish_catalog_v2 import ROOT
from scripts.daily_ingest import _write_atomic

CANDIDATES = ROOT / 'data/san-carlo-secondary-candidates.json'
PUBLIC_CANDIDATES = ROOT / 'public/catalog/san-carlo-secondary-candidates.json'
HEALTH = ROOT / 'data/san-carlo-secondary-health.json'

URL = "https://www.classicalive.it/it/rassegne/teatro-di-san-carlo/stagione-dopera-2026-2027/"
VENUE = "Teatro di San Carlo"
CITY = "Napoli"
MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
DAYS = {"lun": 0, "mar": 1, "mer": 2, "gio": 3, "ven": 4, "sab": 5, "dom": 6}
SHOWTIME = re.compile(
    r"^(Lun|Mar|Mer|Gio|Ven|Sab|Dom)\s+(\d{1,2})\s+"
    r"(" + "|".join(MONTHS) + r")\s+(20\d{2})\s+([01]?\d|2[0-3]):([0-5]\d)$",
    re.I,
)
SEASON = re.compile(r"^/it/rassegne/teatro-di-san-carlo/stagione-dopera-20\d{2}-20\d{2}/$")
NOISE = re.compile(r"\b(?:recite|prossima|direttore|regia|napoli|teatro|stagione|conclusa|biglietti)\b", re.I)
RANGE = re.compile(r"^\d{1,2}\s+\w+\s*[–-]\s*\d{1,2}\s+\w+\s+20\d{2}$")


class CalendarReader(HTMLParser):
    """Read nested heading/link structures without swallowing inner elements.

    The prior parser captured an outer anchor and hid nested h2/h3 nodes.
    Direct visible text is emitted independently of semantic tag closures.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.frames = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        if self.skip:
            return
        if tag in ("h2", "h3", "h4", "a"):
            self.frames.append({
                "tag": tag, "parts": [],
                "href": dict(attrs).get("href") if tag == "a" else None,
            })

    def handle_data(self, data):
        if self.skip:
            return
        value = " ".join(data.split())
        if not value:
            return
        self.items.append(("text", value, None))
        for frame in self.frames:
            frame["parts"].append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip = max(0, self.skip - 1)
            return
        for i in range(len(self.frames) - 1, -1, -1):
            if self.frames[i]["tag"] == tag:
                frame = self.frames.pop(i)
                value = " ".join(frame["parts"]).strip()
                if value:
                    self.items.append((tag, value, frame["href"]))
                break


def _composer(items):
    """Read nearby composer credit, not arbitrary cast metadata."""
    for kind, value, _ in reversed(items[-9:]):
        if kind not in ("text", "a") or RANGE.match(value) or NOISE.search(value):
            continue
        if len(value) > 90 or len(value) < 7 or any(c.isdigit() for c in value):
            continue
        names = value.replace(" / ", " ").split()
        if len(names) >= 2 and all(word[0].isupper() for word in names if word):
            return value
    return None


def parse(html: str, *, url: str = URL, diagnostics: list | None = None) -> list[dict]:
    target = urlsplit(url)
    if target.scheme != "https" or target.hostname != "www.classicalive.it" or (
        not SEASON.fullmatch(target.path)
        or target.query or target.fragment or target.port is not None
        or target.username is not None or target.password is not None
    ):
        raise ValueError("unapproved secondary season URL")
    p = CalendarReader()
    p.feed(html)
    items = p.items
    if ("text", VENUE, None) not in items or not any(
        CITY.lower() == value.lower() for _, value, _ in items
    ):
        raise ValueError("secondary calendar does not identify San Carlo in Napoli")
    blocks = []
    current = None
    recent = []
    accepting_dates = False

    def finish():
        if current is None:
            return
        missing = [field for field, ok in (
            ("composer", current["composer"]),
            ("venue", current["venue_verified"]),
            ("official_ticket", current["official_event_url"]),
            ("recite", current["performances"]),
        ) if not ok]
        if missing:
            if diagnostics is not None:
                diagnostics.append({"heading": current["title"], "missing": missing})
            # A page can contain unrelated headings, closed seasons and
            # incomplete blocks. Never invent missing facts, and report them
            # separately from verified candidate records.
            return
        blocks.append(current)

    latest_date_text = None
    for kind, value, href in items:
        if kind == "h2":
            if current is not None:
                finish()
            composer = _composer([part for part in recent if part[1] != value])
            if not composer:
                current = None
                accepting_dates = False
                continue
            current = {
                "title": value,
                "composer": composer,
                "venue": VENUE,
                "city": CITY,
                "official_event_url": None,
                "venue_verified": False,
                "performances": [],
                "secondary_source": url,
                "review_status": "needs_primary_corroboration",
            }
            accepting_dates = False
            latest_date_text = None
            recent = []
            continue
        if current is None:
            recent.append((kind, value, href))
            recent = recent[-12:]
            continue
        if value.strip().casefold() == "recite":
            accepting_dates = True
        elif re.search(r"^(direzione e compagnie|personaggi e interpreti)$", value, re.I):
            accepting_dates = False
        if value.strip() == VENUE or (VENUE in value and len(value) < 80):
            current["venue_verified"] = True
        if kind in ("a", "text") and accepting_dates:
            m = SHOWTIME.fullmatch(value)
            if not m:
                continue
            weekday, day, month, year, hour, minute = m.groups()
            d = date(int(year), MONTHS[month.lower()], int(day))
            if d.weekday() != DAYS[weekday.lower()]:
                raise ValueError("secondary weekday/date mismatch")
            clock = f"{int(hour):02d}:{minute}"
            record = {"date": d.isoformat(), "time": clock}
            if record in current["performances"]:
                # Nested anchors emit their visible text before the enclosing
                # anchor closes. Suppress only the same anchor echo, never a
                # second independently listed performance.
                if kind == "a" and latest_date_text == record:
                    continue
                raise ValueError("duplicate secondary recita")
            current["performances"].append(record)
            latest_date_text = record if kind == "text" else None
        recent.append((kind, value, href))
        recent = recent[-12:]
    if current is not None:
        finish()
    if not blocks or len(blocks) > 35:
        # Metadata only: preserve diagnostic distinctions without copying HTML.
        observed = {"headings": sum(k == "h2" for k, _, _ in items),
                    "showtime_texts": sum(bool(SHOWTIME.fullmatch(v)) for k, v, _ in items if k == "text"),
                    "incomplete": (diagnostics or [])[:12]}
        raise ValueError("secondary opera season not confirmed: " + json.dumps(observed, ensure_ascii=False))
    identities = [(b["title"].casefold(), b["composer"].casefold()) for b in blocks]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate secondary production")
    for b in blocks:
        del b["venue_verified"]
        b["performances"].sort(key=lambda v: (v["date"], v["time"]))
    return blocks


def build_secondary_checkpoint(productions: list[dict], *, checked_at: str,
                               incomplete: list[dict]) -> tuple[dict, dict]:
    """Cross-source review input, never a first-party canonical observation.

    The routine deliberately does not write the official candidate/evidence
    registries: these rows cannot pass the publishing gate until corroborated.
    """
    if not productions:
        raise ValueError("refuse empty secondary candidate checkpoint")
    records = []
    identities = set()
    for production in productions:
        if (production.get("review_status") != "needs_primary_corroboration"
            or production.get("venue") != VENUE
            or production.get("city") != CITY
            or production.get("secondary_source") != URL
            or not eligible_detail(production.get("official_event_url") or "")
            or not production.get("title") or not production.get("composer")
            or not production.get("performances")):
            raise ValueError("untrusted secondary candidate")
        identity = (production["title"].casefold(), production["composer"].casefold())
        if identity in identities:
            raise ValueError("duplicate secondary candidate identity")
        identities.add(identity)
        clocks = set()
        for recita in production["performances"]:
            if not isinstance(recita, dict) or set(recita) != {"date", "time"}:
                raise ValueError("untrusted secondary clock")
            day = date.fromisoformat(recita["date"])
            clock = recita["time"]
            if (not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clock)
                or day.isoformat() != recita["date"]
                or (recita["date"], clock) in clocks):
                raise ValueError("invalid or duplicate secondary clock")
            clocks.add((recita["date"], clock))
        records.append({
            "title": production["title"],
            "composer": production["composer"],
            "venue": VENUE, "city": CITY,
            "performances": sorted(production["performances"],
                                   key=lambda row: (row["date"], row["time"])),
            "secondary_source": URL,
            "official_event_url": production["official_event_url"],
            "corroboration_status": "pending_independent_event_verification",
        })
    records.sort(key=lambda x: (x["title"].casefold(), x["composer"].casefold()))
    checkpoint = {
        "schema_version": 1,
        "source_key": "napoli-san-carlo-rolling-opera",
        "source_role": "secondary_unverified",
        "source_url": URL,
        "productions": records,
    }
    health = {
        "schema_version": 1, "checked_at": checked_at,
        "source_key": "napoli-san-carlo-rolling-opera",
        "outcome": "acquired_pending_primary_corroboration",
        "production_count": len(records),
        "performance_count": sum(len(p["performances"]) for p in records),
        "incomplete_sections": incomplete,
        "published": False,
    }
    return checkpoint, health


def main():
    parser = argparse.ArgumentParser(description="San Carlo secondary single-source dry-run")
    parser.add_argument("--allow-network", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--sync-candidates", action="store_true")
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("explicit --allow-network is required")
    db = connect()
    try:
        migrate(db)
        origin = "https://www.classicalive.it/"
        db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')", (origin,))
        row = db.execute("SELECT id FROM sources WHERE official_url=?", (origin,)).fetchone()
        response = fetch_official_html(db, source_id=row["id"], url=URL, network_enabled=True)
    finally:
        db.close()
    skipped = []
    productions = parse(response.html, diagnostics=skipped)
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    checkpoint, health = build_secondary_checkpoint(productions, checked_at=checked_at, incomplete=skipped)
    if args.sync_candidates:
        _write_atomic(CANDIDATES, checkpoint)
        _write_atomic(PUBLIC_CANDIDATES, checkpoint)
        _write_atomic(HEALTH, health)
    print(json.dumps({
        "source": URL,
        "checked_at": checked_at,
        "dry_run": args.dry_run,
        "sync_candidates": args.sync_candidates,
        "source_role": "secondary_unverified",
        "status": "candidates_only",
        "productions": productions,
        "production_count": len(productions),
        "incomplete_sections": skipped,
        "incomplete_section_count": len(skipped),
        "performance_count": sum(len(x["performances"]) for x in productions),
        "published": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
