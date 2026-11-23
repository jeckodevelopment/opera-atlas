"""Official Luglio Musicale Trapanese opera detail reader.

A mixed summer/autumn season lists opera, concerts, dance and chamber opera
at different venues; these may never be conflated with the outdoor Teatro
Giuseppe Di Stefano. A new future edition follows the same URL template.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

SOURCE_KEY="trapani-luglio-musicale-2026"
INDEX="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/"
HOST="www.lugliomusicale.it"
ROOT="/it/luglio-musicale-stagioni/"
DETAIL=re.compile(r"/it/luglio-musicale-stagioni/stagione-(20\d{2})/([a-z0-9][a-z0-9-]*)/")
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
TIME=re.compile(r"(?<!\d)([0-3]?\d)\s+("+ "|".join(MONTHS) +r")\s+(20\d{2}),?\s+Ore\s+([01]?\d|2[0-3]):([0-5]\d)",re.I)
VENUES={
    "Opera":("Teatro Giuseppe Di Stefano",
            r'Teatro\s+["“]Giuseppe\s+Di\s+Stefano["”]'),
    "Opera da camera":("Teatro M° Tonino Pardo",
                       r'Teatro\s+M[°º]\s+Tonino\s+Pardo'),
}
COMPOSER=re.compile(r"\b(?:Musica|Musiche)\s+di\s+([A-ZÀ-Ž][\wÀ-ÿ.\-'’ ]{4,85}?)(?=\s+Libretto\b)",re.I)

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.parts=[]
        self.h1=[]
        self._heading=False
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
        if tag=="h1" and not self.skip:self._heading=True
        if tag=="a" and not self.skip:
            href=dict(attrs).get("href")
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag=="h1":self._heading=False
        if tag in ("script","style","noscript"):self.skip=max(self.skip-1,0)
    def handle_data(self,text):
        if self.skip:return
        text=" ".join(text.split())
        if text:
            self.parts.append(text)
            if self._heading:self.h1.append(text)

def eligible_detail(url:str)->bool:
    u=urlsplit(url)
    m=DETAIL.fullmatch(u.path)
    return (u.scheme=="https" and u.hostname==HOST and bool(m)
            and 2026<=int(m[1])<=2099 and not u.query and not u.fragment
            and u.username is None and u.password is None and u.port is None)

def extract_index(html:str,*,url:str=INDEX,min_links:int=3)->list[str]:
    if not re.fullmatch(r"/it/luglio-musicale-stagioni/stagione-20\d{2}/",urlsplit(url).path):
        raise ValueError("invalid first-party Trapani season URL")
    if urlsplit(url).scheme!="https" or urlsplit(url).hostname!=HOST:
        raise ValueError("unapproved Trapani season index")
    reader=Reader();reader.feed(html)
    season=urlsplit(url).path.split("/")[3]
    candidates=sorted({candidate for href in reader.links
                       if eligible_detail(candidate:=urljoin(url,href))
                       and urlsplit(candidate).path.startswith(ROOT+season+"/")})
    if len(candidates)<min_links:
        raise ValueError("Trapani official season index incomplete")
    return candidates

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    if not eligible_detail(url):raise ValueError("unapproved Trapani event")
    reader=Reader();reader.feed(html)
    title=" ".join(reader.h1).strip()
    if not 2<=len(title)<=120:raise ValueError("Trapani work title unverified")
    text=" ".join(reader.parts)
    # The first-party event type is a standalone "Opera" label, not the
    # word 'opera' inside a concert title, review or biographical note.
    start=next((i for i,x in enumerate(reader.parts) if x==title),None)
    if start is None:raise ValueError("Trapani official title missing")
    # The source prints breadcrumbs immediately after H1, then a single
    # event type before repeating the title in the event content.
    # The live CMS may insert image captions, breadcrumbs and accessibility
    # text between H1 and the genre badge. Keep a bounded event header and
    # accept only the source's exact standalone category badge before the
    # repeated work title; never classify by words inside its synopsis.
    prefix=reader.parts[start+1:start+40]
    # Live CMS breadcrumbs or image captions may repeat the H1 title
    # before the genre badge. Bind genre to the bounded event header,
    # before the independent official composer credit, not the title.
    credit_index=next((i for i,item in enumerate(prefix)
                       if re.search(r"\b(?:Musica|Musiche)\s+di\b",item,re.I)),None)
    if credit_index is None:
        raise ValueError("Trapani first-party composer missing")
    genre_positions=[(i,genre) for i,item in enumerate(prefix[:credit_index])
                     for genre in VENUES if item.strip()==genre]
    genres=[genre for _,genre in genre_positions]
    if len(genres)!=1 or credit_index-genre_positions[0][0]>12:
        raise ValueError("Trapani event is not a verified opera")
    genre=genres[0]
    venue,venue_pattern=VENUES[genre]
    primary=" ".join(reader.parts[start:start+22]).split("Personaggi e interpreti",1)[0]
    # The live CMS sometimes separates the explicitly credited composer
    # from the libretto (or omits "di" after "Libretto"). Read the source's
    # standalone "Musica di NAME" node rather than depending on a subsequent
    # libretto label. Reject ambiguous or unbounded prose instead of guessing.
    credits=[]
    for part in reader.parts[start+1:start+40]:
        match=re.fullmatch(
            r"(?:Musica|Musiche)\\s+di\\s+"
            r"([A-ZÀ-Ž][A-Za-zÀ-ÿ.'’\\- ]{4,85})",part.strip(),re.I)
        if match:
            credits.append(" ".join(match.group(1).split()))
    unique={x.casefold():x for x in credits}
    if len(unique)!=1:
        # Retain support for older official markup with combined credit nodes.
        credit=COMPOSER.search(primary)
        if credit is None or unique:
            raise ValueError("Trapani first-party composer missing")
        composer=" ".join(credit.group(1).split())
    else:
        composer=next(iter(unique.values()))
    if not re.search(venue_pattern,primary,re.I):
        raise ValueError("Trapani exact opera venue missing")
    recite=[]
    # Require each verified venue to immediately precede its own date/time.
    pairs=re.findall(
        venue_pattern+r'\s+'
        r'([0-3]?\d)\s+('+ "|".join(MONTHS) +r')\s+(20\d{2}),?\s+Ore\s+'
        r'([01]?\d|2[0-3]):([0-5]\d)',primary,re.I)
    if len(pairs)!=len(re.findall(venue_pattern,primary,re.I)):
        raise ValueError("some Trapani official showtimes are missing or invalid")
    for d,month,y,h,m in pairs:
        year=int(y)
        if year!=int(DETAIL.fullmatch(urlsplit(url).path)[1]):
            raise ValueError("Trapani event date outside official season")
        try:day=date(year,MONTHS[month.casefold()],int(d)).isoformat()
        except ValueError:raise ValueError("invalid official Trapani recita")
        recite.append((day,f"{int(h):02d}:{int(m):02d}"))
    if not recite or len(recite)>12 or len({d for d,_ in recite})!=len(recite):
        raise ValueError("Trapani showtimes absent or ambiguous")
    return title,composer,venue,recite
