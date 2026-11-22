"""Official Teatro Comunale Mario del Monaco 2026/27 multi-opera programme.

The season page explicitly defines preview Wednesday (schools), ordinary
Friday and Sunday performance turns. Never include a school preview by
deducing a public showtime from the dates alone.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlsplit
import re
from opera_atlas.national_detail_parser import clean, MONTHS

HOST="risorse.teatrostabileveneto.it"
PATH="/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27"
VENUE="Teatro Comunale Mario del Monaco"
WORKS=(
    ("La traviata","Giuseppe Verdi",(21,23,25),"ottobre",2026),
    ("Pagliacci","Ruggero Leoncavallo",(1,4,6),"dicembre",2026),
    ("Il cappello di paglia di Firenze","Nino Rota",(3,5,7),"marzo",2027),
)

def parse_program(html:str,*,url:str):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.path.rstrip("/")!=PATH
        or u.username or u.password or u.port is not None or u.query or u.fragment):
        raise ValueError("unapproved Treviso first-party season page")
    text=clean(re.sub(r"(?i)</h[1-6]>", " </h3> ",html))
    m=re.search(r"(?i)\bPROGRAMMA STAGIONE LIRICA 26/27\b(.*?)\bPREZZI ABBONAMENTI LIRICA\b",text,re.S)
    if not m:
        raise ValueError("official opera section missing or unbounded")
    section=m.group(1)
    if not re.search(r"(?i)\bANTEPRIMA PER SCUOLE\b.*?\bMercoledì ore 18[.:]00\b.*?\bTURNO A\b\s+Venerdì ore 20[.:]00\b.*?\bTURNO C\b\s+Domenica ore 16[.:]00\b",section,re.S):
        raise ValueError("official weekday / ticket turn schedule missing")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section):
        raise ValueError("official cancellation requires review")
    rows=[]
    for title,composer,days,month,year in WORKS:
        # Must confirm all three advertised date tokens, followed directly
        # by the production title and composer. Avoid concert listings, ticket
        # prices, cast biographies and generic Opera/Verdi associations.
        pattern=(r"\b"+r"\s*,\s*".join(map(str,days))+r"\s+"+month+
                 r"\s+"+str(year)+r"\s+"+re.escape(title)+
                 r"\s*/\s*"+re.escape(composer)+r"\b")
        if not re.search(pattern,section,re.I):
            raise ValueError(f"missing verified Treviso production: {title}")
        scheduled=[date(year,MONTHS[month],day) for day in days]
        preview_weekday = 1 if title=="Pagliacci" else 2
        if [d.weekday() for d in scheduled]!=[preview_weekday,4,6]:
            raise ValueError("official dates do not match preview/Friday/Sunday turns")
        # On the main season page the mid-week date is explicitly the
        # schools-only preview. It MUST NOT be published as public recita.
        rows.extend((title,composer,VENUE,dt.isoformat(),clock)
                    for dt,clock in ((scheduled[1],"20:00"),(scheduled[2],"16:00")))
    if len(rows)!=6 or len({(x[0],x[3]) for x in rows})!=6:
        raise ValueError("incomplete Treviso public-opera programme")
    return rows
