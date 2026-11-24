"""Strict Teatro Massimo Palermo historical work schedule extractor.

Only exact, independently reviewed public opera detail pages are admitted.
This adapter reports candidate evidence; it does not publish by itself.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit

from opera_atlas.national_detail_parser import clean

APPROVED = {
    "/event/dido-and-aeneas-2/": ("Dido and Aeneas", "Henry Purcell"),
    "/event/semiramide/": ("Semiramide", "Gioachino Rossini"),
    "/event/aida/": ("Aida", "Giuseppe Verdi"),
}
MONTHS = {"Febbraio":2, "Marzo":3, "Maggio":5}
DATES = re.compile(r"(?i)\b(\d{1,2})\s+(Febbraio|Marzo|Maggio)\s+((?:[01]?\d|2[0-3]):[0-5]\d)\b")
SHOW_HEADING = re.compile(r"\bLo spettacolo\b", re.I)


def parse_palermo_historical_showtimes(html: str, url: str):
    parts=urlsplit(url)
    if (parts.scheme!="https" or parts.hostname!="www.teatromassimo.it"
            or parts.path not in APPROVED or parts.query or parts.fragment):
        raise ValueError("unapproved Palermo historical opera detail")
    title, composer=APPROVED[parts.path]
    text=clean(html)
    h=SHOW_HEADING.search(text)
    if not h:
        raise ValueError("no official event heading")
    primary=text[h.end():h.end()+450]
    if (not re.search(r"\b2026\s*\|\s*Sala Grande\b",primary)
            or not re.search(re.escape(title),primary,re.I)
            or not re.search(r"Musiche di\s+"+re.escape(composer),primary,re.I)):
        raise ValueError("work, composer, actual venue or year not confirmed")
    schedule=text[:h.start()]
    hits=list(DATES.finditer(schedule))
    if not hits:
        raise ValueError("official Palermo schedule absent")
    dates={}
    for i,m in enumerate(hits):
        day=date(2026,MONTHS[m[2].capitalize()],int(m[1])).isoformat()
        clock=m[3]
        trailing=schedule[m.end():hits[i+1].start() if i+1<len(hits) else len(schedule)]
        # Explicitly excluded educational performances; the theatrical
        # production can contain both regular and school-only showtimes.
        if re.search(r"\bTurno Scuola\b",trailing,re.I):
            continue
        if day in dates and dates[day]!=clock:
            raise ValueError("conflicting Palermo showtimes")
        dates[day]=clock
    if not dates:
        raise ValueError("no public general-audience recite")
    return title,composer,"Teatro Massimo",sorted(dates.items())
