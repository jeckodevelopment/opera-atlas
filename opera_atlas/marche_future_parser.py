"""Source-scoped, future-year opera programme verification for Marche theatres.

Historical 2026 production records are never applied to future programmes.
A future index is a candidate until its own heading, venue, explicit year,
and dated recite rows are verified. Only uniquely known canonical operas
with first-party composer credit can yield automatic performance evidence.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit

from opera_atlas.marche_2026_parser import WEEKDAYS,MONTHS,canon
from opera_atlas.national_detail_parser import clean

SOURCES={
    "jesi-opera-season-2027":(
        "www.fondazionepergolesispontini.com",
        "Teatro Giovan Battista Pergolesi",
        r"/lirica/programma-stagione-lirica-(20\d{2})/",
        "teatro pergolesi",
    ),
    "ancona-opera-season-2027":(
        "www.fondazionemuse.org",
        "Teatro delle Muse",
        r"/stagione-lirica-(20\d{2})/",
        "teatro delle muse",
    ),
}
DAY=r"(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
MONTH=r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
RECITE=re.compile(
    rf"(?i)\b{DAY}\s+(\d{{1,2}})\s+{MONTH}(?:\s+(20\d{{2}}))?"
    r"\s*,?\s*ore\s*([01]?\d|2[0-3])(?:[.:]([0-5]\d))?"
)

def season_context(html:str,*,url:str,source_key:str)->tuple[str,int,str]:
    if source_key not in SOURCES:
        raise ValueError("unapproved future Marche index source")
    host,venue,pattern,venue_label=SOURCES[source_key]
    parsed=urlsplit(url)
    year=re.fullmatch(pattern,parsed.path)
    if (parsed.scheme!="https" or parsed.hostname!=host or not year or
        parsed.query or parsed.fragment or parsed.username or parsed.password
        or parsed.port is not None):
        raise ValueError("unapproved future Marche season URL")
    season_year=int(year[1])
    if not 2027<=season_year<=2099:
        raise ValueError("invalid future Marche year")
    text=clean(html)
    if source_key.startswith("jesi-"):
        matches=list(re.finditer(
            r"(?i)\b(?:STAGIONE LIRICA(?: DI TRADIZIONE)?\s+"
            +str(season_year)+r"|(?:\d{1,3}\^?\s*)?STAGIONE LIRICA"
            r"(?: DI TRADIZIONE)?\s*(?:\bdi\b)?\s*"
            +str(season_year)+r")\b",text))
    else:
        matches=list(re.finditer(
            r"(?i)\bSTAGIONE LIRICA\s+"+str(season_year)+r"\b",text))
    if len(matches)!=1:
        raise ValueError("official future Marche season year not established")
    excerpt=text[matches[0].start():]
    if venue_label not in canon(excerpt[:1200]):
        raise ValueError("future Marche opera venue not confirmed")
    return excerpt,season_year,venue


def _date_rows(fragment:str,year:int):
    rows=[]
    for m in RECITE.finditer(fragment):
        weekday,day,month,printed_year,hour,minute=m.groups()
        if printed_year and int(printed_year)!=year:
            raise ValueError("Marche future recite year conflicts with season")
        observed=date(year,MONTHS[month.lower()],int(day))
        if observed.weekday()!=WEEKDAYS[weekday.lower()]:
            raise ValueError("Marche future recite weekday inconsistent")
        rows.append((m.start(),m.end(),observed.isoformat(),
                     f"{int(hour):02d}:{minute or '00'}"))
    return rows


def verify_index(html:str,*,url:str,source_key:str)->bool:
    """Only declare an index available if a real year-scoped opera is present."""
    text,year,venue=season_context(html,url=url,source_key=source_key)
    rows=_date_rows(text,year)
    if (len(rows)<2 or len(rows)>80 or
            not re.search(r"(?i)\bmusica\s+di\s+[A-Za-zÀ-ÿ]",text)):
        raise ValueError("future Marche season has no verified opera recite evidence")
    return True


def parse_known_opera_program(html:str,*,url:str,source_key:str,
                              registry:dict)->list[tuple[str,str,str,str,str]]:
    """Return only known, uniquely identified work showtimes; no title guesses.

    Dates are published only if linked to the local work heading and followed
    by its exact credited composer. Mixed bills and unknown works stay in
    manual/central review.
    """
    text,year,venue=season_context(html,url=url,source_key=source_key)
    from opera_atlas.work_identity import resolve_work
    works=registry.get("works",{}) if isinstance(registry,dict) else {}
    if not isinstance(works,dict):
        return []
    rows=_date_rows(text,year)
    evidence=[]
    for work in works.values():
        if not (isinstance(work,dict) and isinstance(work.get("title"),str)
                and isinstance(work.get("composer"),str)):
            continue
        title,composer=work["title"],work["composer"]
        # A title in a later synopsis or publicity mention must not become
        # a programme entry without directly adjacent showtime and credit.
        match=re.compile(r"(?i)(?<!\w)"+re.escape(title)+r"(?!\w)")
        for hit in match.finditer(text):
            before=text[max(0,hit.start()-270):hit.start()]
            previous=[r for r in rows if hit.start()-270<=r[1]<=hit.start()]
            # A standard theatre programme may have an educational preview;
            # reject unclear groupings instead of silently making up recite.
            if len(previous)!=2:
                continue
            credit=text[hit.end():hit.end()+250]
            if not re.search(r"(?i)\bmusica\s+di\s+"+re.escape(composer)+r"\b",credit):
                continue
            if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",
                         before+" "+credit):
                continue
            resolved=resolve_work(registry,title,composer)
            if resolved is None:
                continue
            dates=[(row[2],row[3]) for row in previous]
            if len({x[0] for x in dates})!=2:
                continue
            for day,clock in dates:
                evidence.append((resolved["title"],resolved["composer"],venue,
                                 day,clock))
    # Identical programme mentions are never double-counted.
    return sorted(set(evidence))
