"""Source-specific verified La traviata booking rows from Comune di Rovigo.

The municipality's content API exposes an official individual event page even
when the legacy season index has moved. The 21 January school-only TeatroRagazzi
session is separately identified, not promoted as a public performance.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

URL="https://www.comune.rovigo.it/myportal/C_H620/api/content/share/social/6aa10ea4c4e2c4008be2a957"
DETAIL_URL="https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/eventi/la-traviata-2027"
OFFICIAL_URLS=(URL,DETAIL_URL)
TITLE="La traviata"
COMPOSER="Giuseppe Verdi"
VENUE="Teatro Sociale"
EXPECTED_DATES={"2027-01-22":"20:30","2027-01-24":"16:00"}
DATE=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
    r"\s+(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\s+ore\s+"
    r"([01]?\d|2[0-3])[.:]([0-5]\d)\b"
)
DOW={"lunedì":0,"lunedi":0,"martedì":1,"martedi":1,
     "mercoledì":2,"mercoledi":2,"giovedì":3,"giovedi":3,
     "venerdì":4,"venerdi":4,"sabato":5,"domenica":6}

def parse_official_traviata(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    parsed=urlsplit(url)
    if (url not in OFFICIAL_URLS or parsed.scheme!="https" or
            parsed.hostname!="www.comune.rovigo.it" or parsed.username or
            parsed.password or parsed.port is not None or parsed.query or parsed.fragment):
        raise ValueError("unapproved Rovigo official event URL")
    text=" ".join(clean(html).split())
    if not re.search(r"(?i)\bLA\s+TRAVIATA\b",text):
        raise ValueError("official Rovigo event title missing")
    if not re.search(r"(?i)\b(?:musiche|musica)\s+di\s+Giuseppe\s+Verdi\b",text):
        raise ValueError("official Verdi composer credit missing")
    if not re.search(r"(?i)\bTeatro\s+Sociale\s+di\s+Rovigo\b",text):
        raise ValueError("Rovigo performance venue missing")
    # Only the short date header before the actual credited title qualifies.
    # Never harvest unrelated production descriptions, rehearsal or past dates.
    credit=re.search(r"(?i)\bLA\s+TRAVIATA\s+(?:musiche|musica)\s+di\s+Giuseppe\s+Verdi\b",text)
    if credit is None:
        raise ValueError("unbounded official Rovigo booking header")
    header=text[max(0,credit.start()-450):credit.start()]
    rows={}
    for m in DATE.finditer(header):
        dow,dd,mm,yy,hh,minute=m.groups()
        year=int(yy) if len(yy)==4 else 2000+int(yy)
        try:
            day=date(year,int(mm),int(dd))
        except ValueError as exc:
            raise ValueError("invalid Rovigo official recita date") from exc
        if day.weekday()!=DOW[dow.casefold()]:
            raise ValueError("Rovigo date/weekday mismatch")
        clock=f"{int(hh):02d}:{minute}"
        following=header[m.end():m.end()+35]
        if re.match(r"(?i)\s*TeatroRagazzi\b",following):
            continue
        if day.isoformat() in rows:
            # The Comune's social-sharing page repeats the same public
            # schedule in the heading and in its description. Identical
            # date/time observations are one recital, not a contradiction.
            if rows[day.isoformat()]!=clock:
                raise ValueError("conflicting repeated Rovigo booking time")
            continue
        rows[day.isoformat()]=clock
    if rows!=EXPECTED_DATES:
        raise ValueError("official Rovigo Traviata two public recite incomplete")
    return [(TITLE,COMPOSER,VENUE,day,clock)
            for day,clock in sorted(rows.items())]

# Stable, coarse diagnostic stages. Do not echo untrusted source content
# or exception strings into the published operational dashboard.
_FAILURE_STAGE={
    "official Rovigo event title missing":"title_missing",
    "official Verdi composer credit missing":"composer_missing",
    "Rovigo performance venue missing":"venue_missing",
    "unbounded official Rovigo booking header":"dates_unbounded",
    "invalid Rovigo official recita date":"date_invalid",
    "Rovigo date/weekday mismatch":"weekday_conflict",
    "conflicting repeated Rovigo booking time":"time_conflict",
    "official Rovigo Traviata two public recite incomplete":"recite_incomplete",
    "unapproved Rovigo official event URL":"unapproved_url",
}

def failure_stage(exc:ValueError)->str:
    return _FAILURE_STAGE.get(str(exc),"content_unverified")
