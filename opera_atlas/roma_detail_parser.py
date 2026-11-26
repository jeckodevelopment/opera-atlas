"""Fail-closed exact opera dates from the official Teatro Costanzi detail page."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from html.parser import HTMLParser

from opera_atlas.national_detail_parser import clean
from scripts.publish_catalog_v2 import normalized

MONTHS={"gen":1,"feb":2,"mar":3,"apr":4,"mag":5,"giu":6,
        "lug":7,"ago":8,"set":9,"ott":10,"nov":11,"dic":12}
DAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,
      "venerdì":4,"sabato":5,"domenica":6}
PERFORMANCE=re.compile(
    r"\b(lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)"
    r"\s+([0-3]?\d)\s+(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)"
    r"\s+ORE\s+([01]?\d|2[0-3]):([0-5]\d)\b",re.I)
CANCELLED=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")

# Explicit first-party historic production pages confirmed in the 2025/26
# programme and summer 2026 programme. Other seasons remain fail-closed.
HISTORICAL_SLUGS=frozenset({
    "tosca-11","lohengrin","la-boheme-4","inferno","ariadne-auf-naxos",
    "il-trionfo-del-tempo-e-del-disinganno","romeo-et-juliette","tancredi",
    "la-traviata-12","le-nozze-di-figaro-2","falstaff","aida-6",
})
HISTORICAL_URLS=frozenset(
    f"https://www.operaroma.it/spettacoli/{slug}/" for slug in HISTORICAL_SLUGS)

def expected_season(url:str)->tuple[int,int]:
    return (2025,2026) if url in HISTORICAL_URLS else (2026,2027)

def season_pattern(url:str)->str:
    a,b=expected_season(url)
    return rf"\bStagione\s+{a}\s*/\s*{b}\b"

class Heading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.collect=False
        self.parts=[]
        self.title=None
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.title is None:
            self.collect=True
    def handle_data(self,data):
        if self.collect:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.collect:
            self.title=" ".join("".join(self.parts).split())
            self.collect=False

def parse_roma_detail(html:str,*,url:str,title:str,composer:str)->tuple[str,list[tuple[str,str]]]:
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.operaroma.it"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment
        or not re.fullmatch(r"/spettacoli/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Rome theatre detail")
    heading=Heading()
    heading.feed(html)
    if normalized(heading.title or "").replace("’","'") != normalized(title).replace("’","'"):
        raise ValueError("official Rome heading does not match canonical work")
    visible=clean(html)
    pos=visible.find("Le date")
    if pos<0:
        raise ValueError("official Rome performance schedule missing")
    context=visible[:pos]
    if not re.search(season_pattern(url),context,re.I):
        raise ValueError("Rome event not in verified source season")
    credit=r"\bMusica\s+(?:di\s+)?" if url.endswith("/aida-6/") else r"\bMusica\s+di\s+"
    if not re.search(credit+re.escape(composer)+r"\b",
                     context.replace("’","'"),re.I):
        raise ValueError("composer absent from official Rome production")
    # Read the actual auditorium declared under first-party "Dove"; never
    # substitute the Teatro Costanzi for another approved Rome venue.
    official_venues={"Teatro Costanzi":"Teatro dell'Opera di Roma",
                     "Teatro Valle Franca Valeri":"Teatro Valle Franca Valeri",
                     "Teatro Nazionale":"Teatro Nazionale"}
    if url.endswith("/aida-6/"):
        official_venues["Circo Massimo"]="Circo Massimo"
    venues=re.findall(
        r"\bDove\s+("+ "|".join(map(re.escape,official_venues))+r")\b",context)
    if len(venues)!=1:
        raise ValueError("actual Rome auditorium not confirmed")
    venue=official_venues[venues[0]]
    # Stop before preview performances, recommendations and school activities.
    section=visible[pos+len("Le date"):]
    for stop in ("Anteprima giovani","Ti può interessare anche",
                 "Altri eventi","Potrebbe interessarti"):
        idx=section.find(stop)
        if idx>=0:section=section[:idx]
    if CANCELLED.search(section):
        raise ValueError("cancelled or postponed Rome performance")
    found={}
    for weekday,day,month,hh,mm in PERFORMANCE.findall(section):
        month_number=MONTHS[month.casefold()]
        # A 2026/27 official season also contains productions in Sep-Dec
        # 2027. Choose the uniquely matching calendar year from the theatre's
        # explicit weekday; never assume autumn performances are always 2026.
        possible=[]
        first_year,last_year=expected_season(url)
        for year in ((first_year,last_year) if month_number>=9 else (last_year,)):
            try:
                candidate=date(year,month_number,int(day))
            except ValueError:
                continue
            if candidate.weekday()==DAYS[weekday.casefold()]:
                possible.append(candidate)
        if len(possible)!=1:
            raise ValueError("Rome event weekday or calendar year ambiguous")
        actual=possible[0]
        iso=actual.isoformat()
        clock=f"{int(hh):02d}:{mm}"
        if iso in found and found[iso]!=clock:
            raise ValueError("conflicting Rome performance time")
        found[iso]=clock
    if not found:
        raise ValueError("no dated and timed Rome performances")
    return venue, sorted(found.items())


class OfficialCredits(HTMLParser):
    """Read block-delimited official composer text, never infer from slug/cast."""
    BLOCKS={"p","div","section","h1","h2","h3","h4","li"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines=[]
        self.line=[]
    def handle_starttag(self,tag,attrs):
        if tag in self.BLOCKS:self._flush()
    def handle_endtag(self,tag):
        if tag in self.BLOCKS:self._flush()
    def handle_data(self,data):
        self.line.append(data)
    def _flush(self):
        value=" ".join("".join(self.line).split())
        if value:self.lines.append(value)
        self.line=[]
    def close(self):
        super().close()
        self._flush()



def official_rome_other_season(html:str,*,url:str)->str|None:
    """Return a conflicting *source-declared* season, not an inferred date.

    The Opera di Roma's genre index mixes multiple seasons. An event
    explicitly labelled 2025/2026 must not consume editorial attempts for
    the 2026/2027 source. Only a verified official page, h1 and season label
    in its own introduction count; recommendations after the work do not.
    """
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.operaroma.it"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment
        or not re.fullmatch(r"/spettacoli/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Rome event URL")
    heading=Heading()
    heading.feed(html)
    if not heading.title:
        return None
    class OfficialIntro(HTMLParser):
        """Read only the production's season label immediately before its H1.

        The theatre sometimes renders this label inside a link or inline
        element, unlike its navigation. Excluding every anchor silently lost
        legitimate season evidence. A navigation/footer label never counts.
        """
        BLOCKED={"nav","footer","script","style","head"}
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.blocked=[]
            self.parts=[]
            self.before_h1=True
        def handle_starttag(self,tag,attrs):
            if tag=="h1":
                self.before_h1=False
            if tag in self.BLOCKED:
                self.blocked.append(tag)
        def handle_endtag(self,tag):
            if tag in self.BLOCKED and tag in self.blocked:
                self.blocked.remove(tag)
        def handle_data(self,data):
            value=" ".join(data.split())
            if self.before_h1 and not self.blocked and value:
                self.parts.append(value)
    intro=OfficialIntro()
    intro.feed(html)
    # No season may be borrowed from another production, menu or footer.
    # The official season must be the last visible textual item before H1.
    # A split label (e.g. <span>Stagione</span><a>2025/2026</a>)
    # is accepted only when adjacent in this introduction.
    preface=" ".join(intro.parts[-2:])
    observed=re.findall(r"\bStagione\s+(20\d{2})\s*/\s*(20\d{2})\s*$",
                        preface,re.I)
    if not observed:
        return None
    a,b=map(int,observed[-1])
    if b!=a+1:
        return None
    season=f"{a}/{b}"
    return season if season!="/".join(map(str,expected_season(url))) else None


def parse_roma_credited_detail(html:str,*,url:str)->tuple[str,str,str,list[tuple[str,str]]]:
    """Require exact season, official h1, adjacent author credit and timed shows.

    Credited works not yet in the canonical registry enter the same centralized
    authority/editorial pipeline as all other theatres. This is factual evidence,
    not an autonomous grant of a canonical work ID.
    """
    heading=Heading()
    heading.feed(html)
    title=heading.title
    if not title or not 3<=len(title)<=160:
        raise ValueError("official Rome opera title absent")
    reader=OfficialCredits()
    reader.feed(html)
    reader.close()
    lines=reader.lines
    first_date=next((i for i,x in enumerate(lines) if x=="Le date"),len(lines))
    intro=lines[:first_date]
    if not any(re.search(season_pattern(url),line,re.I)
               for line in intro):
        raise ValueError("Rome event not in verified source season")
    title_ix=next((i for i,x in enumerate(intro)
                   if normalized(x)==normalized(title)),None)
    if title_ix is None:
        raise ValueError("official Rome title not in source heading")
    credits=[]
    for index,line in enumerate(intro[title_ix+1:],start=title_ix+1):
        credit_pattern=(r"Musica\s+(?:di\s+)?(.{4,100})"
                        if url.endswith("/aida-6/") else r"Musica\s+di\s+(.{4,100})")
        m=re.fullmatch(credit_pattern,line,re.I)
        if m:
            credits.append(m[1].strip())
        elif re.fullmatch(r"Musica\s+di",line,re.I) and index+1<len(intro):
            # Some official layouts put the independently credited author
            # in the immediately following block. Only the exact standalone
            # "Musica di" label licenses this; never infer a conductor.
            credits.append(intro[index+1].strip())
    # Names in the approved first-party credits can contain letters outside
    # Latin-1 (e.g. Šostakovič). Match Unicode letters, not an arbitrary
    # historical European character interval. Disallow digits, role labels,
    # symbols and single-word attributions; never infer a composer from slug.
    def credible_person_name(value:str)->bool:
        if not 4<=len(value)<=100:return False
        if not all(char.isalpha() or char in " .-'’" for char in value):
            return False
        tokens=[token for token in re.split(r"[ .'’-]+",value) if token]
        return (len(tokens)>=2 and all(any(ch.isalpha() for ch in token)
                                      for token in tokens)
                and tokens[0].casefold() not in {
                    "direttore","regia","maestro","coro","orchestra","autori",
                    "anonimo","soprano","tenore","compositore","autore",
                    "da","definire","ignoto","sconosciuto"})
    if len(credits)!=1 or not credible_person_name(credits[0]):
        raise ValueError("unambiguous official Rome composer credit missing")
    composer=credits[0]
    venue,dates=parse_roma_detail(html,url=url,title=title,composer=composer)
    return title,composer,venue,dates
