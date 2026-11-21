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
    section=re.search(r"\bBiglietti\s+(.*?)\s+(?:Riduzioni|Calici con vista|Opera -)\b",body,re.I)
    if not section:
        raise ValueError("missing bounded ticket calendar")
    text=section.group(1)
    rx=re.compile(r"\b(\d{2})/(\d{2})/(20\d{2})\s*\|\s*([01]\d|2[0-3]):([0-5]\d)\s*\|\s*([^|]+?)\s*\|",re.I)
    found={}
    matches=list(rx.finditer(text))
    other=re.findall(r"\b\d{2}/\d{2}/20\d{2}\b",text)
    if not matches or len(matches)!=len(other):
        raise ValueError("incomplete Valli ticket dates")
    for m in matches:
        day,month,year,hour,minute,price=m.groups()
        iso=date(int(year),int(month),int(day)).isoformat()
        if int(year) not in (2026,2027):
            raise ValueError("outside 2026/27 Valli Opera season")
        # School/under-28 dress rehearsals are not general public recite.
        if re.search(r"€\s*0[,\.]00",price):
            continue
        if iso in found:
            raise ValueError("duplicate Valli recital")
        found[iso]=f"{hour}:{minute}"
    if not found or len(found)>20:
        raise ValueError("no ordinary ticketed Valli recite")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",leading):
        raise ValueError("cancelled event requires review")
    return title,composer,VENUES[category.group(1)],sorted(found.items())
