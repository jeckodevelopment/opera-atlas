"""2027 Alighieri Ravenna: first-party performing-orchestra evidence, fail closed."""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS, clean

HOST="www.orchestracherubini.it"
VENUE="Teatro Dante Alighieri"
WORKS={
    "pagliacci-2":("Pagliacci","Ruggero Leoncavallo"),
    "la-cenerentola-4":("La Cenerentola","Gioachino Rossini"),
}
WEEKDAYS={"lunedì":0,"lunedi":0,"martedì":1,"martedi":1,
          "mercoledì":2,"mercoledi":2,"giovedì":3,"giovedi":3,
          "venerdì":4,"venerdi":4,"sabato":5,"domenica":6}
SHOW=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
    r"\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+2027\s+alle\s+"
    r"([01]?\d|2[0-3]):([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.port is not None
        or u.username or u.password or u.query or u.fragment):
        raise ValueError("Ravenna source origin is not approved")
    m=re.fullmatch(r"/eventi/([a-z0-9-]+)/?",u.path)
    if not m or m.group(1) not in WORKS:
        raise ValueError("not a verified Ravenna 2027 opera")
    title,composer=WORKS[m.group(1)]
    text=clean(re.sub(r"(?i)</h[2-6]>", " </h3> ",html))
    if not re.search(r"(?i)\b"+re.escape(title)+r"\b",text):
        raise ValueError("official opera title missing")
    if not re.search(r"(?i)\b(?:libretto e )?musica di\s+"+re.escape(composer)+r"\b",text):
        raise ValueError("performing orchestra did not confirm composer")
    if not re.search(r"(?i)\bOrchestra Giovanile Luigi Cherubini\b",text):
        raise ValueError("performing orchestra not identified")
    scope=re.search(r"(?i)\bDate\b(.*?)\bDettagli\b\s+Opera\s+\bLuogo\b\s+Teatro Alighieri,\s*Ravenna\b",text,re.S)
    if not scope:
        raise ValueError("bounded opera schedule and Ravenna venue missing")
    block=scope.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block):
        raise ValueError("performance cancellation requires review")
    rows=[]
    for row in SHOW.finditer(block):
        wd,day,month,hour,minute=row.groups()
        current=date(2027,MONTHS[month.casefold()],int(day))
        if current.weekday()!=WEEKDAYS[wd.casefold()]:
            raise ValueError("weekday differs from official 2027 date")
        rows.append((current.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(rows)!=2 or len(set(rows))!=2:
        raise ValueError("two exact official showtimes required")
    return title,composer,VENUE,sorted(rows)
