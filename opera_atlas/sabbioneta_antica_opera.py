"""Evergreen discovery of operatic performances at Teatro all'Antica, Sabbioneta.

The festival also uses churches and presents concerts, recitals and
educational activities. An official /evento/ link is only a candidate;
detail pages must prove stage, opera, composer and exact local showtime.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
import re

KEY="sabbioneta-antica-rolling-opera"
INDEX="https://sabbionetaoperafestival.it/eventi/"
HOST="sabbionetaoperafestival.it"
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
DATE=re.compile(
    r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+([0-3]?\d)\s+("
    +"|".join(MONTHS)+r")\s*(?:\|\s*|,\s*|-\s*)?(?:ore\s*)"
    r"([01]?\d|2[0-3])[:.]([0-5]\d)\b"
)
CREDIT=re.compile(
    r"\b(?:musica\s+di\s+)?(?:G\.\s*Rossini|Gioachino\s+Rossini|"
    r"Claudio\s+Monteverdi|C\.\s*Monteverdi|"
    r"Giuseppe\s+Verdi|Giacomo\s+Puccini|Gaetano\s+Donizetti)\b",re.I)
AUTHORS={"rossini":"Gioachino Rossini","monteverdi":"Claudio Monteverdi",
         "verdi":"Giuseppe Verdi","puccini":"Giacomo Puccini",
         "donizetti":"Gaetano Donizetti"}
NONOPERA=re.compile(r"\b(?:concerto\s+di\s+natale|sipario\s+all.organo|"
                   r"schumann\s+e\s+mahler|masterclass|gala|gal[aà]|"
                   r"concerto\s+d.organo)\b",re.I)
OPERA=re.compile(r"\b(?:barbiere\s+di\s+siviglia|l.orfeo|"
                 r"favola\s+in\s+musica|riduzione\s+dell.opera|"
                 r"opera\s+lirica|melodramma)\b",re.I)
VENUE=re.compile(r"\bTeatro\s+all[’']?\s*Antica\b",re.I)

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.parts=[];self.h1=[];self.h2=[]
        self._heading=None;self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag in ("h1","h2") and not self._skip:self._heading=tag
        if tag=="a" and not self._skip:
            href=dict(attrs).get("href")
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag==self._heading:self._heading=None
        if tag in ("script","style","noscript"):self._skip=max(self._skip-1,0)
    def handle_data(self,txt):
        if self._skip:return
        val=" ".join(txt.split())
        if val:
            self.parts.append(val)
            if self._heading=="h1":self.h1.append(val)
            if self._heading=="h2":self.h2.append(val)

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname==HOST and
            bool(re.fullmatch(r"/evento/[a-z0-9][a-z0-9-]*/",p.path))
            and not p.query and not p.fragment and
            p.username is None and p.password is None and p.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("Sabbioneta index is not approved")
    page=Page();page.feed(html)
    links=sorted({candidate for href in page.links
                  if eligible_detail(candidate:=urljoin(INDEX,href))})
    if len(links)<min_links:raise ValueError("Sabbioneta opera candidates not verified")
    return links

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Sabbioneta event URL")
    page=Page();page.feed(html)
    # The site renders a shared festival banner and an event-specific H1.
    headings=[x for x in page.h1 if not re.search(r"\bfestival\b",x,re.I)]
    if not headings:raise ValueError("Sabbioneta production title missing")
    raw=headings[0].strip("“”\" ")
    if NONOPERA.search(raw):raise ValueError("Sabbioneta event is not opera")
    try:start=page.parts.index(page.h1[0])
    except ValueError as ex:raise ValueError("Sabbioneta event body missing") from ex
    body=" ".join(page.parts[start:start+130])
    local=body[:3200]
    # Site-wide navigation and related performances are not event evidence.
    local=local.split("Evento Navigazione",1)[0]
    if not OPERA.search(raw+" "+local[:650]):
        raise ValueError("Sabbioneta genre unverified as opera")
    if not VENUE.search(local[:1250]):
        raise ValueError("Sabbioneta event belongs to another venue")
    # The festival calendar header is the edition, not performance evidence.
    editions=re.findall(r"\bResidenze\s+(20\d{2})\b"," ".join(page.parts[:35]),re.I)
    if len(set(editions))!=1 or not editions:
        raise ValueError("Sabbioneta edition year missing")
    year=int(editions[0])
    if not 2020<=year<=2099:raise ValueError("invalid edition")
    first=local[:1650]
    credits=CREDIT.findall(first)
    composers={name for token in credits for key,name in AUTHORS.items()
               if key in token.casefold()}
    if len(composers)!=1:
        raise ValueError("Sabbioneta composer missing or ambiguous")
    recite=[]
    for day,month,hour,minute in DATE.findall(local[:800]):
        try:recite.append((date(year,MONTHS[month.casefold()],int(day)).isoformat(),
                           f"{int(hour):02d}:{minute}"))
        except ValueError as ex:raise ValueError("invalid Sabbioneta recital") from ex
    recite=sorted(set(recite))
    if not recite or len(recite)>20:
        raise ValueError("Sabbioneta official local showtime missing")
    # Strip first-party composer attribution, not the actual work title.
    title=re.sub(r"\s+di\s+(?:G\.\s*Rossini|C\.\s*Monteverdi|"
                 r"Gioachino\s+Rossini|Claudio\s+Monteverdi)\s*$",
                 "",raw,flags=re.I).strip("“”\" ")
    if not 2<=len(title)<=150:raise ValueError("Sabbioneta title invalid")
    title=title[0].upper()+title[1:] if title else title
    return title,next(iter(composers)),"Teatro all'Antica",recite
