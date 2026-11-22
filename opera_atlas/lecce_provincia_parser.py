"""Independent first-party Province of Lecce evidence for Politeama's 2026 opera season.

The Province organizes the season. Unlike the venue website, its press
release is reachable by the approved national source pipeline. Never treat
school rehearsals, talks or the separate Teatro Apollo opera as performances.
"""
from __future__ import annotations
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

URL = ("https://www.provincia.le.it/"
       "https-www-provincia-le-it-al-via-la-51-stagione-lirica-della-"
       "provincia-di-lecce-lunedi-9-novembre-la-conferenza-stampa-"
       "di-presentazione-del-cartellone-2026/")
VENUE = "Teatro Politeama Greco"
SCHEDULE = (
    ("Turandot", "Giacomo Puccini", (("2026-11-13","20:45"),("2026-11-15","18:00"))),
    ("L'elisir d'amore", "Gaetano Donizetti", (("2026-11-27","20:45"),("2026-11-29","18:00"))),
    ("Nabucco", "Giuseppe Verdi", (("2026-12-11","20:45"),("2026-12-13","18:00"))),
)
PATTERNS = (
    r"La Stagione 2026 si aprirà venerdì 13 novembre \\(ore 20\\.45\\), con Turandot di Giacomo Puccini.*?replica domenica 15 \\(ore 18\\)",
    r"secondo titolo in cartellone sarà L'elisir d'amore di Gaetano Donizetti, in scena venerdì 27 \\(ore 20\\.45\\) e domenica 29 novembre \\(ore 18\\)",
    r"Per la terza serata, Nabucco di Giuseppe Verdi, in programma venerdì 11 \\(ore 20\\.45\\) e domenica 13 dicembre \\(ore 18\\)",
)

def parse_program(html: str, *, url: str):
    p=urlsplit(url)
    if (url!=URL or p.scheme!="https" or p.hostname!="www.provincia.le.it"
        or p.username or p.password or p.port is not None or p.query or p.fragment):
        raise ValueError("unapproved Province of Lecce source URL")
    body=clean(html).replace("’","'").replace("‘","'")
    if not re.search(r"51. Stagione lirica della Provincia di Lecce",body,re.I):
        raise ValueError("unverified official season identity")
    if "Teatro Politeama Greco" not in body:
        raise ValueError("Politeama venue not independently established")
    begin=body.find("La Stagione 2026 si aprirà")
    end=body.find("Al via, dunque",begin)
    if begin<0 or end<begin or end-begin>2500:
        raise ValueError("bounded Province programme missing")
    section=body[begin:end]
    if re.search(r"(?i)\\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\\b",section):
        raise ValueError("official cancellation requires review")
    for pattern in PATTERNS:
        if len(re.findall(pattern,section,re.I|re.S))!=1:
            raise ValueError("missing or ambiguous official opera schedule")
    return [(title,composer,VENUE,day,clock)
            for title,composer,dates in SCHEDULE for day,clock in dates]
