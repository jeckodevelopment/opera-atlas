"""Official Ente Concerti Marialisa de Carolis: Sassari 2026 opera recite.

The shared season also includes two Alghero Festival productions and
symphonic concerts; only the three approved Sassari opera event IDs
are eligible for the Teatro Comunale.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

HOST="www.marialisadecarolis.it"
VENUE="Teatro Comunale di Sassari"
WORKS={
    "372":("Il flauto magico","Wolfgang Amadeus Mozart",
           (("2026-09-25","20:30"),("2026-09-27","16:30"))),
    "373":("Don Carlo","Giuseppe Verdi",
           (("2026-10-30","20:30"),("2026-11-01","16:30"))),
    "375":("Rigoletto","Giuseppe Verdi",
           (("2026-12-11","20:30"),("2026-12-13","16:30"))),
}
MONTHS={"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
TIMES=re.compile(r"(?i)\b(\d{1,2})\s+(SETTEMBRE|OTTOBRE|NOVEMBRE|DICEMBRE)\s+"
                 r"([01]?\d|2[0-3]):([0-5]\d)\b")

def parse_detail(html:str,*,url:str):
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname!=HOST or p.path!="/opera-lirica.aspx"
            or p.query not in {"id=372","id=373","id=375"}
            or p.fragment or p.port is not None
            or p.username or p.password):
        raise ValueError("unapproved Sassari production URL")
    title,composer,expected=WORKS[p.query.split("=")[1]]
    text=clean(html).replace("’","'").replace("´","'")
    # Work identity and exact times must be contiguous with the heading:
    # do not read other operas in the shared navigation/season footer.
    heading=re.search(r"(?i)\b"+re.escape(title)+r"\s+"
                      +re.escape(composer)+r"\b\s*",text)
    if not heading or heading.start()>650:
        raise ValueError("official work identity and composer absent in heading")
    if not re.search(r"(?i)\b(?:Stagione\s+2026|Opere e concerti 2026)\b",
                     text[:heading.start()]):
        raise ValueError("official 2026 season context missing")
    after=text[heading.end():heading.end()+115]
    matches=TIMES.findall(after)
    if len(matches)!=2:
        raise ValueError("two precise showtime tokens not beside work heading")
    rows=[]
    for day,month,hour,minute in matches:
        stamp=date(2026,MONTHS[month.casefold()],int(day))
        rows.append((stamp.isoformat(),f"{int(hour):02d}:{minute}"))
    if sorted(rows)!=sorted(expected):
        raise ValueError("showtime does not match approved first-party detail")
    body_end=re.search(r"(?i)\b(?:Notizie\s*/\s*News|Stagione Lirica e Sinfonica)\b",
                       text[heading.end():])
    core=text[heading.end():heading.end()+body_end.start()] if body_end else text[heading.end():heading.end()+1800]
    if not re.search(r"(?i)\bTeatro Comunale\b",core):
        raise ValueError("official Teatro Comunale venue missing in production detail")
    if re.search(r"(?i)\b(?:Alghero Festival|Forte della Maddalena)\b",core[:500]):
        raise ValueError("event is at the Alghero Festival, not Sassari")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",core[:600]):
        raise ValueError("reported cancellation requires review")
    return title,composer,VENUE,sorted(rows)
