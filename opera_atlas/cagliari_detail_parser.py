"""First-party opera detail parser for Teatro Lirico di Cagliari.

Never parse a page's related-events carousel or date cast alternations.
The year comes from an explicit date or a verified 2027 season context,
never from today's date or the URL slug.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

HOST="www.liricocagliari.it"
SOURCE_KEY="lirico-cagliari-opera-2027"
VENUE="Teatro Lirico di Cagliari"
DAYS={"lun","mar","mer","merc","gio","ven","sab","dom"}


class PageHeadings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current=None
        self.parts=[]
        self.headings=[]
        self.text=[]
        self.depth=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript"):
            self.depth+=1
        if not self.depth and tag in ("h1","h2"):
            self.current=tag
            self.parts=[]
        if not self.depth and tag in ("p","li","div","br","h1","h2","h3","span"):
            self.text.append(" ")
    def handle_endtag(self, tag):
        if self.current==tag:
            self.headings.append((tag," ".join(" ".join(self.parts).split())))
            self.current=None
        if tag in ("script","style","noscript"):
            self.depth=max(0,self.depth-1)
        if not self.depth and tag in ("p","li","div","br","h1","h2","h3","span"):
            self.text.append(" ")
    def handle_data(self, data):
        if not self.depth:
            self.text.append(data)
            if self.current:
                self.parts.append(data)


def parse_detail(html: str, *, url: str, season_year: int = 2027) -> tuple[str,str,str,list[tuple[str,str]]]:
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!=HOST or parsed.query or
        parsed.fragment or parsed.username or parsed.password or parsed.port or
        not re.fullmatch(r"/evento/[a-z0-9-]+/",parsed.path)):
        raise ValueError("unapproved Cagliari detail URL")
    if season_year!=2027:
        raise ValueError("unsupported season")
    reader=PageHeadings()
    reader.feed(html)
    h1=[v for tag,v in reader.headings if tag=="h1"]
    h2=[v for tag,v in reader.headings if tag=="h2"]
    if len(h1)!=1 or not h1[0] or not h2:
        raise ValueError("missing unique work and composer headings")
    title=h1[0]
    composer=h2[0]
    if composer.casefold().startswith(("incontro", "parliamo", "balletto","concerto")):
        raise ValueError("not an opera composer")
    text=" ".join(" ".join(reader.text).split())
    # Only the production's Date section, before cast and related items.
    begin=re.search(r"\bDate\s+(?:vedi tutto\s+)?",text,re.I)
    if not begin:
        raise ValueError("missing official performance section")
    end=re.search(r"(?:Personaggi e interpreti|Cast|Team creativo|In breve|Prezzi e info)",text[begin.end():],re.I)
    if not end:
        raise ValueError("no trusted end to performance section")
    section=text[begin.end():begin.end()+end.start()]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section):
        raise ValueError("ambiguous cancellation")
    # Source markup has a duplicated 24/06 placeholder for many shows.
    # Require either the explicit year on each date or a first-party
    # season flag scoped to THIS detail page (not navigation).
    explicit=re.findall(
        r"(?i)\bore\s+([01]?\d|2[0-3]):([0-5]\d)\s+"
        r"(?:lun|mar|mer|merc|gio|ven|sab|dom)\s+"
        r"(\d{1,2})/(\d{1,2})/(20\d{2})\b",section)
    # A calendar with 2027 printed only on the index is not sufficiently
    # authoritative to assign a year to bare dd/mm in the detail.
    if not explicit:
        raise ValueError("recital year not explicit on official detail")
    found={}
    for h,m,d,mo,y in explicit:
        day=date(int(y),int(mo),int(d))
        if day.year!=season_year:
            continue
        clock=f"{int(h):02d}:{m}"
        iso=day.isoformat()
        if iso in found and found[iso]!=clock:
            raise ValueError("conflicting event times")
        found[iso]=clock
    if not found:
        raise ValueError("no explicit dates from requested season")
    if len(found)>35:
        raise ValueError("unreasonable performance count")
    return title,composer,VENUE,sorted(found.items())
