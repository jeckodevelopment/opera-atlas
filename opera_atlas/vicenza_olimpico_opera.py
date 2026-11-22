"""Official evergreen Vicenza in Lirica opera discovery for Teatro Olimpico.

Homepage is an evergreen programme index, but individual production pages
must independently prove the venue, musical work, composer, festival edition,
and each local performance date/time. Concerts, gala events, rehearsals not
open to the public, and productions elsewhere must never be inferred as
Teatro Olimpico recitals.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

KEY = "vicenza-olimpico-rolling-opera"
INDEX = "https://www.vicenzainlirica.it/"
HOST = "www.vicenzainlirica.it"
MONTHS = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
          "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
          "novembre":11,"dicembre":12}
BLACKLIST = re.compile(
    r"(?:concert|gala|galà|petite-messe|quattro-stagioni|biglietteria|"
    r"concorso|morricone|press|area-stampa|programma|festival-|"
    r"comunicato|masterclass|formazione|laboratori|accademia|news)",
    re.I)
GENRE = re.compile(r"\b(?:opera buffa|opera lirica|opera in \d+ atti|"
                   r"melodramma|prima rappresentazione)\b", re.I)
EXCLUDED = re.compile(
    r"\b(?:gala|galà|concerto|masterclass|laboratorio|balletto|musical|"
    r"petite messe|quattro stagioni|morricone)\b", re.I)
YEAR = re.compile(r"\bVicenza\s+in\s+Lirica\s+(20\d{2})\b", re.I)
SHOWTIME = re.compile(
    r"(?i)\b(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
    r"\s+([0-3]?\d)\s+("+"|".join(MONTHS)+r")\s*"
    r"(?:[|,\-– ]+\s*)?(?:ore)\s*([01]?\d|2[0-3])[.:]([0-5]\d)\b")
COMPOSERS = [
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:G\.\s*|Gioachino\s+)ROSSINI\b",re.I),"Gioachino Rossini"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:B\.\s*|Baldass[ar]e\s+)GALUPPI\b",re.I),"Baldassare Galuppi"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:W\.?\s*A\.?\s*|Wolfgang\s+Amadeus\s+)MOZART\b",re.I),"Wolfgang Amadeus Mozart"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:C\.\s*|Claudio\s+)MONTEVERDI\b",re.I),"Claudio Monteverdi"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:G\.\s*|Giuseppe\s+)VERDI\b",re.I),"Giuseppe Verdi"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:G\.\s*|Giacomo\s+)PUCCINI\b",re.I),"Giacomo Puccini"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:G\.\s*|Gaetano\s+)DONIZETTI\b",re.I),"Gaetano Donizetti"),
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:V\.\s*|Vincenzo\s+)BELLINI\b",re.I),"Vincenzo Bellini"),
]

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.parts=[];self.h1=[]
        self._heading=False;self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self._skip+=1
        if tag=="h1" and not self._skip:self._heading=True
        if tag=="a" and not self._skip:
            target=dict(attrs).get("href")
            if target:self.links.append(target)
    def handle_endtag(self,tag):
        if tag=="h1":self._heading=False
        if tag in ("script","style","noscript"):
            self._skip=max(self._skip-1,0)
    def handle_data(self,value):
        if self._skip:return
        value=" ".join(value.split())
        if value:
            self.parts.append(value)
            if self._heading:self.h1.append(value)

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname!=HOST or p.query or p.fragment
        or p.username or p.password or p.port is not None):
        return False
    path=p.path
    return (bool(re.fullmatch(r"/[a-z0-9]+(?:-[a-z0-9]+)*/",path))
            and not BLACKLIST.search(path)
            and path!="/")

def extract_index(html:str,*,url:str=INDEX,min_links:int=1)->list[str]:
    if url!=INDEX:raise ValueError("Vicenza official festival homepage not approved")
    page=Page();page.feed(html)
    candidates=sorted({candidate for href in page.links
                       if eligible_detail(candidate:=urljoin(INDEX,href))})
    if len(candidates)<min_links:
        raise ValueError("Vicenza official production candidates unavailable")
    return candidates

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Vicenza production URL")
    page=Page();page.feed(html)
    title=" ".join(page.h1).strip()
    if not 5<=len(title)<=150:raise ValueError("Vicenza opera title missing")
    if EXCLUDED.search(title):raise ValueError("Vicenza non-operatic title")
    try:begin=page.parts.index(page.h1[0])
    except (ValueError,IndexError) as e:raise ValueError("Vicenza missing event section") from e
    primary=" ".join(page.parts[begin:begin+90])
    # The festival website contains biographies listing other venues and
    # titles. Use only the primary production header and credits.
    header=primary[:1900]
    edition=YEAR.findall(header[:550])
    if len(set(edition))!=1 or not edition:
        raise ValueError("Vicenza official festival year missing")
    year=int(edition[0])
    if not 2020<=year<=2099:
        raise ValueError("Vicenza festival edition year invalid")
    if not GENRE.search(header):
        raise ValueError("Vicenza opera genre unverified")
    if not re.search(r"\bTeatro\s+Olimpico\s+(?:di\s+)?Vicenza\b",header,re.I):
        raise ValueError("Vicenza opera staged elsewhere")
    # Exactly one first-party composer in the production credits.
    credits=[name for pattern,name in COMPOSERS if pattern.search(header)]
    if len(credits)!=1:
        raise ValueError("Vicenza composer missing or ambiguous")
    recite=[]
    for day,month,hour,minute in SHOWTIME.findall(header):
        try:recite.append((date(year,MONTHS[month.casefold()],int(day)).isoformat(),
                           f"{int(hour):02d}:{minute}"))
        except ValueError as e:raise ValueError("Vicenza recital date invalid") from e
    recite=sorted(set(recite))
    if not recite or len(recite)>25:
        raise ValueError("Vicenza missing verified exact recitals")
    # A concert can credit an opera composer; genre + venue + time are also
    # required independently, and no concert is promoted by its title alone.
    return re.split(r"\s+[–-]\s+",title,1)[0].strip(),credits[0],"Teatro Olimpico",recite
