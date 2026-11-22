"""A source-scoped year-independent opera calendar for Teatro di Pisa.

This is intentionally distinct from the historic five-title 2026/27 source.
The official event calendar has recurring performances (one URL per recita)
and also school-only previews. A calendar hit is review-only until an
individual event page corroborates date, time, composer and opera category.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

from opera_atlas.national_detail_parser import clean,MONTHS
from opera_atlas.work_identity import resolve_work

HOST="teatrodipisa.it"
INDEX=f"https://{HOST}/calendario/categoria/opera/elenco/"
VENUE="Teatro Verdi"
URL_PATTERN=re.compile(r"/calendario/([a-z0-9-]+)/")
DATE=re.compile(r"(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+(20\d{2})",re.I)
TIME=re.compile(r"(?<!\d)(2[0-3]|1\d|0?\d):([0-5]\d)(?!\d)")
SCHOOL=re.compile(r"(?i)\b(?:scuol[ae]|generale\s+riservata|prova\s+didattica)\b")
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

class OperaCalendar(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.in_heading=False
        self.heading_parts=[]
        self.headings=[]
        self.event_heading=0
        self.event_title_parts=[]
        self.event_url=None
        self.events=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):self.hidden+=1
        if self.hidden:return
        if tag=="h1":
            self.in_heading=True
            self.heading_parts=[]
        if tag in ("h3","h4"):
            self.event_heading+=1
            if self.event_heading==1:
                self.event_title_parts=[]
                self.event_url=None
        if tag=="a" and self.event_heading:
            self.event_url=dict(attrs).get("href")
    def handle_data(self,data):
        if self.hidden:return
        if self.in_heading:self.heading_parts.append(data)
        if self.event_heading:self.event_title_parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.in_heading:
            self.headings.append(" ".join(" ".join(self.heading_parts).split()))
            self.in_heading=False
        if tag in ("h3","h4") and self.event_heading:
            self.event_heading-=1
            if self.event_heading==0 and self.event_url:
                title=" ".join(" ".join(self.event_title_parts).split())
                self.events.append((self.event_url,title))
                self.event_url=None
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)

def _official(url:str)->bool:
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST and
            not u.query and not u.fragment and not u.username and
            not u.password and u.port is None)

def eligible_detail(url:str)->bool:
    return _official(url) and bool(URL_PATTERN.fullmatch(urlsplit(url).path))

def extract_calendar(html:str,*,url:str,min_links:int)->list[str]:
    if url!=INDEX:raise ValueError("unapproved Pisa opera calendar index")
    parser=OperaCalendar()
    parser.feed(html)
    if not any(h.strip().casefold()=="opera" for h in parser.headings):
        raise ValueError("official Pisa opera category heading missing")
    out=set()
    for href,title in parser.events:
        if SCHOOL.search(title):continue
        candidate=urljoin(INDEX,href)
        if eligible_detail(candidate):out.add(candidate)
    if len(out)<min_links:
        raise ValueError("Pisa opera calendar lacks verified event cards")
    return sorted(out)

def parse_calendar_detail(html:str,*,url:str,registry:dict):
    if not eligible_detail(url):
        raise ValueError("unapproved Pisa opera event detail")
    text=clean(html)
    title_match=re.search(r"(?is)<h1[^>]*>(.*?)</h1>",html)
    if not title_match:raise ValueError("official Pisa event title missing")
    title=clean(title_match[1])
    if SCHOOL.search(title):raise ValueError("school-only opera excluded")
    if not re.search(r"(?i)\bCategoria\s+Evento\s*:\s*opera\b",text):
        raise ValueError("official event is not opera")
    if not re.search(r"(?i)\bFondazione\s+Teatro\s+di\s+Pisa\b",text):
        raise ValueError("first-party Pisa theatre credit absent")
    if not re.search(r"(?i)\bMusica\s+di\b",text):
        raise ValueError("official composer credit absent")
    heading_offset=text.find(title)
    credit_block=text[heading_offset:heading_offset+1300]
    if CANCEL.search(text[:heading_offset+1800]):
        raise ValueError("cancelled opera requires review")
    resolved=[]
    works=registry.get("works",{}) if isinstance(registry,dict) else {}
    for record in works.values():
        if not isinstance(record,dict):continue
        composer=record.get("composer")
        if not isinstance(composer,str) or not isinstance(record.get("title"),str):
            continue
        if (re.search(r"(?i)\bMusica\s+di\s+"+re.escape(composer)+r"\b",credit_block)
                and resolve_work(registry,title,composer) is not None):
            resolved.append(resolve_work(registry,title,composer))
    if len(resolved)!=1:
        raise ValueError("Pisa event title and composer not uniquely canonical")
    # Single recurring event page: only the explicit Details section can
    # supply the date and time, never a historical premiere in the synopsis.
    block=re.search(
        r"(?is)\bDettagli\b(.*?)\bCategoria\s+Evento\s*:\s*opera\b",text)
    if not block:raise ValueError("bounded Pisa event details missing")
    date_match=re.search(r"\bData\s*:\s*"+DATE.pattern,block[1],re.I)
    hour_match=re.search(r"\bOra\s*:\s*"+TIME.pattern,block[1],re.I)
    if not date_match or not hour_match:
        raise ValueError("incomplete official Pisa date and time")
    day,month,year=date_match.groups()
    when=date(int(year),MONTHS[month.casefold()],int(day))
    if when.year<2027:
        raise ValueError("future Pisa source does not backfill old recite")
    hour,minute=hour_match.groups()
    if CANCEL.search(block[1]):
        raise ValueError("event cancellation requires review")
    canonical=resolved[0]
    return [(canonical["title"],canonical["composer"],VENUE,
             when.isoformat(),f"{int(hour):02d}:{minute}")]
