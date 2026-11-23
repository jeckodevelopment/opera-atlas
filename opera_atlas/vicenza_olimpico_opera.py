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
    (re.compile(r"\b(?:musica\s+di|di)\s+(?:B\.\s*|Baldass(?:are|arre)\s+)GALUPPI\b",re.I),"Baldassare Galuppi"),
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
        self.category_years=[]
        self._heading=False;self._heading_offset=None;self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self._skip+=1
        if tag=="h1" and not self._skip:
            self._heading=True
            if self._heading_offset is None:
                self._heading_offset=len(self.parts)
        if tag=="a" and not self._skip:
            target=dict(attrs).get("href")
            if target:
                self.links.append(target)
                # WordPress stores the year in the event's category link
                # outside the main heading. Only the festival category slug
                # is accepted; artist biographies cannot supply a year.
                matched=re.search(
                    r"/category/(?:vil/)?vicenza-in-lirica-(20\d{2})/?(?:[?#].*)?$",
                    target,re.I)
                if matched:self.category_years.append((matched.group(1),len(self.parts)))
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

TICKETING = "https://www.vicenzainlirica.it/biglietteria/"


def corroborated_ticket_rows(html: str, *, title: str,
                            composer: str) -> list[tuple[str, str]]:
    """Read only named, dated official ticket-office lines, never biographies.

    The same ticket page lists concerts and events at other locations.
    A performance is eligible only if its *own* first-party detail has
    independently established opera genre and the Teatro Olimpico venue.
    """
    page = Page()
    page.feed(html)
    text = " ".join(page.parts)
    surname = composer.split()[-1]
    # The office uses "12 e 13/09/2026 ... ore 20,30/19,00" for two
    # consecutive recitals, as well as ordinary "14/09/2026" listings.
    pattern = re.compile(
        r"(?<!\d)([0-3]?\d)(?:\s+e\s+([0-3]?\d))?/"
        r"(0[1-9]|1[0-2])/(20\d{2})\s+"
        + re.escape(title) + r"\s*[–—-]\s*" + re.escape(surname)
        + r"\b.{0,140}?\bore\s+"
        r"((?:[01]?\d|2[0-3])[,.:][0-5]\d"
        r"(?:\s*/\s*(?:[01]?\d|2[0-3])[,.:][0-5]\d)?)",
        re.I)
    rows = []
    for found in pattern.finditer(text):
        first, second, month, year, clocks = found.groups()
        days = [first] + ([second] if second else [])
        times = [clock.strip().replace(",", ":").replace(".", ":")
                 for clock in clocks.split("/")]
        if len(times) != len(days):
            raise ValueError("Vicenza ticket-office slots ambiguous")
        for day, clock in zip(days, times):
            try:
                rows.append((date(int(year), int(month), int(day)).isoformat(),
                             clock))
            except ValueError as exc:
                raise ValueError("Vicenza ticket-office date invalid") from exc
    return sorted(set(rows))


def parse_detail(html:str,*,url:str,
                 ticketing_html:str|None=None)->tuple[str,str,str,list[tuple[str,str]]]:
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
    header_years=YEAR.findall(header[:550])
    # The festival homepage menu can be injected after the article heading,
    # with a chronological archive (2017, 2018, ...). A run of several
    # different festival years cannot be *this production's* edition.
    # Discard this navigation-derived signal, never its first-party showtimes.
    # The strict category check or exact ticket-office corroboration still
    # has to independently supply one consistent edition.
    if len(set(header_years))>=4:
        header_years=[]
    # WordPress often includes related articles from OTHER festival editions
    # in the footer. Only category links adjacent to this article's heading
    # can establish its year; a second edition elsewhere on the page must
    # neither override nor contradict the source's production metadata.
    heading_start=page._heading_offset if page._heading_offset is not None else begin
    category_years=[year for year,offset in page.category_years
                    if max(0,heading_start-30)<=offset<=begin+90]
    # Prefer edition in the original event header; otherwise its exact
    # WordPress category. When both exist they must agree.
    years=set(header_years+category_years)
    if not GENRE.search(header):
        raise ValueError("Vicenza opera genre unverified")
    if not re.search(r"\bTeatro\s+Olimpico\s+(?:di\s+)?Vicenza\b",header,re.I):
        raise ValueError("Vicenza opera staged elsewhere")
    # Exactly one first-party composer in the production credits.
    credits=[name for pattern,name in COMPOSERS if pattern.search(header)]
    if len(credits)!=1:
        raise ValueError("Vicenza composer missing or ambiguous")
    work_title=re.split(r"\s+[–-]\s+",title,1)[0].strip()
    corroborated=(corroborated_ticket_rows(ticketing_html,title=work_title,
                                          composer=credits[0])
                 if ticketing_html is not None else [])
    # Do not override conflicting edition metadata. Only a genuinely missing
    # edition may be supplied by exact first-party ticket-office dates, and
    # each such date must also be stated on the matching production page.
    ticket_years={int(day[:4]) for day,_ in corroborated}
    def edition_error():
        # Source-bound years only; do not expose page body or credentials.
        article=",".join(sorted(set(header_years))) or "-"
        categories=",".join(sorted(set(category_years))) or "-"
        office=",".join(str(x) for x in sorted(ticket_years)) or "-"
        return ValueError(
            "Vicenza official festival year missing or conflicting "
            f"[article={article}; links={categories}; tickets={office}]")
    if len(years)>1:
        # WordPress can link to several unrelated editions in navigation.
        # Such links are not authoritative for *this* production. Resolve
        # them only when an independently source-bound ticket listing proves
        # the exact same title, composer, venue and every local showtime.
        # Never override an explicit contradictory year in the article text.
        if (len(ticket_years)!=1 or
            (header_years and set(header_years)!={str(next(iter(ticket_years)))})
            or str(next(iter(ticket_years))) not in years):
            raise edition_error()
        year=next(iter(ticket_years))
    elif not years:
        if len(ticket_years)!=1:
            raise edition_error()
        year=next(iter(ticket_years))
    else:
        year=int(next(iter(years)))
        if ticket_years and ticket_years!={year}:
            raise ValueError("Vicenza official schedule year conflicts with article")
    if not 2020<=year<=2099:
        raise ValueError("Vicenza festival edition year invalid")
    recite=[]
    for day,month,hour,minute in SHOWTIME.findall(header):
        try:recite.append((date(year,MONTHS[month.casefold()],int(day)).isoformat(),
                           f"{int(hour):02d}:{minute}"))
        except ValueError as e:raise ValueError("Vicenza recital date invalid") from e
    recite=sorted(set(recite))
    if not recite or len(recite)>25:
        raise ValueError("Vicenza missing verified exact recitals")
    if ticketing_html is not None:
        if not corroborated or recite!=corroborated:
            raise ValueError("Vicenza article and ticket-office recitals disagree")
    # A concert can credit an opera composer; genre + venue + time are also
    # required independently, and no concert is promoted by its title alone.
    return re.split(r"\s+[–-]\s+",title,1)[0].strip(),credits[0],"Teatro Olimpico",recite
