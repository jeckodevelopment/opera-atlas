"""Official Comune di Chieti announcement: Marrucino 2026 opera season.

One institutional announcement contains four *separate* ticketed works.
Only explicit title, composer, date and clock pairs are admissible.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit

from opera_atlas.national_detail_parser import clean, MONTHS

URL=("https://comune.chieti.it/novita/"
     "presentata-la-stagione-lirica-2026-del-teatro-marrucino-tra-tradizione-innovazione-e-celebrazioni-culturali/")
VENUE="Teatro Marrucino"
WEEKDAYS={"sabato":5,"venerdi":4,"domenica":6}
# A publication mentioning a work elsewhere in interviews is not a showtime.
WORKS=(
    ("Le avventure di Pinocchio","Antonio Cericola",
     r"(?i)\banteprima di stagione\b",1),
    ("Turandot","Giacomo Puccini",r"(?i)\bLa Stagione entrer[aà] nel vivo\b",2),
    ("Le nozze di Figaro","Wolfgang Amadeus Mozart",
     r"(?i)\bil secondo appuntamento della Stagione\b",2),
    ("La traviata","Giuseppe Verdi",r"(?i)\ba chiudere la Stagione Lirica 2026\b",2),
)
CLOCK=re.compile(
    r"(?i)\b(sabato|venerd[iì]|domenica)\s+(\d{1,2})\s+"
    r"(settembre|ottobre|novembre|dicembre)\s+"
    r"(?:alle\s+)?(?:ore\s+)?(\d{1,2})[.:]([0-5]\d)"
)

def parse_program(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    loc=urlsplit(url)
    if (loc.scheme!="https" or loc.hostname!="comune.chieti.it"
            or loc.path.rstrip("/")!=urlsplit(URL).path.rstrip("/")
            or loc.port is not None or loc.query or loc.fragment
            or loc.username or loc.password):
        raise ValueError("unapproved Chieti institutional announcement")
    text=" ".join(clean(html).split())
    if not (re.search(r"(?i)\bStagione Lirica 2026\b",text)
            and re.search(r"(?i)\bTeatro Marrucino\b",text)):
        raise ValueError("Chieti theatre and 2026 opera season not verified")
    # The bounded paragraphs start at distinctive editorial lead-ins and
    # end before the next work, never the historic retrospective footers.
    positions=[]
    for title,composer,lead,count in WORKS:
        marker=re.search(lead,text)
        if marker is None:
            raise ValueError("missing official work section: "+title)
        positions.append((marker.start(),title,composer,count))
    if positions!=sorted(positions):
        raise ValueError("Chieti opera sections unexpectedly reordered")
    rows=[]
    for i,(start,title,composer,count) in enumerate(positions):
        end=positions[i+1][0] if i+1<len(positions) else text.find(
            "La vicenda di Violetta",start)
        if end<=start:
            end=min(len(text),start+1100)
        section=text[start:end]
        if (not re.search(re.escape(title),section,re.I)
                or not re.search(re.escape(composer),section,re.I)
                or re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section)):
            raise ValueError("Chieti composer/venue/cancellation evidence changed")
        matches=CLOCK.findall(section)
        # In these paragraphs the second date frequently omits a month;
        # use only an explicitly bounded previous month, never arbitrary
        # dates elsewhere in the city-news page.
        if len(matches)!=count:
            raise ValueError("incomplete official Chieti work calendar")
        for weekday,day,month,hour,minute in matches:
            d=date(2026,MONTHS[month.casefold()],int(day))
            if d.weekday()!=WEEKDAYS[weekday.casefold().replace("ì","i")]:
                raise ValueError("Chieti weekday inconsistent with 2026")
            rows.append((title,composer,VENUE,d.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(rows)!=7 or len({(r[0],r[3]) for r in rows})!=7:
        raise ValueError("Chieti season incomplete or duplicate")
    return rows
