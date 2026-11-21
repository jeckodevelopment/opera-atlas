"""Strict exact-showtime parser for Teatro Massimo Bellini Catania.

The venue and work identity must be first-party evidence; a season overview,
an un-dated range, a ballet or an alternate Catania venue is never enough.
"""
from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.national_detail_parser import clean, MONTHS

HOST = "www.teatromassimobellini.it"
SOURCE_KEY = "bellini-catania-opera-2026-27"
VENUE = "Teatro Massimo Bellini"

WEEKDAYS = r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
MONTHS_LONG = r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"


class Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1 = []
        self.current = None
        self.value = []
    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.current = "h1"
            self.value = []
    def handle_data(self, data):
        if self.current:
            self.value.append(data)
    def handle_endtag(self, tag):
        if tag == self.current:
            self.h1.append(" ".join(" ".join(self.value).split()))
            self.current = None


def parse_detail(html: str, *, url: str) -> tuple[str, str, str, list[tuple[str, str]]]:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != HOST or parsed.query or
        parsed.fragment or parsed.username or parsed.password or parsed.port or
        not re.fullmatch(r"/eventi/[a-z0-9-]+/", parsed.path)):
        raise ValueError("invalid official Bellini event detail URL")
    heading = Headings()
    heading.feed(html)
    titles = [h for h in heading.h1 if h]
    if len(titles) != 1:
        raise ValueError("ambiguous Bellini work title")
    title = titles[0]
    body = clean(html)
    # Real venue is per-event. The opera season may also run at Metropolitan
    # or Sangiorgi, and neither must be falsely attributed to Bellini.
    venue_block = re.search(r"\bLuogo\s+(.+?)\s+Categoria\b", body, re.I)
    if not venue_block or not re.match(r"^Teatro Massimo Bellini\b", venue_block.group(1), re.I):
        raise ValueError("event is not at Teatro Massimo Bellini")
    kind = re.search(r"\bCategoria\s+(.+?)\s+Data\b", body, re.I)
    if not kind or "opere" not in kind.group(1).casefold():
        raise ValueError("not an explicitly classified opera event")
    composer_match = re.search(
        r"\bMusica di\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+){1,3})",
        body)
    if not composer_match:
        raise ValueError("official composer missing")
    composer = composer_match.group(1)
    # The range in the metadata ('Feb 14 - 21 2027') is not evidence
    # for individual daily recite. Parse only the signed programme below
    # the "Prima rappresentazione" heading and before global navigation.
    match = re.search(r"\bPrima rappresentazione\b(.*?)\bNaviga sul sito\b", body, re.I)
    if not match:
        raise ValueError("bounded official recite programme missing")
    section = match.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b", section):
        raise ValueError("cancellation or postponement needs reconciliation")
    rx = re.compile(
        rf"(?i)\b{WEEKDAYS}\s+(\d{{1,2}})\s+({MONTHS_LONG})\s+(20\d{{2}})"
        r"\s+ore\s+([01]?\d|2[0-3])[.:]([0-5]\d)\s*\(Turno\s+[A-Z0-9]+\)")
    found = {}
    for day, month, year, hour, minute in rx.findall(section):
        iso = date(int(year), MONTHS[month.casefold()], int(day)).isoformat()
        if iso[:4] not in ("2026", "2027"):
            raise ValueError("unexpected season year")
        clock = f"{int(hour):02d}:{minute}"
        if iso in found:
            raise ValueError("duplicate or conflicting official recital")
        found[iso] = clock
    if not found or len(found) > 20:
        raise ValueError("missing or implausible individual recital dates")
    # Each textual 'ore' in this section must correspond to one recital.
    # This deliberately fails if the theatre changes the per-turn schema.
    if len(re.findall(r"\bore\s+[01]?\d|2[0-3]", section, re.I)) != len(found):
        raise ValueError("incomplete official Bellini showtime extraction")
    return title, composer, VENUE, sorted(found.items())
