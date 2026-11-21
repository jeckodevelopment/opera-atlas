"""Exact-source Teatro Verdi di Salerno opera schedule, season 2026."""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS,clean

HOST="cultura.comune.salerno.it"
VENUE="Teatro Municipale Giuseppe Verdi"
# Only the six explicitly classified opera/operetta pages are included.
# Carmen and La vie en rose/Bolero are ballet, not opera here.
WORKS={
 "trovatore-2026":("Il trovatore","Giuseppe Verdi",2),
 "il-signor-bruschino-2026":("Il signor Bruschino","Gioachino Rossini",2),
 "il-barbiere-di-siviglia-2026":("Il barbiere di Siviglia","Gioachino Rossini",2),
 "macbeth-2026":("Macbeth","Giuseppe Verdi",2),
 "la-vedova-allegra-2026":("La vedova allegra","Franz Lehár",3),
 "turandot-2026":("Turandot","Giacomo Puccini",3),
}
WEEKDAYS={"lunedì":0,"lunedi":0,"martedì":1,"martedi":1,
          "mercoledì":2,"mercoledi":2,"giovedì":3,"giovedi":3,
          "venerdì":4,"venerdi":4,"sabato":5,"domenica":6}
DATE=re.compile(r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre),?\s+ore\s+([01]?\d|2[0-3])[:.]([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.query or u.fragment
        or u.port is not None or u.username or u.password):
        raise ValueError("unapproved Salerno host or URL")
    match=re.fullmatch(r"/eventi/([a-z-]+-2026)/?",u.path)
    if not match or match.group(1) not in WORKS:
        raise ValueError("unapproved Salerno production")
    title,composer,count=WORKS[match.group(1)]
    text=clean(html)
    heading=re.search(r"(?i)\b"+re.escape(title.removeprefix("Il ").replace("’","'"))+r"\b",text)
    if not heading:
        raise ValueError("missing official opera title")
    if not re.search(r"(?i)\b(?:opera|operetta)\b.{0,130}?\bdi\s+"+re.escape(composer)+r"\b",text):
        raise ValueError("missing official composer credit")
    if VENUE.casefold() not in text.casefold():
        raise ValueError("missing exact venue")
    section=re.search(r"(?i)\bAPPUNTAMENTI\b(.*?)(?:\bLuoghi collegati\b|\bData inizio\b)",text,re.S)
    if not section:
        raise ValueError("missing bounded appointment block")
    block=section.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block):
        raise ValueError("cancelled or postponed source requires review")
    rows=[]
    for m in DATE.finditer(block):
        weekday,day,month,hour,minute=m.groups()
        dt=date(2026,MONTHS[month.casefold()],int(day))
        if dt.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("official weekday conflicts with 2026")
        rows.append((dt.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(rows)!=count or len(set(rows))!=count:
        raise ValueError("missing, duplicated or ambiguous showtimes")
    return title,composer,VENUE,sorted(rows)
