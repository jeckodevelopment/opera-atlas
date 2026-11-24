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
    # The live official pages include "Lo spettacolo" and ticket headings
    # in different DOM wrappers. Find the identity block by its explicit
    # year + Sala Grande assertion rather than relying on one heading's
    # exact position in the flattened HTML.
    contexts=[]
    for marker in re.finditer(r"\\b2026\\s*\\|\\s*Sala Grande\\b",text,re.I):
        context=text[marker.start():marker.end()+550]
        if (re.search(re.escape(title),context,re.I)
                and re.search(r"Musiche\\s+di\\s+"+re.escape(composer),context,re.I)):
            contexts.append(marker)
    if len(contexts)!=1:
        raise ValueError("official Palermo work composer venue/year section missing or ambiguous")
    marker=contexts[0]
    heading_matches=list(SHOW_HEADING.finditer(text[:marker.start()]))
    # An unrelated footer or menu cannot authorize a showtime. The actual
    # official work heading is adjacent to the 2026 + Sala Grande assertion.
    if not heading_matches or marker.start()-heading_matches[-1].end()>180:
        raise ValueError("official Palermo work heading not adjacent to schedule")
    schedule=text[:heading_matches[-1].start()]
    # Only the dated ticket area immediately preceding "Lo spettacolo".
    # Footer/news/menus can contain times; use exact month names for the
    # reviewed show and require the identified 2026 main-stage schedule.
    hits=list(DATES.finditer(schedule))
    if not hits:
        raise ValueError("official Palermo dated ticket schedule absent")
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
