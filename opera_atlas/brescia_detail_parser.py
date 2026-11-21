"""Strict factual showtimes from Teatro Grande Brescia's opera detail pages.

The official page gives dated Turno A/B cards before the work description.
A two-opera bill requires separate work identities and is not treated as
one canonically recognised work by this single-work parser.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean
from scripts.publish_catalog_v2 import normalized

MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
WEEKDAYS=r"(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
DATES=re.compile(r"(?i)\b("+WEEKDAYS+r")\s+(\d{1,2})\s+("+
                 "|".join(MONTHS)+r")\s+(20\d{2})\s+"+
                 r"([01]?\d|2[0-3]):([0-5]\d),\s*Sala Grande\b")
MONTH_RE=r"(?i)\b(?:turno\s+[A-Z])\s+"
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

class Heading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_h1=False
        self.h1=None
        self.buf=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.h1 is None:self.in_h1=True
    def handle_endtag(self,tag):
        if tag=="h1" and self.in_h1:
            self.h1=" ".join("".join(self.buf).split())
            self.in_h1=False
    def handle_data(self,data):
        if self.in_h1:self.buf.append(data)

def canonical_text(value:str)->str:
    return normalized(value).replace("’","\u0027")

def parse_brescia_detail(html:str,*,url:str,title:str,composer:str):
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="teatrogrande.it"
        or parsed.username or parsed.password or parsed.port is not None
        or parsed.query or parsed.fragment
        or not re.fullmatch(r"/it/stagioni/20\d{2}/[a-z0-9-]+",parsed.path)):
        raise ValueError("untrusted Brescia opera detail")
    heading=Heading()
    heading.feed(html)
    # A combined programme requires separate canonical work paths.
    if not heading.h1 or "/" in heading.h1.split(" di ")[0]:
        raise ValueError("combined bill requires separate work evidence")
    if canonical_text(heading.h1)!=canonical_text(title+" di "+composer):
        raise ValueError("official opera or composer heading mismatch")
    return ticket_dates(html,url=url,heading=heading.h1)


def ticket_dates(html:str,*,url:str,heading:str):
    parsed=urlsplit(url)
    text=clean(html)
    # Delimit ticket cards before the actual work heading; this excludes
    # price tables and dated accessibility activities lower on the page.
    head_position=text.find(heading)
    if head_position<0:raise ValueError("missing official opera heading in text")
    prefix=text[:head_position]
    start=re.search(r"(?i)\bTurno\s+A\b",prefix)
    if not start:raise ValueError("official ticket showtime cards absent")
    segment=prefix[start.start():]
    if CANCEL.search(prefix):raise ValueError("cancelled or moved performance")
    matches=list(DATES.finditer(segment))
    if not matches:raise ValueError("no dated Sala Grande ticket showtimes")
    # Every ticket turn label must have an independently dated showtime.
    turns=re.findall(r"(?i)\bTurno\s+[A-Z]\b",segment)
    if len(turns)!=len(matches):
        raise ValueError("incomplete dated ticket cards")
    found={}
    for match in matches:
        day=date(int(match[4]),MONTHS[match[3].casefold()],int(match[2]))
        if day.year!=int(parsed.path.split("/")[3]):
            raise ValueError("detail season and recita year conflict")
        key=day.isoformat()
        if key in found:raise ValueError("ambiguous repeated opera date")
        found[key]=f"{int(match[5]):02d}:{match[6]}"
    return sorted(found.items())


DOUBLE_TITLE="Cavalleria Rusticana/Pagliacci"
DOUBLE_COMPOSERS="Pietro Mascagni/Ruggero Leoncavallo"

def parse_brescia_double_bill(html:str,*,url:str,works:dict):
    """Return two separately identified works sharing one official ticket schedule.

    A shared official bill is not a new opera or duplicate event: each of its
    two existing work identities receives the same independently dated slots.
    Fail closed on missing/ambiguous composer or venue evidence.
    """
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="teatrogrande.it"
        or parsed.query or parsed.fragment or parsed.port is not None
        or parsed.username or parsed.password
        or parsed.path!="/it/stagioni/2026/cavalleria-rusticana-pagliacci"):
        raise ValueError("untrusted Brescia double-bill URL")
    heading=Heading()
    heading.feed(html)
    if canonical_text(heading.h1 or "")!=canonical_text(
        DOUBLE_TITLE+" di "+DOUBLE_COMPOSERS):
        raise ValueError("unverified double-bill title and composers")
    text=clean(html)
    # Both independently credited works must be documented on this same
    # official page; combined slash title alone is insufficient.
    if not re.search(r"(?i)\\bCavalleria\\s+Rusticana\\s+"
                     r"Melodramma\\s+in\\s+un\\s+atto\\b.{0,250}?"
                     r"Musica\\s+di\\s+Pietro\\s+Mascagni\\b",text):
        raise ValueError("Cavalleria independent work credit missing")
    if not re.search(r"(?i)\\bPagliacci\\s+Dramma\\s+in\\s+un\\s+prologo\\b"
                     r".{0,250}?Parole\\s+e\\s+musica\\s+di\\s+Ruggero\\s+Leoncavallo\\b",text):
        raise ValueError("Pagliacci independent work credit missing")
    identities=(("Cavalleria rusticana","Pietro Mascagni"),
                ("Pagliacci","Ruggero Leoncavallo"))
    recognized=[]
    for title,composer in identities:
        matches=[w for w in works.values()
                 if canonical_text(w["title"])==canonical_text(title)
                 and canonical_text(w["composer"])==canonical_text(composer)]
        if len(matches)!=1:raise ValueError("ambiguous canonical double-bill work")
        recognized.append(matches[0])
    dates=ticket_dates(html,url=url,heading=heading.h1)
    return [{"event_title":w["title"],"composer":w["composer"],
             "date":day,"clock":hour,"venue":"Teatro Grande"}
            for w in recognized for day,hour in dates]
