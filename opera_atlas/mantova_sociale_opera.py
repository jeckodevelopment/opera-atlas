"""Conservative evergreen opera discovery from the official Teatro Sociale Mantova site.

The official site mixes opera, prose, ballet, concerts and musicals. Index
links are only candidates; detail pages must independently establish opera
genre, composer, theatre and local date/time before being promoted.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

KEY = "mantova-sociale-rolling-opera"
INDEX = "https://www.teatrosocialemantova.it/it-it/ricerca.aspx?fti=opera+lirica"
HOST = "www.teatrosocialemantova.it"
MONTHS = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
          "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
          "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12}
DATE = re.compile(
    r"(?i)\b(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)\s+"
    r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(20\d{2})\s+ore\s+"
    r"([01]?\d|2[0-3]):([0-5]\d)\b"
)


class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.parts = []
        self.headings = []
        self._heading = False
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "h1" and not self._skip:
            self._heading = True
        if tag == "a" and not self._skip:
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "h1":
            self._heading = False
        if tag in ("script", "style", "noscript"):
            self._skip = max(self._skip - 1, 0)

    def handle_data(self, data):
        if self._skip:
            return
        value = " ".join(data.split())
        if value:
            self.parts.append(value)
            if self._heading:
                self.headings.append(value)


def eligible_detail(url: str) -> bool:
    value = urlsplit(url)
    if (value.scheme != "https" or value.hostname != HOST or value.fragment
        or value.port is not None or value.username or value.password):
        return False
    if not re.fullmatch(r"/it-it/[a-z0-9][a-z0-9-]+\.aspx", value.path):
        return False
    # A link to the search, calendar, or general navigation is not a production.
    if value.path in ("/it-it/ricerca.aspx", "/it-it/spettacoli.aspx",
                      "/it-it/eventi.aspx"):
        return False
    return not value.query or bool(re.fullmatch(
        r"event=[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}",
        value.query))


def extract_index(html: str, *, url: str = INDEX, min_links: int = 1) -> list[str]:
    if url != INDEX:
        raise ValueError("unapproved Mantova official opera search")
    page = Reader()
    page.feed(html)
    links = sorted({candidate for href in page.links
                    if eligible_detail(candidate := urljoin(INDEX, href))})
    if len(links) < min_links:
        raise ValueError("Mantova official opera candidate links missing")
    return links


def parse_detail(html: str, *, url: str) -> tuple[str, str, str, list[tuple[str, str]]]:
    if not eligible_detail(url):
        raise ValueError("unapproved Mantova event URL")
    page = Reader()
    page.feed(html)
    if len(page.headings) != 1:
        raise ValueError("Mantova opera heading missing or ambiguous")
    title = page.headings[0].strip()
    visible = " ".join(page.parts)
    # Only inspect the event's own heading/date/description, not the footer,
    # navigation or next/previous event teasers.
    begin = next((i for i, part in enumerate(page.parts) if part == title), None)
    if begin is None:
        raise ValueError("Mantova event body missing")
    primary = " ".join(page.parts[begin:begin + 85]).split("precedente:", 1)[0]
    if not re.search(r"\b(?:opera lirica|repertorio operistico|grande lirica|melodramma)\b",
                     primary, re.I):
        raise ValueError("Mantova event not independently verified as opera")
    if re.search(r"\b(?:musical|gala lirico|galà lirico|concerto di arie)\b",
                 title + " " + primary[:220], re.I):
        raise ValueError("Mantova concert or musical is not an opera")
    credits = re.findall(r"\b(?:di|composta da|musica di)\s+"
                         r"(Giuseppe Verdi|Giacomo Puccini|Wolfgang Amadeus Mozart|"
                         r"Gaetano Donizetti|Gioachino Rossini|Vincenzo Bellini|"
                         r"Richard Wagner|Pietro Mascagni|Ruggero Leoncavallo)\b",
                         primary, re.I)
    if len(set(x.casefold() for x in credits)) != 1:
        raise ValueError("Mantova composer not unambiguously credited")
    if not re.search(r"\bTeatro Sociale di Mantova\b", primary, re.I):
        raise ValueError("Mantova official venue missing")
    matches = DATE.findall(primary)
    if not matches or len(matches) > 16:
        raise ValueError("Mantova date/time not verified")
    rows = set()
    for d, month, year, hh, mm in matches:
        try:
            iso = date(int(year), MONTHS[month.casefold()], int(d)).isoformat()
        except ValueError as exc:
            raise ValueError("invalid Mantova recital date") from exc
        rows.add((iso, f"{int(hh):02d}:{mm}"))
    if len(rows) != len(matches):
        # The event may repeat date/time in the prose: allow identical copies.
        if len(rows) != 1:
            raise ValueError("ambiguous Mantova recitals")
    composer = next(iter(credits))
    # Only source-credited names are published; the canonical work resolver
    # independently confirms work/composer identity.
    return title.capitalize() if title.isupper() else title, composer, "Teatro Sociale", sorted(rows)
