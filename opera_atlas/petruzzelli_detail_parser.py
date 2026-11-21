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
    # The 2026 official pages put the composer's surname in h1 and full
    # name immediately beneath the heading, before the conversation text.
    surname=composer_key.split()[-1]
    if len(pieces)>=2 and pieces[0]==title_key and pieces[1]==surname:
        visible=normalized(clean(html)).replace("’","'")
        heading_key=normalized(heading.text).replace("’","'")
        where=visible.find(heading_key)
        return where>=0 and composer_key in visible[where+len(heading_key):where+len(heading_key)+180]
    # Some 2027 pages (Puccini's La Bohème) have only the opera title
    # followed by ticket dates in H1, and explicitly credit the composer
    # in the official "presenta l'opera" programme introduction.
    if (pieces[0]!=title_key or len(pieces)>2
        or len(pieces)==2 and not re.fullmatch(
            r"[0-3]?\d\s*-\s*[0-3]?\d\s+[a-zà-ÿ]+",pieces[1])):
        return False
    visible=normalized(clean(html)).replace("’","'")
    before=visible.split("orari spettacoli",1)[0]
    credit=(r"\bpresenta\s+l'opera\s+"+re.escape(title_key)
            +r"\s+di\s+"+re.escape(composer_key)
            +r"\s+o&b\s+20\d{2}\b")
    # Only an explicitly labelled source credit counts. A stray sentence
    # mentioning another work (or an actor's biography) is not sufficient.
    return bool(re.search(credit,before))

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
    """Read one composer-credited opera only, never a mixed bill or ballet.

    These are first-party observations for independent Wikidata checks:
    unknown works do not become canonical until the full authority gate.
    """
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="www.fondazionepetruzzelli.it"
        or parsed.port is not None or parsed.username or parsed.password
        or parsed.query or parsed.fragment
        or not re.fullmatch(r"/eventi/[a-z0-9-]+/",parsed.path)):
        raise ValueError("untrusted Petruzzelli production page")
    heading=PrimaryHeading()
    heading.feed(html)
    if not heading.text:raise ValueError("missing official opera H1")
    pieces=[x.strip() for x in heading.text.split("|")]
    if not pieces[0] or len(pieces)>2 or "/" in pieces[0]:
        raise ValueError("ambiguous multi-work bill")
    title_and_author=pieces[0]
    if " di " in title_and_author.casefold():
        # Split the LAST " di ", not the first ("Le nozze di Figaro").
        at=title_and_author.casefold().rfind(" di ")
        title=title_and_author[:at].strip()
        composer=title_and_author[at+4:].strip()
    else:
        title=title_and_author
        before=clean(html).split("Orari Spettacoli",1)[0]
        # The same official page explicitly says "presenta l'opera TITLE
        # di COMPOSER O&B YYYY". No reliance on URL-slug attribution.
        labels=re.findall(
            r"(?i)\bpresenta\s+l['’]opera\s+(.+?)\s+o&b\s+20\d{2}\b",
            before)
        if len(labels)!=1 or " di " not in labels[0].casefold():
            raise ValueError("uncredited official opera programme")
        at=labels[0].casefold().rfind(" di ")
        credited_title=labels[0][:at].strip()
        composer=labels[0][at+4:].strip()
        if normalized(credited_title)!=normalized(title):
            raise ValueError("composer credit refers to another opera")
    if (not 2<=len(title)<=180 or not 3<=len(composer)<=100
        or re.search(r"(?i)\bpresenta\s+il\s+balletto\b",clean(html))):
        raise ValueError("ballet or invalid independent opera credit")
    venue,dates=parse_petruzzelli_detail(
        html,url=url,title=title,composer=composer,season_year=season_year)
    return title,composer,venue,dates
