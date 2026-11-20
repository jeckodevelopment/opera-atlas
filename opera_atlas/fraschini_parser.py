"""Conservative Teatro Fraschini production-page timetable adapter.

Only the leading, explicitly dated two-replica header on an officially
whitelisted production page is recognized. A month/year is never guessed from
the current date, an artistic season, or a different page.
"""
from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

MONTHS = {
    "gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
    "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12,
}
PAIR = re.compile(
    r"(?<!\d)(?P<d1>\d{1,2})\s+(?P<m1>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+(?P<year>20\d{2})\s*,\s*ore\s*(?P<t1>\d{1,2}(?:[.:]\d{1,2})?)"
    r"\s*\|\s*(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)?\s*"
    r"(?P<d2>\d{1,2})\s+(?P<m2>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s*,\s*ore\s*(?P<t2>\d{1,2}(?:[.:]\d{1,2})?)",re.I,
)


class _Extract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading=""
        self.after=[]
        self.in_h1=False
        self.seen_h1=False
        self.skip=0

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"): self.skip+=1
        if tag=="h1" and not self.seen_h1: self.in_h1=True

    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.skip:self.skip-=1
        if tag=="h1" and self.in_h1:self.in_h1=False;self.seen_h1=True

    def handle_data(self,data):
        if self.skip:return
        if self.in_h1:self.heading+=" "+data
        elif self.seen_h1:self.after.append(data)


def _clock(value: str) -> str:
    segments=value.replace(".",":").split(":")
    hour=int(segments[0])
    minute=int(segments[1]) if len(segments)==2 else 0
    if hour>23 or minute>59:raise ValueError("invalid official clock")
    return f"{hour:02d}:{minute:02d}"


def parse_fraschini_detail(html: str, *, url: str, title: str, composer: str):
    uri=urlsplit(url)
    if(uri.scheme!="https" or uri.hostname!="www.teatrofraschini.it"
       or not uri.path.startswith("/programma/") or uri.username or uri.password):
        raise ValueError("not an official Fraschini HTTPS production")
    if not title.strip() or not composer.strip():raise ValueError("verified title and composer required")
    parser=_Extract()
    parser.feed(html)
    if title.casefold() not in parser.heading.casefold():
        raise ValueError("official page heading does not match curated work")
    text=" ".join(" ".join(parser.after).split())
    if composer.casefold() not in text.casefold():
        raise ValueError("composer absent from source page")
    header=text[:550]
    match=PAIR.search(header)
    if not match:raise ValueError("explicit paired showtime header missing")
    year=int(match["year"])
    found=[]
    for suffix in ("1","2"):
        day=date(year,MONTHS[match["m"+suffix].casefold()],int(match["d"+suffix])).isoformat()
        clock=_clock(match["t"+suffix])
        found.append((day,clock))
    if found[0]==found[1]:raise ValueError("duplicate date in official header")
    return found
