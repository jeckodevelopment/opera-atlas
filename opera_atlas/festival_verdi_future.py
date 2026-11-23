"""Official Festival Verdi edition index, independent of the Regio opera season.

Only edition-specific /categoria-spettacoli/edizione-YY-festival-verdi/ pages
may claim festival membership. Detail pages must separately verify work,
composer, venue and exact showtimes before any canonical promotion.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

from opera_atlas.national_detail_parser import clean, parse_national_showtimes
from opera_atlas.work_identity import resolve_work

HOST = "teatroregioparma.it"
KEY = "festival-verdi-rolling"
EDITION = re.compile(r"/categoria-spettacoli/edizione-(\d{2})-festival-verdi/")
DETAIL = re.compile(r"/spettacolo/([a-z0-9-]+)/?")
NON_OPERA = re.compile(
    r"(?i)\b(?:gala|concerto|messa|requiem|coro|prova|under\s*30|"
    r"ramificazioni|verdi\s*off|danza|incontri?|guida|laboratorio|"
    r"quartetto|filarmonica|saggio|scuola|recital|fuoco\s*di\s*gioia)\b"
)


def edition_year(url: str) -> int:
    p = urlsplit(url)
    m = EDITION.fullmatch(p.path)
    if (p.scheme != "https" or p.hostname != HOST or not m or p.query
            or p.fragment or p.port is not None or p.username or p.password):
        raise ValueError("Festival Verdi index must be an official year-scoped page")
    year = 2000 + int(m[1])
    if not 2027 <= year <= 2099:
        raise ValueError("unsupported Festival Verdi edition")
    return year


def next_edition(url: str) -> str | None:
    try:
        year = edition_year(url)
    except ValueError:
        return None
    if year >= 2099:
        return None
    return f"https://{HOST}/categoria-spettacoli/edizione-{(year+1)%100:02d}-festival-verdi/"


def eligible_detail(url: str) -> bool:
    p = urlsplit(url)
    return bool(p.scheme == "https" and p.hostname == HOST
                and DETAIL.fullmatch(p.path) and not p.query and not p.fragment
                and p.username is None and p.password is None and p.port is None)


class _EditionLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = False
        self.heading_parts = []
        self.in_programme = False
        self.anchor = None
        self.parts = []
        self.links = []
        self.done = False

    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.heading = True
            self.heading_parts = []
        elif tag == "a" and self.in_programme and not self.done:
            self.anchor = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.heading:
            self.heading_parts.append(data)
        if self.anchor is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "h1" and self.heading:
            if re.fullmatch(r"(?i)\s*Festival\s+Verdi\s*", " ".join(self.heading_parts)):
                self.in_programme = True
            self.heading = False
        elif tag == "a" and self.anchor is not None:
            label = " ".join(" ".join(self.parts).split())
            if re.search(r"(?i)\bGALA\s+VERDIANO\b", label):
                self.done = True
            elif (label and len(label) <= 90 and not NON_OPERA.search(label)
                  and label.casefold() not in {"info", "scopri", "ticket", "biglietti"}):
                self.links.append((self.anchor, label))
            self.anchor = None


def extract_index(html: str, *, url: str, min_links: int) -> list[str]:
    year = edition_year(url)
    text = clean(html)
    # A navigation link to the current year cannot substitute for a complete
    # page heading and an opera programme for the requested year.
    if not re.search(r"(?i)\bFestival Verdi\b", text[:2800]):
        raise ValueError("Festival Verdi programme heading absent")
    parser = _EditionLinks()
    parser.feed(html)
    if not parser.in_programme:
        raise ValueError("Festival Verdi edition programme heading absent")
    result = set()
    for href, label in parser.links:
        target = urljoin(url, href)
        if eligible_detail(target):
            result.add(target)
    if len(result) < min_links:
        raise ValueError("Festival Verdi official opera index incomplete")
    return sorted(result)


def parse_detail(html: str, *, url: str, year: int, registry: dict) -> list[dict]:
    """Require official title, Verdi composer, exact venue, and timed dates.

    Unknown operas are left for normal authority review rather than invented.
    """
    if not eligible_detail(url) or not 2027 <= year <= 2099:
        raise ValueError("unapproved Festival Verdi opera detail")
    from scripts.collect_candidate_details import FirstHeading
    from scripts.build_verified_catalog import official_local_time
    heading = FirstHeading()
    heading.feed(html)
    title = heading.first
    if not title or NON_OPERA.search(title):
        raise ValueError("nonopera or unverified festival detail")
    text = clean(html)
    first = text[:1900]
    if not re.search(r"(?i)\bGiuseppe Verdi\b", first):
        raise ValueError("composer not verified on official page")
    if not re.search(rf"\b{year}\b", first):
        raise ValueError("festival detail year not confirmed")
    work = resolve_work(registry, title, "Giuseppe Verdi")
    if work is None:
        return []  # Unknown Verdi works require authority reconciliation.
    section = text.split("Musica Giuseppe Verdi", 1)
    if len(section) != 2:
        raise ValueError("Festival Verdi official composer credit absent")
    venue_hits = set(re.findall(r"\bTeatro (?:Regio di Parma|Giuseppe Verdi(?: di Busseto)?)\b",
                               section[1].split("Ticket a partire", 1)[0]))
    if len(venue_hits) != 1:
        raise ValueError("Festival Verdi theatre ambiguous")
    venue = ("Teatro Giuseppe Verdi" if "Giuseppe Verdi" in next(iter(venue_hits))
             else "Teatro Regio di Parma")
    dates = parse_national_showtimes(
        html, source_key="parma-opera-2027", url=url,
        title=work["title"] if title.casefold() == work["title"].casefold() else title,
        composer="Giuseppe Verdi")
    # Reject cancelled/under-30 cards through existing strict showtime parser.
    if not dates or any(not day.startswith(str(year)) for day, _ in dates):
        raise ValueError("no verified Festival Verdi showtimes for edition")
    return [{"event_title": work["title"], "composer": "Giuseppe Verdi",
             "venue": venue, "date": day,
             "starts_at": official_local_time(day, clock)} for day, clock in dates]
