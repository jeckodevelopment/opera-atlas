"""Exact municipal first-party fallback for 2026 Spoleto opera recite.

The Teatro Lirico Sperimentale's official calendar remains the primary,
rolling source. Only this dated Comune di Spoleto article may act as the
secondary source for the 2026 season, with its own recorded provenance.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean, MONTHS
from opera_atlas.spoleto_tls_parser import VENUE,DATE_ROW,WEEKDAY

URL="https://www.comune.spoleto.pg.it/it/news/2022369"
ORIGIN="https://www.comune.spoleto.pg.it/"
INTRO=re.compile(r"(?i)\bL.opera sarà rappresentata al\s+"
                 r"Teatro Nuovo Gian Carlo Menotti di Spoleto\b")

def parse_program(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.comune.spoleto.pg.it"
            or target.path!="/it/news/2022369" or target.query or target.fragment
            or target.username or target.password or target.port is not None):
        raise ValueError("unapproved Comune di Spoleto opera notice")
    text=clean(html)
    if not (re.search(r"(?i)\b80a Stagione Lirica Sperimentale\b",text)
            and re.search(r"(?i)\b2026\b",text)
            and re.search(r"(?i)\bL[’']elisir d[’']amore\b",text)
            and re.search(r"(?i)\bGaetano Donizetti\b",text)):
        raise ValueError("Spoleto municipal opera identity unverified")
    matches=list(INTRO.finditer(text))
    if len(matches)!=1:
        raise ValueError("missing unique Teatro Nuovo municipal recite paragraph")
    section=text[matches[0].end():]
    section=re.split(r"(?i)\b(?:recite per le scuole|Quest.ultima produzione sarà replicata)\b",
                     section,maxsplit=1)[0].strip(" (")
    rows=DATE_ROW.findall(section)
    if len(rows)!=3:
        raise ValueError("incomplete Spoleto municipal public performance calendar")
    result=[]
    for weekday,day,month,hour,minute in rows:
        dt=date(2026,MONTHS[month.lower()],int(day))
        if dt.weekday()!=WEEKDAY[weekday.lower().replace("ì","i")]:
            raise ValueError("Spoleto municipality weekday contradicts date")
        result.append(("L’elisir d’amore","Gaetano Donizetti",VENUE,
                       dt.isoformat(),f"{int(hour):02d}:{minute}"))
    if len({x[3] for x in result})!=3:
        raise ValueError("duplicate municipal recita")
    return result
