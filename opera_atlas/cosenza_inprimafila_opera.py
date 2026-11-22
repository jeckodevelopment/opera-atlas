"""Real calendar fallback for Rendano from the published In Prima Fila ticketing pages.

The official theatre currently returns 403 to some automated clients. The
ticketing partner's year-neutral /eventi listing links individual event pages
with dates and credits. Treat that listing as discovery only; every recital
must be independently proven by its individual ticketing page.

No school-only preview dates, ballet, dance or TAU performances are admitted.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

KEY = "cosenza-inprimafila-rolling-opera"
INDEX = "https://www.inprimafila.net/index.php/eventi"
HOST = "www.inprimafila.net"
MONTHS = {x:i for i,x in enumerate((
    "", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
    "agosto", "settembre", "ottobre", "novembre", "dicembre")) if i}
# Published work-specific ticketing URLs, but any future year is valid.
DETAIL_PATH = re.compile(
    r"/index\.php/eventi/([a-z0-9]+(?:-[a-z0-9]+)*)-cosenza/?",
    re.I,
)
NONOPERA = re.compile(
    r"\b(?:ballet|balletto|danza|musical|concerto|gala|galà|"
    r"educational|scuole|per\s+le\s+scuole)\b",re.I,
)
VENUE = re.compile(r"\bTeatro\s+(?:Alfonso\s*|A\.\s*)?Rendano\s*-\s*Cosenza\b",re.I)
DATE_ENTRY = re.compile(
    r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+"
    r"([0-3]?\d)\s+("+"|".join(MONTHS)+r")"
    r"(?:\s+(20\d{2}))?\s+Ore\s+([01]?\d|2[0-3])[.:]([0-5]\d)\b")
WORKS = {
    "barbiere-di-siviglia": ("Il barbiere di Siviglia", "Gioachino Rossini",
                            r"\b(?:di\s+GIOACHINO\s+ROSSINI|musica\s+di\s+Gioachino\s+Rossini)\b",
                            r"\bopera\s+buffa\s+in\s+2\s+atti\b"),
    "le-nozze-di-figaro": ("Le nozze di Figaro", "Wolfgang Amadeus Mozart",
                           r"\bWOLFGANG\s+AMADEUS\s+MOZART\b",
                           r"\bopera\s+buffa\s+in\s+4\s+atti\b"),
    "la-mere-coupable": ("La mère coupable", "Darius Milhaud",
                         r"\bdi\s+DARIUS\s+MILHAUD\b",
                         r"\batto\s+unico\s+su\s+libretto\b"),
}

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.parts=[];self.title=[];self._heading=False;self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag=="h1" and not self._skip:self._heading=True
        if tag=="a" and not self._skip:
            link=dict(attrs).get("href")
            if link:self.links.append(link)
    def handle_endtag(self,tag):
        if tag=="h1":self._heading=False
        if tag in ("script","style","noscript"):self._skip=max(0,self._skip-1)
    def handle_data(self,value):
        if self._skip:return
        value=" ".join(value.split())
        if value:
            self.parts.append(value)
            if self._heading:self.title.append(value)

def eligible_detail(url:str)->bool:
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST and
            bool(DETAIL_PATH.fullmatch(u.path)) and
            not u.query and not u.fragment and not u.username and
            not u.password and u.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("unapproved Cosenza ticketing index")
    reader=Reader();reader.feed(html)
    urls=sorted({candidate for href in reader.links
                 if eligible_detail(candidate:=urljoin(INDEX,href))})
    # Candidate URLs are safe to fetch but do not prove opera genre.
    if len(urls)<min_links:
        raise ValueError("Cosenza ticketing listing has no verified event links")
    return urls

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Cosenza ticket event")
    path=urlsplit(url).path
    slug=DETAIL_PATH.fullmatch(path)[1]
    # A calendar contains musicals, plays, ballet and talks. Do not silently
    # treat a future "Figaro" event as an opera if title/genre is absent.
    matches=[(prefix,details) for prefix,details in WORKS.items()
             if slug==prefix or slug.startswith(prefix+"-20")]
    if len(matches)!=1:raise ValueError("Cosenza event is not a verified opera")
    _,(canonical,composer,credit,genre)=matches[0]
    reader=Reader();reader.feed(html)
    if len(reader.title)!=1:raise ValueError("Cosenza official ticket heading missing")
    heading=reader.title[0]
    if NONOPERA.search(heading):raise ValueError("non-operatic Cosenza show")
    expected=re.sub(r"[- ]"," ",canonical).casefold()
    normalized=re.sub(r"[- ]"," ",heading).casefold()
    if expected not in normalized and not (canonical=="La mère coupable" and "la mère coupable" in normalized):
        # The seller omits "Il" in "BARBIERE DI SIVIGLIA".
        if not (canonical=="Il barbiere di Siviglia" and "barbiere di siviglia" in normalized):
            raise ValueError("ticket title not matched to opera")
    try:start=reader.parts.index(reader.title[0])
    except ValueError as ex:raise ValueError("Cosenza event content missing") from ex
    body=" ".join(reader.parts[start:start+95]).split("Settori e Prezzi",1)[0]
    if not VENUE.search(body[:600]):
        raise ValueError("Cosenza production is at another venue")
    if not re.search(genre,body[:1500],re.I):
        raise ValueError("Cosenza lyric genre not independently credited")
    if not re.search(credit,body[:1500],re.I):
        raise ValueError("Cosenza composer not independently credited")
    # The full local clock line is before the venue and production title.
    date_header=body.split("Teatro A.Rendano",1)[0]
    entries=DATE_ENTRY.findall(date_header[:230])
    if not entries or len(entries)>15:
        raise ValueError("Cosenza ticket recitals missing")
    years={int(y) for _,_,y,_,_ in entries if y}
    if len(years)!=1:
        raise ValueError("Cosenza season year ambiguous")
    year=next(iter(years))
    recite=[]
    for d,month,explicit,hh,mm in entries:
        if explicit and int(explicit)!=year:raise ValueError("conflicting year")
        try:recite.append((date(year,MONTHS[month.casefold()],int(d)).isoformat(),
                           f"{int(hh):02d}:{mm}"))
        except ValueError as ex:raise ValueError("invalid Cosenza ticket date") from ex
    if len(set(recite))!=len(recite):raise ValueError("duplicate Cosenza date in event")
    return canonical,composer,"Teatro Alfonso Rendano",sorted(recite)
