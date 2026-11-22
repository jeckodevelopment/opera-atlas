"""Source-bound rolling opera discovery for Teatro Coccia, Novara.

The mixed Opera/Danza/Concerti season listing is not an opera-only listing.
Only clearly eligible event cards can become review candidates. The official
individual detail page must independently establish the Opera breadcrumb,
composer, Teatro Coccia venue and each exact showtime before admission.
The three 2027 historical allowlist pages remain unchanged.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin,urlsplit

from opera_atlas.national_detail_parser import MONTHS,clean
from opera_atlas.novara_coccia_parser import WEEKDAYS,VENUE

HOST="www.fondazioneteatrococcia.it"
INDEX=f"https://{HOST}/spettacoli_opera_danza_concerti.html"
EVENT=re.compile(r"/stagione-(\d{2})-([a-z0-9-]+)\.html")
DATE=re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})\s+"
    r"ore\s+(2[0-3]|1\d|0?\d):([0-5]\d)\b"
)
NOT_OPERA=re.compile(
    r"(?i)\b(?:balletto|danza|concerto|gal[aà]|musical|swing|pop|"
    r"omaggio|sinfonico|voci\s+dal\s+vero)\b"
)
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

class _Cards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden=0
        self.card_depth=0
        self.card_title=[]
        self.card_link=None
        self.cards=[]
        self.headings=[]
        self.h1=None
    def handle_starttag(self,tag,attrs):
        if tag in ("nav","footer","script","style"):
            self.hidden+=1
        if self.hidden:return
        if tag=="h1":
            self.h1=[]
        if tag=="h3":
            self.card_depth+=1
            if self.card_depth==1:
                self.card_title=[]
                self.card_link=None
        if tag=="a" and self.card_depth:
            self.card_link=dict(attrs).get("href")
    def handle_data(self,data):
        if self.hidden:return
        if self.h1 is not None:self.h1.append(data)
        if self.card_depth:self.card_title.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.h1 is not None:
            self.headings.append(" ".join(" ".join(self.h1).split()))
            self.h1=None
        if tag=="h3" and self.card_depth:
            self.card_depth-=1
            if self.card_depth==0 and self.card_link:
                self.cards.append((self.card_link," ".join(" ".join(self.card_title).split())))
        if tag in ("nav","footer","script","style"):
            self.hidden=max(0,self.hidden-1)


def eligible_detail(url:str)->bool:
    parsed=urlsplit(url)
    match=EVENT.fullmatch(parsed.path)
    return bool(match and parsed.scheme=="https" and parsed.hostname==HOST
                and parsed.port is None and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment and int(match[1])>=27
                and match[2] not in ("opera-gala","concerto-gala"))


def extract_index(html:str,*,url:str,min_links:int)->list[str]:
    if url!=INDEX:
        raise ValueError("Novara official rolling index URL changed")
    parser=_Cards()
    parser.feed(html)
    if not any(re.fullmatch(r"(?i)SPETTACOLI\s+OPERA\s*,?\s*DANZA\s*,?\s*CONCERTI",h)
               for h in parser.headings):
        raise ValueError("Novara mixed opera and dance heading is missing")
    links=set()
    for href,title in parser.cards:
        if NOT_OPERA.search(title):
            continue
        target=urljoin(url,href)
        if eligible_detail(target):
            links.add(target)
    if len(links)<min_links:
        raise ValueError("no official Novara opera card candidates")
    return sorted(links)


def parse_detail(html:str,*,url:str):
    if not eligible_detail(url):
        raise ValueError("unapproved future Novara opera source")
    parsed=urlsplit(url)
    event_year=2000+int(EVENT.fullmatch(parsed.path)[1])
    text=clean(re.sub(r"(?i)</h[2-6]>", " </h3> ",html))
    heading=re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>",html)
    if not heading:
        raise ValueError("official Novara work title missing")
    title=clean(heading[1])
    if (not title or NOT_OPERA.search(title) or
        not re.search(r"(?i)\bSpettacoli\s*(?:/|\s)\s*Opera\s*(?:/|\s)\s*"+re.escape(title)+r"\b",text)):
        raise ValueError("official Novara opera breadcrumb missing or different genre")
    # A combined ticket must be handled as a multi-work programme; never
    # silently reduce L'amor mio / Il tabarro to one canonical opera.
    if "/" in title:
        raise ValueError("Novara multi-work programme requires component reconciliation")
    # A page may contain a long navigation menu or duplicate work titles in
    # breadcrumbs. Read credits from the actual H1 to the event-information
    # section, never from the first occurrence of the title in site chrome.
    # The HTML slice is source-local; a composer in related links/footer is
    # not accepted as first-party attribution.
    after_heading=html[heading.end():]
    section_end=re.search(r"(?i)informazioni\s+sull.evento",after_heading)
    if not section_end:
        raise ValueError("official Novara event information section missing")
    credit_section=clean(after_heading[:section_end.start()])
    if not 0<len(credit_section)<=10000:
        raise ValueError("Novara first-party production credit section malformed")
    # Read the complete first-party composer line, stopping at a new
    # production credit instead of silently keeping only the first author.
    credit=re.search(
        r"(?is)\bMusica\s+di\s+(.*?)"
        r"(?=Libretto\b|Trascrizione\b|Drammaturgia\b|Cast\b|"
        r"Prima\s+rappresentazione\b|Direttore\b|Regia\b|"
        r"Scene\b|Produzione\b)",credit_section)
    if not credit or credit.start()>600:
        raise ValueError("explicit official Novara opera composer is missing")
    composer=re.sub(r"\s*\([^)]*Accademia\s+AMO[^)]*\)\s*$","",
                    credit.group(1),flags=re.I).strip(" .")
    authors=[name.strip() for name in composer.split(",")]
    if (not 1<=len(authors)<=4
            or any(not re.fullmatch(
                r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'\u2019-]{2,70}",name)
                or len(name.split())<2 for name in authors)):
        raise ValueError("invalid or ambiguous first-party composer credit")
    composer=", ".join(authors)
    booking=re.search(
        r"(?is)\binformazioni\s+sull.evento\b(.*?)"
        r"\b(TEATRO\s+COCCIA|GIARDINI\s+DI\s+PALAZZO\s+NATTA)\b",text)
    if not booking:
        raise ValueError("official Novara showtime section or venue missing")
    block=booking[1]
    venue=(VENUE if re.fullmatch(r"(?i)TEATRO\s+COCCIA",booking[2])
           else "Giardini di Palazzo Natta")
    if CANCELLED.search(block):
        raise ValueError("Novara cancelled or postponed recite requires review")
    rows=[]
    school_dates=0
    matches=list(DATE.finditer(block))
    for i,match in enumerate(matches):
        weekday,day,month,year,hour,minute=match.groups()
        if int(year)!=event_year:
            raise ValueError("Novara event date differs from season slug year")
        observed=date(event_year,MONTHS[month.casefold()],int(day))
        if observed.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("Novara weekday inconsistent with date")
        # A date may list morning school-only recite alongside later public
        # performances on other dates. Never publish school-only entries.
        following=block[match.end():matches[i+1].start() if i+1<len(matches) else len(block)]
        if re.search(r"(?i)\brecite?\s+per\s+le\s+scuole\b",following):
            school_dates+=1
            continue
        if re.search(r"(?i)\b(?:ore\s+)?\d{1,2}:[0-5]\d\b",following):
            raise ValueError("multiple or ambiguous public Novara showtimes")
        rows.append((observed.isoformat(),f"{int(hour):02d}:{minute}"))
    declared_dates=re.findall(
        r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
        r"venerd[iì]|sabato|domenica)\s+\d{1,2}\s+"
        r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
        r"settembre|ottobre|novembre|dicembre)\s+20\d{2}",block)
    if (not rows or len(rows)>24 or len(rows)+school_dates!=len(declared_dates)
        or len(rows)!=len(set(rows))):
        raise ValueError("incomplete, duplicate or ambiguous Novara recite")
    return title,composer,venue,sorted(rows)
