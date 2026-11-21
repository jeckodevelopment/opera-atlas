"""First-party opera detail parser for Teatro Lirico di Cagliari.

Never parse a page's related-events carousel or date cast alternations.
Yearless dates must match the verified first-party 2027 opera brochure
for the exact work, date and hour.
"""
from __future__ import annotations
import re
import json
import unicodedata
from pathlib import Path
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

HOST="www.liricocagliari.it"
SOURCE_KEY="lirico-cagliari-opera-2027"
VENUE="Teatro Lirico di Cagliari"
BROCHURE=Path(__file__).resolve().parents[1]/"data"/"cagliari-season-2027.json"


def normalize(value: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                           if not unicodedata.combining(c)).split())


def verified_brochure(slug: str, title: str, composer: str) -> dict:
    document=json.loads(BROCHURE.read_text(encoding="utf-8"))
    expected_url=("https://www.liricocagliari.it/wp-content/uploads/2026/11/"
                  "Pieghevole-Stagione-Opera-2027-21x15-4-ante.pdf")
    if (document.get("schema_version")!=1 or document.get("year")!=2027 or
        document.get("official_schedule_url")!=expected_url):
        raise ValueError("unverified official Cagliari brochure")
    works=[x for x in document.get("works",[]) if x.get("slug")==slug]
    if len(works)!=1:
        raise ValueError("production not individually verified in official brochure")
    work=works[0]
    if (normalize(work["title"])!=normalize(title) or
        normalize(work["composer"])!=normalize(composer)):
        raise ValueError("official brochure work identity disagrees with detail")
    return work



class PageHeadings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current=None
        self.parts=[]
        self.headings=[]
        self.text=[]
        self.depth=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript"):
            self.depth+=1
        if not self.depth and tag in ("h1","h2"):
            self.current=tag
            self.parts=[]
        if not self.depth and tag in ("p","li","div","br","h1","h2","h3","span"):
            self.text.append(" ")
    def handle_endtag(self, tag):
        if self.current==tag:
            self.headings.append((tag," ".join(" ".join(self.parts).split())))
            self.current=None
        if tag in ("script","style","noscript"):
            self.depth=max(0,self.depth-1)
        if not self.depth and tag in ("p","li","div","br","h1","h2","h3","span"):
            self.text.append(" ")
    def handle_data(self, data):
        if not self.depth:
            self.text.append(data)
            if self.current:
                self.parts.append(data)


def parse_detail(html: str, *, url: str, season_year: int = 2027) -> tuple[str,str,str,list[tuple[str,str]]]:
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!=HOST or parsed.query or
        parsed.fragment or parsed.username or parsed.password or parsed.port or
        not re.fullmatch(r"/evento/[a-z0-9-]+/",parsed.path)):
        raise ValueError("unapproved Cagliari detail URL")
    if season_year!=2027:
        raise ValueError("unsupported season")
    reader=PageHeadings()
    reader.feed(html)
    h1=[i for i,(tag,value) in enumerate(reader.headings) if tag=="h1" and value]
    if len(h1)!=1:
        raise ValueError("missing unique work heading")
    pos=h1[0]
    next_heading=reader.headings[pos+1:pos+2]
    if not next_heading or next_heading[0][0]!="h2":
        raise ValueError("missing work-specific composer heading")
    title=reader.headings[pos][1]
    composer=next_heading[0][1]
    if composer.casefold().startswith(("incontro", "parliamo", "balletto","concerto")):
        raise ValueError("not an opera composer")
    text=" ".join(" ".join(reader.text).split())
    # Only the production's Date section, before cast and related items.
    begin=re.search(r"\bDate\s+(?:vedi tutto\s+)?",text,re.I)
    if not begin:
        raise ValueError("missing official performance section")
    end=re.search(r"(?:Personaggi e interpreti|Cast|Team creativo|In breve|Prezzi e info)",text[begin.end():],re.I)
    if not end:
        raise ValueError("no trusted end to performance section")
    section=text[begin.end():begin.end()+end.start()]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section):
        raise ValueError("ambiguous cancellation")
    # Yearless dd/mm rows are acceptable only with first-party documentary
    # evidence for this exact opera (not the site's global season menu).
    slug=parsed.path.strip("/").split("/")[-1]
    work=verified_brochure(slug,title,composer)
    expected={}
    for day,clock in work["dates"]:
        if (not re.fullmatch(r"2027-\d{2}-\d{2}",day) or
            not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",clock)):
            raise ValueError("invalid brochure performance")
        date.fromisoformat(day)
        if day in expected:
            raise ValueError("duplicate official brochure performance")
        expected[day]=clock
    if not expected or len(expected)>35:
        raise ValueError("no bounded official season performances")

    row=re.compile(
        r"(?i)\bore\s+([01]?\d|2[0-3]):([0-5]\d)\s+"
        r"(?:lun|mar|mer|merc|gio|ven|sab|dom)\s+"
        r"(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b")
    found={}
    matches=list(row.finditer(section))
    for i,match in enumerate(matches):
        hour,minute,day,month,explicit_year=match.groups()
        clock=f"{int(hour):02d}:{minute}"
        # The live site currently repeats 24/06 20:00 placeholder rows.
        # They are never evidence of a real performance.
        if day=="24" and month=="06" and clock=="20:00" and not explicit_year:
            continue
        until=matches[i+1].start() if i+1<len(matches) else len(section)
        suffix=section[match.end():until]
        if re.search(r"(?i)\b(?:Opera\s+NextGen|scuole|matin[ée]e)\b",suffix):
            continue
        year=int(explicit_year) if explicit_year else 2027
        iso=date(year,int(month),int(day)).isoformat()
        if iso not in expected or expected[iso]!=clock:
            raise ValueError("detail calendar conflicts with official 2027 brochure")
        found[iso]=clock
    if found!=expected:
        raise ValueError("incomplete official 2027 recital evidence")
    return title,composer,VENUE,sorted(found.items())
