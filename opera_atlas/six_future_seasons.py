"""Six future municipal opera sources: year-safe index discovery and recite evidence.

Source schemas are inferred from the *previously observed official URL patterns*.
A prospective URL is never considered available until the official site actually
responds with matching year, institution, genre and programme evidence.
Historical 2026/27 parsers remain unchanged.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit,parse_qs,urljoin,urlencode

from opera_atlas.national_detail_parser import clean,MONTHS
from opera_atlas.work_identity import resolve_work

SOURCES={
 "chieti-marrucino-season-2027":("comune.chieti.it","search","Chieti","Marrucino"),
 "modena-municipal-opera-2027-28":("www.comune.modena.it","two","Modena","Teatro Comunale"),
 "rovigo-sociale-season-2027-28":("www.comune.rovigo.it","two","Rovigo","Teatro Sociale"),
 "treviso-del-monaco-season-2027-28":("risorse.teatrostabileveneto.it","short","Treviso","Teatro"),
 "padova-verdi-season-2027":("padovacultura.padovanet.it","one","Padova","Teatro Verdi"),
 "lecce-provincia-season-2027":("www.provincia.le.it","search","Lecce","Politeama"),
}
SEARCH={"chieti-marrucino-season-2027":"stagione lirica {year} marrucino",
        "lecce-provincia-season-2027":"{edition} stagione lirica {year}"}
DIRECT={
 "modena-municipal-opera-2027-28":r"/vivere-modena/eventi/(20\d{2})/stagione-opera-(20\d{2})-(20\d{2})",
 "rovigo-sociale-season-2027-28":r"/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-(20\d{2})-(20\d{2})",
 "treviso-del-monaco-season-2027-28":r"/treviso-teatro-del-monaco-stagione-lirica-concertistica-(\d{2})-(\d{2})",
 "padova-verdi-season-2027":r"/it/attivita-culturali/stagione-lirica-di-padova-(20\d{2})",
}
PERFORMANCE=re.compile(r"(?i)(?<!\w)(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+(20\d{2})\s*(?:[,–-]\s*)?(?:alle\s+)?ore\s+"
    r"(2[0-3]|1\d|0?\d)[.:]([0-5]\d)(?!\d)")
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")
NONOPERA=re.compile(r"(?i)\b(?:opera pop|crossover|musical|concertistica|gala|balletto|danza|prosa)\b")

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.heading=None
        self.parts=[]
        self.headings=[]
        self.links=[]
        self.anchor=None
        self.anchor_text=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.hidden+=1
        if not self.hidden and tag=="h1":
            self.heading=[]
        if not self.hidden and tag=="a":
            self.anchor=dict(attrs).get("href")
            self.anchor_text=[]
    def handle_data(self,data):
        if self.hidden:return
        if self.heading is not None:self.heading.append(data)
        if self.anchor is not None:self.anchor_text.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.heading is not None:
            value=" ".join(" ".join(self.heading).split())
            if value:self.headings.append(value)
            self.heading=None
        if tag=="a" and self.anchor is not None:
            self.links.append((self.anchor," ".join(self.anchor_text)))
            self.anchor=None
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)

def index_year(key:str,url:str)->tuple[int,int]:
    if key not in SOURCES:raise ValueError("unknown future opera source")
    host,kind,city,theatre=SOURCES[key]
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!=host or parsed.port is not None
            or parsed.username or parsed.password or parsed.fragment):
        raise ValueError("non-first-party future season index")
    if kind=="search":
        terms=parse_qs(parsed.query,strict_parsing=True)
        if parsed.path!="/" or set(terms)!={"s"} or len(terms["s"])!=1:
            raise ValueError("unapproved official search")
        term=terms["s"][0]
        m=(re.fullmatch(r"stagione lirica (20\d{2}) marrucino",term)
           if key.startswith("chieti-") else
           re.fullmatch(r"(\d{2,3}) stagione lirica (20\d{2})",term))
        if not m:raise ValueError("unexpected future-season search")
        year=int(m[1] if key.startswith("chieti-") else m[2])
        if key.startswith("lecce-") and int(m[1])!=year-1975:
            raise ValueError("Lecce edition and year disagree")
        if not 2027<=year<=2099:raise ValueError("future search year out of bounds")
        return year,year
    if parsed.query:raise ValueError("unexpected future season parameters")
    match=re.fullmatch(DIRECT[key],parsed.path)
    if not match:raise ValueError("unexpected season index URL")
    years=tuple(map(int,match.groups()))
    if kind=="one":start=end=years[0]
    elif kind=="short":start,end=2000+years[0],2000+years[1]
    elif key.startswith("modena-"):
        catalog_year,start,end=years
        if catalog_year!=start:raise ValueError("Modena year folder inconsistent")
    else:start,end=years
    if start<2027 or start>=2099 or end!=start+(kind!="one"):
        raise ValueError("invalid contiguous future season")
    return start,end

def next_url(key:str,url:str,*,today:date,allow_early:bool=False)->str|None:
    try:start,end=index_year(key,url)
    except ValueError:return None
    if end>=2099:return None
    activation=date(end,6,1) if start!=end else date(start,9,1)
    if not allow_early and today<activation:return None
    host,kind,_,_=SOURCES[key]
    if kind=="search":
        year=start+1
        term=SEARCH[key].format(year=year,edition=year-1975)
        return f"https://{host}/?{urlencode({'s':term})}"
    path=urlsplit(url).path
    if kind=="short":
        path=re.sub(r"-(\d{2})-(\d{2})$",f"-{(start+1)%100:02d}-{(end+1)%100:02d}",path)
    elif kind=="one":
        path=re.sub(r"20\d{2}$",str(start+1),path)
    else:
        path=path.replace(f"{start}-{end}",f"{start+1}-{end+1}")
        if kind=="two" and key.startswith("modena-"):
            path=path.replace(f"/{start}/",f"/{start+1}/")
    return f"https://{host}{path}"

def extract_index(key:str,url:str,html:str,min_links:int)->list[str]:
    start,end=index_year(key,url)
    host,kind,city,theatre=SOURCES[key]
    visible=Visible()
    visible.feed(html)
    if kind=="search":
        approved=[]
        for href,label in visible.links:
            candidate=urlsplit(urljoin(url,href))
            if (candidate.scheme!="https" or candidate.hostname!=host
                    or candidate.query or candidate.fragment or candidate.port is not None):
                continue
            path=candidate.path.lower()
            if key.startswith("chieti-"):
                if not path.startswith("/novita/"):continue
                if not (f"stagione-lirica-{start}" in path and "marrucino" in path):
                    continue
            else:
                if not (f"{start}" in path and "stagione-lirica" in path
                        and (str(start-1975) in path or "provincia-di-lecce" in path)):
                    continue
            if not re.search(r"(?i)stagione\s+lirica",label+" "+path.replace("-"," ")):
                continue
            approved.append(candidate.geturl())
        if len(set(approved))<min_links:
            raise ValueError("future official search returned no season announcement")
        return sorted(set(approved))
    text=clean(html)
    # A generic historic navigation link must never activate a new season.
    if not visible.headings:
        raise ValueError("future programme lacks official h1 heading")
    if kind=="one":
        year_match=rf"(?<!\d){start}(?!\d)"
    elif kind=="short":
        year_match=rf"(?<!\d){start%100:02d}\s*/\s*{end%100:02d}(?!\d)"
    else:
        year_match=rf"(?<!\d){start}\s*/\s*{end}(?!\d)"
    header=" ".join(visible.headings)
    if (not re.search(year_match,header)
        or not re.search(r"(?i)\b(?:opera|lirica)\b",header)
        or city.casefold() not in text.casefold()
        or not re.search(r"(?i)\b(?:opera|lirica)\b",text)
        or not re.search(r"(?i)\b(?:teatro|comunale)\b",text)):
        raise ValueError("future programme identity not established")
    # Require a dated programme, not an empty landing page or navigation.
    if not (re.search(rf"(?<!\d){start}(?!\d)",text) and
            re.search(r"(?i)\b(?:musica\s+di|giuseppe\s+verdi|gaetano\s+donizetti|"
                      r"gioachino\s+rossini|ruggero\s+leoncavallo|giacomo\s+puccini)\b",text)):
        raise ValueError("no source-credited future opera")
    return [url]

def known_recite(key:str,url:str,html:str,registry:dict):
    """No automatic new-opera creation; exact title/composer/date/hour only."""
    start,end=index_year(key,url)
    host,kind,city,theatre=SOURCES[key]
    if kind!="search":
        extract_index(key,url,html,1)
    else:
        # A discovered official article must be validated separately.
        parsed=urlsplit(url)
        if (parsed.hostname!=host or parsed.scheme!="https"
            or parsed.query or parsed.fragment or parsed.port is not None):
            raise ValueError("untrusted future municipal notice")
        text_check=clean(html)
        if not re.search(rf"(?i)stagione\s+lirica\s+{start}\b",text_check):
            raise ValueError("article does not confirm future season")
    text=clean(html)
    if CANCEL.search(text):return []
    if NONOPERA.search(text[:200]):return []
    results=[]
    works=registry.get("works",{}) if isinstance(registry,dict) else {}
    for row in works.values():
        if not isinstance(row,dict):continue
        title,composer=row.get("title"),row.get("composer")
        if not isinstance(title,str) or not isinstance(composer,str):continue
        # Keep identity and credited authorship in the same compact passage.
        for mention in re.finditer(r"(?i)(?<!\w)"+re.escape(title)+r"(?!\w)",text):
            body=text[mention.end():mention.end()+260]
            if not re.search(r"(?i)\b(?:musica\s+di|di)\s+"+re.escape(composer)+r"\b",body):
                continue
            identity=resolve_work(registry,title,composer)
            if identity is None:continue
            dates=[]
            for found in PERFORMANCE.finditer(body):
                day,month,year,hour,minute=found.groups()
                when=date(int(year),MONTHS[month.lower()],int(day))
                if not (date(start,1,1)<=when<=date(end,12,31)):
                    raise ValueError("future performance outside official season")
                dates.append((when.isoformat(),f"{int(hour):02d}:{minute}"))
            if not dates or len(set(dates))!=len(dates) or len(dates)>24:continue
            results.extend((identity["title"],identity["composer"],theatre,day,hour)
                           for day,hour in dates)
    return sorted(set(results))
