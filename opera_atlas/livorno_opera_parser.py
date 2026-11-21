"""Official Livorno Goldoni 2026/27 opera schedule parser.

Two independent controls: source-published dates and weekdays, and the
composer credit directly following the selected work heading. The single
season article contains unrelated theatre venues and event genres.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS,clean

HOST="www.goldoniteatro.it"
PATH="/notizie/la-stagione-lirica"
VENUE="Teatro Goldoni"
SOURCES={
    "goldoni-livorno-dido-2026-27":("DIDO AND AENEAS","Henry Purcell",2026,2),
    "goldoni-livorno-otello-2026-27":("OTELLO","Giuseppe Verdi",2027,2),
    "goldoni-livorno-elisir-2026-27":("L’ELISIR D’AMORE","Gaetano Donizetti",2027,2),
}
DATE=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
    r"\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre),?\s*"
    r"ore\s+([01]\d|2[0-3]|[0-9])(?:[.:]([0-5]\d))?\b")
WEEKDAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,"venerdì":4,"sabato":5,"domenica":6,
          "lunedi":0,"martedi":1,"mercoledi":2,"giovedi":3,"venerdi":4}


def parse_detail(html:str,*,url:str,source_key:str):
    site=urlsplit(url)
    if (site.scheme!="https" or site.hostname!=HOST or
        site.path.rstrip("/")!=PATH or site.username or site.password or
        site.port is not None or site.query or site.fragment):
        raise ValueError("Livorno opera source outside first-party URL")
    if source_key not in SOURCES:
        raise ValueError("unknown Livorno opera source")
    title,composer,year,required=SOURCES[source_key]
    content=clean(html)
    # Bound article and all operas before Opera Oggi, which uses Goldonetta,
    # not the Teatro Goldoni, and has separate contemporary works.
    match=re.search(r"\bLA STAGIONE LIRICA 2026/27\b(.*?)\bOPERA OGGI\b",content,re.I)
    if not match:
        raise ValueError("official 2026/27 Livorno season article missing")
    article=match.group(1)
    all_titles=["CAVALLERIA RUSTICANA"]+[value[0] for value in SOURCES.values()]
    # Date lines immediately preceding the title belong to that title.
    start=re.search(re.escape(title),article,re.I)
    if not start or len(list(re.finditer(re.escape(title),article,re.I)))!=1:
        raise ValueError("missing unique Livorno opera title")
    earlier=[(article.upper().rfind(x.upper(),0,start.start()),x)
             for x in all_titles]
    earlier=[(index,heading) for index,heading in earlier if index>=0]
    if not earlier:
        raise ValueError("Livorno previous season boundary missing")
    previous,previous_heading=max(earlier,key=lambda x:x[0])
    before=article[previous+len(previous_heading):start.start()]
    # Only the final two showtimes preceding each work can be accepted;
    # cross-verify their weekday and year. No season-wide date guessing.
    dates=list(DATE.finditer(before))
    if len(dates)!=required:
        raise ValueError("incomplete or ambiguous Livorno showtime section")
    found=[]
    for match_day in dates:
        weekday,day,month,hour,minute=match_day.groups()
        day_date=date(year,MONTHS[month.casefold()],int(day))
        if day_date.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("Livorno official day conflicts with season year")
        found.append((day_date.isoformat(),f"{int(hour):02d}:{minute or '00'}"))
    if len({d for d,_ in found})!=required:
        raise ValueError("duplicate official Livorno recite")
    following=article[start.end():]
    next_title=min([p for x in all_titles if x!=title
                   for p in [following.upper().find(x.upper())] if p>=0]+[len(following)])
    credit_text=following[:next_title]
    if not re.search(r"\bMusica di\s+"+re.escape(composer)+r"\b",credit_text,re.I):
        raise ValueError("official composer not verified for selected Livorno work")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",
                 article[start.start():start.end()+len(credit_text)]):
        raise ValueError("cancellation or postponed event requires reconciliation")
    return title,composer,VENUE,sorted(found)
