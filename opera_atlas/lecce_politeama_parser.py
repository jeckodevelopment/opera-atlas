"""Official Politeama Greco: historic exact records and dynamic opera details."""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean, MONTHS

HOST="www.politeamagreco.it"
VENUE="Teatro Politeama Greco"
WORKS={
    "1147":("Turandot","Giacomo Puccini",((13,11,"20:45"),(15,11,"18:00"))),
    "1148":("L'elisir d'amore","Gaetano Donizetti",((27,11,"20:45"),(29,11,"18:00"))),
    "1149":("Nabucco","Giuseppe Verdi",((11,12,"20:45"),(13,12,"18:00"))),
}

def parse_historical_detail(html:str,*,url:str):
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname!=HOST or p.path!="/scheda.asp"
        or p.query not in {"id=1147","id=1148","id=1149"}
        or p.fragment or p.username or p.password or p.port is not None):
        raise ValueError("unapproved Politeama opera URL")
    title,composer,expected=WORKS[p.query.split("=")[1]]
    body=clean(re.sub(r"(?i)</h[1-6]>", " </h3> ",html)).replace("’","'")
    if not re.search(r"(?i)\bTEATRO POLITEAMA GRECO DI LECCE\b",body):
        raise ValueError("official opera venue missing")
    if not re.search(r"(?i)\bStagione Lirica di tradizione 2026\b",body):
        raise ValueError("incorrect season")
    # The detail page explicitly labels its season with the year; dates in
    # its own ticket panel are the only evidence, not promotional metadata.
    heading=re.search(r"(?i)Stagione Lirica di tradizione 2026\s+"
                      +re.escape(title)+r"\s+di\s+"+re.escape(composer)+r"\b",body)
    if not heading:
        raise ValueError("work and composer not attributed on official page")
    tail=body[heading.end():]
    end=re.search(r"(?i)\bPREZZI\b|\bPERSONAGGI E INTERPRETI\b",tail)
    panel=tail[:end.start()] if end else tail[:900]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",panel):
        raise ValueError("cancellation requires review")
    month_names={11:"novembre",12:"dicembre"}
    rows=[]
    for day,month,clock in expected:
        # A standalone date with its exact labelled showtime must appear
        # within this specific work panel. The same title's historic premiere
        # or ticket-sale hours are not substitute evidence.
        pattern=(rf"\b{day}\s+{month_names[month]}\s+ore\s+"
                 +clock.replace(":",r"[.:]")+r"\b")
        if len(re.findall(pattern,panel,re.I))!=1:
            raise ValueError("unverified or duplicated ticketed showtime")
        rows.append((date(2026,month,day).isoformat(),clock))
    other=re.findall(r"\b(\d{1,2})\s+(novembre|dicembre)\s+ore\s+([01]?\d|2[0-3])[.:]([0-5]\d)\b",panel,re.I)
    if len(other)!=2:
        raise ValueError("unexpected extra official production date")
    return title,composer,VENUE,rows


INDEX="https://www.politeamagreco.it/programmazione.asp?categoria=1"

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname==HOST and p.path=="/scheda.asp"
            and bool(re.fullmatch(r"id=[1-9]\d{0,7}",p.query))
            and p.query not in {"id=1146","id=1150"}
            and not p.fragment and not p.username and not p.password
            and p.port is None)

def parse_detail(html:str,*,url:str):
    """Validate a single title in the official season and dated ticket panel.

    Historic 2026 IDs retain their original exact date and credit contract.
    Unknown IDs are not evidence of genre; the individual page must agree
    on title, composer, season, venue, date range and every public clock.
    """
    if not eligible_detail(url):
        raise ValueError("unapproved Politeama opera URL")
    if urlsplit(url).query.split("=")[1] in WORKS:
        return parse_historical_detail(html,url=url)
    body=clean(html).replace("’","'")
    # The official CMS shows a dated ticket panel immediately before the
    # individual event title and the category/date-range header.
    slot=r"(?:»\s*)?(\d{1,2})/(\d{1,2})/(20\d{2})\s*[-–]\s*([01]?\d|2[0-3])[.:]([0-5]\d)"
    header=re.search(r"(?i)\bOrario Spettacoli\s+((?:"+slot+
        r"\s*)+)(.{2,160}?)\s+dal\s+(\d{1,2}/\d{1,2}/20\d{2})\s+al\s+"
        r"(\d{1,2}/\d{1,2}/20\d{2})\s*[-–]\s*Stagione Lirica\b",body)
    if not header:
        raise ValueError("individual official opera ticket panel missing")
    tickets=header.group(1)
    credited=header.group(7).strip()
    identity=re.fullmatch(r"(.{2,100}?)\s+di\s+([A-Za-zÀ-ÿ' .-]{5,80})",credited,re.I)
    if not identity:
        raise ValueError("individual title and composer missing")
    title,composer=(x.strip() for x in identity.groups())
    if re.search(r"(?i)\b(?:conferenze?|ouverture|gala|concerto|balletto|musical|stagione|masterclass)\b",title):
        raise ValueError("ancillary or composite event, not individual opera")
    season=re.search(r"(?i)\bTEATRO POLITEAMA GRECO DI LECCE\s+"
        r"Stagione Lirica di tradizione\s+(20\d{2})\s+"+re.escape(credited)+r"\b",body[header.end():])
    if not season:
        raise ValueError("venue, season or repeated composer credit missing")
    year=int(season.group(1))
    if not 2027<=year<=2099:
        raise ValueError("unknown historical season")
    tail=body[header.end()+season.end():]
    end=re.search(r"(?i)\bPREZZI\b|\bPERSONAGGI E INTERPRETI\b",tail)
    if not end:
        raise ValueError("unbounded individual showtime panel")
    panel=tail[:end.start()]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|recite scuole|scolastic[oahe]+)\b",panel):
        raise ValueError("cancellation or school performance needs review")
    # Require the separately printed textual dates as well; ticket header
    # and programme must corroborate exactly the same public slots.
    dates=[]
    for d,m,y,h,minute in re.findall(slot,tickets):
        if int(y)!=year:
            raise ValueError("ticket outside stated season")
        dates.append((date(int(y),int(m),int(d)).isoformat(),f"{int(h):02d}:{minute}"))
    textual=[]
    for d,m,h,minute in re.findall(r"(?i)\b(\d{1,2})\s+("+
            "|".join(MONTHS)+r")\s+ore\s+([01]?\d|2[0-3])[.:]([0-5]\d)\b",panel):
        textual.append((date(year,MONTHS[m.casefold()],int(d)).isoformat(),f"{int(h):02d}:{minute}"))
    def iso(value):
        d,m,y=map(int,value.split("/"))
        return date(y,m,d).isoformat()
    if (not dates or len(dates)>24 or len(set(dates))!=len(dates)
            or sorted(textual)!=sorted(dates)
            or min(d[0] for d in dates)!=iso(header.group(8))
            or max(d[0] for d in dates)!=iso(header.group(9))):
        raise ValueError("incomplete or conflicting official ticket slots")
    if title.isupper():title=title.capitalize()
    composer=" ".join(part.capitalize() if part.isupper() else part for part in composer.split())
    return title,composer,VENUE,sorted(dates)
