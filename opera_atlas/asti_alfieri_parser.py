"""Conservative evergreen Opera discovery for Teatro Alfieri, Asti.

A season category includes concerts and prose. Only independently verified
first-party detail pages with an opera genre, credited composer, physical
theatre and local performance clock may reach central reconciliation.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

INDEX="https://www.teatroalfieriasti.it/events/categoria/fuori-abbonamento/"
HOST="www.teatroalfieriasti.it"
KEY="asti-alfieri-rolling-opera"
_DETAIL=re.compile(r"/event/[a-z0-9-]+/")
_DATE=re.compile(r"(?<!\d)([0-3]?\d)/([01]?\d)/(20\d{2})\s*@\s*([01]?\d|2[0-3]):([0-5]\d)")
_GENRE=re.compile(r"\b(?:opera(?!\s+musical)|melodramma|dramma\s+lirico)\b",re.I)
_CREDIT=re.compile(
    r"\b(?:musica\s+di|di)\s+"
    r"([A-ZÀ-Ž][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÀ-Ž][A-Za-zÀ-ÿ.'’\-]+){1,4})"
    r"\s+(?=Regia\b|Produzione\b|Direzione\b|Cast\b|"
    r"Fuori\s+abbonamento\b|Opera\b|Melodramma\b)",re.I)

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.parts=[]
        self.h1=[]
        self._h1=False
        self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag=="h1" and not self._skip:self._h1=True
        if tag=="a" and not self._skip:
            href=dict(attrs).get("href")
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag=="h1":self._h1=False
        if tag in ("script","style","noscript"):self._skip=max(0,self._skip-1)
    def handle_data(self,text):
        if self._skip:return
        text=" ".join(text.split())
        if text:
            self.parts.append(text)
            if self._h1:self.h1.append(text)

def eligible_detail(url:str)->bool:
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST
            and bool(_DETAIL.fullmatch(u.path)) and not u.query
            and not u.fragment and u.username is None and u.password is None
            and u.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("unapproved Asti theatre index")
    reader=Reader()
    reader.feed(html)
    urls=sorted({link for href in reader.links
                 if eligible_detail(link:=urljoin(INDEX,href))})
    # These are candidates, not proof of opera genre. A concert at the same
    # URL structure is rejected by parse_detail before promotion.
    if len(urls)<min_links:
        raise ValueError("season index incomplete or structure changed")
    return urls

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Asti event URL")
    reader=Reader()
    reader.feed(html)
    if len(reader.h1)==0:
        raise ValueError("Asti opera title unverified")
    title=" ".join(reader.h1).strip()
    if not 2<=len(title)<=140:raise ValueError("invalid Asti opera title")
    visible=" ".join(reader.parts)
    head=re.search(r"\b"+re.escape(title)+r"\b",visible,re.I)
    if head is None:raise ValueError("Asti opera title missing from official page")
    primary=visible[head.end():head.end()+1500]
    # Do not identify genre from the global footer or unrelated ticket info.
    if not _GENRE.search(primary[:700]) or re.search(r"\bopera\s+musical\b",primary[:700],re.I):
        raise ValueError("Asti event is not verified as an opera")
    credits=_CREDIT.findall(primary[:650])
    if len(credits)!=1:
        raise ValueError("missing or ambiguous Asti composer credit")
    composer=credits[0]
    venue=re.search(r"\bLuogo\s+Teatro Alfieri\b.{0,180}?\bAsti\b",visible,re.I)
    if not venue:raise ValueError("Asti venue not verified")
    date_match=_DATE.search(primary[:120])
    if not date_match:
        raise ValueError("missing Asti official event date and time")
    day,month,year,hour,minute=map(int,date_match.groups())
    try:when=date(year,month,day).isoformat()
    except ValueError:raise ValueError("invalid Asti official date")
    return title,composer,"Teatro Alfieri",[(when,f"{hour:02d}:{minute:02d}")]
