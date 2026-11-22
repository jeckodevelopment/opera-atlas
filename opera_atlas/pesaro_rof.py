"""Rossini Opera Festival: official archived season and actual Teatro Rossini.

Separate opera from concerts, events at Scavolini, and academy classes.
For historic 2026 three named works have independent festival identity;
later years require a direct first-party Rossini composer credit.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
import re

KEY="pesaro-rof-2026"
HOST="www.rossinioperafestival.it"
INDEX="https://www.rossinioperafestival.it/archivio/stagione-2026/"
INDEX_RE=re.compile(r"/archivio/stagione-(20\d{2})/")
DETAIL_RE=re.compile(r"/archivio/stagione-(20\d{2})/(?:festival-giovane/)?([a-z0-9][a-z0-9-]*)/")
KNOWN_2026={
    "le-siege-de-corinthe":"Le Siège de Corinthe",
    "loccasione-fa-il-ladro":"L’occasione fa il ladro",
    "la-scala-di-seta":"La scala di seta",
    "il-viaggio-a-reims":"Il viaggio a Reims",
}
OPERA_TITLE_RE=re.compile(r"(?:burletta\s+per\s+musica|farsa\s+comica|dramma\s+giocoso|opera\s+in\s+un\s+atto)",re.I)
SLOTS=re.compile(r"((?:\d{1,2}\s*,\s*)*\d{1,2})\s+agosto,?\s+ore\s+([01]?\d|2[0-3])[\.:]([0-5]\d)",re.I)

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.parts=[];self.h1=[]
        self._head=False;self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag=="h1" and not self._skip:self._head=True
        if tag=="a" and not self._skip:
            href=dict(attrs).get("href")
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag=="h1":self._head=False
        if tag in ("script","style","noscript"):self._skip=max(0,self._skip-1)
    def handle_data(self,value):
        if self._skip:return
        value=" ".join(value.split())
        if value:
            self.parts.append(value)
            if self._head:self.h1.append(value)

def eligible_detail(url:str)->bool:
    u=urlsplit(url)
    m=DETAIL_RE.fullmatch(u.path)
    return bool(u.scheme=="https" and u.hostname==HOST and m
                and 2026<=int(m[1])<=2099 and not u.query
                and not u.fragment and not u.username and not u.password
                and u.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=3)->list[str]:
    u=urlsplit(url);m=INDEX_RE.fullmatch(u.path)
    if not (u.scheme=="https" and u.hostname==HOST and m
            and 2026<=int(m[1])<=2099 and not u.query and not u.fragment):
        raise ValueError("unapproved ROF archive index")
    reader=Reader();reader.feed(html)
    links=sorted({candidate for href in reader.links
                  if eligible_detail(candidate:=urljoin(url,href))
                  and int(DETAIL_RE.fullmatch(urlsplit(candidate).path)[1])==int(m[1])})
    if len(links)<min_links:
        raise ValueError("Rossini festival official index incomplete")
    return links

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved official ROF opera detail")
    u=urlsplit(url);m=DETAIL_RE.fullmatch(u.path)
    year=int(m[1]);slug=m[2]
    r=Reader();r.feed(html)
    title=" ".join(r.h1).strip()
    if not 2<=len(title)<=140:raise ValueError("ROF primary title absent")
    visible=" ".join(r.parts)
    heading=next((i for i,x in enumerate(r.parts) if x==title),None)
    if heading is None:raise ValueError("ROF first-party heading unverified")
    intro=" ".join(r.parts[heading+1:heading+12])
    # ROF's 2026 opening *Le Siège de Corinthe* was staged in the
    # Auditorium Scavolini. Other 2026 operas use Teatro Rossini.
    expected_venue=("Auditorium Scavolini"
                    if year==2026 and slug=="le-siege-de-corinthe"
                    else "Teatro Rossini")
    venue_pos=intro.find(expected_venue)
    if venue_pos<0 or any(
            other in intro[:venue_pos]
            for other in ({"Teatro Rossini","Auditorium Scavolini"}-{expected_venue})):
        raise ValueError("ROF opera not at verified official venue")
    date_blob=intro[:venue_pos]
    groups=SLOTS.findall(date_blob)
    dates=[]
    for days,clock,minute in groups:
        for day in re.findall(r"\d{1,2}",days):
            try:iso=date(year,8,int(day)).isoformat()
            except ValueError:raise ValueError("ROF invalid official August day")
            dates.append((iso,f"{int(clock):02d}:{minute}"))
    if not dates or len(dates)>14 or len({d for d,_ in dates})!=len(dates):
        raise ValueError("ROF missing or ambiguous official dates")
    if slug in KNOWN_2026 and year==2026:
        if title.casefold().replace("'", "’")!=KNOWN_2026[slug].casefold():
            raise ValueError("ROF known official 2026 opera title changed")
        # Exact titles independently identified as Rossini operas by ROF's
        # 2026 programme and Rossini Foundation; prose authors named after
        # "di" are librettists, NOT alternative composers.
        if not (OPERA_TITLE_RE.search(visible[:1800])
                or re.search(r"Edizione\s+critica\s+della\s+Fondazione\s+Rossini",visible,re.I)):
            raise ValueError("ROF genre or work authority unverified")
        composer="Gioachino Rossini"
    else:
        credit=re.search(r"\bMusica\s+di\s+(Gioachino\s+Rossini)\b",visible[:1800],re.I)
        if credit is None or not OPERA_TITLE_RE.search(visible[:1800]):
            raise ValueError("ROF future opera/composer not directly verified")
        composer="Gioachino Rossini"
    canonical_venue=("Auditorium Scavolini" if expected_venue=="Auditorium Scavolini"
                     else "Teatro Gioachino Rossini")
    return title,composer,canonical_venue,dates
