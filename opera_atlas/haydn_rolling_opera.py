"""First-party Haydn opera calendar for Bolzano and Trento, not a mixed-genre feed.

The evergreen genre index is only a candidate source. Every dated recital
must be corroborated by the individually fetched Haydn event page: explicit
opera genre, composer credit, performance venue, city, date and local clock.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

INDEX="https://www.haydn.it/eventi/genere/opera"
SOURCE_KEY="haydn-rolling-opera"
HOST="www.haydn.it"
DETAIL=re.compile(r"/eventi/[a-z0-9][a-z0-9-]*/?")
DATE=re.compile(
    r"(?<!\d)([0-3]?\d)\.([01]?\d)\.(20\d{2})\s+alle\s+"
    r"([01]?\d|2[0-3])\.([0-5]\d)",re.I)

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.h1=[]
        self._h1=False
        self._ignore=0
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._ignore+=1
        if tag=="h1" and not self._ignore:self._h1=True
        if tag=="a" and not self._ignore:
            link=dict(attrs).get("href")
            if link:self.links.append(link)
    def handle_endtag(self,tag):
        if tag=="h1":self._h1=False
        if tag in ("script","style","noscript"):
            self._ignore=max(0,self._ignore-1)
    def handle_data(self,value):
        if self._ignore:return
        value=" ".join(value.split())
        if value:
            self.parts.append(value)
            if self._h1:self.h1.append(value)

def eligible_detail(url:str)->bool:
    parsed=urlsplit(url)
    return (parsed.scheme=="https" and parsed.hostname==HOST
            and bool(DETAIL.fullmatch(parsed.path)) and not parsed.query
            and not parsed.fragment and parsed.username is None
            and parsed.password is None and parsed.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("unapproved Haydn opera index")
    reader=Reader()
    reader.feed(html)
    # The index is first-party opera-filtered, but each detail must be
    # independently verified. No URL slugs are used as work evidence.
    urls=sorted({candidate for href in reader.links
                 if eligible_detail(candidate:=urljoin(INDEX,href))})
    if len(urls)<min_links:
        raise ValueError("season index incomplete or structure changed")
    return urls

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Haydn opera detail")
    reader=Reader()
    reader.feed(html)
    title=" ".join(reader.h1).strip()
    if not 2<=len(title)<=150:
        raise ValueError("Haydn primary title unverified")
    text=" ".join(reader.parts)
    # A biography after the Cast section can mention another composer,
    # theatre or opera. Never use it as programme evidence.
    primary=text.split(" Cast ",1)[0][:2500]
    start=primary.casefold().find(title.casefold())
    if start<0:raise ValueError("Haydn event heading absent")
    primary=primary[start+len(title):]
    if not re.search(r"(?<!\w)Opera(?!\w)",primary[:200]):
        raise ValueError("Haydn opera genre missing")
    credit=re.search(r"\bMusica\s+di\s+(.{3,95}?)\s+Libretto\s+di\b",
                     primary[:500],re.I)
    if credit is None:
        raise ValueError("Haydn composer credit missing or ambiguous")
    composer=" ".join(credit.group(1).split())
    if not re.fullmatch(r"[A-ZÀ-Ž][\wÀ-ÿ.'’ -]{3,85}",composer):
        raise ValueError("Haydn composer credit invalid")
    if len(re.findall(r"\bMusica\s+di\b",primary[:500],re.I))!=1:
        raise ValueError("conflicting Haydn composer credits")
    found=DATE.findall(primary[:850])
    if len(found)!=1:
        raise ValueError("missing or ambiguous Haydn event date and clock")
    day,month,year,hour,minute=map(int,found[0])
    try:iso=date(year,month,day).isoformat()
    except ValueError:raise ValueError("invalid Haydn official recital date")
    # Venue proof must occur inside the event facts, not biographies.
    programme=primary[:1100]
    if (re.search(r"Teatro\s+Comunale\s*[-–]\s*Sala\s+Grande"
                  r"\s+Piazza\s+Verdi\s+40\s*[-–]\s*Bolzano",programme,re.I)):
        venue="Teatro Comunale di Bolzano"
    elif re.search(r"Teatro\s+Sociale\s+Via\s+Paolo\s+Oss[-–]Mazzurana"
                   r"\s+19\s*[-–]\s*Trento",programme,re.I):
        venue="Teatro Sociale"
    else:
        raise ValueError("Haydn official physical venue not verified")
    return title,composer,venue,[(iso,f"{hour:02d}:{minute:02d}")]
