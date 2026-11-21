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

def explicit_cancelled_dates(text:str)->set[str]:
    """Read explicit Italian cancellation notices without inferring a date.

    Unknown or ambiguous notice dates invalidate the page; an official
    cancellation must never be silently published as an active performance.
    """
    cue=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b|non\s+(?:avrà|avra)\s+luogo|non\s+si\s+terrà")
    day_rx=re.compile(r"(?i)\b(\d{1,2})\s+("+MONTH_RE+r")\s+(20\d{2})\b")
    cancelled=set()
    for match in cue.finditer(text):
        before=re.split(r"[.;!?]",text[max(0,match.start()-160):match.start()])[-1]
        after=re.split(r"[.;!?]",text[match.end():match.end()+160])[0]
        candidates=list(day_rx.finditer(before))
        if not candidates:
            candidates=list(day_rx.finditer(after))
        if len(candidates)!=1:
            raise ValueError("ambiguous official cancellation date")
        found=candidates[0]
        cancelled.add(_date(found[1],found[2],found[3]))
    return cancelled

def fenice_primary_credits(html:str)->tuple[str,str,str]:
    """Read work, composer and actual performance theatre from one primary block.

    La Fenice's season also uses Teatro Malibran; never silently replace that
    venue with the main theatre or use other events in the footer as evidence.
    """
    from scripts.collect_candidate_details import FirstHeading
    heading=FirstHeading()
    heading.feed(html)
    title=heading.first
    text=clean(html)
    marker=text.find("Seleziona una data")
    if not title or marker<0:
        raise ValueError("missing Fenice work heading or ticket schedule")
    start=text.casefold().rfind(title.casefold(),0,marker)
    if start<0:
        raise ValueError("Fenice title absent from primary work section")
    section=text[start+len(title):marker]
    found=re.search(r"\bTeatro (?:La Fenice|Malibran)\b",section)
    if not found:
        raise ValueError("no official Fenice performance venue")
    composer=section[:found.start()].strip()
    if (not re.fullmatch(r"[A-ZÀ-Ž][A-Za-zÀ-ÿ'’.-]+"
                         r"(?:\s+[A-ZÀ-Ž][A-Za-zÀ-ÿ'’.-]+){1,5}",composer)
        or len(composer)>100):
        raise ValueError("no unique primary composer credit at Fenice")
    return title,composer,found.group(0)


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
        cancelled=explicit_cancelled_dates(text)
        for m in rx.finditer(segment):
            day=_date(m[1],m[2],m[3])
            trailing=segment[m.end():m.end()+50]
            if (day in cancelled or CANCELLED.search(trailing)
                or re.search(r"(?i)\bRISERVAT[OAIE]\s+ALLE?\s+SCUOLE\b",trailing)):
                continue
            _insert(dates,day,f"{int(m[4]):02d}:{m[5]}")
    elif source_key=="parma-opera-2027":
        # The page includes a dated header and detailed day/time cards.
        # A full date in the header independently establishes the year.
        header=text.split("Musica",1)[0]
        year_hits={int(y) for y in re.findall(
            r"\b\d{1,2}\s+(?:"+MONTH_RE+r")\s+(20\d{2})\b",header,re.I)}
        if len(year_hits)!=1:raise ValueError("Parma year ambiguous")
        year=next(iter(year_hits))
        # Parma places an anchor navigation ("Spettacolo / Cast /
        # Informazioni") BEFORE the actual date cards. Splitting at "Cast"
        # truncated every live showtime. Start after the opera's composer
        # section and end at the ticket-information paragraph instead.
        detail=re.split(r"(?i)\bMusica\s+"+re.escape(composer)+r"\b",text,maxsplit=1)
        if len(detail)!=2:
            raise ValueError("missing Parma composer section")
        segment=re.split(r"(?i)\bTickets for\b",detail[1],maxsplit=1)[0]
        rx=re.compile(r"(?i)\b"+WEEKDAY+r"\s+(\d{1,2})\s+("+MONTH_RE+
                      r")\s+"+CLOCK+r"\b")
        matches=list(rx.finditer(segment))
        for i,m in enumerate(matches):
            following=segment[m.end():matches[i+1].start() if i+1<len(matches) else len(segment)]
            if CANCELLED.search(following):raise ValueError("changed Parma schedule")
            if REHEARSAL.search(following[:100]):continue
            _insert(dates,_date(m[1],m[2],year),f"{int(m[3]):02d}:{m[4]}")
    else:
        # Ticket cards omit the year. The official description supplies
        # full dates, sometimes crossing two months (e.g. Ernani: October
        # and November 2027); all cards must match the dated summary.
        summary=re.search(
            r"(?i)\bLo spettacolo\b\s*"
            r"(?P<calendar>(?:\d{1,2}(?:\s*,\s*\d{1,2})*\s+"+
            MONTH_RE+r"\s*,?\s*){1,3})"
            r"(?P<year>20\d{2})\s*\|",text)
        if not summary:raise ValueError("dated Palermo summary missing")
        year=summary["year"]
        groups=list(re.finditer(r"(?i)(\d{1,2}(?:\s*,\s*\d{1,2})*)\s+("+
                                MONTH_RE+r")",summary["calendar"]))
        if not groups or len(groups)>3:
            raise ValueError("ambiguous Palermo summary")
        months=[MONTHS[group[2].casefold()] for group in groups]
        if months!=sorted(months):
            # December-to-January needs an independently stated year per
            # month; do not assume both months belong to the same year.
            raise ValueError("Palermo summary crosses a year boundary")
        expected=set()
        for group in groups:
            for day in re.findall(r"\d{1,2}",group[1]):
                expected.add(_date(day,group[2],year))
        # A navigation anchor may also say "Lo spettacolo" *before* the
        # ticket calendar. Split at the validated date-summary position,
        # not at the first occurrence of that navigation label.
        segment=text[:summary.start()]
        rx=re.compile(r"(?i)\b(\d{1,2})\s+("+MONTH_RE+r")\s+"+CLOCK+r"\b")
        for m in rx.finditer(segment):
            day=_date(m[1],m[2],year)
            if day not in expected:
                continue
            _insert(dates,day,f"{int(m[3]):02d}:{m[4]}")
        if set(dates)!=expected:
            raise ValueError("Palermo cards incomplete versus dated summary")
    if not dates:raise ValueError("no verified official opera recite")
    return sorted(dates.items())
