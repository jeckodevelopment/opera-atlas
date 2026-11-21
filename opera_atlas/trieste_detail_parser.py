"""Strict Teatro Verdi Trieste opera detail parser.

Only the official opera listing and detailed first-party work credit plus
explicit date/time rows count as evidence. No inferred clock or composer.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean, MONTHS, MONTH_RE

KEY = "verdi-trieste-season-2026-27"
HOST = "www.teatroverdi-trieste.com"
WEEKDAY = r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"


class Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tag = None
        self.text = []
        self.h1 = []
    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.tag = tag
            self.text = []
    def handle_data(self, data):
        if self.tag:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == self.tag:
            self.h1.append(" ".join(" ".join(self.text).split()))
            self.tag = None


def parse_detail(html: str, *, url: str) -> tuple[str, str, str, list[tuple[str,str]]]:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != HOST or parsed.query
        or parsed.fragment or parsed.username or parsed.password or parsed.port
        or not re.fullmatch(r"/it/spettacoli/[a-z0-9-]+/", parsed.path)):
        raise ValueError("invalid official Trieste opera detail URL")
    heads = Headings()
    heads.feed(html)
    if len(heads.h1) != 1:
        raise ValueError("Trieste production must have exactly one heading")
    title = heads.h1[0]
    body = clean(html)
    # First-party work identity: never guess composer from the slug/title.
    credits = re.search(r"\bMusica(?:\s+e\s+libretto)?\s+di\s+"
                        r"([A-ZÀ-Ý][\wÀ-ÿ'’-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'’-]+){1,3})\b",
                        body)
    if not credits:
        raise ValueError("missing official composer credit")
    # The theatre renders the next genre heading in the same text stream
    # as "Musica di <composer>". The lexical regex may otherwise swallow
    # "Opera", "Tragedia", "Melodramma" etc as the composer's surname.
    # Remove only one exact, documented musical-genre label after a
    # full two-word author name, never infer an author from the title.
    composer = re.sub(
        r"(?:\s+(?:Opera|Tragedia|Melodramma|Dramma|Operetta|Ed|Maestro|Regia|Direzione|Stagione))+$",
        "", credits.group(1))
    if len(composer.split())<2:
        raise ValueError("incomplete official composer credit")
    # The 'Altre info' section lists actual recite with weekdays, full dates,
    # and times. Cast alternations with day numbers are not performances.
    section = body.rfind("Altre info")
    if section < 0:
        raise ValueError("missing performance details section")
    text = body[section:]
    cutoff = re.search(r"(?:Foto Gallery|\* DURATA|Stagione Sponsor)", text, re.I)
    if cutoff:
        text = text[:cutoff.start()]
    rx = re.compile(r"(?i)\b" + WEEKDAY + r"\s+(\d{1,2})\s+(" +
                    MONTH_RE + r")\s+(20\d{2})\s+ore\s+([01]?\d|2[0-3])[.:]([0-5]\d)\b")
    dates = {}
    for match in rx.finditer(text):
        day, month, year, hour, minute = match.groups()
        if month.casefold() not in MONTHS:
            raise ValueError("unrecognized month")
        iso = date(int(year), MONTHS[month.casefold()], int(day)).isoformat()
        if not 2026 <= int(year) <= 2027:
            raise ValueError("Trieste date outside approved season")
        clock = f"{int(hour):02d}:{minute}"
        if iso in dates and dates[iso] != clock:
            raise ValueError("conflicting clock on one official date")
        dates[iso] = clock
    if not dates:
        raise ValueError("no verified Trieste opera showtimes")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b", text):
        raise ValueError("unresolved cancellation or postponement")
    return title, composer, "Teatro Lirico Giuseppe Verdi", sorted(dates.items())
