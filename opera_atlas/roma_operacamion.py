"""First-party OperaCamion discovery: preserve tour cards, not fake theatres.

A tour page is evidence, not a grant to create a new canonical staging.
Separate rounds may share an edition; the reviewed itinerant registry remains
the publication authority for identity, exact municipality and all dates.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.roma_detail_parser import DAYS, MONTHS, PERFORMANCE, CANCELLED, Heading
from scripts.build_verified_catalog import official_local_time

SOURCE_KEY="opera-roma-season-2026-27"
OWNER="Teatro dell'Opera di Roma"

def eligible(url):
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname=="www.operaroma.it"
            and p.port is None and not any((p.username,p.password,p.query,p.fragment))
            and bool(re.fullmatch(r"/spettacoli/[a-z0-9-]*operacamion[a-z0-9-]*/",p.path)))

class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","nav","footer"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","nav","footer"):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def parse(html,*,url):
    if not eligible(url):raise ValueError("not an approved OperaCamion detail URL")
    h=Heading()
    h.feed(html)
    title=h.title or ""
    if not re.search(r"\bOperaCamion\b",title,re.I):
        raise ValueError("OperaCamion missing from official event heading")
    reader=Text()
    reader.feed(html)
    text=" ".join(" ".join(reader.parts).split())
    intro,sep,schedule=text.partition("Le date")
    if not sep:raise ValueError("missing official OperaCamion date cards")
    seasons=set(re.findall(r"\bStagione\s+(20\d{2})\s*/\s*(20\d{2})\b",intro,re.I))
    if len(seasons)!=1:raise ValueError("ambiguous official tour season")
    a,b=map(int,next(iter(seasons)))
    if b!=a+1:raise ValueError("invalid tour season")
    owner=r"OperaCamion\s+è\s+un\s+progetto\s+del\s+Teatro\s+dell[’']Opera\s+di\s+Roma"
    if not re.search(owner,intro,re.I):raise ValueError("official tour organiser unconfirmed")
    # Explicit source credit, not the slug, casting or the adaptation credit.
    credits=re.findall(r"\bda\s+(.{2,150}?)\s+di\s+(.{4,100}?)\s+adattamento\s+musicale\b",intro,re.I)
    if len(credits)!=1:raise ValueError("unambiguous official opera credit missing")
    work,composer=credits[0]
    if not all(c.isalpha() or c in " .-'’" for c in composer):
        raise ValueError("invalid composer credit")
    for stop in ("Ti può interessare anche","Potrebbe interessarti","Altri eventi"):
        schedule=schedule.split(stop,1)[0]
    if CANCELLED.search(schedule):raise ValueError("tour cancellation or postponement requires review")
    # Both the site heading and exact day/time are needed. Fail closed if
    # a date is missing its own admission label, rather than dropping it.
    card=re.compile(r"(INGRESSO\s+LIBERO(?:\s*\([^)]*\))?|ANTEPRIMA|PROVA\s+GENERALE(?:\s+APERTA)?)\s*[-–—]\s*(.*?)\s*"+PERFORMANCE.pattern,re.I)
    matches=list(card.finditer(schedule))
    if not matches or len(matches)!=len(list(PERFORMANCE.finditer(schedule))):
        raise ValueError("incomplete OperaCamion date cards")
    events=[]
    previews=[]
    seen=set()
    for m in matches:
        admission,place,weekday,day,month,hh,mm=m.groups()
        possible=[]
        for year in (a,b):
            try:d=date(year,MONTHS[month.casefold()],int(day))
            except ValueError:continue
            if d.weekday()==DAYS[weekday.casefold()]:possible.append(d.isoformat())
        if len(possible)!=1 or not place.strip() or len(place)>300:
            raise ValueError("ambiguous OperaCamion date or place")
        day=possible[0]
        if day in seen:raise ValueError("duplicate OperaCamion day")
        seen.add(day)
        clock=f"{int(hh):02d}:{mm}"
        # Rome's numbered municipal districts are a positive city signal.
        # Other named places remain explicit raw evidence for municipality
        # verification, rather than assigning all tour stops to Roma.
        city="Roma" if re.search(r"\bMunicipio\s+[IVXLCDM]+\b",place,re.I) else None
        if not city:
            for known in ("Bracciano","Valmontone"):
                if re.search(r",\s*"+known+r"\s*$",place,re.I):city=known
        row={"date":day,"starts_at":official_local_time(day,clock),
             "venue":place.strip(),"municipality":city,"region":"Lazio" if city else None}
        (events if admission.casefold().startswith("ingresso") else previews).append(row)
    if not events:raise ValueError("no ordinary public OperaCamion performances")
    return {"project_name":"OperaCamion","organizer":OWNER,"season":f"{a}-{b}",
            "title":work,"composer":composer,"performances":events,"previews":previews}
