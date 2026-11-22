"""Macerata Opera Festival annual edition discovery, separate from 2027 history.

The official festival's year-scoped edition page links each production.
Individual work pages reuse yearless slugs; recite are only accepted when
source text confirms that edition year and each weekday/date/clock.
An index link alone never establishes a production or invents a performance.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

from opera_atlas.national_detail_parser import MONTHS,clean
from opera_atlas.macerata_opera_parser import WEEKDAYS, VENUE

HOST="www.sferisterio.it"
EDITION=re.compile(r"/macerata-opera-festival-(20\d{2})/?")
DETAIL=re.compile(r"/macerata-opera-festival/([a-z0-9-]+)/?")
DATES=re.compile(r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
                 r"\s+(\d{1,2})\s+(luglio|agosto)\s+H\s*(2[0-3]|1\d|0?\d)[:.]([0-5]\d)\b")
DECLARED=re.compile(r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
                    r"\s+\d{1,2}\s+(?:luglio|agosto)\b")
NOT_OPERA=re.compile(r"(?i)\b(?:balletto|danza|concerto|musical|opera pop|crossover|sferisterio scuola)\b")
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

class _ProductionLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.in_bill=False
        self.anchor=None
        self.parts=[]
        self.links=[]
        self.heading=None
        self.heading_parts=[]
        self.seen_bill=False
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.hidden+=1
        if self.hidden:return
        if tag in ("h2","h3"):
            self.heading=tag
            self.heading_parts=[]
        if tag=="a" and self.in_bill:
            self.anchor=dict(attrs).get("href")
            self.parts=[]
    def handle_data(self,data):
        if self.hidden:return
        if self.heading is not None:self.heading_parts.append(data)
        if self.anchor is not None:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag in ("h2","h3") and self.heading==tag:
            heading=" ".join(" ".join(self.heading_parts).split())
            if re.search(r"(?i)\bGli appuntamenti in cartellone\b",heading):
                self.in_bill=True
                self.seen_bill=True
            elif self.in_bill and re.search(
                 r"(?i)\b(?:Hai già le idee chiare|Newsletter|Iscriviti|Finproject|Partner|Sponsor)\b",heading):
                self.in_bill=False
            self.heading=None
        if tag=="a" and self.anchor is not None:
            label=" ".join(" ".join(self.parts).split())
            self.links.append((self.anchor,label))
            self.anchor=None
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)

def edition_year(url:str)->int:
    p=urlsplit(url)
    match=EDITION.fullmatch(p.path)
    if (p.scheme!="https" or p.hostname!=HOST or p.port is not None
        or p.username or p.password or p.query or p.fragment or not match):
        raise ValueError("Macerata edition URL is not first-party and year scoped")
    year=int(match[1])
    if not 2027<=year<=2099:
        raise ValueError("Macerata edition year outside supported period")
    return year

def next_edition(url:str)->str|None:
    try:year=edition_year(url)
    except ValueError:return None
    return f"https://{HOST}/macerata-opera-festival-{year+1}" if year<2099 else None

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    m=DETAIL.fullmatch(p.path)
    return bool(m and p.scheme=="https" and p.hostname==HOST
                and p.port is None and not p.username and not p.password
                and not p.query and not p.fragment and
                not m[1].startswith(("sferisterio-scuola","concerto","balletto")))

def extract_index(html:str,*,url:str,min_links:int)->list[str]:
    year=edition_year(url)
    text=clean(html)
    # The active annual landing page must confirm the exact edition year,
    # not just contain a footer link to the previous year's programme.
    intro=text[:2200]
    if not re.search(rf"(?i)\bMacerata Opera Festival\s+{year}\b",intro):
        raise ValueError("official festival edition/year missing")
    if not re.search(r"(?i)\bSferisterio\b",intro):
        raise ValueError("official Sferisterio identity missing")
    parser=_ProductionLinks()
    parser.feed(html)
    if not parser.seen_bill:
        raise ValueError("missing production list of official festival edition")
    found=set()
    for href,label in parser.links:
        if not re.search(r"(?i)\bSCOPRI\s+DI\s+PIÙ\s+SU\b",label):
            continue
        if NOT_OPERA.search(label):
            continue
        resolved=urljoin(url,href)
        if eligible_detail(resolved):
            found.add(resolved)
    if len(found)<min_links:
        raise ValueError("future Macerata edition has no credited work links")
    return sorted(found)

def parse_detail(html:str,*,url:str):
    if not eligible_detail(url):
        raise ValueError("unknown first-party Macerata production detail")
    text=clean(html)
    heading=re.search(r"(?is)<h[12]\b[^>]*>(.*?)</h[12]>",html)
    if not heading:
        raise ValueError("official Macerata work heading absent")
    title=clean(heading[1]).strip()
    if not title or len(title)>140 or NOT_OPERA.search(title):
        raise ValueError("non-operatic or missing Macerata work title")
    # The yearless event URL requires an edition-year reference on the
    # detail page itself; never inherit the year from an old fixture or slug.
    edition_years=set(int(y) for y in re.findall(
        r"(?i)\bMacerata Opera Festival\s+(20\d{2})\b",text[:1900]))
    if len(edition_years)!=1:
        raise ValueError("Macerata detail cannot uniquely establish festival year")
    year=edition_years.pop()
    if year<2027:
        raise ValueError("Macerata event belongs to historic edition")
    # Navigation may contain the separate Sferisterio Scuola programme;
    # determine genre from the work title and bounded local composer credit.
    # Source composer and type in one introductory credit, never directors,
    # historical première dates, or unrelated footer production cards.
    credit=re.search(r"(?i)\bOpera lirica in .{0,160}?\bdi\s+"
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'’\-]*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'’\-]*){1,3})"
        r"(?=\s+(?:su\s+libretto|libretto|prima\s+rappresentazione|regia)\b|[.;]|$)",
        text[:1750])
    if not credit:
        raise ValueError("first-party composer credit of Macerata opera missing")
    composer=re.sub(r"(?i)\s+su$","",credit[1]).strip(" .")
    if any(x in composer.casefold().split() for x in
           ("non","ignoto","sconosciuto","anonimo","vari","diversi","e","un")):
        raise ValueError("ambiguous Macerata composer credit")
    section=text[credit.end():]
    boundary=re.search(r"(?i)\bCast\b",section)
    linked_programme=re.search(r"(?i)\bGli appuntamenti in cartellone\b",section)
    if not boundary or not linked_programme or boundary.start()>=linked_programme.start():
        raise ValueError("unbounded Macerata work-specific booking dates")
    booking=section[:boundary.start()]
    if CANCELLED.search(booking):
        raise ValueError("cancelled Macerata event requires editorial review")
    recite=[]
    for m in DATES.finditer(booking):
        weekday,day,month,hour,minute=m.groups()
        value=date(year,MONTHS[month.casefold()],int(day))
        if value.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("Macerata date/weekday conflict for edition year")
        recite.append((value.isoformat(),f"{int(hour):02d}:{minute}"))
    if not recite or len(recite)>24 or len(recite)!=len(DECLARED.findall(booking)) or len(set(recite))!=len(recite):
        raise ValueError("Macerata opera dates missing or ambiguous")
    # Source identity is the festival's work page and an explicit festival
    # edition, not an inferred title/venue from a general web search.
    return title,composer,VENUE,sorted(recite)
