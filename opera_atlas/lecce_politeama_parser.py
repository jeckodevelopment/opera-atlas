"""Official Politeama Greco, Lecce: three explicitly ticketed 2026 operas.

Query-bearing ASP pages are allowed only for three exact numeric IDs.
The source must independently confirm date, time, venue and composer;
press conferences and season bundles cannot become performances.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

HOST="www.politeamagreco.it"
VENUE="Teatro Politeama Greco"
WORKS={
    "1147":("Turandot","Giacomo Puccini",((13,11,"20:45"),(15,11,"18:00"))),
    "1148":("L'elisir d'amore","Gaetano Donizetti",((27,11,"20:45"),(29,11,"18:00"))),
    "1149":("Nabucco","Giuseppe Verdi",((11,12,"20:45"),(13,12,"18:00"))),
}

def parse_detail(html:str,*,url:str):
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname!=HOST or p.path!="/scheda.asp"
        or p.query not in {"id=1147","id=1148","id=1149"}
        or p.fragment or p.username or p.password or p.port is not None):
        raise ValueError("unapproved Politeama opera URL")
    title,composer,expected=WORKS[p.query.split("=")[1]]
    body=clean(re.sub(r"(?i)</h[1-6]>", " </h3> ",html)).replace("’","'")
    if not re.search(r"(?i)\bTEATRO POLITEAMA GRECO DI LECCE\b",body):
        raise ValueError("official opera venue missing")
    if not re.search(r"(?i)\bStagione Lirica di tradizione 2026\b",body):
        raise ValueError("incorrect season")
    # The detail page explicitly labels its season with the year; dates in
    # its own ticket panel are the only evidence, not promotional metadata.
    heading=re.search(r"(?i)Stagione Lirica di tradizione 2026\s+"
                      +re.escape(title)+r"\s+di\s+"+re.escape(composer)+r"\b",body)
    if not heading:
        raise ValueError("work and composer not attributed on official page")
    tail=body[heading.end():]
    end=re.search(r"(?i)\bPREZZI\b|\bPERSONAGGI E INTERPRETI\b",tail)
    panel=tail[:end.start()] if end else tail[:900]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",panel):
        raise ValueError("cancellation requires review")
    month_names={11:"novembre",12:"dicembre"}
    rows=[]
    for day,month,clock in expected:
        # A standalone date with its exact labelled showtime must appear
        # within this specific work panel. The same title's historic premiere
        # or ticket-sale hours are not substitute evidence.
        pattern=(rf"\b{day}\s+{month_names[month]}\s+ore\s+"
                 +clock.replace(":",r"[.:]")+r"\b")
        if len(re.findall(pattern,panel,re.I))!=1:
            raise ValueError("unverified or duplicated ticketed showtime")
        rows.append((date(2026,month,day).isoformat(),clock))
    other=re.findall(r"\b(\d{1,2})\s+(novembre|dicembre)\s+ore\s+([01]?\d|2[0-3])[.:]([0-5]\d)\b",panel,re.I)
    if len(other)!=2:
        raise ValueError("unexpected extra official production date")
    return title,composer,VENUE,rows
