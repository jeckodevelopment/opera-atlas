"""Exact first-party performance times for Teatro Vittorio Emanuele Messina.

The official opera category includes two operas and one operetta.
No date-range interpolation, default showtime, or genre inference.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

HOST="www.teatrovittorioemanuele.it"
VENUE="Teatro Vittorio Emanuele"
WORKS={
    "madama-butterfly":("Madama Butterfly","Giacomo Puccini",
        (("2027-02-26","21:00"),("2027-02-28","17:30"))),
    "la-traviata":("La traviata","Giuseppe Verdi",
        (("2027-04-16","21:00"),("2027-04-18","17:30"))),
    "al-cavallino-bianco":("Al cavallino bianco","Ralph Benatzky",
        (("2027-05-07","21:00"),("2027-05-08","21:00"))),
}
SHOW=re.compile(r"(?i)\bData\s*-\s*(\d{2})-(\d{2})-(20\d{2})\s+"
                r"Orario\s*-\s*([01]?\d|2[0-3]):([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    target=urlsplit(url)
    m=re.fullmatch(r"/evento/([a-z0-9-]+)/?",target.path)
    if (target.scheme!="https" or target.hostname!=HOST
        or target.query or target.fragment or target.port is not None
        or target.username or target.password or not m
        or m.group(1) not in WORKS):
        raise ValueError("unapproved Messina opera event URL")
    title,composer,expected=WORKS[m.group(1)]
    text=clean(html)
    # Title, composer, venue and the category must be on the SAME official
    # event page, not inferred from index or a similarly named opera.
    if not re.search(r"(?i)\b"+re.escape(title)+r"\b",text):
        raise ValueError("production heading missing")
    head=text[:text.find("Orario spettacoli e turni abbonati")]
    if not re.search(r"(?i)\bdi\s+"+re.escape(composer)+r"\b",head):
        raise ValueError("composer not credited on official event")
    block=re.search(r"(?i)\bOrario spettacoli e turni abbonati\b(.*?)\bDate spettacolo\b",
                    text,re.S)
    if not block:
        raise ValueError("showtime block not bounded by official headings")
    if not re.search(r"(?i)\bSala Grande\s*-\s*Teatro Vittorio Emanuele\b",text):
        raise ValueError("official Messina theatre venue not identified")
    if not re.search(r"(?i)\bOpera 26/27\b",text):
        raise ValueError("official 2026/27 opera category absent")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block.group(1)):
        raise ValueError("performance cancellation requires manual verification")
    rows=[]
    for day,month,year,hour,minute in SHOW.findall(block.group(1)):
        stamp=date(int(year),int(month),int(day)).isoformat()
        rows.append((stamp,f"{int(hour):02d}:{minute}"))
    # Explicit blank form rows are harmless; any extra dated performance,
    # missing detail, duplicate or changed time must fail closed.
    if sorted(rows)!=sorted(expected) or len(rows)!=2:
        raise ValueError("two exact official Messina performances required")
    return title,composer,VENUE,sorted(rows)
