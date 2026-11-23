"""Conservative multi-publisher Teatro Antico di Taormina opera discovery.

Three different first-party sites may announce the same opera; index links
are candidates, not authoritative proof of genre, venue, composer or showtime.
An event only reaches canonical reconciliation if all facts are explicitly
printed on its own official page. No inference from festival membership.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

SOURCES={
    "taormina-arte-rolling-opera":("https://festivaltaorminarte.it/programma/","festivaltaorminarte.it"),
    "taormina-opera-festival-rolling":("https://www.taorminaoperafestival.org/","www.taorminaoperafestival.org"),
    "taormina-fondazione-rolling-opera":("https://www.fondazione-taormina.it/","www.fondazione-taormina.it"),
}
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
        "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
WORKS={"nabucco":("Nabucco","Giuseppe Verdi"),
       "la traviata":("La traviata","Giuseppe Verdi"),
       "cavalleria rusticana":("Cavalleria rusticana","Pietro Mascagni"),
       "pagliacci":("Pagliacci","Ruggero Leoncavallo"),
       "carmen":("Carmen","Georges Bizet"),
       "manon lescaut":("Manon Lescaut","Giacomo Puccini"),
       "aida":("Aida","Giuseppe Verdi"),
       "rigoletto":("Rigoletto","Giuseppe Verdi"),
       "il trovatore":("Il trovatore","Giuseppe Verdi"),
       "norma":("Norma","Vincenzo Bellini")}
EXCLUDE=re.compile(r"\b(?:gala|galà|concerto|recital|aria|arie|omaggio|"
                   r"sinfonico|musical|balletto|danza|talk|film|jazz|pop)\b",re.I)
# Explicitly observed informational pages, not performance detail links.\nFESTIVAL_NONPRODUCTION_SLUGS=frozenset({\n    "consiglio-di-amministrazione",
    "atti",
    "sostieni",
    "soci",
    "statuto",
    "gallery",
    "cookie-policy",
    "chi-siamo",
    "bandi-e-gare",
    "press",
    "contattaci",
    "luoghi",
    "media",
    "complessi-artistici",
    "amministrazione-trasparente",
    "enrico-castiglione-conquista-new-york-con-la-sua-carmen-standing-ovation-tra-i-grattacieli-di-manhattan",
})
VENUE=re.compile(r"\bTeatro\s+Antico\s+(?:di\s+)?Taormina\b",re.I)
DATE=re.compile(r"\b([0-3]?\d)[/.-]([01]?\d)[/.-](20\d{2})\s*"
                r"(?:ore|alle|h\.?)\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b",re.I)
TEXTDATE=re.compile(r"\b([0-3]?\d)\s+("+"|".join(MONTHS)+r")\s+(20\d{2})"
                    r"\s*(?:ore|alle|h\.?)\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b",re.I)

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.parts=[];self.h1=[];self._skip=0;self._h=False
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self._skip+=1
        if tag=="h1" and not self._skip:self._h=True
        if tag=="a" and not self._skip:
            link=dict(attrs).get("href")
            if link:self.links.append(link)
    def handle_endtag(self,tag):
        if tag=="h1":self._h=False
        if tag in ("script","style","noscript"):self._skip=max(0,self._skip-1)
    def handle_data(self,data):
        if self._skip:return
        text=" ".join(data.split())
        if text:
            self.parts.append(text)
            if self._h:self.h1.append(text)

def eligible_detail(key:str,url:str)->bool:
    if key not in SOURCES:return False
    _,host=SOURCES[key];u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=host or u.fragment or u.username or u.password or u.port is not None:
        return False
    if key=="taormina-arte-rolling-opera":
        return bool(re.fullmatch(r"/evento/[a-z0-9][a-z0-9-]*/",u.path)) and not u.query
    if key=="taormina-opera-festival-rolling":
        return (bool(re.fullmatch(r"/[a-z0-9][a-z0-9-]*/",u.path))
                and not u.query
                and u.path.strip("/") not in FESTIVAL_NONPRODUCTION_SLUGS
                and not re.search(
                    r"calendario|festival|stampa|news|direttore|box-office|privacy|contatti",u.path))
    return bool(re.fullmatch(r"/eventi/[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}",u.path)) and not u.query

def extract_index(key:str,html:str,*,url:str,min_links:int=1)->list[str]:
    if key not in SOURCES or url!=SOURCES[key][0]:raise ValueError("unapproved Taormina source index")
    reader=Reader();reader.feed(html)
    candidates=sorted({link for href in reader.links
                       if eligible_detail(key,link:=urljoin(url,href))})
    if len(candidates)<min_links:
        raise ValueError("Taormina official event links missing or index incomplete")
    return candidates

def _work(text:str)->tuple[str,str]:
    # Exact work mentions only; two different works require a compound event
    # review, never silent selection of a work in a gala or double bill.
    found=[(canonical,composer) for title,(canonical,composer) in WORKS.items()
           if re.search(r"(?<!\w)"+re.escape(title)+r"(?!\w)",text,re.I)]
    if len(found)!=1:raise ValueError("Taormina work title ambiguous or missing")
    return found[0]

def parse_detail(key:str,html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(key,url):raise ValueError("unapproved Taormina event detail")
    reader=Reader();reader.feed(html)
    if not reader.h1:raise ValueError("Taormina production heading missing")
    title=" ".join(reader.h1).strip()
    if EXCLUDE.search(title):raise ValueError("Taormina detail is a nonopera")
    try:offset=reader.parts.index(reader.h1[0])
    except ValueError as exc:raise ValueError("Taormina detail section missing") from exc
    # Exclude global news links, featured articles and related-event cards.
    primary=" ".join(reader.parts[offset:offset+75])
    primary=re.split(r"\b(?:Articoli correlati|Potrebbe interessarti|Altri eventi|Torna agli eventi)\b",
                     primary,1,flags=re.I)[0][:1700]
    if not re.search(r"\b(?:opera\s+lirica|melodramma|opera\s+in\s+\d+\s+atti|"
                     r"rappresentazione\s+operistica)\b",primary,re.I):
        raise ValueError("Taormina detail does not independently verify opera genre")
    if not VENUE.search(primary):
        raise ValueError("Taormina event is not at the Teatro Antico")
    work,composer=_work(title)
    # Composer must be independently credited, not inferred solely from title.
    if not re.search(r"\b(?:di|musica\s+di|compositore\s*:)\s+"+
                     re.escape(composer)+r"\b",primary,re.I):
        raise ValueError("Taormina official composer credit missing")
    rows=set()
    for d,m,y,h,minute in DATE.findall(primary):
        try:rows.add((date(int(y),int(m),int(d)).isoformat(),f"{int(h):02d}:{minute}"))
        except ValueError as exc:raise ValueError("invalid Taormina official date") from exc
    for d,m,y,h,minute in TEXTDATE.findall(primary):
        try:rows.add((date(int(y),MONTHS[m.casefold()],int(d)).isoformat(),f"{int(h):02d}:{minute}"))
        except ValueError as exc:raise ValueError("invalid Taormina official date") from exc
    if not rows or len(rows)>20:raise ValueError("Taormina official local recitals not verified")
    return work,composer,"Teatro Antico di Taormina",sorted(rows)
