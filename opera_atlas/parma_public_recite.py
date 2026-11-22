"""Verified first-party Parma family tickets, never school performances.

The venue publishes four labelled rows on two December dates. Only the
Saturday 5 December 2026 Famiglie slots can enter the public catalog.
"""
from __future__ import annotations
from html.parser import HTMLParser
import re
from scripts.build_verified_catalog import official_local_time
from opera_atlas.national_detail_parser import clean

URL="https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/"
TITLE="Piccolo Orso e la montagna di ghiaccio"
COMPOSER="Giovanni Sollima"
PUBLIC=(("2026-12-05","15:00"),("2026-12-05","18:00"))

def official_public_recite(html:str,*,url:str)->list[dict]:
    if url!=URL:
        raise ValueError("unapproved Parma opera detail")
    # WordPress renders adjacent inline ticket fields without separators.
    markup=re.sub(r"(?i)</?(?:span|small|strong|b|em|ul|ol|button|label|time|h[1-6])\b[^>]*>",
                  " ",html)
    text=clean(markup)
    head=text.casefold().find(TITLE.casefold())
    if head<0:
        raise ValueError("missing Parma opera heading")
    event=text[head:head+11000]
    if (COMPOSER not in event or "Giancarlo De Cataldo" not in event
        or "Teatro Regio di Parma" not in event
        or "4 dic 2026" not in event or "5 dic 2026" not in event):
        raise ValueError("missing independent Parma work or season attribution")
    # Parse the actual source ticket segment only. The theatre may add words
    # between date and clock; row validity still requires a day, one clock
    # and the adjacent audience label, never a ticket inferred from the year.
    start=event.find("Teatro Regio di Parma")
    calendar=event[start:]
    calendar=re.split(r"(?i)\b(?:ticket|agevolazioni|kit\s+dello\s+spettatore|informazioni)\b",
                      calendar,maxsplit=1)[0]
    # Exclude labels such as a paragraph about school ticket collection
    # by requiring a weekday/date, clock and audience in the same row.
    row=re.compile(r"(?i)\b(ven|sab)\.?\s*([45])\s+dic\b"
                   r"([^\n]{0,160}?)\b([01]?\d|2[0-3]):([0-5]\d)\b"
                   r"([^\n]{0,80}?)\b(Scuole|Famiglie)\b")
    observed=[]
    for m in row.finditer(calendar):
        day=int(m[2])
        clock=f"{int(m[4]):02d}:{m[5]}"
        observed.append((day,clock,m[7].casefold()))
    expected={(4,"09:00","scuole"),(4,"11:00","scuole"),
              (5,"15:00","famiglie"),(5,"18:00","famiglie")}
    if set(observed)!=expected or len(observed)!=4:
        raise ValueError("incomplete official Parma public/school ticket schedule")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",calendar):
        raise ValueError("cancelled Parma recita needs review")
    return [{"event_title":TITLE,"composer":COMPOSER,
             "venue":"Teatro Regio di Parma","date":day,
             "starts_at":official_local_time(day,hour)}
            for day,hour in PUBLIC]
