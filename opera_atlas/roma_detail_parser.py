"""Fail-closed exact opera dates from the official Teatro Costanzi detail page."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from html.parser import HTMLParser

from opera_atlas.national_detail_parser import clean
from scripts.publish_catalog_v2 import normalized

MONTHS={"gen":1,"feb":2,"mar":3,"apr":4,"mag":5,"giu":6,
        "lug":7,"ago":8,"set":9,"ott":10,"nov":11,"dic":12}
DAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,
      "venerdì":4,"sabato":5,"domenica":6}
PERFORMANCE=re.compile(
    r"\b(lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
    r"\s+([0-3]?\d)\s+(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)"
    r"\s+ORE\s+([01]?\d|2[0-3]):([0-5]\d)\b",re.I)
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")

class Heading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.collect=False
        self.parts=[]
        self.title=None
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.title is None:
            self.collect=True
    def handle_data(self,data):
        if self.collect:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.collect:
            self.title=" ".join("".join(self.parts).split())
            self.collect=False

def parse_roma_detail(html:str,*,url:str,title:str,composer:str)->tuple[str,list[tuple[str,str]]]:
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.operaroma.it"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment
        or not re.fullmatch(r"/spettacoli/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Rome theatre detail")
    heading=Heading()
    heading.feed(html)
    if normalized(heading.title or "").replace("’","'") != normalized(title).replace("’","'"):
        raise ValueError("official Rome heading does not match canonical work")
    visible=clean(html)
    pos=visible.find("Le date")
    if pos<0:
        raise ValueError("official Rome performance schedule missing")
    context=visible[:pos]
    if not re.search(r"Stagione\s+2026\s*/\s*2027",context,re.I):
        raise ValueError("Rome event not in verified 2026/27 season")
    if not re.search(r"\bMusica\s+di\s+"+re.escape(composer)+r"\b",
                     context.replace("’","'"),re.I):
        raise ValueError("composer absent from official Rome production")
    if "Teatro Costanzi" not in context:
        raise ValueError("actual Rome auditorium not confirmed")
    # Stop before preview performances, recommendations and school activities.
    section=visible[pos+len("Le date"):]
    for stop in ("Anteprima giovani","Ti può interessare anche",
                 "Altri eventi","Potrebbe interessarti"):
        idx=section.find(stop)
        if idx>=0:section=section[:idx]
    if CANCELLED.search(section):
        raise ValueError("cancelled or postponed Rome performance")
    found={}
    for weekday,day,month,hh,mm in PERFORMANCE.findall(section):
        try:
            actual=date(2027 if MONTHS[month.casefold()]<=8 else 2026,
                        MONTHS[month.casefold()],int(day))
        except ValueError as exc:
            raise ValueError("invalid Rome performance date") from exc
        if actual.weekday()!=DAYS[weekday.casefold()]:
            raise ValueError("Rome event weekday contradicts official date")
        iso=actual.isoformat()
        clock=f"{int(hh):02d}:{mm}"
        if iso in found and found[iso]!=clock:
            raise ValueError("conflicting Rome performance time")
        found[iso]=clock
    if not found:
        raise ValueError("no dated and timed Rome performances")
    return "Teatro dell'Opera di Roma", sorted(found.items())
