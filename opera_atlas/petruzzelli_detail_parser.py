"""Official 2027 Petruzzelli opera: exact ticket dates, no inferred clocks."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean
from scripts.publish_catalog_v2 import normalized

MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
DAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,
      "venerdì":4,"sabato":5,"domenica":6}
SCHEDULE=re.compile(
    r"\b(lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
    r"\s+([0-3]?\d)\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})"
    r"\s*-\s*([01]?\d|2[0-3]):([0-5]\d)\b",re.I)
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")

def parse_petruzzelli_detail(html:str,*,url:str,title:str,composer:str):
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.fondazionepetruzzelli.it"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment
        or not re.fullmatch(r"/eventi/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Petruzzelli opera detail")
    visible=clean(html)
    split=visible.find("Orari Spettacoli")
    if split<0:raise ValueError("official Petruzzelli ticket schedule missing")
    head=normalized(visible[:split]).replace("’","'")
    # Credit must be attached to the actual production: either the H1
    # itself, or the explicitly marked first-party opera presentation.
    # A concert, talk or a performer mentioning an opera is not a bill.
    from html.parser import HTMLParser
    class Heading(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.in_heading=False
            self.parts=[]
            self.first=None
        def handle_starttag(self,tag,attrs):
            if tag=="h1" and self.first is None:self.in_heading=True
        def handle_data(self,data):
            if self.in_heading:self.parts.append(data)
        def handle_endtag(self,tag):
            if tag=="h1" and self.in_heading:
                self.first=" ".join("".join(self.parts).split())
                self.in_heading=False
    heading=Heading()
    heading.feed(html)
    prefix=normalized((heading.first or "").split("|")[0]).replace("’","'")
    t=normalized(title).replace("’","'")
    c=normalized(composer).replace("’","'")
    official=t+" di "+c
    h1_match=prefix==official
    # Only the theatre's explicit opera-credit segment can complement
    # a heading that omits the composer (as in Puccini's La bohème).
    presentations=re.findall(
        r"presenta\s+l['’]opera\s+(.+?)(?:O&B\s+2027|Orari\s+Spettacoli)",
        visible[:split],re.I)
    presentation_match=(len(presentations)==1 and
                        normalized(presentations[0]).replace("’","'").strip()==official)
    if re.search(r"presenta\s+il\s+balletto\b",visible[:split],re.I):
        raise ValueError("non-operatic ballet must not be catalogued as opera")
    if presentations and not presentation_match:
        raise ValueError("conflicting first-party composer or opera title")
    if not (h1_match or (prefix==t and presentation_match)):
        raise ValueError("official title and composer credit not confirmed")
    if "|" in (heading.first or "").split(" | ")[0] and not h1_match:
        raise ValueError("ambiguous composite bill")
    schedule=visible[split+len("Orari Spettacoli"):]
    for stop in ("Interpretato Da","Chiudi","Privacy Overview"):
        i=schedule.find(stop)
        if i>=0:schedule=schedule[:i]
    if CANCELLED.search(schedule):
        raise ValueError("cancelled or postponed Petruzzelli performance")
    # All official dates require hours. Never silently drop an incomplete card.
    weekday_dates=re.findall(
        r"(?i)\b(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
        r"\s+[0-3]?\d\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
        r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+20\d{2}\b",
        schedule)
    matches=SCHEDULE.findall(schedule)
    if len(matches)!=len(weekday_dates):
        raise ValueError("Petruzzelli schedule has dates without verified hours")
    found={}
    for weekday,day,month,year,hh,mm in matches:
        try:
            value=date(int(year),MONTHS[month.casefold()],int(day))
        except ValueError as exc:
            raise ValueError("invalid official Petruzzelli performance date") from exc
        if int(year)!=2027 or value.weekday()!=DAYS[weekday.casefold()]:
            raise ValueError("unexpected season or contradictory date/weekday")
        stamp=value.isoformat()
        hour=f"{int(hh):02d}:{mm}"
        if stamp in found and found[stamp]!=hour:
            raise ValueError("conflicting Petruzzelli ticket times")
        found[stamp]=hour
    if not found:
        raise ValueError("no complete Petruzzelli showtimes")
    return "Teatro Petruzzelli",sorted(found.items())

def extract_official_petr_opera(html:str,*,url:str):
    """Extract only one independently credited opera, not a ballet/mixed bill.

    Return source facts for independent authority resolution; never infer the
    composer from the URL slug or a later biography.
    """
    from html.parser import HTMLParser
    class H1(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active=False
            self.parts=[]
            self.first=None
        def handle_starttag(self,tag,attrs):
            if tag=="h1" and self.first is None:self.active=True
        def handle_data(self,data):
            if self.active:self.parts.append(data)
        def handle_endtag(self,tag):
            if tag=="h1" and self.active:
                self.first=" ".join("".join(self.parts).split())
                self.active=False
    heading=H1()
    heading.feed(html)
    title_text=(heading.first or "").split("|",1)[0].strip()
    # Composite bills are reserved for a separate bill identity, never
    # collapsed to one work (Arlésienne/Pagliacci).
    if (not title_text or "/" in title_text or
        (heading.first or "").count("|")>1):
        raise ValueError("unsupported multi-work or uncredited official bill")
    match=re.fullmatch(r"(.+?)\s+di\s+(.+)",title_text,re.I)
    if match:
        title,composer=(value.strip() for value in match.groups())
    else:
        title=title_text
        visible=clean(html)
        prefix=visible.split("Orari Spettacoli",1)[0]
        claims=re.findall(
            r"presenta\s+l['’]opera\s+(.+?)\s+di\s+"
            r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’.\- ]{2,90}?)\s*(?:O&B\s+2027|Orari\s+Spettacoli)",
            prefix,re.I)
        if len(claims)!=1 or normalized(claims[0][0])!=normalized(title):
            raise ValueError("unknown opera lacks explicit official composer")
        composer=claims[0][1].strip()
    if not (2<=len(title)<=180 and 3<=len(composer)<=100):
        raise ValueError("invalid credited work title/composer")
    venue,dates=parse_petruzzelli_detail(
        html,url=url,title=title,composer=composer)
    return title,composer,venue,dates
