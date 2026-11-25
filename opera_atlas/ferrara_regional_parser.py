"""Ferrara public opera 2026/27 from two independent official sources.

The regional government season page confirms each production and its Ferrara
date span. The theatre-issued season PDF corroborates composer and exact
recital hours. No theatre anti-bot challenge is accessed or bypassed.
"""
from __future__ import annotations
import json
import re
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data/ferrara-opera-2026-27.json"
HOST="spettacolo.emiliaromagnacultura.it"
INDEX="/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"
VENUE="Teatro Comunale Claudio Abbado"
SOURCE_PREFIX="ferrara-"


def fold(value:str)->str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD",value.casefold())
                           if not unicodedata.combining(c)).replace("’","'").split())


class RegionalProgram(HTMLParser):
    """Keep the text within each h3 production, not the site's nav/footer."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_h3=False
        self.title_parts=[]
        self.current=None
        self.sections={}
        self.acc=[]
        self.stack=[]
        self.blocked=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","nav","footer"):
            self.blocked+=1
        if self.blocked:return
        if tag=="h3":
            self._commit()
            self.in_h3=True
            self.title_parts=[]
        if tag in ("li","p","h3","div"):
            self.acc.append(" ")
    def handle_data(self,data):
        if self.blocked:return
        if self.in_h3:
            self.title_parts.append(data)
        if self.current:
            self.acc.append(data)
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","nav","footer"):
            self.blocked=max(0,self.blocked-1)
        if self.blocked:return
        if tag=="h3":
            self.in_h3=False
            title=" ".join(" ".join(self.title_parts).split())
            if title:
                self.current=title
                self.acc=[]
        if tag in ("li","p","h3","div"):
            self.acc.append(" ")
    def _commit(self):
        if self.current:
            self.sections[self.current]=" ".join(" ".join(self.acc).split())
            self.current=None
            self.acc=[]
    def close(self):
        super().close()
        self._commit()


def records():
    source=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if (source.get("schema_version")!=1 or
        source.get("source")!="https://cartellone.emiliaromagnacultura.it/wp-content/uploads/2026/09/Depliant_Opera_Danza_2026.pdf" or
        source.get("regional_index")!="https://"+HOST+INDEX or
        source.get("season")!="2026-2027"):
        raise ValueError("invalid official Ferrara evidence registry")
    entries=source.get("works",[])
    keys=[x.get("key") for x in entries]
    if len(entries)!=5 or len(set(keys))!=5:
        raise ValueError("incomplete or duplicate five-opera reference")
    return {x["key"]:x for x in entries}


def production(html:str,*,source_key:str,url:str):
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!=HOST or parsed.path!=INDEX or
        parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port is not None):
        raise ValueError("Ferrara source outside approved regional season")
    source=records().get(source_key)
    if source is None:
        raise ValueError("unknown exact Ferrara opera candidate")
    if "TEATRO COMUNALE FERRARA" not in html.upper():
        raise ValueError("official Ferrara regional season heading missing")
    regional=RegionalProgram()
    regional.feed(html)
    regional.close()
    # The h3 may include a composer suffix in the title (MACBETH - Giuseppe Verdi).
    expected=fold(source["title"])
    matching=[(heading,body) for heading,body in regional.sections.items()
              if fold(heading)==expected or
              fold(heading)==expected+" - "+fold(source["composer"])]
    if len(matching)!=1:
        raise ValueError("official region does not uniquely corroborate work")
    body=fold(matching[0][1])
    if "teatro comunale di ferrara" not in body or "ferrara" not in body:
        raise ValueError("no work-specific Ferrara venue")
    # Require the *exact* regional start/end dates, not just a broad season
    # window. Times come only from the theatre's independent brochure.
    for span in source["span"]:
        if fold(span) not in body:
            raise ValueError("regional performance date disagrees with official brochure")
    entries=[]
    for day,hour in source["dates"]:
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",day):
            raise ValueError("untrusted official Ferrara date")
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",hour):
            raise ValueError("untrusted official Ferrara time")
        date.fromisoformat(day)
        if not ("2026-11-01"<=day<="2027-05-31"):
            raise ValueError("Ferrara date outside published season")
        entries.append((day,hour))
    if len(entries)!=len(set(d for d,_ in entries)) or not entries or len(entries)>8:
        raise ValueError("missing or duplicate Ferrara recital")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",body):
        raise ValueError("official cancellation or postponement")
    return source["title"],source["composer"],VENUE,sorted(entries)


def verified_index_candidate(html:str,*,source_key:str,url:str)->bool:
    """Discover one real opera from an approved source; fail closed."""
    production(html,source_key=source_key,url=url)
    return True


TOURISM_ORIGIN = "https://www.ferrarainfo.com/"
TOURISM_URL = TOURISM_ORIGIN + "it/vivi-gli-eventi/tutti-gli-eventi/musica-teatro-danza/stagione-opera-danza"

def verify_tourism_calendar(html: str, *, url: str, source_key: str) -> None:
    """Corroborate exact existing dates from an independent institutional page."""
    if url != TOURISM_URL:
        raise ValueError("unapproved Ferrara tourism source")
    from opera_atlas.national_detail_parser import clean
    body = fold(clean(html))
    if not (re.search(r"stagione opera\s*(?:&|e)\s*danza", body)
            and "teatro comunale" in body and "ferrara" in body
            and "2026" in body and "2027" in body):
        raise ValueError("Ferrara tourism season or venue unverified")
    source = records().get(source_key)
    if source is None:
        raise ValueError("unknown Ferrara tourism work")
    months = {11:"novembre", 1:"gennaio", 2:"febbraio", 3:"marzo", 4:"aprile"}
    dates = []
    for day, clock in source["dates"]:
        d = date.fromisoformat(day)
        dates.append(r"\b0?"+str(d.day)+r"\s+"+months[d.month]+r"(?:\s+"+str(d.year)+r")?,?\s+ore\s+"+clock.replace(":",r"[.:]")+r"\b")
    title = fold(source["title"])
    title_pattern = r"dido\s*(?:&|and)\s*(?:aeneas|æneas)" if title=="dido and aeneas" else re.escape(title)
    pattern = r"[\s,;–-]+".join(dates)+r"[\s,;–-]+"+title_pattern+r"\s+musica di\s+"+re.escape(fold(source["composer"]))+r"\b"
    if len(re.findall(pattern, body)) != 1:
        raise ValueError("Ferrara tourism work, composer or recite conflict")
    if re.search(r"\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b", body):
        raise ValueError("Ferrara tourism cancellation requires review")
