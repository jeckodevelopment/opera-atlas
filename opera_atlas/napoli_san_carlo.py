"""First-party Napoli San Carlo opera only: never bypass anti-bot checks.

An accessible public events index is discovery, not evidence of a performance.
Each event must separately prove opera genre, composer, official venue, and
dated local recita. Security-check HTML is neither an empty season nor success.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
import re

SOURCE_KEY="napoli-san-carlo-rolling-opera"
INDEX="https://www.teatrosancarlo.it/spettacoli/"
HOST="www.teatrosancarlo.it"
EVENT=re.compile(r"/spettacoli/([a-z0-9][a-z0-9-]*)/")
DATES=re.compile(r"(?<!\d)([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})\s*(?:alle|ore|h\.?)[ ]*([01]?\d|2[0-3])[:.]([0-5]\d)",re.I)
AUTHOR=re.compile(r"\b(?:Musica|Composizione)\s+di\s+([A-ZÀ-Ž][\wÀ-ÿ.'’ -]{3,75}?)(?=\s+(?:Libretto\s+di|Date\b|Teatro\s+di\s+San\s+Carlo\b))",re.I)

class SanCarloSecurityChallenge(ValueError):
    """Official site returned an anti-bot checkpoint, not an opera index."""


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.h1=[];self.links=[];self._heading=False;self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag=="h1" and not self._skip:self._heading=True
        if tag=="a" and not self._skip:
            url=dict(attrs).get("href")
            if url:self.links.append(url)
    def handle_endtag(self,tag):
        if tag=="h1":self._heading=False
        if tag in ("script","style","noscript"):self._skip=max(self._skip-1,0)
    def handle_data(self,s):
        if self._skip:return
        s=" ".join(s.split())
        if s:
            self.parts.append(s)
            if self._heading:self.h1.append(s)

def eligible_detail(url:str)->bool:
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST
        and bool(EVENT.fullmatch(u.path)) and not u.query and not u.fragment
        and u.port is None and u.username is None and u.password is None)

def _accessible(text:str):
    if re.search(r"(?:security\s+check\s+required|your browsing looks a bit unusual|"
                 r"complete this security check|captcha|access denied)",text,re.I):
        raise SanCarloSecurityChallenge("San Carlo security challenge; defer instead of bypass")

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("unapproved San Carlo rolling index")
    _accessible(html)
    page=Page();page.feed(html)
    found=sorted({candidate for href in page.links
                  if eligible_detail(candidate:=urljoin(url,href))})
    if len(found)<min_links:
        raise ValueError("San Carlo official opera event links not verified")
    return found

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved San Carlo detail")
    _accessible(html)
    page=Page();page.feed(html)
    title=" ".join(page.h1).strip()
    if not 2<=len(title)<=150:raise ValueError("San Carlo official work title missing")
    start=next((i for i,v in enumerate(page.parts) if v==title),None)
    if start is None:raise ValueError("San Carlo primary heading missing")
    primary=" ".join(page.parts[start:start+65]).split(" Cast ",1)[0]
    # A calendar covering ballet/concerts/education is not itself genre proof.
    if not re.search(r"\bOpera\b", " ".join(page.parts[start+1:start+8]),re.I):
        raise ValueError("San Carlo event genre not certified as opera")
    # Never capture the following Libretto line as a composer if
    # the source prints an empty "Musica di" field.
    credits=[part[len("Musica di "):].strip() for part in page.parts
             if part.startswith("Musica di ")]
    if (len(credits)!=1 or not re.fullmatch(
            r"[A-ZÀ-Ž][A-Za-zÀ-ÿ.'’ -]{3,75}",credits[0])):
        raise ValueError("San Carlo composer not credited")
    composer=credits[0]
    if not re.search(r"\bTeatro\s+di\s+San\s+Carlo\b",primary,re.I):
        raise ValueError("San Carlo venue not explicitly confirmed")
    entries=DATES.findall(primary)
    if not entries or len(entries)>20:
        raise ValueError("San Carlo exact official showtimes not found")
    rows=[]
    for d,m,y,h,minute in entries:
        try:day=date(int(y),int(m),int(d)).isoformat()
        except ValueError:raise ValueError("invalid San Carlo official calendar day")
        rows.append((day,f"{int(h):02d}:{minute}"))
    if len(rows)!=len({day for day,_ in rows}):
        raise ValueError("ambiguous multiple San Carlo performances on same day")
    return title,composer,"Teatro di San Carlo",rows
