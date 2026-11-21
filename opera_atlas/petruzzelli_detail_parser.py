"""Official Petruzzelli annual opera: exact ticket dates, no inferred clocks."""
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
DAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,
      "venerdì":4,"sabato":5,"domenica":6}
SCHEDULE=re.compile(
    r"\b(lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
    r"\s+([0-3]?\d)\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})"
    r"\s*-\s*([01]?\d|2[0-3]):([0-5]\d)\b",re.I)
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")

class PrimaryHeading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=False
        self.parts=[]
        self.text=None
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.text is None:self.active=True
    def handle_data(self,data):
        if self.active:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.active:
            self.text=" ".join("".join(self.parts).split())
            self.active=False

def verified_work_heading(html:str,*,title:str,composer:str)->bool:
    """Require an actual production h1 and independently credited composer.

    A paragraph about another opera (such as the recurring La traviata
    conversation notice) must never establish the current production's ID.
    """
    heading=PrimaryHeading()
    heading.feed(html)
    if not heading.text:return False
    pieces=[normalized(x).replace("’","'").strip() for x in heading.text.split("|")]
    title_key=normalized(title).replace("’","'")
    composer_key=normalized(composer).replace("’","'")
    if pieces[0]==title_key+" di "+composer_key:
        return True
    # First-party explicit composer credit permits abbreviated official H1s.
    # Never identify a production from the page's unrelated notices.
    if pieces[0]==title_key and not re.search(r"presenta\s+il\s+balletto\b",clean(html),re.I):
        visible=clean(html)
        before=visible.split("Orari Spettacoli",1)[0]
        claims=re.findall(r"presenta\s+l['’]opera\s+(.+?)\s+di\s+"
                          r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’.\- ]{2,90}?)\s*(?:O&B\s+2027|Orari\s+Spettacoli)",before,re.I)
        if len(claims)==1 and (normalized(claims[0][0])==title_key and
                               normalized(claims[0][1])==composer_key):
            return True
    # The 2026 official pages put the composer's surname in h1 and full
    # name immediately beneath the heading, before the conversation text.
    surname=composer_key.split()[-1]
    if len(pieces)<2 or pieces[0]!=title_key or pieces[1]!=surname:
        return False
    visible=normalized(clean(html)).replace("’","'")
    heading_key=normalized(heading.text).replace("’","'")
    where=visible.find(heading_key)
    return where>=0 and composer_key in visible[where+len(heading_key):where+len(heading_key)+180]

def parse_petruzzelli_detail(html:str,*,url:str,title:str,composer:str,season_year:int=2027):
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.fondazionepetruzzelli.it"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment
        or not re.fullmatch(r"/eventi/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Petruzzelli opera detail")
    visible=clean(html)
    split=visible.find("Orari Spettacoli")
    if split<0:raise ValueError("official Petruzzelli ticket schedule missing")
    if not verified_work_heading(html,title=title,composer=composer):
        raise ValueError("official production heading and composer do not match")
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
        if int(year)!=season_year or value.weekday()!=DAYS[weekday.casefold()]:
            raise ValueError("unexpected season or contradictory date/weekday")
        stamp=value.isoformat()
        hour=f"{int(hh):02d}:{mm}"
        if stamp in found and found[stamp]!=hour:
            raise ValueError("conflicting Petruzzelli ticket times")
        found[stamp]=hour
    if not found:
        raise ValueError("no complete Petruzzelli showtimes")
    return "Teatro Petruzzelli",sorted(found.items())

def extract_official_petr_opera(html:str,*,url:str,season_year:int=2027):
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
        html,url=url,title=title,composer=composer,season_year=season_year)
    return title,composer,venue,dates
