"""Official Teatro Filarmonico 2027 opera showtimes: exact first-party pages."""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS, clean

HOST="www.arena.it"
VENUE="Teatro Filarmonico"
WORKS={
    "il-ratto-dal-serraglio":("Il ratto dal serraglio","Wolfgang Amadeus Mozart"),
    "alzira":("Alzira","Giuseppe Verdi"),
    "fidelio":("Fidelio","Ludwig van Beethoven"),
    "il-signor-bruschino":("Il signor Bruschino","Gioachino Rossini"),
    "cristoforo-colombo":("Cristoforo Colombo","Alberto Franchetti"),
}
WEEKDAYS={"lunedi":0,"lunedì":0,"martedi":1,"martedì":1,
          "mercoledi":2,"mercoledì":2,"giovedi":3,"giovedì":3,
          "venerdi":4,"venerdì":4,"sabato":5,"domenica":6}
DATE=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
    r"\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+2027\s+ore\s+([01]?\d|2[0-3]):([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.query or u.fragment
        or u.port is not None or u.username or u.password):
        raise ValueError("unapproved Filarmonico source origin")
    match=re.fullmatch(r"/teatro-filarmonico-verona/2027/([a-z-]+)/?",u.path)
    if not match or match.group(1) not in WORKS:
        raise ValueError("unapproved Filarmonico 2027 opera")
    title,composer=WORKS[match.group(1)]
    text=clean(html)
    # The explicit Musica credit is part of the unique work detail.
    # Avoid composer guesses from page headings or related-opera footers.
    evidence=re.search(
        r"(?i)\bTipo di spettacolo\s+Opera\b.{0,350}?\bMusica\s+"
        +re.escape(composer)+r"\b",text)
    if not evidence:
        raise ValueError("official opera classification/composer absent")
    if not re.search(r"(?i)\bLocation\s+Teatro Filarmonico\b",text[:evidence.end()]):
        raise ValueError("official venue not confirmed")
    after=text[evidence.end():]
    # Exclude identical titles in related shows, cast biographies, footers,
    # descriptive prose and the general festival schedule.
    begin=re.search(r"(?i)\bProssimi spettacoli\b",after)
    if not begin:
        raise ValueError("official specific-show schedule not found")
    tail=after[begin.end():]
    end=re.search(r"(?i)\bCast\b",tail)
    if not end:
        raise ValueError("unbounded official specific-show schedule")
    block=tail[:end.start()]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block):
        raise ValueError("official cancellation requires review")
    recite=[]
    for row in DATE.finditer(block):
        weekday,day,month,hour,minute=row.groups()
        current=date(2027,MONTHS[month.casefold()],int(day))
        if current.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("official weekday conflicts with 2027 date")
        recite.append((current.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(recite)!=4 or len(set(recite))!=4:
        raise ValueError("missing or ambiguous four official Filarmonico performances")
    return title,composer,VENUE,sorted(recite)
