"""Official Bellini chamber-opera press calendars; no inferred times or venues.

The Catania event pages provide month ranges but omit individual clocks.
The theatre's first-party news releases publish their exact schedule.
A press page is fetched through the same robots-aware official source adapter,
and only an exact event-page / press-URL pair is eligible.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean, MONTHS
from opera_atlas.catania_detail_parser import Headings

EVENTS={
    "https://www.teatromassimobellini.it/eventi/il-quinto-moschettiere-2/":(
        "https://www.teatromassimobellini.it/il-quinto-moschettiere-il-teatro-massimo-bellini-torna-al-sangiorgi-con-le-opere-da-camera/",
        "Il quinto moschettiere","Matteo Musumeci","Il compositore Matteo Musumeci",
        date(2026,11,13),date(2027,1,22)),
    "https://www.teatromassimobellini.it/eventi/le-nozze-dellorso/":(
        "https://www.teatromassimobellini.it/continuano-le-opere-da-camera-al-teatro-sangiorgi-con-le-nozze-dellorso/",
        "Le nozze dell’orso","Joe Schittino","Musica di Joe Schittino",
        date(2026,11,20),date(2027,1,15)),
}
VENUE="Teatro Sangiorgi"
CLOCK_PATTERN=re.compile(
    r"(?i)\b((?:\d{1,2}\s*,\s*)*\d{1,2}(?:\s+e\s+\d{1,2})?)\s+"
    r"(novembre|dicembre|gennaio)\s+ore\s+"
    r"([01]?\d|2[0-3])(?:[.,:]([0-5]\d))?\b"
)

def press_url(event_url:str)->str|None:
    return EVENTS.get(event_url,(None,))[0]

def parse_press_calendar(event_html:str,press_html:str,*,event_url:str,
                         news_url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    record=EVENTS.get(event_url)
    if record is None or news_url!=record[0]:
        raise ValueError("unverified Bellini chamber opera source pair")
    for url in (event_url,news_url):
        loc=urlsplit(url)
        if (loc.scheme!="https" or loc.hostname!="www.teatromassimobellini.it"
            or loc.query or loc.fragment or loc.port or loc.username or loc.password):
            raise ValueError("untrusted Bellini press URL")
    expected_title,composer,composer_proof,first,last=record[1:]
    heading=Headings()
    heading.feed(event_html)
    if len(heading.h1)!=1 or heading.h1[0].casefold()!=expected_title.casefold():
        raise ValueError("official event title disagrees with press")
    event_body=clean(event_html)
    if VENUE not in event_body:
        raise ValueError("event does not confirm Sangiorgi venue")
    text=clean(press_html)
    boundary=text.find("Naviga sul sito")
    if boundary<0:
        raise ValueError("unbounded official press calendar")
    begin=text.rfind("Calendario",0,boundary)
    if begin<0 or expected_title.casefold() not in text[:begin].casefold():
        raise ValueError("official press production identity missing")
    if composer_proof.casefold() not in text[:begin].casefold():
        raise ValueError("official press composer evidence missing")
    # The complete two-year range must be explicit, rather than deriving
    # a year from the current date or guessing from the month alone.
    season_range=re.compile(
        r"(?i)\bdal\s+(\d{1,2})\s+(novembre)\s+(2026)\s+al\s+"
        r"(\d{1,2})\s+(gennaio)\s+(2027)")
    bounds=season_range.search(text[:begin])
    if not bounds or (date(int(bounds[3]),11,int(bounds[1]))!=first
                      or date(int(bounds[6]),1,int(bounds[4]))!=last):
        raise ValueError("unverified year range for Bellini chamber performances")
    section=text[begin+len("Calendario"):boundary]
    performances={}
    matches=list(CLOCK_PATTERN.finditer(section))
    if not matches or len(matches)!=6:
        raise ValueError("official Bellini press date groups incomplete")
    for match in matches:
        days_text,month,hh,mm=match.groups()
        days=[int(x) for x in re.findall(r"\d{1,2}",days_text)]
        if not 1<=len(days)<=3:
            raise ValueError("ambiguous day group in Bellini press")
        year=2027 if month.casefold()=="gennaio" else 2026
        for number in days:
            day=date(year,MONTHS[month.casefold()],number)
            if day<first or day>last or day in performances:
                raise ValueError("date outside verified press range or repeated")
            performances[day]=f"{int(hh):02d}:{mm or '00'}"
    if len(performances)!=9 or min(performances)!=first or max(performances)!=last:
        raise ValueError("Bellini first-party calendar has missing dates")
    return expected_title,composer,VENUE,[
        (day.isoformat(),performances[day]) for day in sorted(performances)]
