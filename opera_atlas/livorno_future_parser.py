"""Rolling Teatro Goldoni Lirica calendar: one official URL per performance.

The season article's three title-specific 2026/27 adapters remain unchanged.
The category archive proposes event URLs, and each detail page must explicitly
credit Lirica, venue, credited composer, an event date and its own clock.
Other recital dates in the description, gallery and calendar are never used.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
import re
from opera_atlas.national_detail_parser import MONTHS,clean

HOST="www.goldoniteatro.it"
INDEX=f"https://{HOST}/tipo-spettacolo/lirica/"
DETAIL=re.compile(r"/spettacoli/([a-z0-9-]+)/?")
DATE=re.compile(r"(?i)Teatro Goldoni\s*[-–]\s*(\d{1,2})\s+"
                r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
                r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})")
CLOCK=re.compile(r"(?i)Orario/i\s*:\s*(2[0-3]|1\d|0?\d)(?:[.:]([0-5]\d))?\b")
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")
EXCLUDE=re.compile(r"(?i)\b(?:abbonamenti|abbonamento|concerto|musical|crossover|"
                   r"balletto|danza|gala|prova generale|scuole)\b")

class Archive(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.title=[]
        self.h1=False
        self.h3=False
        self.heading=[]
        self.link=None
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):self.hidden+=1
        if self.hidden:return
        if tag=="h1":self.h1=True
        if tag=="h3":self.h3=True
        if tag=="a" and self.h3:
            self.link=dict(attrs).get("href")
            self.heading=[]
    def handle_data(self,data):
        if self.hidden:return
        if self.h1:self.title.append(data)
        if self.link is not None:self.heading.append(data)
    def handle_endtag(self,tag):
        if tag=="h1":self.h1=False
        if tag=="a" and self.link is not None:
            label=" ".join(" ".join(self.heading).split())
            self.links.append((self.link,label))
            self.link=None
        if tag=="h3":self.h3=False
        if tag in ("nav","footer","script","style"):self.hidden=max(0,self.hidden-1)

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    return bool(p.scheme=="https" and p.hostname==HOST and p.port is None
        and not p.username and not p.password and not p.query and not p.fragment
        and DETAIL.fullmatch(p.path))

def extract_index(html:str,*,url:str,min_links:int)->list[str]:
    if url!=INDEX:raise ValueError("unapproved Goldoni lirica archive")
    parsed=Archive()
    parsed.feed(html)
    if not re.search(r'(?i)\bArchivio spettacoli\s*["“]?Lirica\b',
                     " ".join(parsed.title)):
        raise ValueError("Goldoni Lirica category not confirmed")
    links=set()
    for href,title in parsed.links:
        if not title or EXCLUDE.search(title):continue
        candidate=urljoin(INDEX,href)
        if eligible_detail(candidate):links.add(candidate)
    if len(links)<min_links:raise ValueError("no official Goldoni opera event links")
    return sorted(links)

def parse_detail(html:str,*,url:str):
    if not eligible_detail(url):raise ValueError("unapproved Goldoni opera detail")
    text=clean(html)
    # The event date and time are the page's leading metadata, not the
    # two-or-more showtimes listed in the descriptive prose.
    header=text[:600]
    day=DATE.search(header)
    clock=CLOCK.search(header)
    if day is None or clock is None:
        raise ValueError("Goldoni detail lacks its own dated ticket clock")
    number,month,year=day.groups()
    when=date(int(year),MONTHS[month.casefold()],int(number))
    if when.year<2027:raise ValueError("historic Goldoni event belongs to original source")
    hour,minute=clock.groups()
    hour=f"{int(hour):02d}:{minute or '00'}"
    if not re.search(r"(?i)\bLirica\b",header):
        raise ValueError("Goldoni event not in Lirica category")
    heading=re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>",html)
    if heading is None:raise ValueError("Goldoni opera work heading missing")
    title=clean(heading[1]).strip()
    if not title or len(title)>170 or EXCLUDE.search(title):
        raise ValueError("non-operatic Goldoni event")
    # Credits must precede reviews, gallery and the calendar. Do not infer
    # composer from a different event's footer or history.
    start=text.find(title)
    stop=re.search(r"(?i)\b(?:Mediagallery|Acquista il biglietto|"
                   r"Scopri le date dello spettacolo)\b",text[start:])
    if start<0 or stop is None:
        raise ValueError("unbounded Goldoni official credits")
    body=text[start:start+stop.start()]
    if CANCEL.search(body):raise ValueError("cancelled Goldoni performance")
    credit=re.search(
        r"(?i)\bMusica di\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'.’\-]*"
        r"(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'.’\-]*){1,3})"
        r"(?=\s+(?:Direttore|Regia|Maestro|Orchestra|Libretto|"
        r"Nuovo\s+allestimento|Coro)\b|[.;]|$)",body)
    if credit is None:raise ValueError("Goldoni composer attribution not source-verified")
    composer=credit[1].strip(" .")
    if composer.casefold().split()[0] in {"direttore","regia","maestro",
            "orchestra","libretto","nuovo","coro"}:
        raise ValueError("director or production crew is not a composer")

    if any(w in {"non","identificato","un","artista","ignoto","anonimo","vari","e"}
           for w in composer.casefold().split()):
        raise ValueError("ambiguous Goldoni composer attribution")
    return title,composer,"Teatro Goldoni",[(when.isoformat(),hour)]
