"""First-party Teatro del Giglio 2026/27 opera detail parser.

Only dates and clocks scoped to the production panel are considered; unrelated
'prossimi spettacoli' in the site's shared header must never leak into a work.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS, clean

KEY="giglio-lucca-opera-2026-27"
HOST="www.teatrodelgigliogiacomopuccini.it"
ROOT="/it/cartellone/lirica/stagione-2026-2027/"
VENUE="Teatro del Giglio Giacomo Puccini"
MONTH=r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"


class Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_h1=False
        self.value=[]
        self.h1=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h1":
            self.in_h1=True
            self.value=[]
    def handle_data(self,data):
        if self.in_h1:
            self.value.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.in_h1:
            self.h1.append(" ".join(" ".join(self.value).split()))
            self.in_h1=False


def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    loc=urlsplit(url)
    if (loc.scheme!="https" or loc.hostname!=HOST or loc.query or loc.fragment or
        loc.username or loc.password or loc.port is not None or
        not re.fullmatch(re.escape(ROOT)+r"[a-z0-9-]+/?",loc.path)):
        raise ValueError("unapproved Lucca opera detail URL")
    headings=Headings()
    headings.feed(html)
    if len(headings.h1)!=1:
        raise ValueError("missing unique Lucca work heading")
    title=headings.h1[0]
    body=clean(html)
    # The global header contains performances of *other* productions.
    # Only the production panel after MENU belongs to this work.
    panel=re.search(r"\bMENU\s+TEATRO DEL GIGLIO\s+(.*?)\s+Segui tutte le novità\b",body,re.I)
    if not panel:
        raise ValueError("no bounded work-specific Lucca recital panel")
    text=panel.group(1)
    if not text.startswith(title+" "):
        raise ValueError("work-specific event heading differs from page title")
    if not re.search(r"\bTeatro del Giglio\s+Lirica\b",text,re.I):
        raise ValueError("event not at Teatro del Giglio or not opera")
    credit=re.search(r"\bMusica di\s+([A-ZÀ-Ý][A-ZÀ-Ý\s'’-]{2,60})",text)
    if not credit:
        raise ValueError("official composer credit missing")
    composer=" ".join(credit.group(1).split())
    if len(composer.split())<2:
        raise ValueError("composer not specific enough")
    # Date and clock always occur together and include the full year.
    rx=re.compile(rf"(?i)\bIl\s+(\d{{1,2}})\s+({MONTH})\s+(20\d{{2}})\s+Ore\s+([01]?\d|2[0-3]):([0-5]\d)\b")
    found={}
    for d,m,y,h,minute in rx.findall(text):
        day=date(int(y),MONTHS[m.casefold()],int(d)).isoformat()
        if int(y) not in (2026,2027):
            raise ValueError("date outside approved Lucca season")
        if day in found:
            raise ValueError("duplicate or conflicting official Lucca recite")
        found[day]=f"{int(h):02d}:{minute}"
    # Prevent silently dropping event rows if page markup changes.
    if (not found or len(found)>24 or
        len(re.findall(r"\bIl\s+\d{1,2}\s+"+MONTH+r"\s+20\d{2}",text,re.I))!=len(found)):
        raise ValueError("incomplete official Lucca date/time evidence")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",text):
        raise ValueError("cancellation needs review")
    return title,composer,VENUE,sorted(found.items())
