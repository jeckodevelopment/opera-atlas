"""First-party Opera 2026/27 at the Teatro Municipale Valli, Reggio Emilia."""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

HOST="www.iteatri.re.it"
KEY="reggio-valli-opera-2026-27"
VENUES={"Teatro Municipale Valli":"Teatro Valli","Teatro Ariosto":"Teatro Ariosto"}
TITLE_RE=re.compile(r"^(.+?)$")


class Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1=[]
        self.current=None
        self.value=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h1":
            self.current=tag
            self.value=[]
    def handle_data(self,data):
        if self.current:self.value.append(data)
    def handle_endtag(self,tag):
        if tag==self.current:
            self.h1.append(" ".join(" ".join(self.value).split()))
            self.current=None


def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    loc=urlsplit(url)
    if (loc.scheme!="https" or loc.hostname!=HOST or loc.query or loc.fragment
        or loc.username or loc.password or loc.port is not None
        or not re.fullmatch(r"/spettacolo/[a-z0-9-]+/?",loc.path)):
        raise ValueError("invalid official Valli opera detail")
    parser=Headings()
    parser.feed(html)
    if len(parser.h1)!=1:
        raise ValueError("missing unique Valli work heading")
    title=parser.h1[0]
    body=clean(html)
    # Scope to the single work, never the recommended concerts in the footer.
    start=body.find(title)
    category=re.search(r"\b(Teatro Municipale Valli|Teatro Ariosto)\s+Opera\b",body[start:],re.I)
    if start<0 or not category:
        raise ValueError("not an opera at an approved Reggio Emilia venue")
    leading=body[start:start+category.end()]
    m=re.search(r"\bMusica\s+di\s+(.+?)\s+(?:Libretto|Cast|Descrizione|Extra|Acquista)\b",leading,re.I)
    if not m:raise ValueError("official opera composer missing")
    composer=" ".join(m.group(1).split())
    if (not re.fullmatch(r"[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+){1,3}",composer)):
        raise ValueError("official composer not unambiguous")
    # Only ticket rows carry full years. Month/day headings are insufficient.
    # Official WordPress H2 headings can wrap their title in spans or links.
    # Select the matching heading's DOM range, not the navigation's first
    # occurrence of the word Biglietti.
    h2=list(re.finditer(r"<h2\b[^>]*>.*?</h2>",html,re.I|re.S))
    begin=next((i for i,m in enumerate(h2)
                if clean(m.group()).strip().casefold()=="biglietti"),None)
    end=next((i for i,m in enumerate(h2)
              if begin is not None and i>begin
              and clean(m.group()).strip().casefold()=="riduzioni"),None)
    if begin is None or end is None:
        raise ValueError("missing bounded ticket calendar")
    text=clean(html[h2[begin].end():h2[end].start()])
    # WordPress' HTML can separate ticket columns with DOM elements rather
    # than literal pipes. Keep the bounded H2 section and validate each
    # complete calendar row independently: date, clock, price and action.
    dates=list(re.finditer(r"\b(\d{2})/(\d{2})/(20\d{2})\b",text))
    if not dates:
        raise ValueError("incomplete Valli ticket dates")
    found={}
    for index,m in enumerate(dates):
        row=text[m.end():dates[index+1].start() if index+1<len(dates) else len(text)]
        clock=re.match(r"\s*\|?\s*([01]\d|2[0-3]):([0-5]\d)\b",row)
        price=re.search(r"€\s*(\d+)[,.](\d{2})\b",row)
        action=re.search(r"\bAcquista\b",row,re.I)
        if not clock or not price or not action:
            raise ValueError("incomplete Valli ticket dates")
        day,month,year=m.groups()
        iso=date(int(year),int(month),int(day)).isoformat()
        if int(year) not in (2026,2027):
            raise ValueError("outside 2026/27 Valli Opera season")
        if int(price.group(1))==0 and price.group(2)=="00":
            continue
        if iso in found:
            raise ValueError("duplicate Valli recital")
        found[iso]=f"{clock.group(1)}:{clock.group(2)}"
    if not found or len(found)>20:
        raise ValueError("no ordinary ticketed Valli recite")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",leading):
        raise ValueError("cancelled event requires review")
    return title,composer,VENUES[category.group(1)],sorted(found.items())
