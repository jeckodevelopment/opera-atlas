"""Official Comune di Modena opera events: exact work, venue, date and time.

The municipality publishes the Pavarotti-Freni opera season and individual
event pages. Yearless day/month rows are assigned a year ONLY if exactly one
of 2026 or 2027 matches the weekday in the officially labelled 2026/27 season.
"""
from __future__ import annotations
import re
import unicodedata
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.national_detail_parser import clean, MONTHS

KEY="modena-opera-2026-27"
HOST="www.comune.modena.it"
SEASON_PATH=re.compile(r"/vivere-modena/eventi/(20\d{2})/stagione-opera-\1-(20\d{2})/[a-z0-9-]+/?")
VENUE="Teatro Comunale Pavarotti-Freni"
WEEKDAYS={"lunedi":0,"martedi":1,"mercoledi":2,"giovedi":3,
          "venerdi":4,"sabato":5,"domenica":6}


class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.value=[]
        self.titles=[]
        self.in_h1=False
    def handle_starttag(self,tag,attrs):
        if tag=="h1":
            self.in_h1=True
            self.value=[]
    def handle_data(self,data):
        if self.in_h1:
            self.value.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.in_h1:
            self.titles.append(" ".join(" ".join(self.value).split()))
            self.in_h1=False


def unaccent(s:str)->str:
    return "".join(x for x in unicodedata.normalize("NFKD",s.casefold())
                   if not unicodedata.combining(x))


def exact_day(weekday:str,day:str,month:str,year:str|None,*,
              season_start_year:int=2026)->str:
    if unaccent(month) not in MONTHS or unaccent(weekday) not in WEEKDAYS:
        raise ValueError("unsupported Modena date wording")
    if not 2026<=season_start_year<=2098:
        raise ValueError("unsupported Modena opera season")
    years=[int(year)] if year else [season_start_year,season_start_year+1]
    valid=[]
    for y in years:
        try: d=date(y,MONTHS[unaccent(month)],int(day))
        except ValueError:continue
        if (date(season_start_year,10,1)<=d<=date(season_start_year+1,7,31)
            and d.weekday()==WEEKDAYS[unaccent(weekday)]):
            valid.append(d.isoformat())
    if len(valid)!=1:
        raise ValueError("day/month is not uniquely verified in official season")
    return valid[0]


def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    loc=urlsplit(url)
    if (loc.scheme!="https" or loc.hostname!=HOST or loc.query or loc.fragment
        or loc.username or loc.password or loc.port is not None
        or not SEASON_PATH.fullmatch(loc.path)):
        raise ValueError("invalid official Modena season event URL")
    season_match=SEASON_PATH.fullmatch(loc.path)
    season_start_year=int(season_match.group(1))
    if int(season_match.group(2))!=season_start_year+1:
        raise ValueError("inconsistent official Modena season years")
    head=TitleParser()
    head.feed(html)
    if len(head.titles)!=1:
        raise ValueError("missing unique official opera event heading")
    raw=head.titles[0]
    # A title-with-author is verified from the first-party page heading.
    # Other work identities stay in the review queue until verified separately.
    credit=re.fullmatch(r"(.+?)\s+di\s+([A-ZÀ-Ý][\wÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'’.-]+){1,3})",raw)
    if not credit:
        raise ValueError("composer not credited in official production heading")
    title,composer=credit.groups()
    body=clean(html)
    venue=re.search(r"\bLuogo\s+(.+?)\s+(?:Corso Canal Grande|Maggiori dettagli|Date e orari)\b",body,re.I)
    if not venue or VENUE.casefold() not in venue.group(1).casefold():
        raise ValueError("event not assigned to Teatro Comunale Pavarotti-Freni")
    section=re.search(r"\bDate e orari\s+Orari\s+(.*?)\s+(?:Costi|Contatti|Fa parte della rassegna)\b",body,re.I)
    if not section:
        raise ValueError("missing bounded municipal showtime section")
    text=section.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",text):
        raise ValueError("official cancellation needs reconciliation")
    rx=re.compile(
        r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
        r"\s+(\d{1,2})\s+"
        r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|ottobre|novembre|dicembre)"
        r"(?:\s+(20\d{2}))?\s+ore\s+([01]?\d|2[0-3])(?:[.:]([0-5]\d))?\b")
    found={}
    for dow,day,month,year,hour,minute in rx.findall(text):
        iso=exact_day(dow,day,month,year or None,season_start_year=season_start_year)
        time=f"{int(hour):02d}:{minute or '00'}"
        if iso in found:
            raise ValueError("duplicate or conflicting municipal recital")
        found[iso]=time
    # Every named weekday/date in the bounded section must have a verified
    # clock. A half-parsed schedule cannot publish a subset of its recite.
    dated_rows=len(re.findall(r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)\s+\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)",text))
    if not found or len(found)>24 or dated_rows!=len(found) or len(re.findall(r"\bore\s+\d{1,2}",text,re.I))!=len(found):
        raise ValueError("incomplete municipal opera recital calendar")
    return title,composer,VENUE,sorted(found.items())
