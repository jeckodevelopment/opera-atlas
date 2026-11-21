"""Official Petruzzelli annual opera: exact ticket dates, no inferred clocks."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean
from scripts.publish_catalog_v2 import normalized

MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
DAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,
      "venerdì":4,"sabato":5,"domenica":6}
SCHEDULE=re.compile(
    r"\b(lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
    r"\s+([0-3]?\d)\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})"
    r"\s*-\s*([01]?\d|2[0-3]):([0-5]\d)\b",re.I)
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")

def parse_petruzzelli_detail(html:str,*,url:str,title:str,composer:str,season_year:int=2027):
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.fondazionepetruzzelli.it"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment
        or not re.fullmatch(r"/eventi/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Petruzzelli opera detail")
    visible=clean(html)
    split=visible.find("Orari Spettacoli")
    if split<0:raise ValueError("official Petruzzelli ticket schedule missing")
    head=normalized(visible[:split]).replace("’","'")
    # The authoritative credit precedes the exact ticket schedule.
    official=normalized(title+" di "+composer).replace("’","'")
    # The opera credit must precede staff and talk notices; a later
    # conference mentioning the work is not sufficient attribution.
    credits=head.split("direttore",1)[0]
    if official not in credits:
        raise ValueError("official title and composer credit not confirmed")
    if not re.search(r"\b"+re.escape(normalized(composer))+r"\b",head):
        raise ValueError("composer absent from official Petruzzelli event")
    schedule=visible[split+len("Orari Spettacoli"):]
    for stop in ("Interpretato Da","Chiudi","Privacy Overview"):
        i=schedule.find(stop)
        if i>=0:schedule=schedule[:i]
    if CANCELLED.search(schedule):
        raise ValueError("cancelled or postponed Petruzzelli performance")
    # All official dates require hours. Never silently drop an incomplete card.
    weekday_dates=re.findall(
        r"(?i)\b(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
        r"\s+[0-3]?\d\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
        r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+20\d{2}\b",
        schedule)
    matches=SCHEDULE.findall(schedule)
    if len(matches)!=len(weekday_dates):
        raise ValueError("Petruzzelli schedule has dates without verified hours")
    found={}
    for weekday,day,month,year,hh,mm in matches:
        try:
            value=date(int(year),MONTHS[month.casefold()],int(day))
        except ValueError as exc:
            raise ValueError("invalid official Petruzzelli performance date") from exc
        if int(year)!=season_year or value.weekday()!=DAYS[weekday.casefold()]:
            raise ValueError("unexpected season or contradictory date/weekday")
        stamp=value.isoformat()
        hour=f"{int(hh):02d}:{mm}"
        if stamp in found and found[stamp]!=hour:
            raise ValueError("conflicting Petruzzelli ticket times")
        found[stamp]=hour
    if not found:
        raise ValueError("no complete Petruzzelli showtimes")
    return "Teatro Petruzzelli",sorted(found.items())
