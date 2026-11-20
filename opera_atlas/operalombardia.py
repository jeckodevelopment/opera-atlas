"""OperaLombardia production evidence: stage dates, never fabricate showtimes.

The official 2026/27 production articles may show lines such as:
"Teatro Sociale, Como – 13 e 15 novembre 2026".
These are exact calendar days, not start times; they must not become
canonical performances until an authorized source confirms hour and venue.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

MONTHS = {
    "gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
    "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
    "novembre":11,"dicembre":12,
}
LINE = re.compile(
    r"(?P<venue>Teatro[^\n–—]+?)\s*[,，]\s*(?P<city>[A-Za-zÀ-ÿ ]+?)\s*[–—-]\s*"
    r"(?P<dates>\d{1,2}(?:\s*(?:e|,|/)\s*\d{1,2})*)\s+"
    r"(?P<month>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+(?P<year>20\d{2})(?=$|\s|[.;])", re.I
)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines=[]
        self.current=""
        self.depth=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):
            self.depth+=1
        elif tag in ("p","li","div","br"):
            self.flush()
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.depth:
            self.depth-=1
        elif tag in ("p","li","div","h1","h2","br"):
            self.flush()
    def handle_data(self,data):
        if not self.depth:
            self.current += data
    def flush(self):
        value=" ".join(self.current.split())
        if value:
            self.lines.append(value)
        self.current=""


@dataclass(frozen=True)
class StagedDate:
    work_title: str
    venue_name: str
    city: str
    local_date: str
    production_url: str


def parse_dates_only(html: str, *, url: str, title: str) -> list[StagedDate]:
    """Parse only explicit recital lines, with no inferred times or venues."""
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname!="www.operalombardia.it" or p.username or p.password:
        raise ValueError("expected official OperaLombardia HTTPS URL")
    if not title.strip():
        raise ValueError("verified work title required")
    parser=_Text()
    parser.feed(html)
    parser.flush()
    if not any(title.casefold() in line.casefold() for line in parser.lines):
        raise ValueError("verified production title missing from snapshot")
    if not any(line.strip().upper().startswith("RECITE:") for line in parser.lines):
        raise ValueError("no explicit RECITE section")
    # Extract ONLY lines after the heading, up to the first non-recital line.
    started=False
    result={}
    for line in parser.lines:
        if line.strip().upper().startswith("RECITE:"):
            started=True
            continue
        if not started:
            continue
        match=LINE.fullmatch(line)
        if not match:
            if result:
                break
            continue
        y=int(match["year"])
        m=MONTHS[match["month"].casefold()]
        for raw_day in re.findall(r"\d{1,2}",match["dates"]):
            value=date(y,m,int(raw_day)).isoformat()
            obj=StagedDate(title.strip(),match["venue"].strip(),
                           match["city"].strip(),value,url)
            result[(obj.venue_name,obj.city,obj.local_date)]=obj
    return list(result.values())


def stage_dates(
    conn: sqlite3.Connection, *, source_id: int,
    html: str, url: str, title: str,
) -> int:
    """Upsert a date-only evidence snapshot; never write performances."""
    source=conn.execute(
        "SELECT official_url,access_status FROM sources WHERE id=?",(source_id,)
    ).fetchone()
    if (source is None or source["access_status"]!="approved"
        or source["official_url"].rstrip("/")!="https://www.operalombardia.it"):
        raise ValueError("OperaLombardia source must be explicitly approved")
    rows=parse_dates_only(html,url=url,title=title)
    if not rows:
        raise ValueError("no complete recital dates found; manual review required")
    fingerprint=hashlib.sha256(html.encode("utf-8")).hexdigest()
    for item in rows:
        conn.execute(
            """INSERT INTO staged_recite
               (source_id,production_url,work_title,venue_name,city,local_date,evidence_fingerprint)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(source_id,production_url,work_title,venue_name,city,local_date)
               DO UPDATE SET last_seen_at=CURRENT_TIMESTAMP,
                 evidence_fingerprint=excluded.evidence_fingerprint""",
            (source_id,item.production_url,item.work_title,item.venue_name,
             item.city,item.local_date,fingerprint),
        )
    return len(rows)
