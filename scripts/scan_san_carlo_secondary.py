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
from urllib.parse import urlsplit

from opera_atlas.controlled_fetch import fetch_official_html
from opera_atlas.db import connect, migrate

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
    """Emit only meaningful headings and links; ignore decorative HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.stack = []
        self.skip = 0
        self.capture = None
        self.buffer = []
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        if self.skip:
            return
        if tag in ("h2", "h3", "a") and self.capture is None:
            self.capture = tag
            self.buffer = []
            self.href = dict(attrs).get("href") if tag == "a" else None

    def handle_data(self, data):
        if self.skip:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self.capture is not None:
            self.buffer.append(value)
        else:
            self.items.append(("text", value, None))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip = max(0, self.skip - 1)
            return
        if self.capture == tag:
            value = " ".join(self.buffer).strip()
            if value:
                self.items.append((tag, value, self.href))
            self.capture, self.buffer, self.href = None, [], None


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


def parse(html: str, *, url: str = URL) -> list[dict]:
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
        if not current["composer"] or not current["venue_verified"] or not current["performances"]:
            raise ValueError("secondary production lacks composer, venue or exact recite")
        blocks.append(current)

    for kind, value, href in items:
        if kind == "h2":
            if current is not None:
                finish()
            composer = _composer(recent)
            if not composer:
                current = None
                accepting_dates = False
                continue
            current = {
                "title": value,
                "composer": composer,
                "venue": VENUE,
                "city": CITY,
                "venue_verified": False,
                "performances": [],
                "secondary_source": url,
                "review_status": "needs_primary_corroboration",
            }
            accepting_dates = False
            recent = []
            continue
        if current is None:
            recent.append((kind, value, href))
            recent = recent[-12:]
            continue
        if kind == "h3":
            accepting_dates = value.casefold() == "recite"
        if value == VENUE:
            current["venue_verified"] = True
        if kind == "a" and accepting_dates:
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
                raise ValueError("duplicate secondary recita")
            current["performances"].append(record)
        recent.append((kind, value, href))
        recent = recent[-12:]
    if current is not None:
        finish()
    if not blocks or len(blocks) > 35:
        raise ValueError("secondary opera season not confirmed")
    identities = [(b["title"].casefold(), b["composer"].casefold()) for b in blocks]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate secondary production")
    for b in blocks:
        del b["venue_verified"]
        b["performances"].sort(key=lambda v: (v["date"], v["time"]))
    return blocks


def main():
    parser = argparse.ArgumentParser(description="San Carlo secondary single-source dry-run")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args()
    if not args.allow_network or not args.dry_run:
        parser.error("the secondary probe requires --allow-network --dry-run")
    db = connect()
    try:
        migrate(db)
        origin = "https://www.classicalive.it/"
        db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')", (origin,))
        row = db.execute("SELECT id FROM sources WHERE official_url=?", (origin,)).fetchone()
        response = fetch_official_html(db, source_id=row["id"], url=URL, network_enabled=True)
    finally:
        db.close()
    productions = parse(response.html)
    print(json.dumps({
        "source": URL,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dry_run": True,
        "source_role": "secondary_unverified",
        "status": "candidates_only",
        "productions": productions,
        "production_count": len(productions),
        "performance_count": sum(len(x["performances"]) for x in productions),
        "published": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
