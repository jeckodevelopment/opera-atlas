"""Conservative showtime parsing for official Scala/Arena opera detail pages.

Do not parse range summaries, cancelled/replaced dates or cast mentions as
performances. A changed website layout must fail closed, not invent recite.
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
MONTHS_RE="|".join(MONTHS)
DATE=re.compile(r"(?i)\b(\d{1,2})\s+("+MONTHS_RE+r")\s+(20\d{2})\b")
CLOCK=re.compile(r"(?i)\bore\s+(\d{1,2}):(\d{2})\b")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines=[]
        self.buffer=[]
        self.skip=0
    def flush(self):
        text=" ".join(" ".join(self.buffer).split())
        if text: self.lines.append(text)
        self.buffer=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"): self.skip+=1
        elif tag in ("p","li","div","br","h1","h2","h3","time"):
            if not self.skip:self.flush()
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"): self.skip=max(0,self.skip-1)
        elif tag in ("p","li","div","br","h1","h2","h3","time"):
            if not self.skip:self.flush()
    def handle_data(self,text):
        if not self.skip:self.buffer.append(text)


def parse_showtimes(html: str, *, url: str, title: str, composer: str,
                    adapter: str) -> list[tuple[str,str]]:
    host=urlsplit(url).hostname
    if adapter=="scala":
        if host!="www.teatroallascala.org" or "/opera/" not in urlsplit(url).path:
            raise ValueError("wrong official Scala production URL")
    elif adapter=="arena":
        if host!="www.arena.it" or "/arena-opera-festival/" not in urlsplit(url).path:
            raise ValueError("wrong official Arena production URL")
    else: raise ValueError("unsupported opera calendar")
    if urlsplit(url).scheme!="https" or not title or not composer:
        raise ValueError("verified opera metadata required")
    parser=_Text();parser.feed(html);parser.flush()
    text=" ".join(parser.lines)
    if title.casefold() not in text.casefold() or composer.casefold() not in text.casefold():
        raise ValueError("opera or composer not found in official page")
    if adapter=="scala":
        # The public HTML does not always include the visual "Date" heading
        # or the sponsor label: do not depend on either. Full day/month/year
        # directly followed by "Ore HH:MM" is the evidence. Cast snippets
        # without an adjacent clock cannot become performances.
        segment=text
    else:
        anchors=list(re.finditer("Prossimi spettacoli",text))
        start=anchors[-1].end() if anchors else -1
        if start<0: raise ValueError("Arena dated schedule missing")
        segment=text[start:]
    dates=list(DATE.finditer(segment))
    if not dates:raise ValueError("no individual performance dates")
    results={}
    for i,match in enumerate(dates):
        following=segment[match.end():dates[i+1].start() if i+1<len(dates) else len(segment)]
        # In Arena cards a second mention of the date may occur inside cast
        # metadata. Only an immediate "ore HH:MM" counts as the showtime.
        strict=CLOCK.match(following.lstrip())
        if strict is None:
            continue
        hours=[strict.groups()]
        if len(hours)!=1:raise ValueError("ambiguous or missing exact performance time")
        day=date(int(match.group(3)),MONTHS[match.group(2).lower()],int(match.group(1))).isoformat()
        hour,minute=map(int,hours[0])
        if not(0<=hour<=23 and 0<=minute<=59): raise ValueError("invalid performance time")
        if day in results: raise ValueError("duplicate official performance day")
        results[day]=f"{hour:02}:{minute:02}"
    if not results: raise ValueError("no complete date/time pairs")
    return sorted(results.items())
