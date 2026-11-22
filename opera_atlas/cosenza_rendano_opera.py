"""Conservative evergreen official source for Teatro Alfonso Rendano, Cosenza.

The Rendano website publishes opera, ballet, prose, educational experiences
and collateral events. An index link is a candidate, NEVER proof of an opera
performance. Only the exact official event body may prove composer, theatre
and local showtime; absence of any fact remains review-only.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, unquote
import re

KEY = "cosenza-rendano-rolling-opera"
INDEX = "https://www.teatrorendanocosenza.it/lirica-2/"
HOST = "www.teatrorendanocosenza.it"
MONTHS = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
          "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
          "novembre":11,"dicembre":12}
SKIP = re.compile(
    r"(?:^|[-/])(?:danza|ballet|prosa|concerti?|eventi|calendario|"
    r"biglietteria|rubriche|campagne|young|speciale|experience|"
    r"gallery|foto|contatti|storia|teatro|progetto|scuole|laboratori)(?:[-/]|$)",re.I)
DATE = re.compile(r"\b([0-3]?\d)[ /.-]+([01]?\d)[ /.-]+(20\d{2})"
                  r"\s*(?:ore|alle|h[.:]?)\s*([01]?\d|2[0-3])[.:]([0-5]\d)\b",re.I)
TEXTDATE = re.compile(
    r"\b([0-3]?\d)\s+("+"|".join(MONTHS)+r")\s+(20\d{2})"
    r"\s*(?:ore|alle|h[.:]?)\s*([01]?\d|2[0-3])[.:]([0-5]\d)\b",re.I)
COMPOSER = re.compile(
    r"\b(?:musica\s+di|compositore\s*:|opera\s+di)\s+"
    r"(Gioachino Rossini|Wolfgang Amadeus Mozart|Darius Milhaud|"
    r"Giuseppe Verdi|Giacomo Puccini|Gaetano Donizetti|Vincenzo Bellini|"
    r"Ruggero Leoncavallo|Pietro Mascagni|Georges Bizet)\b",re.I)

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.parts=[]
        self.headings=[]
        self._h1=False
        self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self._skip+=1
        if tag=="h1" and not self._skip:self._h1=True
        if tag=="a" and not self._skip:
            href=dict(attrs).get("href")
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag=="h1":self._h1=False
        if tag in ("script","style","noscript"):self._skip=max(0,self._skip-1)
    def handle_data(self,value):
        if self._skip:return
        txt=" ".join(value.split())
        if txt:
            self.parts.append(txt)
            if self._h1:self.headings.append(txt)

def eligible_detail(url:str)->bool:
    v=urlsplit(url)
    if (v.scheme!="https" or v.hostname!=HOST or v.query or v.fragment or
        v.username or v.password or v.port is not None):
        return False
    path=unquote(v.path)
    if not re.fullmatch(r"/[a-z0-9][a-z0-9-]*/",path):
        return False
    if path==urlsplit(INDEX).path or SKIP.search(path):
        return False
    # Only page-like WordPress event URLs from an independently verified
    # first-party opera listing. Nothing is promoted by this gate alone.
    return True

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("unapproved Rendano opera index")
    page=Reader();page.feed(html)
    links=sorted({candidate for href in page.links
                  if eligible_detail(candidate:=urljoin(INDEX,href))})
    if len(links)<min_links:
        raise ValueError("Rendano official opera event links not verified")
    return links

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Rendano production URL")
    page=Reader();page.feed(html)
    if len(page.headings)!=1:
        raise ValueError("Rendano title missing or ambiguous")
    title=page.headings[0].strip()
    if not 3<=len(title)<=140:raise ValueError("Rendano title invalid")
    try:start=page.parts.index(title)
    except ValueError as ex:raise ValueError("Rendano event body missing") from ex
    content=" ".join(page.parts[start:start+100])
    # Explicit local category required: the same website also presents the
    # Barbiere di Siviglia ballet, Figaro backstage and other non-operas.
    if not re.search(r"\b(?:opera\s+lirica|stagione\s+operistica|"
                     r"rappresentazione\s+operistica|melodramma)\b",content[:1000],re.I):
        raise ValueError("Rendano event genre is not verified opera")
    if re.search(r"\b(?:balletto|ballet|danza|musical|gala|galà|"
                 r"concerto|backstage|laboratorio|scuole)\b",title,re.I):
        raise ValueError("Rendano event is not an operatic performance")
    if not re.search(r"\b(?:Teatro\s+(?:Alfonso\s+)?Rendano|"
                     r"Teatro\s+di\s+Tradizione\s+Alfonso\s+Rendano)\b",
                     content[:1200],re.I):
        raise ValueError("Rendano venue unverified")
    credits=COMPOSER.findall(content[:1400])
    if len({name.casefold() for name in credits})!=1:
        raise ValueError("Rendano composer ambiguous or missing")
    rows=[]
    for day,month,year,hr,minute in DATE.findall(content[:1800]):
        try:rows.append((date(int(year),int(month),int(day)).isoformat(),
                         f"{int(hr):02d}:{minute}"))
        except ValueError as ex:raise ValueError("Rendano invalid recital date") from ex
    for day,month,year,hr,minute in TEXTDATE.findall(content[:1800]):
        try:rows.append((date(int(year),MONTHS[month.casefold()],int(day)).isoformat(),
                         f"{int(hr):02d}:{minute}"))
        except ValueError as ex:raise ValueError("Rendano invalid recital date") from ex
    rows=sorted(set(rows))
    if not rows or len(rows)>20:
        raise ValueError("Rendano recital clock missing or excessive")
    return title,credits[0],"Teatro Alfonso Rendano",rows
