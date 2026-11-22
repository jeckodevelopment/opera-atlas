"""Strict Opera Giocosa homepage evidence for Savona, never an organizer-as-venue.

The official evergreen homepage carries multiple seasons and genres. Findings
remain evidence for the central reconciler; this module publishes nothing.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

URL = "https://operagiocosa.it/"
VENUE = "Teatro Chiabrera"
MONTHS = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
          "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
          "novembre":11,"dicembre":12}
SEASON = re.compile(r"Stagione lirica (autunnale|estiva) (20\d{2})",re.I)
DATE = re.compile(
    r"(?<!\d)([0-3]?\d)\s+"
    r"(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|"
    r"Settembre|Ottobre|Novembre|Dicembre)\s*[-–]?\s*"
    r"ore\s*([01]?\d|2[0-3])[:.]([0-5]\d)",re.I)

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.suppressed=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.suppressed+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):
            self.suppressed=max(0,self.suppressed-1)
    def handle_data(self,data):
        if not self.suppressed:
            value=" ".join(data.split())
            if value:self.parts.append(value)

def parse_homepage(html:str,*,url:str=URL)->list[dict]:
    """Only exact official Opera cards with verified Chiabrera venue and clocks.

    The website may have summer shows at Priàmar, concerts or other venues.
    Year comes from the *same* season block, never from execution date.
    """
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname not in
        ("operagiocosa.it","www.operagiocosa.it")
        or parsed.path not in ("","/") or parsed.query or parsed.fragment
        or parsed.username or parsed.password or parsed.port is not None):
        raise ValueError("unapproved Opera Giocosa programme URL")
    visible=Visible()
    visible.feed(html)
    text=" ".join(visible.parts)
    headings=list(SEASON.finditer(text))
    # The homepage repeats its section headings in responsive layouts.
    # Work on each independently bounded segment, deduplicating observations.
    found={}
    for i,heading in enumerate(headings):
        following=headings[i+1].start() if i+1<len(headings) else len(text)
        part=text[heading.end():following]
        year=int(heading.group(2))
        if heading.group(1).lower()=="autunnale":
            part=part.split("Stagione lirica estiva",1)[0]
        # A card starts with its explicit genre, so concerts cannot be
        # mistaken for operas by searching globally for an opera title.
        cards=re.split(r"(?<!\w)(Opera|Concerto)(?!\w)",part,flags=re.I)
        for j in range(1,len(cards)-1,2):
            if cards[j].casefold()!="opera":continue
            card=cards[j+1]
            if "Teatro Chiabrera Savona" not in " ".join(card.split()):
                continue
            # Require a bounded explicit place/name/composer statement.
            match=re.search(
                r"Teatro Chiabrera\s+Savona\s+(.{3,140}?)\s+di\s+"
                r"([\wÀ-ÿ.'’ -]{4,90}?)(?=\s+(?:Opera|Concerto|Eventi|"
                r"Stagione|Teatro|\d{1,2}\s+\w+\s*[-–]?\s*ore)|$)",
                card,re.I)
            if not match:continue
            title,composer=(" ".join(x.split()) for x in match.groups())
            # Only the date area BEFORE this same card's venue/title
            # belongs to its recite; exclude school/other event blocks.
            dates=[]
            for day,month,hour,minute in DATE.findall(card[:match.start()]):
                try:
                    iso=date(year,MONTHS[month.casefold()],int(day)).isoformat()
                except ValueError:
                    raise ValueError("invalid official Savona performance date")
                dates.append((iso,f"{int(hour):02d}:{minute}"))
            if not dates:continue
            ident=(title.casefold(),composer.casefold(),VENUE.casefold())
            for iso,clock in dates:
                key=(ident,iso)
                if key in found and found[key]["time"]!=clock:
                    raise ValueError("conflicting official Savona recita clocks")
                found[key]={"title":title,"composer":composer,
                            "venue":VENUE,"city":"Savona","date":iso,
                            "time":clock,"organizer":"Teatro dell'Opera Giocosa",
                            "source_url":url}
    return sorted(found.values(),key=lambda x:(x["date"],x["time"],x["title"]))
