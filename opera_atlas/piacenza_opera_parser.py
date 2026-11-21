"""Official 2026/27 Piacenza opera production cards, without school previews.

The source is a single approved official season index. Each production page
must independently credit a composer and list exact public dates and hours.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS, clean

HOST="teatripiacenza.it"
KEY="piacenza-opera-2026-27"
VENUE="Teatro Municipale"
INDEX="https://teatripiacenza.it/stagioni/stagione-26-27/"
RESTRICTED=re.compile(r"(?i)\b(?:scuole|studenti|docenti|prova aperta|anteprima|riservat[oaie]|#siberia18)\b")
DAY=r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
MONTH=r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
SHOWTIME=re.compile(rf"(?i)\b{DAY}\s+(\d{{1,2}})\s+({MONTH})\s+(20\d{{2}})\s*Ore\s+([01]?\d|2[0-3]):([0-5]\d)\b")


class Production(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title=[]
        self.composers=[]
        self.tag=None
        self.parts=[]
        self.anchors=[]
        self.anchor=None
        self.stopped=False
    def handle_starttag(self,tag,attrs):
        if self.stopped:return
        if tag in ("h1","h6"):
            self.tag=tag
            self.parts=[]
        if tag=="a":
            self.anchor=[]
    def handle_data(self,data):
        if self.stopped:return
        if self.tag is not None:self.parts.append(data)
        if self.anchor is not None:self.anchor.append(data)
    def handle_endtag(self,tag):
        if self.stopped:return
        if tag==self.tag:
            value=" ".join(" ".join(self.parts).split())
            if tag=="h1" and value:self.title.append(value)
            if tag=="h6" and value:self.composers.append(value)
            self.tag=None
        if tag=="a" and self.anchor is not None:
            value=" ".join(" ".join(self.anchor).split())
            self.anchors.append(value)
            self.anchor=None
        if tag=="h3" and self.anchors:
            # Stop only when the first performer section starts (text checked below).
            pass


def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    loc=urlsplit(url)
    if (loc.scheme!="https" or loc.hostname!=HOST or loc.query or loc.fragment
        or loc.username or loc.password or loc.port is not None
        or not re.fullmatch(r"/event/[a-z0-9-]+/?",loc.path)):
        raise ValueError("Piacenza detail outside official source allowlist")
    parser=Production()
    parser.feed(html)
    if len(parser.title)!=1 or not parser.composers:
        raise ValueError("missing unique official Piacenza production credits")
    title=parser.title[0]
    credit=parser.composers[0].strip()
    if not re.fullmatch(r"[A-ZÀ-Ý][A-ZÀ-Ýa-zà-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][A-ZÀ-Ýa-zà-ÿ'’.-]+){1,3}",credit):
        raise ValueError("ambiguous first-party composer")
    text=clean(html)
    # Keep the first production facts; the page then repeats the entire
    # season navigation (including other operas, concerts and Young events).
    end=re.search(r"\bINTERPRETI\b",text,re.I)
    if not end:
        raise ValueError("missing boundary to production-only schedule")
    scope=text[:end.start()]
    if title.casefold() not in scope.casefold():
        raise ValueError("work identity outside production header")
    found={}
    # Each named date is one source listing, including excluded school
    # previews. Never mistake those as regular ticketed performances.
    dates=list(SHOWTIME.finditer(scope))
    loose=re.findall(rf"(?i)\b{DAY}\s+\d{{1,2}}\s+{MONTH}\s+20\d{{2}}",scope)
    if not dates or len(loose)!=len(dates):
        raise ValueError("missing or partial production showtimes")
    for index,match in enumerate(dates):
        trailing=scope[match.end():dates[index+1].start() if index+1<len(dates) else len(scope)]
        is_restricted=bool(RESTRICTED.search(trailing))
        if is_restricted:
            continue
        day,month,year,hour,minute=match.groups()
        if int(year) not in (2026,2027):
            raise ValueError("recital outside approved season")
        iso=date(int(year),MONTHS[month.casefold()],int(day)).isoformat()
        if iso in found:
            raise ValueError("duplicate or contradictory official recital")
        found[iso]=f"{int(hour):02d}:{minute}"
    if not found or len(found)>24:
        raise ValueError("no valid ordinary opera recite in official detail")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",scope):
        raise ValueError("official cancellation requires reconciliation")
    return title,credit,VENUE,sorted(found.items())
