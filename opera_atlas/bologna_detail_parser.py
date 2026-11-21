"""Verified Teatro Comunale di Bologna production details (not the season teaser).

Never infer a composer, venue or start time from the season summary.
The ticket section on the official opera detail must state each date and
clock. The actual performance building is retained, including Manzoni.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

MONTHS={"gen":1,"feb":2,"mar":3,"apr":4,"mag":5,"giu":6,
        "lug":7,"ago":8,"set":9,"ott":10,"nov":11,"dic":12}
DATE=re.compile(r"\b(\d{1,2})\s+(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)\s+(20\d{2})\s+Ore\s+([01]?\d|2[0-3]):([0-5]\d)\b",re.I)
VENUES={"Teatro Comunale":"Teatro Comunale di Bologna",
        "Teatro Auditorium Manzoni":"Teatro Auditorium Manzoni"}
class Heading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth=0
        self.title=None
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.title is None:
            self.depth=1
            self.parts=[]
        elif self.depth:self.depth+=1
    def handle_endtag(self,tag):
        if self.depth:
            self.depth-=1
            if self.depth==0:self.title=" ".join("".join(self.parts).split())
    def handle_data(self,data):
        if self.depth:self.parts.append(data)

def parse_detail(html:str,*,url:str):
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.tcbo.it" or
        target.query or target.fragment or target.username or target.password or
        target.port is not None or not re.fullmatch(
            r"/evento/opera/[a-z0-9-]+-(20\d{2})/",target.path)):
        raise ValueError("unapproved Bologna opera detail")
    year=int(re.search(r"(20\d{2})/$",target.path)[1])
    heading=Heading()
    heading.feed(html)
    title=heading.title
    if not title or not 2<=len(title)<=140:
        raise ValueError("Bologna official opera title missing")
    text=clean(html)
    if not re.search(r"\bOpera\b",text[:1500]):
        raise ValueError("Bologna page is not an opera")
    match=re.search(r"\bCompositore\s+(.{3,90}?)\s*\(\d{4}(?:-\d{4})?\)",text)
    if not match:
        raise ValueError("official Bologna composer missing")
    composer=match[1].strip()
    if "Date e turni" not in text:
        raise ValueError("no Bologna ticket-date section")
    section=text.split("Date e turni",1)[1].split("Sede",1)[0]
    if not section or len(section)>3500:
        raise ValueError("ambiguous Bologna ticket-date section")
    following=text.split("Date e turni",1)[1].split("Sede",1)
    if len(following)!=2:raise ValueError("Bologna venue missing")
    venue=next((canonical for label,canonical in sorted(VENUES.items(),key=lambda p:-len(p[0]))
                if re.match(r"\s*"+re.escape(label)+r"\b",following[1])),None)
    if not venue:raise ValueError("unsupported official Bologna performance venue")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section):
        raise ValueError("changed/cancelled Bologna date requires individual verification")
    output={}
    for m in DATE.finditer(section):
        try:day=date(int(m[3]),MONTHS[m[2].lower()],int(m[1]))
        except ValueError:continue
        if day.year!=year:continue
        clock=f"{int(m[4]):02d}:{m[5]}"
        if day.isoformat() in output and output[day.isoformat()]!=clock:
            raise ValueError("conflicting Bologna showtimes")
        output[day.isoformat()]=clock
    if not output:
        raise ValueError("no individually clocked Bologna performances")
    return title,composer,venue,sorted(output.items())
