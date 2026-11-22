"""First-party calendar of the 73rd Festival Puccini (2027).

Six productions are announced. Il trittico is one composite programme and is
left to the programme-composition reconciler; its two recite may NOT be
attributed independently to Il tabarro, Suor Angelica or Gianni Schicchi.
The five unambiguous operas are safe for canonical promotion.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean

KEY="puccini-torre-del-lago-2027"
URL="https://www.puccinifestival.it/en/73rd-puccini-festival-2027/"
VENUE="Gran Teatro Giacomo Puccini"
COMPOSER="Giacomo Puccini"
# Official 2027 six-production line-up, including the composite bill.
PROGRAM=(
    ("La rondine",2),
    ("Turandot",5),
    ("Tosca",4),
    ("Il Trittico",2),
    ("Madama Butterfly",3),
    ("La bohème",3),
)
MONTHS={"july":7,"august":8}
GROUP=re.compile(r"(?i)\s*(\d{1,2}(?:\s*(?:,|and)\s*\d{1,2})*)\s+"
                 r"(july|august)\s*")

def _parse_days(text:str,*,year:int)->list[str]:
    groups=re.split(r"\s*[·•]\s*",text.strip())
    if not 1<=len(groups)<=2:
        raise ValueError("unrecognized Puccini date group")
    days=[]
    for group in groups:
        m=GROUP.fullmatch(group)
        if m is None:
            raise ValueError("ambiguous month/date assignment on festival index")
        month=MONTHS[m[2].lower()]
        numbers=re.split(r"\s*(?:,|and)\s*",m[1])
        for number in numbers:
            day=date(year,month,int(number)).isoformat()
            if day in days:raise ValueError("duplicate Puccini festival date")
            days.append(day)
    return days

def parse_program(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.puccinifestival.it"
        or target.path.rstrip("/")!="/en/73rd-puccini-festival-2027"
        or target.query or target.fragment or target.username or target.password
        or target.port is not None):
        raise ValueError("unapproved Puccini official 2027 programme")
    body=clean(html)
    if not (re.search(r"(?i)\b73rd Puccini Festival\b",body)
        and re.search(r"(?i)\b2027 programme\b",body)
        and re.search(r"(?i)\bGiacomo Puccini Open-Air Theatre\b",body)
        and re.search(r"(?i)\bAll performances start at 9\.15 pm\b",body)):
        raise ValueError("Puccini programme/year/venue/clock unverified")
    start=re.search(r"(?i)\bThe operas\b",body)
    end=re.search(r"(?i)\bThe concerts\b",body)
    if start is None or end is None or end.start()<=start.end():
        raise ValueError("Puccini opera programme boundaries missing")
    panel=body[start.end():end.start()]
    heads=[]
    for title,count in PROGRAM:
        matches=list(re.finditer(r"(?i)(?<!\w)"+re.escape(title)+r"(?!\w)",panel))
        if len(matches)!=1:
            raise ValueError("missing or ambiguous Puccini production heading: "+title)
        heads.append((matches[0].start(),matches[0].end(),title,count))
    if heads!=sorted(heads):
        raise ValueError("Puccini programme ordering changed")
    result=[]
    for i,(begin,end,title,expected) in enumerate(heads):
        previous_end=heads[i-1][1] if i else 0
        date_area=panel[previous_end:begin].strip()
        # Programme cards contain a trailing "Explore the opera and cast"
        # from the preceding card, not part of the next calendar.
        date_area=re.split(r"(?i)Explore the opera and cast",date_area)[-1].strip()
        days=_parse_days(date_area,year=2027)
        if len(days)!=expected:
            raise ValueError("incomplete Puccini official opera dates: "+title)
        if title=="Il Trittico":
            # These are two composite-bill performances, never three
            # separately ticketed performances on each date.
            fragment=panel[end:heads[i+1][0] if i+1<len(heads) else len(panel)]
            if not all(re.search(r"(?i)\b"+re.escape(part)+r"\b",fragment)
                       for part in ("Il tabarro","Suor Angelica","Gianni Schicchi")):
                raise ValueError("Puccini composite programme identity changed")
            continue
        result.extend((title,COMPOSER,VENUE,day,"21:15") for day in days)
    if len(result)!=17:
        raise ValueError("partial first-party Puccini festival calendar")
    return result
