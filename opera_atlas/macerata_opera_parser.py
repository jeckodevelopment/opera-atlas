"""Official Macerata Opera Festival 2027 detail parser, bounded to one work."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS, clean

VENUE="Arena Sferisterio"
WORKS={
    "tosca":("Tosca","Giacomo Puccini",4),
    "la-traviata":("La traviata","Giuseppe Verdi",4),
    "elisir-damore":("L'elisir d'amore","Gaetano Donizetti",3),
}
WEEKDAYS={"lunedi":0,"lunedì":0,"martedi":1,"martedì":1,
          "mercoledi":2,"mercoledì":2,"giovedi":3,"giovedì":3,
          "venerdi":4,"venerdì":4,"sabato":5,"domenica":6}
DATES=re.compile(r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+(luglio|agosto)\s+H\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    source=urlsplit(url)
    if (source.scheme!="https" or source.hostname!="www.sferisterio.it"
        or source.username or source.password or source.port is not None
        or source.query or source.fragment):
        raise ValueError("unapproved Macerata official URL")
    match=re.fullmatch(r"/macerata-opera-festival/([a-z-]+)",source.path.rstrip("/"))
    if not match or match.group(1) not in WORKS:
        raise ValueError("unapproved Macerata opera page")
    title,composer,required=WORKS[match.group(1)]
    content=clean(html)
    # Each detail has a composer credit and dates before the Cast heading.
    # The footer repeats dates for all three works and MUST NOT be parsed.
    label=re.search(r"(?i)Opera lirica in .{0,160}? di\s+"+re.escape(composer)+r"\b",content)
    if not label:
        raise ValueError("Macerata official opera composer credit missing")
    tail=content[label.end():]
    boundary=re.search(r"(?i)\bCast\b|\bGli appuntamenti in cartellone\b",tail)
    if not boundary:
        raise ValueError("Macerata event schedule boundary missing")
    block=tail[:boundary.start()]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block):
        raise ValueError("Macerata event cancelled or postponed")
    rows=[]
    for match_day in DATES.finditer(block):
        weekday,day,month,hour,minute=match_day.groups()
        observed=date(2027,MONTHS[month.casefold()],int(day))
        if observed.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("Macerata weekday conflicts with the 2027 season")
        rows.append((observed.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(rows)!=required or len(set(rows))!=required:
        raise ValueError("Macerata opera dates missing or ambiguous")
    return title,composer,VENUE,sorted(rows)
