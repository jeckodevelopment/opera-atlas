"""Rolling official Teatro Filarmonico opera discovery, independent of 2027 allowlist.

The official 'prossime stagioni' page mixes opera, concerts and ballet.
Index cards may only propose candidates. Production-level source text must
confirm Opera, Teatro Filarmonico, named composer, and bounded ticket times.
Historical five-title 2027 parser remains unchanged.
"""
from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit,urljoin
from opera_atlas.national_detail_parser import MONTHS,clean
from opera_atlas.verona_filarmonico_parser import WEEKDAYS,VENUE

HOST="www.arena.it"
INDEX=f"https://{HOST}/prossime-stagioni/"
DETAIL=re.compile(r"/teatro-filarmonico-verona/(20\d{2})/([a-z0-9-]+)/?")
SHOWTIME=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})\s+ore\s+"
    r"(2[0-3]|1\d|0?\d):([0-5]\d)\b")
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

class _OfficialCards(HTMLParser):
    """Track category immediately preceding a card heading, not nav/footer."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.heading=0
        self.title=[]
        self.href=None
        self.category=""
        self.category_parts=[]
        self.cards=[]
        self.recent=""
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.hidden+=1
        if self.hidden:return
        if tag=="h2":
            self.heading+=1
            self.title=[]
            self.href=None
        elif tag=="a" and self.heading:
            self.href=dict(attrs).get("href")
    def handle_data(self,data):
        if self.hidden:return
        normalized=" ".join(data.split())
        if not normalized:return
        if self.heading:
            self.title.append(normalized)
        else:
            # Mixed first-party season list has a genre label before h2.
            # A card is eligible only if the immediately previous label is Opera.
            self.recent=normalized
    def handle_endtag(self,tag):
        if tag=="h2" and self.heading:
            self.heading-=1
            if not self.heading and self.href:
                self.cards.append((self.recent,self.href," ".join(self.title)))
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    match=DETAIL.fullmatch(p.path)
    return bool(p.scheme=="https" and p.hostname==HOST and match
                and not p.query and not p.fragment and not p.username
                and not p.password and p.port is None
                and 2027<=int(match[1])<=2099)

def extract_index(html:str,*,url:str,min_links:int)->list[str]:
    if url!=INDEX:
        raise ValueError("unapproved Filarmonico future calendar")
    parser=_OfficialCards()
    parser.feed(html)
    candidates=set()
    for genre,href,title in parser.cards:
        if genre.casefold()!="opera" or not title:
            continue
        target=urljoin(url,href)
        if eligible_detail(target):
            candidates.add(target)
    if len(candidates)<min_links:
        raise ValueError("official Filarmonico programme has no verified opera cards")
    return sorted(candidates)

def parse_detail(html:str,*,url:str):
    if not eligible_detail(url):
        raise ValueError("unapproved Filarmonico future opera detail")
    year=int(DETAIL.fullmatch(urlsplit(url).path)[1])
    heading=re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>",html)
    if heading is None:
        raise ValueError("Filarmonico event title missing")
    title=clean(heading[1]).strip()
    if not title or len(title)>180:
        raise ValueError("invalid Filarmonico opera title")
    # Keep heading boundaries so neighbouring work cards cannot supply credit.
    text=clean(re.sub(r"(?i)</h[4-6]>", " </h4> ",html))
    start=text.find(title)
    local=text[max(0,start):max(0,start)+1400]
    identity=re.search(
        r"(?i)\bLocation\s+Teatro Filarmonico\b.{0,450}?"
        r"\bTipo di spettacolo\s+Opera\b.{0,300}?"
        r"\bMusica\s+(.+?)\s+(?:Durata|Prossimi spettacoli)\b",
        local)
    if not identity:
        raise ValueError("official Filarmonico opera venue, genre or composer missing")
    composer=identity[1].strip(" .–-")
    if (not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'\u2019-]{3,80}",composer)
            or len(composer.split())<2):
        raise ValueError("ambiguous Filarmonico composer credit")
    after=text[start+identity.end():]
    block_start=re.search(r"(?i)\bProssimi spettacoli\b",after)
    if not block_start:
        raise ValueError("specific Filarmonico ticket schedule missing")
    remainder=after[block_start.end():]
    block_end=re.search(r"(?i)\bCast\s+Regia\b",remainder)
    if not block_end:
        raise ValueError("unbounded Filarmonico ticket schedule")
    block=remainder[:block_end.start()]
    if CANCELLED.search(block):
        raise ValueError("cancelled Filarmonico performance requires review")
    times=[]
    for m in SHOWTIME.finditer(block):
        weekday,day,month,actual_year,hour,minute=m.groups()
        if int(actual_year)!=year:
            raise ValueError("Filarmonico performance year differs from official production URL")
        observed=date(year,MONTHS[month.casefold()],int(day))
        if observed.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("Filarmonico performance date conflicts with weekday")
        times.append((observed.isoformat(),f"{int(hour):02d}:{minute}"))
    declared=re.findall(
        r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
        r"venerd[iì]|sabato|domenica)\s+\d{1,2}\s+"
        r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
        r"settembre|ottobre|novembre|dicembre)\s+20\d{2}",block)
    if not times or len(times)>20 or len(times)!=len(declared) or len(set(times))!=len(times):
        raise ValueError("Filarmonico future performance dates incomplete or duplicated")
    return title,composer,VENUE,sorted(times)
