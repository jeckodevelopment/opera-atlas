"""Official Comune di Padova opera programme (Teatro Verdi, 2026).

One season notice includes both the operas and a separate New Year's concert.
Only literal individual times tied to the opera/venue are eligible.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

HOST="padovacultura.padovanet.it"
PATH="/it/attivita-culturali/stagione-lirica-di-padova-2026"
VENUE="Teatro Verdi"
PRODUCTIONS=(
    ("Pagliacci","Ruggero Leoncavallo",((20,"novembre","20.45"),(22,"novembre","16.00"))),
    ("La traviata","Giuseppe Verdi",((28,"dicembre","20.45"),(29,"dicembre","20.45"),(31,"dicembre","21.00"))),
)
MONTHS={"novembre":11,"dicembre":12}

def parse_program(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.path.rstrip("/")!=PATH
            or u.port is not None or u.username or u.password
            or u.query or u.fragment):
        raise ValueError("unapproved Padova first-party season page")
    text=clean(re.sub(r"(?i)</h[1-6]>", " </h3> ",html))
    if not re.search(r"(?i)\bStagione Lirica di Padova 2026\b",text):
        raise ValueError("season 2026 not established")
    m=re.search(r"(?i)\bProgramma\b(.*?)\bInformazioni\b",text,re.S)
    if not m:
        raise ValueError("bounded official opera programme missing")
    section=m.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section):
        raise ValueError("official cancellation requires review")
    rows=[]
    for title,composer,showtimes in PRODUCTIONS:
        # Each opera is a unique line of official ticket information ending
        # with the theatre name, followed by a composer-bearing description.
        dates=r"\s*,\s*".join(
            rf"{day}\s+{month}\s+ore\s+{re.escape(clock)}"
            if i==0 else rf"{day}\s+{month}\s+ore\s+{re.escape(clock)}"
            for i,(day,month,clock) in enumerate(showtimes))
        # The official source omits the month after the first date; do not
        # require it again for subsequent dates.
        dates=r"\s*,\s*".join(
            rf"{day}\s+"+(rf"{month}\s+" if i==0 else rf"(?:{month}\s+)?")+
            rf"ore\s+{re.escape(clock)}"
            for i,(day,month,clock) in enumerate(showtimes))
        pattern=(re.escape(title)+r"\s*,\s*"+dates+
                 r"\s*,\s*Teatro Verdi di Padova\b")
        found=re.search(pattern,section,re.I)
        if not found:
            raise ValueError(f"missing complete Padova opera schedule for {title}")
        next_detail=section[found.end():found.end()+700]
        # Close at ticket info, not at the following opera's composer.
        next_detail=re.split(r"(?i)\bbiglietti da\b",next_detail,maxsplit=1)[0]
        if not re.search(r"(?i)\b(?:musica (?:e libretto )?di|opera in tre atti di)\s+"+re.escape(composer)+r"(?=\s*(?:[.,;]|su\b))",next_detail):
            raise ValueError(f"missing official composer for {title}")
        for day,month,clock in showtimes:
            stamp=date(2026,MONTHS[month],day).isoformat()
            rows.append((title,composer,VENUE,stamp,clock.replace(".",":")))
    if len(rows)!=5 or len({(x[0],x[3],x[4]) for x in rows})!=5:
        raise ValueError("Padova five public opera showtimes not verified")
    return rows
