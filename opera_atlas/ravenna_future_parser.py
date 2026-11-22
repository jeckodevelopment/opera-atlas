"""Dynamic first-party Teatro Alighieri opera evidence from Orchestra Cherubini.

The orchestra's mixed events listing serves many cities and uses the
category "Opera" even for a Requiem. Admission requires a *single row*
with Opera, Teatro Alighieri Ravenna, and a credible operatic title.
The linked detail must confirm both music credit and exact ticket dates.
This is independent of the approved two-title Ravenna 2027 source.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

from opera_atlas.national_detail_parser import MONTHS,clean
from opera_atlas.ravenna_cherubini_parser import WEEKDAYS,VENUE

HOST="www.orchestracherubini.it"
INDEX=f"https://{HOST}/eventi/tpl/list/"
EVENT=re.compile(r"/eventi/([a-z0-9-]+)/?")
DATES=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})\s+alle\s+"
    r"(2[0-3]|1\d|0?\d):([0-5]\d)\b")
DECLARED=re.compile(
    r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+\d{1,2}\s+"
    r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+20\d{2}\b")
NONOPERA=re.compile(
    r"(?i)\b(?:requiem|concerto|balletto|danza|musical|"
    r"opera pop|crossover|ultimo incanto)\b")
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")


class _EventTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_table=False
        self.in_tr=False
        self.in_td=False
        self.cell=[]
        self.cells=[]
        self.href=None
        self.links=[]
        self.rows=[]
        self.heading=[]
        self.in_h1=False
        self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.hidden+=1
        if self.hidden:return
        if tag=="h1":
            self.in_h1=True
        if tag=="table":
            self.in_table=True
        elif tag=="tr" and self.in_table:
            self.in_tr=True;self.cells=[];self.links=[]
        elif tag=="td" and self.in_tr:
            self.in_td=True;self.cell=[]
        elif tag=="a" and self.in_td:
            self.href=dict(attrs).get("href")
    def handle_data(self,data):
        if self.hidden:return
        if self.in_h1:self.heading.append(data)
        if self.in_td:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag=="h1":self.in_h1=False
        if tag=="a" and self.href is not None and self.in_td:
            self.links.append(self.href)
            self.href=None
        if tag=="td" and self.in_td:
            self.cells.append(" ".join(" ".join(self.cell).split()))
            self.in_td=False
        if tag=="tr" and self.in_tr:
            if len(self.cells)==4:self.rows.append((tuple(self.cells),tuple(self.links)))
            self.in_tr=False
        if tag=="table":self.in_table=False
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    m=EVENT.fullmatch(p.path)
    return bool(m and p.scheme=="https" and p.hostname==HOST and
                p.port is None and not p.username and not p.password and
                not p.query and not p.fragment and len(m[1])<=110)

def extract_index(html:str,*,url:str,min_links:int)->list[str]:
    if url!=INDEX:
        raise ValueError("unapproved Cherubini event index")
    parsed=_EventTable()
    parsed.feed(html)
    if not re.search(r"(?i)\bEventi\b"," ".join(parsed.heading)):
        raise ValueError("Cherubini events heading missing")
    if not parsed.rows:
        raise ValueError("no complete official Cherubini event rows")
    links=set()
    for cells,hrefs in parsed.rows:
        _date,title,genre,location=cells
        if (genre.casefold()!="opera" or
            not re.fullmatch(r"(?i)Teatro Alighieri,\s*Ravenna",location) or
            not title or NONOPERA.search(title)):
            continue
        if len(hrefs)!=1:
            continue
        urlcandidate=urljoin(INDEX,hrefs[0])
        if eligible_detail(urlcandidate):
            links.add(urlcandidate)
    if len(links)<min_links:
        raise ValueError("no Ravenna Alighieri opera event rows")
    return sorted(links)

def parse_detail(html:str,*,url:str):
    if not eligible_detail(url):
        raise ValueError("unapproved Ravenna event detail")
    title_match=re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>",html)
    if not title_match:
        raise ValueError("Ravenna work heading missing")
    title=clean(title_match[1]).strip()
    if not title or NONOPERA.search(title) or len(title)>160:
        raise ValueError("non-operatic Ravenna work title")
    text=clean(re.sub(r"(?i)</h[2-6]>"," </h3> ",html))
    if not re.search(r"(?i)\bOrchestra Giovanile Luigi Cherubini\b",text):
        raise ValueError("performing orchestra not confirmed")
    # Never infer composers from cast members or other orchestra productions.
    credit=re.search(
        r"(?i)\b(?:libretto e )?musica di\s+"
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'’\-]*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'’\-]*){1,3})"
        r"(?=\s+(?:libretto|prima\s+rappresentazione|regia)\b|[.;]|$)",
        text[:1500])
    if not credit:
        raise ValueError("Ravenna work-specific composer attribution absent")
    composer=re.sub(r"(?i)\s+su$","",credit[1]).strip(" .")
    if any(token in {"un","una","ignoto","anonimo","non","vari","e","sconosciuto"} 
           for token in composer.casefold().split()):
        raise ValueError("Ravenna composer attribution ambiguous")
    scope=re.search(
        r"(?is)\bDate\b(.*?)\bDettagli\b\s+Opera\s+\bLuogo\b\s+Teatro Alighieri,\s*Ravenna\b",
        text)
    if not scope:
        raise ValueError("Ravenna opera classification/venue or showtime boundary absent")
    block=scope[1]
    if CANCEL.search(block):raise ValueError("Ravenna event cancelled")
    rows=[]
    for m in DATES.finditer(block):
        weekday,day,month,year,hour,minute=m.groups()
        yr=int(year)
        if yr<2027:
            raise ValueError("future Ravenna parser cannot backfill historic years")
        observed=date(yr,MONTHS[month.casefold()],int(day))
        if observed.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("Ravenna official weekday/date mismatch")
        rows.append((observed.isoformat(),f"{int(hour):02d}:{minute}"))
    if not rows or len(rows)>24 or len(rows)!=len(DECLARED.findall(block)) or len(rows)!=len(set(rows)):
        raise ValueError("Ravenna showtimes missing, duplicate or lacking hours")
    if len({row[0][:4] for row in rows})>2:
        raise ValueError("Ravenna detail covers inconsistent year ranges")
    return title,composer,VENUE,sorted(rows)
