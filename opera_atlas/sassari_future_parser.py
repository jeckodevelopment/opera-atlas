"""Dynamic Sassari opera archive with strict first-party event identity.

The Ente de Carolis archive mixes symphonic concerts, Alghero Festival
performances and Teatro Comunale productions. A card is only a *candidate*:
each linked event must independently confirm a single credited work,
season year, complete showtimes and the Sassari venue.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit,urljoin,parse_qs

from opera_atlas.national_detail_parser import clean,MONTHS

HOST="www.marialisadecarolis.it"
INDEX=f"https://{HOST}/opere-liriche.aspx"
VENUE="Teatro Comunale di Sassari"
ID=re.compile(r"[1-9][0-9]{0,5}")
DATE=re.compile(r"(?i)\b(\d{1,2})\s+"
                r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
                r"settembre|ottobre|novembre|dicembre)\s+"
                r"(2[0-3]|1\d|0?\d):([0-5]\d)\b")
BAD=re.compile(r"(?i)\b(?:concerto|sinfonia|sinfonico|requiem|balletto|"
               r"danza|musical|crossover|opera pop|gala|lezione|"
               r"carmina burana|alghero festival)\b")
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

def eligible_detail(url:str)->bool:
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname!=HOST or p.path!="/opera-lirica.aspx"
        or p.username or p.password or p.port is not None or p.fragment):
        return False
    query=parse_qs(p.query,keep_blank_values=True)
    return bool(set(query)=={"id"} and len(query["id"])==1
                and ID.fullmatch(query["id"][0])
                and p.query=="id="+query["id"][0])

class _ArchiveCards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.in_h2=0
        self.href=None
        self.title=[]
        self.cards=[]
        self.year=None
        self.seen_heading=False
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.hidden+=1
        if self.hidden:return
        if tag=="h2":
            self.in_h2+=1
        if tag=="a" and self.in_h2:
            self.href=dict(attrs).get("href")
            self.title=[]
    def handle_data(self,data):
        if self.hidden:return
        text=" ".join(data.split())
        if not text:return
        if "Stagione lirica" in text:
            self.seen_heading=True
        if self.in_h2 and self.href is not None:
            self.title.append(text)
        elif not self.in_h2 and re.fullmatch(r"20\d{2}",text):
            self.year=int(text)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None and self.in_h2:
            self.cards.append((self.year,self.href," ".join(self.title)))
            self.href=None
        if tag=="h2" and self.in_h2:
            self.in_h2-=1
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)

def extract_index(html:str,*,url:str,min_links:int)->list[str]:
    if url!=INDEX:
        raise ValueError("Sassari archive URL is not the approved first-party index")
    parser=_ArchiveCards()
    parser.feed(html)
    if not parser.seen_heading:
        raise ValueError("official Sassari opera archive identity missing")
    links=set()
    for year,href,title in parser.cards:
        if year is None or year<2026 or not title or BAD.search(title):
            continue
        target=urljoin(INDEX,href)
        if eligible_detail(target):
            links.add(target)
    if len(links)<min_links:
        raise ValueError("no eligible recent Sassari event cards")
    return sorted(links)

def parse_detail(html:str,*,url:str):
    if not eligible_detail(url):
        raise ValueError("unapproved Sassari event detail")
    # Keep title/composer/year/date evidence entirely inside the work's
    # header, prior to description, news and season-wide footer.
    text=clean(html).replace("’","'").replace("´","'")
    head=re.search(r"(?i)\b(?:Opere e concerti|Stagione)\s+(20\d{2})\b",text[:430])
    if not head:
        raise ValueError("Sassari event season year absent near first-party heading")
    year=int(head[1])
    if not 2026<=year<=2099:
        raise ValueError("historical Sassari archive item")
    # An article heading is followed by the credited composer and exact
    # date/time tokens. Do not read the footer's other production cards.
    h=re.search(r"(?is)<h[12]\b[^>]*>(.*?)</h[12]>",html)
    if not h:
        raise ValueError("Sassari opera heading missing")
    title=clean(h[1]).replace("’","'").replace("´","'").strip()
    if not title or len(title)>160 or BAD.search(title):
        raise ValueError("Sassari event is non-operatic or unclassified")
    start=text.find(title)
    if start<0 or start>750:
        raise ValueError("official Sassari work title outside leading block")
    remainder=text[start+len(title):]
    # Composer must be the very next field, not found in cast/news/footer.
    credit=re.match(
        r"\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'’-]*"
        r"(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'’-]*){1,3})"
        r"(?=\s+\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
        r"luglio|agosto|settembre|ottobre|novembre|dicembre)\b)",
        remainder,re.I)
    if not credit:
        raise ValueError("Sassari composer not immediately credited")
    composer=credit[1].strip()
    if BAD.search(composer) or any(x in {"aa.vv.","vari","e","non","ignoto","anonimo"}
       for x in composer.casefold().split()):
        raise ValueError("Sassari composer credit ambiguous")
    # Only the first work-specific H3 after the title/composer is a ticket
    # schedule. The later prose can repeat the days without precise hours.
    schedule=re.search(r"(?is)<h3\\b[^>]*>(.*?)</h3>",html[h.end():h.end()+550])
    if not schedule:
        raise ValueError("Sassari work-specific schedule heading absent")
    date_block=clean(schedule[1])
    matches=list(DATE.finditer(date_block))
    if not 1<=len(matches)<=12:
        raise ValueError("official Sassari precise work-specific showtimes missing")
    if len(re.findall(r"(?i)\b\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|"
                      r"giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\b",date_block))!=len(matches):
        raise ValueError("Sassari showtimes incomplete or ambiguous")
    dates=[]
    for m in matches:
        day,month,hour,minute=m.groups()
        dt=date(year,MONTHS[month.casefold()],int(day))
        dates.append((dt.isoformat(),f"{int(hour):02d}:{minute}"))
    if len(dates)!=len(set(dates)):
        raise ValueError("duplicated Sassari recite")
    boundary=re.search(r"(?i)\b(?:Notizie\s*/\s*News|Stagione Lirica e Sinfonica)\b",remainder)
    body=remainder[:boundary.start()] if boundary else remainder[:1800]
    if not re.search(r"(?i)\bTeatro Comunale(?:\s+di\s+Sassari)?\b",body[:1100]):
        raise ValueError("Sassari Teatro Comunale venue missing")
    if re.search(r"(?i)\b(?:Alghero Festival|Forte della Maddalena)\b",body[:600]):
        raise ValueError("Alghero production cannot be attributed to Sassari")
    if CANCEL.search(body[:600]):
        raise ValueError("cancelled Sassari production requires review")
    # Unknown operas need genre-level evidence from their own body,
    # rather than the season index's mixed 'Opere e concerti' category.
    if not re.search(r"(?i)\b(?:opera|operetta|melodramma|dramma lirico)\b",body[:900]):
        raise ValueError("Sassari work lacks operatic-genre evidence")
    return title,composer,VENUE,sorted(dates)
