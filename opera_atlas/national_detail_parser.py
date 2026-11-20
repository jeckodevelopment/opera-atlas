"""Conservative exact-date adapters for three official Italian opera theatres.

Only titles/composers already established in the canonical work registry or
independently authoritative enrichment may be used. Never infer a date, year,
composer, or cancelled/rehearsal showtime.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

MONTHS = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
          "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12,
          "gen":1,"feb":2,"mar":3,"apr":4,"mag":5,"giu":6,"lug":7,"ago":8,
          "set":9,"sett":9,"ott":10,"nov":11,"dic":12}
MONTH_RE = "(?:"+"|".join(sorted(MONTHS,key=len,reverse=True))+")"
WEEKDAY = r"(?:lun(?:edì)?|mar(?:tedì)?|mer(?:coledì)?|gio(?:vedì)?|ven(?:erdì)?|sab(?:ato)?|dom(?:enica)?)"
CLOCK = r"([01]?\d|2[0-3]):([0-5]\d)"
CANCELLED = re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")
REHEARSAL = re.compile(r"(?i)\b(?:prova|prove|rehearsal|under\s?30)\b")

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
        if tag in ("div","p","li","h1","h2","h3","br","section","a","time") and not self.skip:
            self.parts.append(" ")
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.skip=max(0,self.skip-1)
        if tag in ("div","p","li","h1","h2","h3","br","section","a","time") and not self.skip:
            self.parts.append(" ")
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def clean(html):
    reader=VisibleText()
    reader.feed(html)
    return " ".join("".join(reader.parts).split())

HOSTS={"fenice-opera-2026-27":"www.teatrolafenice.it",
       "parma-opera-2027":"teatroregioparma.it",
       "massimo-season-2026-27":"www.teatromassimo.it"}

def _date(day,month,year):
    return date(int(year),MONTHS[month.casefold()],int(day)).isoformat()

def _match_identity(text,title,composer):
    if not title or not composer:
        raise ValueError("verified work title and composer required")
    if not re.search(re.escape(title),text,re.I):
        raise ValueError("official page does not confirm work title")
    if not re.search(re.escape(composer),text,re.I):
        raise ValueError("official page does not confirm composer")

def _insert(out,day,hour):
    if day in out and out[day]!=hour:
        raise ValueError("conflicting official showtime for one day")
    out[day]=hour

def parse_national_showtimes(html: str, *, source_key:str,url:str,
                            title:str,composer:str)->list[tuple[str,str]]:
    expected=HOSTS.get(source_key)
    parsed=urlsplit(url)
    if not expected or parsed.hostname!=expected or parsed.scheme!="https" or parsed.query or parsed.fragment:
        raise ValueError("unsupported official national opera detail URL")
    if source_key=="fenice-opera-2026-27" and not parsed.path.startswith("/event/"):
        raise ValueError("invalid Fenice detail path")
    if source_key=="parma-opera-2027" and not parsed.path.startswith("/spettacolo/"):
        raise ValueError("invalid Parma detail path")
    if source_key=="massimo-season-2026-27" and not parsed.path.startswith("/event/"):
        raise ValueError("invalid Palermo detail path")
    text=clean(html)
    _match_identity(text,title,composer)
    dates={}
    if source_key=="fenice-opera-2026-27":
        segment=re.split(r"(?i)\bI prossimi eventi\b",text,maxsplit=1)[0]
        if "Seleziona una data" not in segment:
            raise ValueError("Fenice ticket-date section absent")
        segment=segment.split("Seleziona una data",1)[1]
        rx=re.compile(r"(?i)\b"+WEEKDAY+r"\s+(\d{1,2})\s+("+MONTH_RE+
                      r")\s+(20\d{2})\s+"+CLOCK+r"\b")
        for m in rx.finditer(segment):
            trailing=segment[m.end():m.end()+50]
            if CANCELLED.search(trailing):raise ValueError("cancelled date in ticket calendar")
            _insert(dates,_date(m[1],m[2],m[3]),f"{int(m[4]):02d}:{m[5]}")
    elif source_key=="parma-opera-2027":
        # The page includes a dated header and detailed day/time cards.
        # A full date in the header independently establishes the year.
        header=text.split("Musica",1)[0]
        year_hits={int(y) for y in re.findall(
            r"\b\d{1,2}\s+(?:"+MONTH_RE+r")\s+(20\d{2})\b",header,re.I)}
        if len(year_hits)!=1:raise ValueError("Parma year ambiguous")
        year=next(iter(year_hits))
        # Restrict to the ticketing card list, excluding the footer.
        segment=re.split(r"(?i)\b(?:Tickets for|acquista 19|Cast)\b",text,maxsplit=1)[0]
        rx=re.compile(r"(?i)\b"+WEEKDAY+r"\s+(\d{1,2})\s+("+MONTH_RE+
                      r")\s+"+CLOCK+r"\b")
        matches=list(rx.finditer(segment))
        for i,m in enumerate(matches):
            following=segment[m.end():matches[i+1].start() if i+1<len(matches) else len(segment)]
            if CANCELLED.search(following):raise ValueError("changed Parma schedule")
            if REHEARSAL.search(following[:100]):continue
            _insert(dates,_date(m[1],m[2],year),f"{int(m[3]):02d}:{m[4]}")
    else:
        # Palermo's date cards omit the year; the same official page gives
        # a year-stamped summary of exactly those days in the show description.
        description=re.search(r"(?i)\b(\d{1,2}(?:\s*,\s*\d{1,2})+)\s+("+
                              MONTH_RE+r")\s+(20\d{2})\s*\|",text)
        if not description:raise ValueError("dated Palermo summary missing")
        days={int(d) for d in re.findall(r"\d{1,2}",description[1])}
        month,year=description[2],description[3]
        segment=re.split(r"(?i)\bLo spettacolo\b",text,maxsplit=1)[0]
        rx=re.compile(r"(?i)\b(\d{1,2})\s+("+MONTH_RE+r")\s+"+CLOCK+r"\b")
        for m in rx.finditer(segment):
            if int(m[1]) not in days or MONTHS[m[2].casefold()]!=MONTHS[month.casefold()]:
                continue
            _insert(dates,_date(m[1],m[2],year),f"{int(m[3]):02d}:{m[4]}")
        if {int(d.split("-")[-1]) for d in dates}!=days:
            raise ValueError("Palermo cards incomplete versus dated summary")
    if not dates:raise ValueError("no verified official opera recite")
    return sorted(dates.items())
