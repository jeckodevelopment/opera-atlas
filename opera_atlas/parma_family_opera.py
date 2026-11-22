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
ROW=re.compile(
    r"(?i)\b(lun|mar|mer|gio|ven|sab|dom)\s+([0-3]?\d)\s+"
    r"(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s+"
    r"([01]?\d|2[0-3]):([0-5]\d)\s+(Scuole|Famiglie)\b")
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
    text=clean(html)
    at=text.find(TITLE)
    if at<0:raise ValueError("Parma work heading absent")
    intro=text[at:at+220]
    years=set(re.findall(r"\b(?:[0-3]?\d)\s+(?:"
        + "|".join(MONTHS)+r")\s+(20\d{2})\b",intro,re.I))
    if len(years)!=1:raise ValueError("ambiguous official Parma season year")
    year=int(next(iter(years)))
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
    schedule=schedule.split("Informazioni",1)[0]
    matches=list(ROW.finditer(schedule))
    if not matches or len(matches)>24:
        raise ValueError("missing complete official Parma ticket schedule")
    # Every labelled audience row inside the scoped box must be accounted
    # for; introductory references to school ticket collection do not count.
    labels=re.findall(r"\b(?:Scuole|Famiglie)\b",schedule,re.I)
    if len(labels)!=len(matches):
        raise ValueError("unrecognized Parma audience-specific ticket row")
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
