"""Conservative five-title Teatro Verdi di Pisa 2026/27 opera parser."""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS,clean

HOST="teatrodipisa.it"
VENUE="Teatro Verdi"
# Exact source pages verified for this specific season; no assumptions from
# the larger historical 'Opera' archive or similarly titled other composers.
WORKS={
 "dido-and-aeneas":("Dido and Aeneas","Henry Purcell",2026),
 "loccasione-fa-il-ladro-ossia-il-cambio-della-valigia":("L'occasione fa il ladro","Gioachino Rossini",2026),
 "otello":("Otello","Giuseppe Verdi",2027),
 "aida":("Aida","Giuseppe Verdi",2027),
 "la-clemenza-di-tito":("La clemenza di Tito","Wolfgang Amadeus Mozart",2027),
}
DATE=re.compile(r"(?i)\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})\s+([01]?\d|2[0-3]):([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.port is not None
        or u.username or u.password or u.query or u.fragment):
        raise ValueError("unapproved Pisa opera source")
    match=re.fullmatch(r"/spettacolo/([a-z0-9-]+)/?",u.path)
    if not match or match.group(1) not in WORKS:
        raise ValueError("unknown official Pisa season opera")
    title,composer,year=WORKS[match.group(1)]
    text=clean(html)
    if not re.search(r"(?i)\bMusica di\s+"+re.escape(composer)+r"\b",text):
        raise ValueError("official composer credit missing")
    if not re.search(r"(?i)\bTeatro Verdi di Pisa\b",text):
        raise ValueError("source does not identify the Pisa opera house")
    # Performance rows only, never historical premiere dates and prose.
    section=re.search(r"(?i)\bDate\s*:\s*(.*?)(?:Acquista biglietto|Allegati|Galleria fotografica)",text,re.S)
    if not section:
        raise ValueError("bounded official performance dates absent")
    block=section.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block):
        raise ValueError("official schedule requires review")
    rows=[]
    for m in DATE.finditer(block):
        day,month,actual_year,hour,minute=m.groups()
        if int(actual_year)!=year:
            raise ValueError("source season year mismatch")
        dt=date(year,MONTHS[month.casefold()],int(day))
        rows.append((dt.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(rows)!=2 or len(set(rows))!=2:
        raise ValueError("missing or duplicate official Pisa showtimes")
    return title,composer,VENUE,sorted(rows)
