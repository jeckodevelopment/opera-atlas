"""Exact first-party performance times for Teatro Vittorio Emanuele Messina.

The official opera category includes two operas and one operetta.
No date-range interpolation, default showtime, or genre inference.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

HOST="www.teatrovittorioemanuele.it"
VENUE="Teatro Vittorio Emanuele"
WORKS={
    "madama-butterfly":("Madama Butterfly","Giacomo Puccini",
        (("2027-02-26","21:00"),("2027-02-28","17:30"))),
    "la-traviata":("La traviata","Giuseppe Verdi",
        (("2027-04-16","21:00"),("2027-04-18","17:30"))),
    "al-cavallino-bianco":("Al cavallino bianco","Ralph Benatzky",
        (("2027-05-07","21:00"),("2027-05-08","21:00"))),
}
SHOW=re.compile(r"(?i)\bData\s*-\s*(\d{2})-(\d{2})-(20\d{2})\s+"
                r"Orario\s*-\s*([01]?\d|2[0-3]):([0-5]\d)\b")

def parse_detail(html:str,*,url:str,registry:dict|None=None):
    target=urlsplit(url)
    m=re.fullmatch(r"/evento/([a-z0-9-]+)/?",target.path)
    if (target.scheme!="https" or target.hostname!=HOST
        or target.query or target.fragment or target.port is not None
        or target.username or target.password or not m
        ):
        raise ValueError("unapproved Messina opera event URL")
    text=clean(html)
    categories=re.findall(r"(?i)\\bOpera\\s+(\\d{2})\\s*/\\s*(\\d{2})\\b",text)
    if len(categories)!=1:
        raise ValueError("unique official Messina opera category required")
    season_start,season_end=map(int,categories[0])
    if season_start<26 or season_start>98 or season_end!=(season_start+1)%100:
        raise ValueError("invalid official Messina opera season")
    if season_start!=26:
        return parse_future_detail(html,url=url,season_start=season_start,
                                   registry=registry)
    if m.group(1) not in WORKS:
        raise ValueError("unapproved 2026/27 Messina opera URL")
    title,composer,expected=WORKS[m.group(1)]
    text=clean(html)
    # Title, composer, venue and the category must be on the SAME official
    # event page, not inferred from index or a similarly named opera.
    if not re.search(r"(?i)\b"+re.escape(title)+r"\b",text):
        raise ValueError("production heading missing")
    head=text[:text.find("Orario spettacoli e turni abbonati")]
    if not re.search(r"(?i)\bdi\s+"+re.escape(composer)+r"\b",head):
        raise ValueError("composer not credited on official event")
    block=re.search(r"(?i)\bOrario spettacoli e turni abbonati\b(.*?)\bDate spettacolo\b",
                    text,re.S)
    if not block:
        raise ValueError("showtime block not bounded by official headings")
    if not re.search(r"(?i)\bSala Grande\s*-\s*Teatro Vittorio Emanuele\b",text):
        raise ValueError("official Messina theatre venue not identified")
    if not re.search(r"(?i)\bOpera 26/27\b",text):
        raise ValueError("official 2026/27 opera category absent")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block.group(1)):
        raise ValueError("performance cancellation requires manual verification")
    rows=[]
    for day,month,year,hour,minute in SHOW.findall(block.group(1)):
        stamp=date(int(year),int(month),int(day)).isoformat()
        rows.append((stamp,f"{int(hour):02d}:{minute}"))
    # Explicit blank form rows are harmless; any extra dated performance,
    # missing detail, duplicate or changed time must fail closed.
    if sorted(rows)!=sorted(expected) or len(rows)!=2:
        raise ValueError("two exact official Messina performances required")
    return title,composer,VENUE,sorted(rows)

class _Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth=0
        self.current=[]
        self.headings=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h1":
            self.depth+=1
            if self.depth==1:self.current=[]
    def handle_data(self,data):
        if self.depth:self.current.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.depth:
            self.depth-=1
            if not self.depth:self.headings.append(" ".join(self.current).strip())

def parse_future_detail(html:str,*,url:str,season_start:int,
                        registry:dict|None):
    """Future season: source-credited, known opera identities and exact recite.

    Requires first-party event HTML already discovered via the official
    season index. Unknown works remain for authority review, never guessed.
    """
    if not registry or not isinstance(registry.get("works"),dict):
        raise ValueError("future Messina opera needs a canonical registry")
    headings=_Headings()
    headings.feed(html)
    if len(headings.headings)!=1 or not headings.headings[0]:
        raise ValueError("single official opera production heading required")
    title=clean(headings.headings[0])
    text=clean(html)
    head=text.split("Orario spettacoli e turni abbonati",1)[0]
    if head==text:
        raise ValueError("showtime section absent")
    from opera_atlas.work_identity import resolve_work
    recognized=[]
    for composer in {w["composer"] for w in registry["works"].values()
                     if isinstance(w,dict) and isinstance(w.get("composer"),str)}:
        if (re.search(r"(?i)\\bdi\\s+"+re.escape(composer)+r"\\b",head)
                and resolve_work(registry,title,composer) is not None):
            recognized.append(composer)
    if len(recognized)!=1:
        raise ValueError("unique title and explicit composer credit required")
    composer=recognized[0]
    block=re.search(r"(?i)\\bOrario spettacoli e turni abbonati\\b(.*?)\\bDate spettacolo\\b",
                    text,re.S)
    if not block:
        raise ValueError("unbounded showtime section")
    if not re.search(r"(?i)\\bSala Grande\\s*-\\s*Teatro Vittorio Emanuele\\b",text):
        raise ValueError("official Messina venue missing")
    if re.search(r"(?i)\\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\\b",block[1]):
        raise ValueError("cancelled recite requires manual verification")
    rows=[]
    for day,month,year,hour,minute in SHOW.findall(block[1]):
        when=date(int(year),int(month),int(day))
        if not date(2000+season_start,7,1)<=when<=date(2001+season_start,6,30):
            raise ValueError("recite date outside official opera season")
        rows.append((when.isoformat(),f"{int(hour):02d}:{minute}"))
    # No inferred dates, and no incomplete dated/time rows or duplicates.
    dated=re.findall(r"(?i)\\bData\\s*-\\s*\\d{2}-\\d{2}-20\\d{2}",block[1])
    times=re.findall(r"(?i)\\bOrario\\s*-\\s*(?:[01]?\\d|2[0-3]):[0-5]\\d",block[1])
    if (not rows or len(rows)>24 or len(dated)!=len(rows)
            or len(times)!=len(rows) or len(set(rows))!=len(rows)):
        raise ValueError("future Messina showtimes incomplete or duplicate")
    return title,composer,VENUE,sorted(rows)
