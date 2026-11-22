"""Official theatre-operated Modena opera pages, independent of municipal host.

The Opera index is the only approved source of linked detail URLs. Detail
recite dates come from the production page and are never inferred from index.
"""
from __future__ import annotations
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.modena_opera_parser import exact_day, VENUE
from opera_atlas.national_detail_parser import clean

HOST="www.teatrocomunalemodena.it"
INDEX="https://www.teatrocomunalemodena.it/opera/"

class Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_h1=False
        self.in_h4=False
        self.parts=[]
        self.h4_parts=[]
        self.headings=[]
        self.h4_headings=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h1":
            self.in_h1=True
            self.parts=[]
        elif tag=="h4":
            self.in_h4=True
            self.h4_parts=[]
    def handle_data(self,data):
        if self.in_h1:
            self.parts.append(data)
        if self.in_h4:
            self.h4_parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.in_h1:
            self.headings.append(" ".join(" ".join(self.parts).split()))
            self.in_h1=False
        elif tag=="h4" and self.in_h4:
            self.h4_headings.append(" ".join(" ".join(self.h4_parts).split()))
            self.in_h4=False

DATE=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
    r"\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"(?:\s+(20\d{2}))?\s*[-–]\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b"
)

def parse_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!=HOST or target.query
            or target.fragment or target.port is not None or target.username
            or target.password or
            not re.fullmatch(r"/spettacolo/[a-z0-9-]+/?",target.path)):
        raise ValueError("unapproved official Modena theatre detail URL")
    headings=Headings()
    headings.feed(html)
    if target.path.rstrip("/")=="/spettacolo/gaia-aloisi-veleno":
        # The only credited opera identity is in the official H4, which
        # may contain inline spans/strong tags. Collect visible heading text,
        # never infer a composer's name from the slug. Ignore unrelated
        # H1 headlines injected by the common website template.
        verified=[x for x in headings.h4_headings
                  if re.fullmatch(r"Gaia Aloisi\s*[–-]\s*Veleno",x,re.I)]
        if len(verified)!=1:
            raise ValueError("missing unique Modena production title")
        heading=verified[0]
    elif len(headings.headings)==1:
        heading=headings.headings[0]
    else:
        raise ValueError("missing unique Modena production title")
    match=re.fullmatch(r"(.+?)\s*[–-]\s*(.+)",heading)
    if match is None:
        raise ValueError("opera title and credited composer not both explicit")
    composer,title=match.groups()
    # This exact first-party bilingual heading identifies ONE Richard Wagner
    # composition; its Italian translation is not a second opera. Keep the
    # original German canonical title (and a stable historical poster key)
    # while preserving every first-party date and clock unchanged.
    if (target.path.rstrip("/")==
        "/spettacolo/richard-wagner-der-fliegender-hollander-lolandese-volante"
        and composer=="Richard Wagner"
        and title=="Der fliegende Holländer (L’olandese volante)"):
        title="Der fliegende Holländer"
    # Compound composer credits and unsupported music programmes need their
    # own verified work identity, never an arbitrary inferred single composer.
    if (len(composer)>90 or len(title)>150 or "/" in composer
            or re.search(r"(?i)\b(?:gala|concerto|musical)\b",title)):
        raise ValueError("not one unambiguous credited opera")
    body=clean(html)
    if VENUE.casefold() not in body.casefold():
        raise ValueError("Modena production venue not identified")
    # The production intro repeats its date summary twice, before cast notes
    # and general ticketing. Deduplicate identical recite observations only.
    start=body.find(heading)
    if start<0:
        raise ValueError("official title not present in detail body")
    bounded=body[start:start+1100]
    bounded=re.split(r"(?i)\b(?:acquista online|programma di sala|invito all.opera)\b",
                     bounded,maxsplit=1)[0]
    if re.search(r"(?i)\b(?:annullat[oaie]|cancellat[oaie]|rinviat[oaie])\b",bounded):
        raise ValueError("cancelled Modena performance requires reconciliation")
    found={}
    for weekday,day,month,year,hour,minute in DATE.findall(bounded):
        date_iso=exact_day(weekday,day,month,year or None)
        clock=f"{int(hour):02d}:{minute}"
        if date_iso in found and found[date_iso]!=clock:
            raise ValueError("conflicting showtime for same Modena recita")
        found[date_iso]=clock
    if not 1<=len(found)<=8:
        raise ValueError("missing bounded official Modena recite times")
    return title,composer,VENUE,sorted(found.items())
