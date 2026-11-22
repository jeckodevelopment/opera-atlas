"""Source-verified family performances for Parma's contemporary children's opera.

The official event sells two separate audiences on each day (Scuole and
Famiglie). Only public family ticket rows are catalogued; never deduce public
times from the school schedule.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

URL="https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/"
TITLE="Piccolo Orso e la montagna di ghiaccio"
COMPOSER="Giovanni Sollima"
VENUE="Teatro Regio di Parma"
MONTHS={"gen":1,"feb":2,"mar":3,"apr":4,"mag":5,"giu":6,
        "lug":7,"ago":8,"set":9,"ott":10,"nov":11,"dic":12}
WEEKDAYS={"lun":0,"mar":1,"mer":2,"gio":3,"ven":4,"sab":5,"dom":6}
# The production's CMS may insert inline labels, punctuation and 'ore'
# between date, time and audience. These are *adjacent ticket fields*;
# the calendar block is scoped before the first external ticket link.
SEP=r"(?:[\s,.;:–-]{0,16})"
ROW=re.compile(
    r"(?i)\b(lun|mar|mer|gio|ven|sab|dom)"+SEP+
    r"([0-3]?\d)"+SEP+
    r"(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)"+SEP+
    r"(?:ore"+SEP+r")?([01]?\d|2[0-3]):([0-5]\d)"+SEP+
    r"(Scuole|Famiglie)\b")
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

def parse_family_opera(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    uri=urlsplit(url)
    if (url!=URL or uri.scheme!="https" or uri.hostname!="teatroregioparma.it"
        or uri.query or uri.fragment or uri.username or uri.password
        or uri.port is not None):
        raise ValueError("unapproved official Parma family-opera source")
    from scripts.collect_candidate_details import FirstHeading
    heading=FirstHeading()
    heading.feed(html)
    if heading.first!=TITLE:
        raise ValueError("Parma primary work heading mismatch")
    # The official ticket widget emits day, clock and audience in sibling
    # spans/list cells. The common HTML text reader preserves whitespace
    # for div/p/li but not span/b/small, otherwise concatenating
    # "ven 4 dic09:00Scuole" into one unparseable token.
    spaced=re.sub(r"(?i)</?(?:span|small|strong|b|em|ul|ol|button|label|time|h[1-6])\b[^>]*>",
                  " ",html)
    text=clean(spaced)
    at=text.find(TITLE)
    if at<0:raise ValueError("Parma work heading absent")
    # The site renders its heading dates as separate day/month/year nodes.
    # Take only the dates before the first 'Spettacolo' content heading:
    # later school ticket notices may mention a different year entirely.
    intro_end=re.search(r"(?i)\bSpettacolo\b",text[at+len(TITLE):])
    if not intro_end:
        raise ValueError("missing Parma header date boundary")
    intro=text[at+len(TITLE):at+len(TITLE)+intro_end.start()]
    header_dates=re.findall(r"\b([0-3]?\d)\s+("
        + "|".join(MONTHS)+r")\s+(20\d{2})\b",intro,re.I)
    if not 1<=len(header_dates)<=12:
        raise ValueError("missing official Parma header calendar")
    years={int(year) for _,_,year in header_dates}
    if len(years)!=1:
        raise ValueError("ambiguous official Parma season year")
    year=next(iter(years))
    # The author and librettist are credited as separate labels in the
    # official 'Spettacolo' section. Never confuse the librettist with author.
    if not re.search(r"(?i)\bmusica\s+Giovanni Sollima\s+libretto\b",text):
        raise ValueError("official Parma opera composer missing")
    if VENUE not in text[at:]:
        raise ValueError("official Parma venue missing")
    section=text[at:]
    if CANCEL.search(section[:1800]):
        raise ValueError("cancelled Parma family event requires review")
    schedule=section[section.index(VENUE)+len(VENUE):]
    # Only the audience-tagged ticket calendar, not the following
    # "kit dello spettatore famiglie" or footer, contributes audience tags.
    schedule=re.split(r"(?i)\b(?:ticket|agevolazioni|kit\s+dello\s+spettatore|informazioni)\b",
                      schedule,maxsplit=1)[0]
    matches=list(ROW.finditer(schedule))
    if not matches or len(matches)>24:
        raise ValueError("missing complete official Parma ticket schedule")
    # This source-specific December 2026 opera advertises four labelled
    # ticket slots. A partial card is not a verified complete programme.
    allowed={
        (4,"dic","09:00","scuole"),
        (4,"dic","11:00","scuole"),
        (5,"dic","15:00","famiglie"),
        (5,"dic","18:00","famiglie"),
    }
    observed={(int(m[2]),m[3].lower(),f"{int(m[4]):02d}:{m[5]}",m[6].lower())
              for m in matches}
    if year!=2026 or observed!=allowed or len(matches)!=len(allowed):
        raise ValueError("Parma official school and family ticket slots incomplete")
    # Every labelled audience row inside the scoped box must be accounted
    # for; introductory references to school ticket collection do not count.
    labels=re.findall(r"\b(?:Scuole|Famiglie)\b",schedule,re.I)
    if len(labels)!=len(matches):
        raise ValueError("unrecognized Parma audience-specific ticket row")
    clocks=re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b",schedule)
    if len(clocks)!=len(matches):
        raise ValueError("unbound official Parma ticket hour")
    rows=[]
    for m in matches:
        weekday,day,month,hour,minute,audience=m.groups()
        dt=date(year,MONTHS[month.lower()],int(day))
        if dt.weekday()!=WEEKDAYS[weekday.lower()]:
            raise ValueError("Parma source weekday inconsistent with year")
        if audience.lower()=="famiglie":
            row=(dt.isoformat(),f"{int(hour):02d}:{minute}")
            if row in rows:
                raise ValueError("duplicate Parma public ticket")
            rows.append(row)
    if not rows:raise ValueError("only school-only Parma tickets")
    return TITLE,COMPOSER,VENUE,sorted(rows)
