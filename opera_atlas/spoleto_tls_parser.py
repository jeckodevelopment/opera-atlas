"""First-party Spoleto Teatro Lirico Sperimentale programme.

Only the specific Teatro Nuovo Gian Carlo Menotti panel is eligible.
School matinees, the Teatro Caio Melisso and regional touring dates are not
attributed to this venue. The programme year comes from the checked URL,
which allows future season rollover with no code change.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean, MONTHS

HOST="www.tls-belli.it"
VENUE="Teatro Nuovo Gian Carlo Menotti"
SOURCE_KEY="spoleto-tls-lirica-2026"
START=re.compile(r"(?i)\bL[’']ELISIR D[’']AMORE\b")
CREDIT=re.compile(r"(?i)\bmusica\s+(?:di\s+)?Gaetano\s+Donizetti\b")
THEATRE=re.compile(r"(?i)\bSPOLETO\s+Teatro Nuovo\b")
DATE_ROW=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
    r"\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s*,?\s*(?:ore|alle)\s+([01]?\d|2[0-3])[.:]([0-5]\d)\b"
)
WEEKDAY={"lunedi":0,"martedi":1,"mercoledi":2,"giovedi":3,
         "venerdi":4,"sabato":5,"domenica":6}

def parse_program(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    p=urlsplit(url)
    year_match=re.fullmatch(r"/stagione-lirica-(20\d{2})/?",p.path)
    if (p.scheme!="https" or p.hostname!=HOST or p.port is not None or
            p.username or p.password or p.query or p.fragment or not year_match):
        raise ValueError("unapproved Spoleto official season URL")
    year=int(year_match[1])
    if not 2026<=year<=2099:
        raise ValueError("Spoleto season outside monitored years")
    body=" ".join(clean(html).split())
    headings=list(START.finditer(body))
    if not headings:
        raise ValueError("Spoleto Donizetti production not established")
    # A programme may repeat the work in an abonnement footer. Accept only
    # the heading that is followed by the composer and venue, close together.
    candidates=[]
    for heading in headings:
        section=body[heading.end():heading.end()+1700]
        composer=CREDIT.search(section)
        venue=THEATRE.search(section)
        if composer is None or venue is None or not composer.start()<venue.start():
            continue
        # Limit all showtimes to the home-venue panel, before the following
        # production commentary, ticketing or regional tour section.
        primary=section[venue.end():]
        primary=re.split(
            r"(?i)\b(?:L[’']elisir d[’']amore è un|DURATA:|CAMPAGNA ABBONAMENTI|STAGIONE REGIONALE|"
            r"ASSISI Teatro Lyrick|PERUGIA Teatro Morlacchi)\b",
            primary,maxsplit=1
        )[0][:380]
        # The school matinees are explicitly excluded even if the text
        # mentions another time in the same school row.
        primary=re.sub(
            r"(?i)\bmercoled[iì]\s+\d+\s+e\s+gioved[iì]\s+\d+\s+\w+"
            r"\s*,?\s*(?:ore|alle)\s+\d{1,2}[.:]\d{2}\s*\(recite scuole\)",
            " ",primary)
        seen={}
        for weekday,day,month,hour,minute in DATE_ROW.findall(primary):
            dt=date(year,MONTHS[month.casefold()],int(day))
            key=weekday.casefold().replace("ì","i")
            if dt.weekday()!=WEEKDAY[key]:
                raise ValueError("Spoleto official weekday/date contradiction")
            clock=f"{int(hour):02d}:{minute}"
            if dt.isoformat() in seen and seen[dt.isoformat()]!=clock:
                raise ValueError("conflicting Spoleto performance times")
            seen[dt.isoformat()]=clock
        if seen:
            candidates.append(seen)
    if len(candidates)!=1:
        raise ValueError("missing unique verified Spoleto Teatro Nuovo booking panel")
    found=candidates[0]
    if not 1<=len(found)<=15 or (year==2026 and len(found)!=3):
        raise ValueError("incomplete Spoleto official opera calendar")
    return [("L’elisir d’amore","Gaetano Donizetti",VENUE,day,clock)
            for day,clock in sorted(found.items())]
