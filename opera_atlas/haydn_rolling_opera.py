"""First-party Haydn Opera area calendar for Bolzano and Trento; detail-gated.

The evergreen Opera-area index mixes recite, introductions and education. Every recital
must be corroborated by the individually fetched Haydn event page: explicit
opera genre, composer credit, performance venue, city, date and local clock.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

INDEX="https://www.haydn.it/eventi/area/opera"
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
    # The first-party Opera area includes intros, backstage events and opera.
    # Each event detail must be
    # independently verified. No URL slugs are used as work evidence.
    urls=sorted({candidate for href in reader.links
                 if eligible_detail(candidate:=urljoin(INDEX,href))})
    if len(urls)<min_links:
        raise ValueError("season index incomplete or structure changed")
    return urls

def replica_group_url(html:str,*,url:str)->str|None:
    """Read the explicit first-party Repliche link, never infer from ticket slugs."""
    if not eligible_detail(url):return None
    from scripts.haydn_replica_identity import valid_group
    reader=Reader()
    reader.feed(html)
    groups={absolute for link in reader.links
            if valid_group(absolute:=urljoin(url,link))}
    return next(iter(groups)) if len(groups)==1 else None


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
    category=primary.split("Musica di",1)[0]
    if not re.search(r"(?<!\w)Opera(?!\w)",category[:200]):
        raise ValueError("Haydn opera genre missing")
    credit=re.search(r"\bMusica\s+di\s+(.{3,95}?)\s+Libretto\s+di\b",
                     primary[:500],re.I)
    if credit is None:
        raise ValueError("Haydn composer credit missing or ambiguous")
    composer=" ".join(credit.group(1).split())
    # Haydn prints a full composer name under the event H1 and may use
    # an abbreviated middle name in the separate "Musica di" label.
    # Reconcile the two *same-page* credits only when every token agrees
    # literally or via an unambiguous initial; do not guess identities.
    heading_position=next((i for i,value in enumerate(reader.parts)
                           if value==title),None)
    if heading_position is None or heading_position+1>=len(reader.parts):
        raise ValueError("Haydn composer heading missing")
    heading_composer=reader.parts[heading_position+1].strip()
    full_tokens=heading_composer.split()
    credited_tokens=composer.split()
    if (not 2<=len(full_tokens)<=5 or len(full_tokens)!=len(credited_tokens)
        or not all(
            first.casefold()==second.casefold()
            or (len(second)==2 and second.endswith(".")
                and len(first)>2 and first[0].casefold()==second[0].casefold())
            for first,second in zip(full_tokens,credited_tokens))):
        raise ValueError("Haydn heading and music composer credits conflict")
    composer=heading_composer
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
