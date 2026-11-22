"""Year-scoped future Ferrara Opera & Danza programme evidence.

The region's season listing verifies production identity and date spans,
not necessarily exact performance start times. Never invent times or re-use
2026/27 brochure dates for subsequent years. Opera titles stay subject to
canonical work reconciliation; ballet, dance and crossover are excluded.
"""
from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.ferrara_regional_parser import RegionalProgram, fold, VENUE
from opera_atlas.national_detail_parser import MONTHS
from opera_atlas.work_identity import resolve_work

KEY="ferrara-season-opera-2027-28"
HOST="spettacolo.emiliaromagnacultura.it"
PATH=re.compile(r"/it/rassegna/teatro-comunale-ferrara-opera-danza-(20\d{2})-(20\d{2})/")
DAY=re.compile(r"(?i)(?<!\w)(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})(?!\d)")
TIMED=re.compile(r"(?i)(?<!\w)(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})\s*(?:[,–-]\s*)?(?:alle\s+)?ore\s+((?:[01]?\d|2[0-3]))[.:]([0-5]\d)(?!\d)")
NONOPERA=re.compile(r"(?i)\b(?:balletto|danza|coreografia|concerto|musical|lucio\s+dalla|opera\s+pop|crossover)\b")

class _Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=False
        self.blocked=0
        self.parts=[]
        self.headings=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.blocked+=1
        if tag=="h1" and not self.blocked:
            self.active=True
            self.parts=[]
    def handle_data(self,data):
        if self.active and not self.blocked:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.active:
            heading=" ".join(" ".join(self.parts).split())
            if heading:self.headings.append(heading)
            self.active=False
        if tag in ("nav","footer","script","style"):
            self.blocked=max(0,self.blocked-1)

def _context(html:str,*,url:str)->tuple[int,int,dict[str,str]]:
    parsed=urlsplit(url)
    match=PATH.fullmatch(parsed.path)
    if (parsed.scheme!="https" or parsed.hostname!=HOST or not match
            or parsed.port is not None or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError("Ferrara future index is not an exact official URL")
    start,end=map(int,match.groups())
    if start<2027 or start>=2099 or end!=start+1:
        raise ValueError("Ferrara season years are inconsistent")
    headings=_Headings()
    headings.feed(html)
    expected=re.compile(
        rf"(?i)\bTEATRO\s+COMUNALE\s+FERRARA\b.*\bOPERA\s*(?:&|E)\s*DANZA\s+{start}\s*/\s*{end}\b")
    if not any(expected.search(h) for h in headings.headings):
        raise ValueError("Ferrara official opera season year heading missing")
    program=RegionalProgram()
    program.feed(html)
    program.close()
    if not program.sections:
        raise ValueError("Ferrara future programme has no productions")
    return start,end,program.sections

def _entry_dates(body:str,start:int,end:int)->list[str]:
    found=[]
    for m in DAY.finditer(body):
        day,month,year=m.groups()
        observed=date(int(year),MONTHS[month.lower()],int(day))
        if not date(start,7,1)<=observed<=date(end,6,30):
            raise ValueError("Ferrara programme includes date outside its season")
        found.append(observed.isoformat())
    return found

def _opera_sections(html:str,*,url:str):
    start,end,sections=_context(html,url=url)
    valid=[]
    for heading,body in sections.items():
        if NONOPERA.search(heading):
            continue
        if not re.search(r"(?i)\bmusica\s+di\s+[A-Za-zÀ-ÿ]",heading+" "+body):
            continue
        if not re.search(r"(?i)\bTEATRO\s+COMUNALE\s+DI\s+FERRARA\b",body):
            continue
        dates=_entry_dates(body,start,end)
        if not dates:
            continue
        if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",body):
            continue
        valid.append((heading,body,start,end,dates))
    if not valid:
        raise ValueError("no source-credited Ferrara future opera productions")
    return valid

def verify_index(html:str,*,url:str)->bool:
    """Index discovery only: no performance dates or generic title promotion."""
    return bool(_opera_sections(html,url=url))

def parse_known_recite(html:str,*,url:str,registry:dict)->list[tuple[str,str,str,str,str]]:
    """Emit verified recite only when individual date AND hour are explicit.

    Regional date ranges lacking exact hours are deliberately review-only.
    """
    rows=[]
    for heading,body,start,end,dates in _opera_sections(html,url=url):
        if NONOPERA.search(body[:200]):
            continue
        recognized=[]
        for work in registry.get("works",{}).values():
            if not isinstance(work,dict):continue
            title,composer=work.get("title"),work.get("composer")
            if not isinstance(title,str) or not isinstance(composer,str):continue
            heading_base=fold(heading)
            if heading_base not in (fold(title),fold(title+" - "+composer)):
                continue
            if not re.search(r"(?i)\bmusica\s+di\s+"+re.escape(composer)+r"\b",body):
                continue
            canonical=resolve_work(registry,title,composer)
            if canonical is not None:recognized.append(canonical)
        if len(recognized)!=1:continue
        exact=[]
        for m in TIMED.finditer(body):
            day,month,year,hour,minute=m.groups()
            observed=date(int(year),MONTHS[month.lower()],int(day))
            if not date(start,7,1)<=observed<=date(end,6,30):
                raise ValueError("Ferrara recital year contradicts official season")
            exact.append((observed.isoformat(),f"{int(hour):02d}:{minute}"))
        # All distinct explicit performance dates must have exact start
        # times; if only a span is published do not invent time or recite.
        if not exact or len(exact)>20 or len(set(exact))!=len(exact):
            continue
        if set(dates)!=set(d for d,_ in exact):
            continue
        work=recognized[0]
        rows.extend((work["title"],work["composer"],VENUE,day,clock)
                    for day,clock in exact)
    return sorted(set(rows))
