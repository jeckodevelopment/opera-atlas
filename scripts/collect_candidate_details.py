"""Bounded, robots-gated reading of newly discovered official production pages.

Records only explicit, structured factual Event metadata from JSON-LD.
No page is promoted to the canonical performance catalog automatically.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import date,datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit
from pathlib import Path

from opera_atlas.controlled_fetch import AccessDenied,FetchUnavailable,fetch_official_html
from opera_atlas.db import connect,migrate
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import CONFIG,OUTPUT as INDEX,validate_config,eligible
from scripts.publish_catalog_v2 import ROOT,REGISTRY
from scripts.build_verified_catalog import official_local_time
from opera_atlas.scala_arena_parser import parse_showtimes
from opera_atlas.national_detail_parser import parse_national_showtimes, VisibleText
from scripts.publish_catalog_v2 import normalized

OUTPUT=ROOT/"data"/"candidate-detail-evidence.json"
PUBLIC=ROOT/"public"/"catalog"/"candidate-detail-evidence.json"
HEALTH=ROOT/"data"/"candidate-detail-health.json"
PARTIAL_HEALTH=ROOT/"data"/"candidate-detail-health-partial.json"
MAX_PAGES=60
MAX_PER_SOURCE=24
# Pause between individual official page requests. Every fetch also checks
# current robots.txt and its source policy before reading HTML.
REQUEST_GAP_SECONDS=0.75
MAX_EVENTS=80

class JsonLdReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=False
        self.parts=[]
        self.scripts=[]
    def handle_starttag(self,tag,attrs):
        if tag=="script" and dict(attrs).get("type","").lower().split(";")[0].strip()=="application/ld+json":
            self.active=True
            self.parts=[]
    def handle_data(self,data):
        if self.active:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="script" and self.active:
            self.scripts.append("".join(self.parts))
            self.parts=[]
            self.active=False

def _nodes(value):
    if isinstance(value,list):
        for child in value:yield from _nodes(child)
    elif isinstance(value,dict):
        yield value
        for field in ("@graph","subEvent"):
            if field in value:yield from _nodes(value[field])

def _types(item):
    value=item.get("@type",[])
    return [value] if isinstance(value,str) else value if isinstance(value,list) else []

def _event_day(value):
    if not isinstance(value,str) or not value.strip():return None
    try:
        if len(value)==10:
            return (date.fromisoformat(value).isoformat(),None)
        stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:return None
        return (stamp.date().isoformat(),stamp.isoformat(timespec="seconds"))
    except ValueError:
        return None

def structured_composer(event:dict)->str|None:
    """Trust only an explicitly attributed composer in structured opera data."""
    def name(value):
        if isinstance(value,str):return value.strip()
        if isinstance(value,dict) and isinstance(value.get("name"),str):
            return value["name"].strip()
        return ""
    # MusicComposition.composer under workPerformed is the least ambiguous
    # schema.org representation; an event performer/conductor is not composer.
    work=event.get("workPerformed")
    if not isinstance(work,dict):return None
    if not any(str(t).split("/")[-1] in ("MusicComposition","CreativeWork")
               for t in _types(work)):
        return None
    composers=work.get("composer")
    if isinstance(composers,list):
        values={name(x) for x in composers}
        return next(iter(values)) if len(values)==1 and "" not in values else None
    value=name(composers)
    return value if 3<=len(value)<=100 else None

def parse_event_facts(html:str)->list[dict]:
    parser=JsonLdReader()
    parser.feed(html)
    rows=[]
    for script in parser.scripts:
        try:loaded=json.loads(script)
        except (ValueError,TypeError):continue
        for event in _nodes(loaded):
            if not any(t.split("/")[-1] in ("Event","MusicEvent","TheaterEvent")
                       for t in _types(event) if isinstance(t,str)):
                continue
            start=_event_day(event.get("startDate"))
            if not start:continue
            title=event.get("name")
            if not isinstance(title,str) or not 2<=len(title.strip())<=180:continue
            venue=None
            location=event.get("location")
            if isinstance(location,dict):
                place=location.get("name")
                if isinstance(place,str) and 2<=len(place.strip())<=180:
                    venue=place.strip()
            row={"event_title":title.strip(),"date":start[0],
                 "starts_at":start[1],"venue":venue}
            composer=structured_composer(event)
            if composer:row["composer"]=composer
            if row not in rows:
                rows.append(row)
            if len(rows)>MAX_EVENTS:raise ValueError("too many structured event rows")
    rows.sort(key=lambda x:(x["date"],x["starts_at"] or "",x["event_title"]))
    return rows

class FirstHeading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_heading=False
        self.parts=[]
        self.first=None
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.first is None:self.in_heading=True
    def handle_endtag(self,tag):
        if tag=="h1" and self.in_heading:
            self.first=" ".join("".join(self.parts).split())
            self.in_heading=False
    def handle_data(self,text):
        if self.in_heading:self.parts.append(text)

def heading_work(html:str,registry:dict)->dict|None:
    reader=FirstHeading()
    reader.feed(html)
    if not reader.first:return None
    matches=[work for work in registry.get("works",{}).values()
             if normalized(work["title"]).replace("’","\u0027")==
                normalized(reader.first).replace("’","\u0027")]
    return matches[0] if len(matches)==1 else None

def known_arena_edition_work(slug:str,registry:dict)->dict|None:
    """An exact official edition slug may refer to an existing work.

    Distinct productions retain their original source URLs. We never infer
    composer from the slug; parse_showtimes must confirm it in official HTML.
    """
    if not slug.startswith("aida-ed-") or len(slug)>80:
        return None
    matches=[w for w in registry.get("works",{}).values()
             if normalized(w["title"])=="aida" and normalized(w["composer"])=="giuseppe verdi"]
    return matches[0] if len(matches)==1 else None

def parse_known_opera_detail(source_key:str,url:str,html:str,registry:dict)->list[dict]:
    """Fallback only for unambiguous canonical title+composer and verified HTML.

    Never infer metadata for a newly discovered work from a URL slug alone.
    """
    if source_key=="salerno-verdi-opera-2026":
        from opera_atlas.salerno_opera_parser import parse_detail
        heading,credit,venue,recite=parse_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
        return [{"event_title":work["title"],"composer":work["composer"],
                 "venue":venue,"date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key=="macerata-festival-2027":
        from opera_atlas.macerata_opera_parser import parse_detail
        heading,credit,venue,recite=parse_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
        return [{"event_title":work["title"],"composer":work["composer"],
                 "venue":venue,"date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key.startswith(("jesi-","ancona-")) and source_key in (
        "jesi-don-pasquale-opera-2026","jesi-esecuzione-opera-2026",
        "jesi-nabucco-opera-2026","ancona-elisir-opera-2026"):
        from opera_atlas.marche_2026_parser import read_program
        title,composer,venue,recite,components=read_program(
            html,source_key=source_key,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(title)
                 and normalized(w["composer"])==normalized(composer)]
        if len(matches)!=1:return []
        work=matches[0]
        return [{"event_title":work["title"],"composer":work["composer"],
                 "venue":venue,"date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key.startswith("goldoni-livorno-") and source_key.endswith("-2026-27"):
        from opera_atlas.livorno_opera_parser import parse_detail
        title,composer,venue,recite=parse_detail(html,url=url,source_key=source_key)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(title)
                 and normalized(w["composer"])==normalized(composer)]
        if len(matches)!=1:return []
        work=matches[0]
        return [{"event_title":work["title"],"composer":work["composer"],
                 "venue":venue,"date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key.startswith("ferrara-") and source_key.endswith("-opera-2026-27"):
        from opera_atlas.ferrara_regional_parser import production
        title,composer,venue,recite=production(html,source_key=source_key,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(title)
                 and normalized(w["composer"])==normalized(composer)]
        if len(matches)!=1:return []
        return [{"event_title":matches[0]["title"],"composer":matches[0]["composer"],
                 "venue":venue,"date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
        from opera_atlas.bologna_detail_parser import parse_detail
        title,composer,venue,recite=parse_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(title) and normalized(w["composer"])==normalized(composer)]
        if len(matches)!=1:return []
        work=matches[0]
        return [{"event_title":work["title"],"composer":work["composer"],"venue":venue,
                 "date":day,"starts_at":official_local_time(day,clock)} for day,clock in recite]
    adapter={"scala-season-2026-27":"scala",
             "arena-festival-2027":"arena"}.get(source_key)
    if adapter is None and source_key not in (
            "fenice-opera-2026-27","parma-opera-2027","massimo-season-2026-27",
            "carlo-felice-season-2026-27","donizetti-opera-2026",
            "teatro-grande-opera-2026","opera-roma-season-2026-27",
            "petruzzelli-opera-2026","petruzzelli-opera-2027",
            "lirico-cagliari-opera-2027","bellini-catania-opera-2026-27",
            "modena-opera-2026-27","giglio-lucca-opera-2026-27",
            "piacenza-opera-2026-27","reggio-valli-opera-2026-27",
            "jesi-don-pasquale-opera-2026","jesi-esecuzione-opera-2026",
            "jesi-nabucco-opera-2026","ancona-elisir-opera-2026",
            *("goldoni-livorno-"+k+"-2026-27" for k in ("dido","otello","elisir")),
            *("ferrara-"+k+"-opera-2026-27" for k in ("macbeth","barbiere","dido","clemenza","boccanegra"))):
        return []
    if (source_key=="teatro-grande-opera-2026" and
        urlsplit(url).path=="/it/stagioni/2026/cavalleria-rusticana-pagliacci"):
        from opera_atlas.brescia_detail_parser import parse_brescia_double_bill
        entries=parse_brescia_double_bill(html,url=url,works=registry.get("works",{}))
        return [{**{k:v for k,v in x.items() if k!="clock"},
                 "starts_at":official_local_time(x["date"],x["clock"])}
                for x in entries]
    if source_key in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
        from opera_atlas.petruzzelli_detail_parser import parse_petruzzelli_detail
        # Match the official production h1, never a different work mentioned
        # in the recurring conversation/notice text of the page.
        from opera_atlas.petruzzelli_detail_parser import verified_work_heading
        known=[w for w in registry.get("works",{}).values()
               if verified_work_heading(html,title=w["title"],composer=w["composer"])]
        if len(known)!=1:return []
        work=known[0]
        venue,raw=parse_petruzzelli_detail(
            html,url=url,title=work["title"],composer=work["composer"],
            season_year=int(source_key.rsplit("-",1)[-1]))
    elif source_key=="reggio-valli-opera-2026-27":
        from opera_atlas.reggio_opera_parser import parse_detail as reggio_detail
        heading,credit,venue,raw=reggio_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="piacenza-opera-2026-27":
        from opera_atlas.piacenza_opera_parser import parse_detail as piacenza_detail
        heading,credit,venue,raw=piacenza_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="giglio-lucca-opera-2026-27":
        from opera_atlas.lucca_opera_parser import parse_detail as lucca_detail
        heading,credit,venue,raw=lucca_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="modena-opera-2026-27":
        from opera_atlas.modena_opera_parser import parse_detail as modena_detail
        heading,credit,venue,raw=modena_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="bellini-catania-opera-2026-27":
        from opera_atlas.catania_detail_parser import parse_detail as bellini_detail
        heading,credit,venue,raw=bellini_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="lirico-cagliari-opera-2027":
        from opera_atlas.cagliari_detail_parser import parse_detail as cagliari_detail
        heading,credit,venue,raw=cagliari_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="verdi-trieste-season-2026-27":
        from opera_atlas.trieste_detail_parser import parse_detail as trieste_detail
        heading,credit,venue,raw=trieste_detail(html,url=url)
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"])==normalized(heading)
                 and normalized(w["composer"])==normalized(credit)]
        if len(matches)!=1:return []
        work=matches[0]
    elif source_key=="opera-roma-season-2026-27":
        from opera_atlas.roma_detail_parser import parse_roma_detail
        work=heading_work(html,registry)
        if work is None:return []
        venue,raw=parse_roma_detail(html,url=url,title=work["title"],
                                    composer=work["composer"])
    elif source_key=="teatro-grande-opera-2026":
        from opera_atlas.brescia_detail_parser import Heading,parse_brescia_detail,canonical_text
        heading=Heading()
        heading.feed(html)
        works=[w for w in registry.get("works",{}).values()
               if canonical_text(heading.h1 or "")==
                  canonical_text(w["title"]+" di "+w["composer"])]
        if len(works)!=1:return []
        work=works[0]
        raw=parse_brescia_detail(html,url=url,title=work["title"],
                                 composer=work["composer"])
        venue="Teatro Grande"
    elif source_key in ("carlo-felice-season-2026-27","donizetti-opera-2026"):
        from opera_atlas.italian_detail_parser import parse_detail
        work=heading_work(html,registry)
        if work is None:return []
        venue,raw=parse_detail(html,source_key=source_key,url=url,
                               title=work["title"],composer=work["composer"])
    elif adapter is None:
        work=heading_work(html,registry)
        if work is None:return []
        raw=parse_national_showtimes(html,source_key=source_key,url=url,
                                     title=work["title"],composer=work["composer"])
        venue=(__import__("opera_atlas.national_detail_parser",fromlist=["fenice_primary_credits"]).fenice_primary_credits(html)[2]
               if source_key=="fenice-opera-2026-27" else
               {"parma-opera-2027":"Teatro Regio di Parma",
                "massimo-season-2026-27":"Teatro Massimo"}[source_key])
    else:
        slug=urlsplit(url).path.rstrip("/").split("/")[-1].removesuffix(".html")
        known=[work for work in registry.get("works",{}).values() if work.get("slug")==slug]
        if len(known)==1:
            work=known[0]
        elif not known and adapter=="arena":
            work=known_arena_edition_work(slug,registry)
            if work is None:return []
        else:
            return []
        raw=parse_showtimes(html,url=url,title=work["title"],
                            composer=work["composer"],adapter=adapter)
        venue="Teatro alla Scala" if adapter=="scala" else "Arena di Verona"
    return [{"event_title":work["title"],"composer":work["composer"],
             "date":day,"starts_at":official_local_time(day,hour),
             "venue":venue} for day,hour in raw]

def parse_authoritative_new_work_detail(item:dict,html:str,
                                        intelligence:dict)->list[dict]:
    """The official page must confirm both composer and individually dated shows."""
    matches=[w for w in intelligence.get("works",[])
             if w.get("candidate_id")==item["id"] and
                w.get("source_url")==item["official_url"] and
                w.get("source_key")==item["source_key"] and
                isinstance(w.get("synopsis"),str) and 45<=len(w["synopsis"])<=300]
    if len(matches)!=1:return []
    info=matches[0]
    adapter={"scala-season-2026-27":"scala",
             "arena-festival-2027":"arena"}.get(item["source_key"])
    if adapter is None and item["source_key"] not in (
            "fenice-opera-2026-27","parma-opera-2027","massimo-season-2026-27",
            "carlo-felice-season-2026-27","donizetti-opera-2026",
            "teatro-grande-opera-2026"):
        return []
    if item["source_key"]=="teatro-grande-opera-2026":
        from opera_atlas.brescia_detail_parser import parse_brescia_detail
        venue="Teatro Grande"
        rows=parse_brescia_detail(html,url=item["official_url"],
                                  title=info["title"],composer=info["composer"])
    elif item["source_key"] in ("carlo-felice-season-2026-27","donizetti-opera-2026"):
        from opera_atlas.italian_detail_parser import parse_detail
        venue,rows=parse_detail(html,source_key=item["source_key"],
                                url=item["official_url"],title=info["title"],
                                composer=info["composer"])
    elif adapter is None:
        heading=FirstHeading()
        heading.feed(html)
        if normalized(heading.first)!=normalized(info["title"]):
            raise ValueError("opera title mismatches official page heading")
        rows=parse_national_showtimes(html,source_key=item["source_key"],
                                     url=item["official_url"],title=info["title"],
                                     composer=info["composer"])
        venue=(__import__("opera_atlas.national_detail_parser",fromlist=["fenice_primary_credits"]).fenice_primary_credits(html)[2]
               if item["source_key"]=="fenice-opera-2026-27" else
               {"parma-opera-2027":"Teatro Regio di Parma",
                "massimo-season-2026-27":"Teatro Massimo"}[item["source_key"]])
    else:
        rows=parse_showtimes(html,url=item["official_url"],title=info["title"],
                             composer=info["composer"],adapter=adapter)
        venue="Teatro alla Scala" if adapter=="scala" else "Arena di Verona"
    return [{"event_title":info["title"],"composer":info["composer"],
             "date":day,"starts_at":official_local_time(day,hour),
             "venue":venue} for day,hour in rows]

def parse_official_parma_work_detail(url:str,html:str)->list[dict]:
    """Verify first-party Parma work credits and independently dated tickets.

    A work need not exist in the canonical registry before its official source
    can be researched; composer/title must be explicit, never URL-derived.
    """
    import re
    from opera_atlas.national_detail_parser import clean,parse_national_showtimes
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="teatroregioparma.it"
        or target.username or target.password or target.port is not None
        or target.query or target.fragment
        or not re.fullmatch(r"/spettacolo/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Parma opera detail")
    heading=FirstHeading()
    heading.feed(html)
    title=heading.first
    if not isinstance(title,str) or not 2<=len(title.strip())<=140:
        raise ValueError("missing official Parma work heading")
    text=clean(html)
    # The actual work information block follows a repeated "Spettacolo"
    # navigation label; other composers mentioned in the cast are not proof.
    section=text.rsplit("Spettacolo",1)[-1][:2800]
    if "Teatro Regio di Parma" not in section:
        raise ValueError("unverified Parma performance venue")
    credit=re.compile(
        r"(?i)\bmusica\s+"
        r"([A-ZÀ-Ž][\w'’.-]+(?:\s+[A-ZÀ-Ž][\w'’.-]+){1,5})"
        r"\s+(?=(?:Dramma|Opera|Commedia|Libretto|Melodramma|"
        r"Singspiel|Farsa|Oratorio|Tragedia)\b)")
    matches=credit.findall(section)
    if (len(matches)!=1 or
        len(re.findall(r"(?i)\bmusica\s+[A-ZÀ-Ž]",section))!=1):
        raise ValueError("missing or contradictory official Parma composer")
    composer=matches[0]
    dates=parse_national_showtimes(
        html,source_key="parma-opera-2027",url=url,
        title=title,composer=composer)
    return [{"event_title":title,"composer":composer,
             "venue":"Teatro Regio di Parma","date":day,
             "starts_at":official_local_time(day,clock)} for day,clock in dates]


def parse_official_massimo_work_detail(url:str,html:str)->list[dict]:
    """Read explicit Palermo first-party work/composer credits before authority research.

    The site exposes exact showtime cards and a dated season summary but new
    works cannot yet be matched to the canonical registry. Do not infer a
    composer from an URL, a performer credit, or an adjacent production.
    """
    import re
    from urllib.parse import urlsplit
    from opera_atlas.national_detail_parser import clean,parse_national_showtimes
    target=urlsplit(url)
    if (target.scheme!="https" or target.hostname!="www.teatromassimo.it"
        or target.username or target.password or target.port is not None
        or target.query or target.fragment
        or not re.fullmatch(r"/event/[a-z0-9-]+/",target.path)):
        raise ValueError("untrusted Palermo opera detail")
    heading=FirstHeading()
    heading.feed(html)
    title=heading.first
    if not isinstance(title,str) or not 2<=len(title.strip())<=140:
        raise ValueError("missing Palermo primary work heading")
    visible=clean(html)
    # The heading and its first-party credit must both be in the real
    # "Lo spettacolo" block, never in the navigation or artist biographies.
    section=visible.rsplit("Lo spettacolo",1)[-1][:1100]
    where=section.casefold().find(title.casefold())
    if where<0:
        raise ValueError("Palermo work title absent from performance section")
    credit=section[where+len(title):where+len(title)+400]
    # Stop at an independently labelled genre: otherwise a free-standing
    # musician name could swallow directors or character names as composer.
    pattern=(r"(?i)\bMusiche?\s+di\s+"
             r"([A-ZÀ-Ž][A-Za-zÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ž][A-Za-zÀ-ÿ'’.-]+){1,4})"
             r"\s+(?=(?:Dramma|Commedia|Singspiel|Melodramma|Opera|Tragedia|"
             r"Oratorio|Farsa|Direttore|Regia)\b)")
    credits=re.findall(pattern,credit)
    # Every labelled composer mention in this bounded primary block must
    # resolve to the same single independently credited identity.
    if len(re.findall(r"(?i)\bMusiche?\s+di\b",credit))!=1:
        raise ValueError("conflicting Palermo composer credits")
    if len(credits)!=1:
        raise ValueError("missing or ambiguous labelled Palermo composer")
    composer=credits[0]
    dates=parse_national_showtimes(
        html,source_key="massimo-season-2026-27",url=url,
        title=title,composer=composer)
    return [{"event_title":title,"composer":composer,
             "venue":"Teatro Massimo","date":day,
             "starts_at":official_local_time(day,hour)} for day,hour in dates]


def parse_source_credited_opera_detail(source_key:str,url:str,html:str)->list[dict]:
    """Carry first-party composer evidence to independent authority research."""
    if source_key in (
        "jesi-don-pasquale-opera-2026","jesi-esecuzione-opera-2026",
        "jesi-nabucco-opera-2026","ancona-elisir-opera-2026"):
        from opera_atlas.marche_2026_parser import read_program
        title,composer,venue,recite,parts=read_program(
            html,source_key=source_key,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key.startswith("goldoni-livorno-") and source_key.endswith("-2026-27"):
        from opera_atlas.livorno_opera_parser import parse_detail
        title,composer,venue,recite=parse_detail(html,url=url,source_key=source_key)
        return [{"event_title":title,"composer":composer,
                 "venue":venue,"date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key.startswith("ferrara-") and source_key.endswith("-opera-2026-27"):
        from opera_atlas.ferrara_regional_parser import production
        title,composer,venue,recite=production(html,source_key=source_key,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key=="reggio-valli-opera-2026-27":
        from opera_atlas.reggio_opera_parser import parse_detail as reggio_detail
        title,composer,venue,recite=reggio_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="piacenza-opera-2026-27":
        from opera_atlas.piacenza_opera_parser import parse_detail as piacenza_detail
        title,composer,venue,recite=piacenza_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="giglio-lucca-opera-2026-27":
        from opera_atlas.lucca_opera_parser import parse_detail as lucca_detail
        title,composer,venue,recite=lucca_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="modena-opera-2026-27":
        from opera_atlas.modena_opera_parser import parse_detail as modena_detail
        title,composer,venue,recite=modena_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="bellini-catania-opera-2026-27":
        from opera_atlas.catania_detail_parser import parse_detail as bellini_detail
        title,composer,venue,recite=bellini_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="lirico-cagliari-opera-2027":
        from opera_atlas.cagliari_detail_parser import parse_detail as cagliari_detail
        title,composer,venue,recite=cagliari_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="verdi-trieste-season-2026-27":
        from opera_atlas.trieste_detail_parser import parse_detail as trieste_detail
        title,composer,venue,recite=trieste_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key=="opera-roma-season-2026-27":
        from opera_atlas.roma_detail_parser import parse_roma_credited_detail
        title,composer,venue,dates=parse_roma_credited_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in dates]
    if source_key=="donizetti-opera-2026":
        from opera_atlas.donizetti_credited_detail import parse_credited_detail
        title,composer,venue,recite=parse_credited_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in recite]
    if source_key=="scala-season-2026-27":
        from opera_atlas.scala_credited_detail import parse_scala_credited_opera
        title,composer,recite=parse_scala_credited_opera(html,url=url)
        return [{"event_title":title,"composer":composer,
                 "date":day,"starts_at":official_local_time(day,hour),
                 "venue":"Teatro alla Scala"} for day,hour in recite]
    if source_key in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
        from opera_atlas.petruzzelli_detail_parser import extract_official_petr_opera
        title,composer,venue,recite=extract_official_petr_opera(
            html,url=url,season_year=int(source_key.rsplit("-",1)[-1]))
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,hour)}
                for day,hour in recite]
    if source_key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
        from opera_atlas.bologna_detail_parser import parse_detail
        title,composer,venue,recite=parse_detail(html,url=url)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,clock)} for day,clock in recite]
    if source_key=="fenice-opera-2026-27":
        if urlsplit(url).hostname!="www.teatrolafenice.it":
            return []
        from opera_atlas.national_detail_parser import fenice_primary_credits
        title,composer,venue=fenice_primary_credits(html)
        days=parse_national_showtimes(html,source_key=source_key,url=url,
                                     title=title,composer=composer)
        return [{"event_title":title,"composer":composer,"venue":venue,
                 "date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in days]
    if source_key=="parma-opera-2027":
        return parse_official_parma_work_detail(url,html)
    if source_key=="massimo-season-2026-27":
        return parse_official_massimo_work_detail(url,html)
    if source_key!="carlo-felice-season-2026-27":
        return []
    from opera_atlas.italian_detail_parser import extract_source_credited_carlo_felice
    title,composer,venue,recite=extract_source_credited_carlo_felice(
        html,url=url)
    return [{"event_title":title,"composer":composer,
             "date":day,"starts_at":official_local_time(day,hour),
             "venue":venue} for day,hour in recite]


def selected_candidates(candidates:dict,*,today:date|None=None)->list[dict]:
    if candidates.get("schema_version")!=1 or not isinstance(candidates.get("candidates"),list):
        raise ValueError("invalid discovery candidate registry")
    allowed={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
             if x["access_status"]=="approved"}
    possible=[]
    for x in candidates["candidates"]:
        if x.get("status")!="needs_review":continue
        key=x.get("source_key")
        source=allowed.get(key)
        if source is None:continue
        url=urlsplit(x.get("official_url",""))
        parent=urlsplit(source["official_url"])
        if (url.scheme!="https" or url.hostname!=parent.hostname or not eligible(key,x["official_url"]) or url.port is not None
            or url.query or url.fragment or url.username or url.password):continue
        possible.append(x)
    possible.sort(key=lambda x:x["id"])
    if not possible:return []
    # Prioritize candidates we can already recognize deterministically:
    # they can become published productions on this very same execution.
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    known_slugs={work["slug"] for work in registry["works"].values()}
    recognized=[]
    other=[]
    for item in possible:
        path=urlsplit(item["official_url"]).path.rstrip("/").split("/")[-1]
        slug=(urlsplit(item["official_url"]).path.rstrip("/").split("/")[-2]
              if item["source_key"]=="donizetti-opera-2026" and
                 __import__("re").fullmatch(r"20\d{2}-\d{2}-\d{2}",path)
              else path).removesuffix(".html")
        if (item["source_key"] in ("scala-season-2026-27","arena-festival-2027")
            and (slug in known_slugs or
                 (item["source_key"]=="arena-festival-2027" and
                  known_arena_edition_work(slug,registry) is not None))):
            recognized.append(item)
        else:
            other.append(item)
    # Every theatre receives one first-pass opportunity per day (up to
    # MAX_PAGES sources), rather than allowing a dense Scala index to take
    # every slot. Within each category advance by one position per day.
    ordinal=(today or date.today()).toordinal()
    def rotate(items):
        if not items:return []
        offset=ordinal%len(items)
        return items[offset:]+items[:offset]
    recognized=rotate(recognized)
    other=rotate(other)
    from scripts.auto_work_research import preverified_work_material
    prepared=preverified_work_material()
    # An original, source-bound editorial seed is also a completed candidate
    # card, even before it enters the published site/ JSON. Otherwise the
    # first-party new-opera pipeline can starve its own most actionable works
    # behind a national backlog of unstructured historic links.
    seed_path=ROOT/"data"/"verified-work-authority-seeds.json"
    seed_doc=json.loads(seed_path.read_text(encoding="utf-8"))
    if seed_doc.get("schema_version")!=1 or not isinstance(seed_doc.get("works"),list):
        raise ValueError("invalid official candidate seed registry")
    from scripts.publish_work_editorial import validate_history
    seeded_urls=set()
    for seed in seed_doc["works"]:
        key,url=seed.get("source_key"),seed.get("source_url")
        if (key in allowed and isinstance(url,str)
                and eligible(key,url)
                and urlsplit(url).hostname==urlsplit(allowed[key]["official_url"]).hostname
                and isinstance(seed.get("title"),str) and seed["title"].strip()
                and isinstance(seed.get("composer"),str) and seed["composer"].strip()
                and isinstance(seed.get("synopsis"),str)
                and 45<=len(seed["synopsis"].strip())<=300
                and validate_history(seed.get("history"))):
            seeded_urls.add((key,url))
    def has_card(item):
        if (item["source_key"],item["official_url"]) in seeded_urls:
            return True
        parts=urlsplit(item["official_url"]).path.rstrip("/").split("/")
        slug=(parts[-2] if item["source_key"]=="donizetti-opera-2026"
              and __import__("re").fullmatch(r"20\d{2}-\d{2}-\d{2}",parts[-1])
              else parts[-1]).removesuffix(".html")
        return slug in prepared
    # Reserve up to two fast-path slots for already sourced new operas;
    # rotate the remaining unknowns rather than starving them indefinitely.
    ready=[x for x in other if has_card(x)]
    unexplored=[x for x in other if not has_card(x)]
    other=ready[:2]+unexplored+ready[2:]
    reserved=min(4,len(other)) if recognized else min(MAX_PAGES,len(other))
    target_known=min(len(recognized),MAX_PAGES-reserved)
    target_other=min(len(other),MAX_PAGES-target_known)
    target_known=min(len(recognized),MAX_PAGES-target_other)
    selected=[]
    seen_ids=set()
    counts={"known":0,"other":0}
    per_source={}
    def take(item,kind,limit):
        source=item["source_key"]
        if (item["id"] in seen_ids or counts[kind]>=limit or
                per_source.get(source,0)>=MAX_PER_SOURCE):
            return False
        seen_ids.add(item["id"])
        per_source[source]=per_source.get(source,0)+1
        selected.append(item)
        counts[kind]+=1
        return True
    sources=sorted({x["source_key"] for x in recognized+other})
    # One candidate per source where feasible; prefer recognizable pages,
    # but respect the separate unknown-work quota.
    for source in sources:
        if len(selected)>=MAX_PAGES:break
        for kind,items,limit in (("known",recognized,target_known),
                                 ("other",other,target_other)):
            item=next((x for x in items if x["source_key"]==source
                       and x["id"] not in seen_ids),None)
            if item is not None and take(item,kind,limit):break
    for kind,items,limit in (("known",recognized,target_known),
                             ("other",other,target_other)):
        for item in items:
            if counts[kind]>=limit:break
            take(item,kind,limit)
    return selected

def collect(candidates:dict,previous:dict,*,network_enabled:bool,
            fetcher=fetch_official_html,today:date|None=None,
            pause=None):
    if previous.get("schema_version")!=1 or not isinstance(previous.get("evidence"),list):
        raise ValueError("invalid previous evidence")
    retained={x["candidate_id"]:x.copy() for x in previous["evidence"]}
    chosen=selected_candidates(candidates,today=today)
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    from scripts.auto_work_research import OUT as RESEARCH
    intelligence=(json.loads(RESEARCH.read_text(encoding="utf-8"))
                  if RESEARCH.exists() else {"schema_version":1,"works":[]})
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))}
    health=[]
    # Network pacing is injected only by the production CLI; unit tests use
    # deterministic mocked page fetchers and never wait or perform HTTP.
    pause=pause or (lambda seconds:None)
    db=connect()
    try:
        migrate(db)
        for index,item in enumerate(chosen):
            source=sources[item["source_key"]]
            if network_enabled and index:
                pause(REQUEST_GAP_SECONDS)
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                           (source["official_url"],))
                source_id=db.execute("SELECT id FROM sources WHERE official_url=?",
                                     (source["official_url"],)).fetchone()["id"]
                page=fetcher(db,source_id=source_id,url=item["official_url"],network_enabled=True)
                if item["source_key"]=="opera-roma-season-2026-27":
                    from opera_atlas.roma_detail_parser import official_rome_other_season
                    other=official_rome_other_season(page.html,url=item["official_url"])
                    if other is not None:
                        # An explicit season on the exact official production
                        # page is positive evidence of a historical listing;
                        # do not invent current performances from index links.
                        retained[item["id"]]={
                            "candidate_id":item["id"],"source_key":item["source_key"],
                            "source_url":item["official_url"],
                            "content_sha256":page.sha256,
                            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "status":"out_of_monitored_season",
                            "official_season":other}
                        health.append({"candidate_id":item["id"],
                                       "outcome":"verified_other_season","rows":0})
                        continue
                if item["source_key"] in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
                    from opera_atlas.petruzzelli_detail_parser import official_petruzzelli_other_year
                    other=official_petruzzelli_other_year(
                        page.html,url=item["official_url"],
                        season_year=int(item["source_key"].rsplit("-",1)[-1]))
                    if other is not None:
                        # A 2022 opera linked from the 2027 index cannot
                        # create invented recite in 2027. Preserve the
                        # original source hash, page and actual year.
                        retained[item["id"]]={
                            "candidate_id":item["id"],"source_key":item["source_key"],
                            "source_url":item["official_url"],"content_sha256":page.sha256,
                            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "status":"out_of_monitored_season","official_season":other}
                        health.append({"candidate_id":item["id"],
                                       "outcome":"verified_other_season","rows":0})
                        continue
                if item["source_key"] in (
                        "jesi-trittico-opera-2026","ancona-cavalleria-program-2026"):
                    from opera_atlas.marche_2026_parser import read_program
                    heading,composer,venue,dates,components=read_program(
                        page.html,source_key=item["source_key"],url=item["official_url"])
                    # Bind all canonical components to this source's one ticket:
                    # the non-operatic Leopardi poem is not a second opera.
                    program_heading="/".join(x[0] for x in components)+" di "+"/".join(
                        x[1] for x in components)
                    facts=[{"event_title":title,"composer":credit,"venue":venue,
                            "date":day,"starts_at":official_local_time(day,hour)}
                           for day,hour in dates for title,credit in components]
                    retained[item["id"]]={
                        "candidate_id":item["id"],"source_key":item["source_key"],
                        "source_url":item["official_url"],"content_sha256":page.sha256,
                        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "status":"needs_program_review",
                        "program_heading":program_heading,
                        "program_heading_source_url":item["official_url"],
                        "program_components":[{"title":t,"composer":c} for t,c in components],
                        "event_facts":facts}
                    health.append({"candidate_id":item["id"],
                                   "outcome":"verified_composite_program","rows":len(facts)})
                    continue
                # Source-specific adapters may supply a compound official bill.
                # The central program publisher handles all compound programs
                # identically; never mislabel the whole ticket as one opera.
                if item["source_key"] in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
                    from opera_atlas.petruzzelli_detail_parser import parse_petruzzelli_program_detail
                    try:
                        heading,components,venue,dates=parse_petruzzelli_program_detail(
                            page.html,url=item["official_url"],
                            season_year=int(item["source_key"].rsplit("-",1)[-1]))
                    except ValueError:
                        pass  # ordinary single-opera parser runs below
                    else:
                        anchor=components[0]
                        facts=[{"event_title":anchor["title"],"composer":anchor["composer"],
                                "date":day,"starts_at":official_local_time(day,hour),
                                "venue":venue} for day,hour in dates]
                        retained[item["id"]]={
                            "candidate_id":item["id"],"source_key":item["source_key"],
                            "source_url":item["official_url"],"content_sha256":page.sha256,
                            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "status":"needs_program_review","program_heading":heading,
                            "program_heading_source_url":item["official_url"],
                            "event_facts":facts}
                        health.append({"candidate_id":item["id"],
                                       "outcome":"verified_composite_program","rows":len(facts)})
                        continue
                if item["source_key"]=="teatro-grande-opera-2026":
                    from opera_atlas.brescia_detail_parser import parse_brescia_double_bill, Heading
                    try:
                        rows=parse_brescia_double_bill(
                            page.html,url=item["official_url"],works=registry.get("works",{}))
                    except ValueError:
                        pass
                    else:
                        reader=Heading()
                        reader.feed(page.html)
                        credits=[
                            {"title":"Cavalleria rusticana","composer":"Pietro Mascagni"},
                            {"title":"Pagliacci","composer":"Ruggero Leoncavallo"}]
                        facts=[
                            {"event_title":r["event_title"],"composer":r["composer"],
                             "date":r["date"],
                             "starts_at":official_local_time(r["date"],r["clock"]),
                             "venue":r["venue"]} for r in rows]
                        retained[item["id"]]={
                            "candidate_id":item["id"],"source_key":item["source_key"],
                            "source_url":item["official_url"],"content_sha256":page.sha256,
                            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "status":"needs_program_review","program_heading":reader.h1,
                            "program_heading_source_url":item["official_url"],
                            "program_components":credits,"event_facts":facts}
                        health.append({"candidate_id":item["id"],
                                       "outcome":"verified_composite_program","rows":len(facts)})
                        continue
                # Prefer parsers which verify the canonical composer and
                # page-specific showtime. Generic Event JSON-LD alone has no
                # authoritative work identity and must never outrank those.
                facts=[]
                diagnostic=[]
                parsers=[
                    ("canonical_work",lambda:parse_known_opera_detail(
                        item["source_key"],item["official_url"],page.html,registry)),
                    ("authority_work",lambda:parse_authoritative_new_work_detail(
                        item,page.html,intelligence)),
                ]
                if item["source_key"].startswith(("ferrara-","goldoni-livorno-","jesi-","ancona-")) or item["source_key"] in ("opera-roma-season-2026-27","verdi-trieste-season-2026-27","lirico-cagliari-opera-2027","bellini-catania-opera-2026-27","modena-opera-2026-27","giglio-lucca-opera-2026-27","piacenza-opera-2026-27","reggio-valli-opera-2026-27","fenice-opera-2026-27","scala-season-2026-27","parma-opera-2027","massimo-season-2026-27","carlo-felice-season-2026-27","donizetti-opera-2026","bologna-comunale-opera-2026","bologna-comunale-opera-2027","petruzzelli-opera-2026","petruzzelli-opera-2027"):
                    parsers.append(("official_composer_credit",
                        lambda:parse_source_credited_opera_detail(
                            item["source_key"],item["official_url"],page.html)))
                parsers.append(("schema_event",lambda:parse_event_facts(page.html)))
                for name,parse in parsers:
                    try:
                        facts=parse()
                        if not facts:diagnostic.append(name+":no_evidence")
                    except ValueError as exc:
                        # These are our own validation errors, not raw HTML.
                        diagnostic.append(name+":"+str(exc)[:100])
                        continue
                    if facts:break
                if not facts:
                    health.append({"candidate_id":item["id"],
                                   "outcome":"unavailable_or_unstructured",
                                   "reason":"no_verified_showtimes",
                                   "diagnostic":diagnostic,"rows":0})
                    continue
                if item["source_key"] in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
                    from opera_atlas.bologna_detail_parser import normalize_event_fact
                    facts=[normalize_event_fact(row) for row in facts]
                # Capture authenticated image metadata during the same
                # robots-gated production fetch. An unrelated promotional
                # picture must not become the new canonical opera's cover.
                image=None
                identities={(normalized(x.get("event_title","")),
                             normalized(x.get("composer","")))
                            for x in facts if isinstance(x,dict)}
                if len(identities)==1:
                    from scripts.publish_work_posters import extract_official_poster
                    title=facts[0].get("event_title","")
                    if isinstance(title,str) and title.strip():
                        image=extract_official_poster(page.html,item["official_url"],title)
                retained[item["id"]]={
                    "candidate_id":item["id"],"source_key":item["source_key"],
                    "source_url":item["official_url"],"content_sha256":page.sha256,
                    "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "status":"needs_editorial_review","event_facts":facts,
                    **({"poster_evidence":image} if image else {}),
                }
                health.append({"candidate_id":item["id"],"outcome":"facts_found",
                               "rows":len(facts)})
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                health.append({"candidate_id":item["id"],"outcome":"unavailable_or_unstructured",
                               "reason":type(exc).__name__,
                               **({"diagnostic":str(exc)[:160]} if isinstance(exc,ValueError) else {}),
                               "rows":0})
    finally:
        db.close()
    return {"schema_version":1,"evidence":sorted(retained.values(),key=lambda x:x["candidate_id"])},health

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--allow-network",action="store_true")
    args.add_argument("--priority-only",action="store_true",
                      help="First-party complete-card candidates before broad crawls")
    args.add_argument("--source-key",default=None,
                      help="Bounded first-pass scan of one approved source")
    parsed=args.parse_args()
    candidates=json.loads(INDEX.read_text(encoding="utf-8"))
    if parsed.source_key is not None:
        approved={x["key"] for x in validate_config(
            json.loads(CONFIG.read_text(encoding="utf-8")))
            if x["access_status"]=="approved"}
        if parsed.source_key not in approved:
            raise ValueError("priority scan must use an approved source key")
        candidates={**candidates,"candidates":[x for x in candidates["candidates"]
                    if x.get("source_key")==parsed.source_key]}
    if parsed.priority_only:
        # A short, source-neutral fast pass. Preserve original registry and
        # already published evidence; only narrow the fetch selection.
        from scripts.publish_work_editorial import validate_history
        seed_doc=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text(
            encoding="utf-8"))
        if seed_doc.get("schema_version")!=1 or not isinstance(seed_doc.get("works"),list):
            raise ValueError("invalid official source-bound seed registry")
        verified={(w.get("source_key"),w.get("source_url"))
                  for w in seed_doc["works"]
                  if isinstance(w.get("title"),str) and w["title"].strip()
                  and isinstance(w.get("composer"),str) and w["composer"].strip()
                  and isinstance(w.get("synopsis"),str)
                  and 45<=len(w["synopsis"].strip())<=300
                  and validate_history(w.get("history"))}
        candidates={**candidates,"candidates":[x for x in candidates["candidates"]
                   if (x.get("source_key"),x.get("official_url")) in verified]}
    previous=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {
        "schema_version":1,"evidence":[]}
    import time
    result,health=collect(candidates,previous,network_enabled=parsed.allow_network,
                          pause=time.sleep)
    _write_atomic(OUTPUT,result)
    _write_atomic(PUBLIC,result)
    # The Roma and priority fast passes are deliberately partial. Never
    # replace the national acquisition diagnostic with their attempt counts.
    # Keep an explicitly scoped checkpoint for observing these short scans.
    is_partial=parsed.source_key is not None or parsed.priority_only
    health_path=PARTIAL_HEALTH if is_partial else HEALTH
    _write_atomic(health_path,{"schema_version":1,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope":("source" if parsed.source_key else "priority" if parsed.priority_only
                 else "national"),
        **({"source_key":parsed.source_key} if parsed.source_key else {}),
        "attempted":len(health),"outcomes":health})
    print(json.dumps({"evidence":len(result["evidence"]),"attempts":len(health),
                      "structured":sum(x["outcome"]=="facts_found" for x in health)}))

if __name__=="__main__":
    main()
