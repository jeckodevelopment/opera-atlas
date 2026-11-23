"""First-party Festival della Valle d'Itria operas at exact official venues.

The same programme includes concerts, ballets, and operas in other venues.
All candidate pages must be independently verified by genre, credited work,
venue, dates and local time. A mixed ballet/opera programme contributes only
the opera component, never its ballet.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
import re

KEY="martina-valle-itria-2026"
HOST="www.festivaldellavalleditria.it"
INDEX="https://www.festivaldellavalleditria.it/programma-2026"
EVENT=re.compile(r"/spettacolo/([a-z0-9][a-z0-9-]*)/(20\d{2})-(\d{2})-(\d{2})/?")
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
DATES=re.compile(r"([0-3]?\d)\s+("+ "|".join(MONTHS) +r")\s+(20\d{2})\s*\.\s*H\s*([01]?\d|2[0-3]):([0-5]\d)\s+(Palazzo\s+Ducale|Chiostro\s+del\s+Carmine),\s*Martina\s+Franca",re.I)
VENUES={"palazzo ducale":"Palazzo Ducale di Martina Franca",
        "chiostro del carmine":"Chiostro del Carmine"}

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.parts=[]
        self.titles=[]
        self._h1=False
        self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag=="h1" and not self._skip:self._h1=True
        if tag=="a" and not self._skip:
            url=dict(attrs).get("href")
            if url:self.links.append(url)
    def handle_endtag(self,tag):
        if tag=="h1":self._h1=False
        if tag in ("script","style","noscript"):self._skip=max(0,self._skip-1)
    def handle_data(self,text):
        if self._skip:return
        text=" ".join(text.split())
        if text:
            self.parts.append(text)
            if self._h1:self.titles.append(text)

def eligible_detail(url:str)->bool:
    u=urlsplit(url)
    m=EVENT.fullmatch(u.path)
    return bool(u.scheme=="https" and u.hostname==HOST and m
                and 2026<=int(m[2])<=2099
                and not u.query and not u.fragment and u.username is None
                and u.password is None and u.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=2)->list[str]:
    u=urlsplit(url)
    m=re.fullmatch(r"/programma-(20\d{2})",u.path)
    if (u.scheme!="https" or u.hostname!=HOST or not m or
            not 2026<=int(m[1])<=2099 or u.query or u.fragment):
        raise ValueError("unapproved Valle d'Itria season programme")
    p=Page();p.feed(html)
    # Only links to dated official detail pages, not a genre inferred from
    # index labels. Genre and venue are verified inside each detail page.
    links=sorted({candidate for href in p.links
                  if eligible_detail(candidate:=urljoin(url,href))
                  and int(EVENT.fullmatch(urlsplit(candidate).path)[2])==int(m[1])})
    if len(links)<min_links:
        raise ValueError("Valle d'Itria index incomplete or markup changed")
    return links

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Valle d'Itria detail")
    page=Page();page.feed(html)
    heading=" ".join(page.titles).strip()
    if not 2<=len(heading)<=160:
        raise ValueError("Valle d'Itria official title missing")
    text=" ".join(page.parts)
    pre=text.split(" Locandina ",1)[0]
    details=text.split(" Dettagli ",1)[-1].split(" Contatti ",1)[0]
    if not re.search(r"\bCategoria:\s*Opera\b",details,re.I):
        raise ValueError("Valle d'Itria page is not categorised as opera")
    venue_match=re.search(r"\bDove:\s*(Palazzo\s+Ducale|Chiostro\s+del\s+Carmine),\s*Martina\s+Franca\b",details,re.I)
    if not venue_match:
        raise ValueError("Valle d'Itria exact performance venue not verified")
    venue=VENUES[" ".join(venue_match.group(1).lower().split())]
    # A special officially documented ballet/opera double bill is not
    # two operas: Pulcinella is a ballet with song, Orfeo the opera.
    # The first-party CMS may collapse spaces around the slash or insert
    # extra whitespace from H1 emphasis tags. Match only this exact
    # documented pairing; a different mixed programme remains unverified.
    normalized_heading=re.sub(r"\s+", " ", heading).strip()
    is_casella_bill=bool(re.fullmatch(
        r"pulcinella\s*/\s*la favola di orfeo\s*\(dittico\)",
        normalized_heading, re.I))
    if is_casella_bill:
        if (not re.search(r"Musiche di Igor Stravinskij e Alfredo Casella",pre)
            or not re.search(r"Pulcinella,\s*balletto\b",pre,re.I)
            or not re.search(r"La favola di Orfeo:\s*opera da camera\b",pre,re.I)):
            raise ValueError("unverified mixed ballet/opera bill")
        title,composer="La favola di Orfeo","Alfredo Casella"
    else:
        if "/" in heading or "dittico" in heading.casefold():
            raise ValueError("unverified composite festival programme")
        m=re.search(r"\bMusica di\s+([A-ZÀ-Ž][A-Za-zÀ-ÿ.'’ -]{4,85})",pre)
        if not m:raise ValueError("Valle d'Itria composer credit absent")
        # Stop before editorial prose: the next source paragraph follows
        # the separate 'Musica di' HTML text node.
        composer=next((part[len("Musica di "):].strip()
                       for part in page.parts if part.startswith("Musica di ")),None)
        if not composer or not re.fullmatch(r"[A-ZÀ-Ž][A-Za-zÀ-ÿ.'’ -]{4,85}",composer):
            raise ValueError("unverified first-party composer")
        title=heading
    pairs=DATES.findall(pre)
    if len(pairs)!=len(re.findall(r"(?:Palazzo\s+Ducale|Chiostro\s+del\s+Carmine),\s*Martina\s+Franca",pre,re.I)):
        raise ValueError("incomplete official festival showtime evidence")
    if not pairs or len(pairs)>12:
        raise ValueError("no official Palazzo Ducale performances")
    recital=[]
    year=int(EVENT.fullmatch(urlsplit(url).path)[2])
    for d,m,y,h,minute,performance_venue in pairs:
        if VENUES[" ".join(performance_venue.lower().split())]!=venue:
            raise ValueError("mixed physical festival venues on one event")
        if int(y)!=year:raise ValueError("festival date outside event season")
        try:day=date(year,MONTHS[m.casefold()],int(d)).isoformat()
        except ValueError:raise ValueError("invalid official festival date")
        recital.append((day,f"{int(h):02d}:{int(minute):02d}"))
    if len(set(x[0] for x in recital))!=len(recital):
        raise ValueError("duplicate festival showtime")
    return title,composer,venue,recital
