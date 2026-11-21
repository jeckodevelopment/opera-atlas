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
    adapter={"scala-season-2026-27":"scala",
             "arena-festival-2027":"arena"}.get(source_key)
    if adapter is None and source_key not in (
            "fenice-opera-2026-27","parma-opera-2027","massimo-season-2026-27",
            "carlo-felice-season-2026-27","donizetti-opera-2026",
            "teatro-grande-opera-2026","opera-roma-season-2026-27"):
        return []
    if (source_key=="teatro-grande-opera-2026" and
        urlsplit(url).path=="/it/stagioni/2026/cavalleria-rusticana-pagliacci"):
        from opera_atlas.brescia_detail_parser import parse_brescia_double_bill
        entries=parse_brescia_double_bill(html,url=url,works=registry.get("works",{}))
        return [{**{k:v for k,v in x.items() if k!="clock"},
                 "starts_at":official_local_time(x["date"],x["clock"])}
                for x in entries]
    if source_key=="opera-roma-season-2026-27":
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
        venue={"fenice-opera-2026-27":"Teatro La Fenice",
               "parma-opera-2027":"Teatro Regio di Parma",
               "massimo-season-2026-27":"Teatro Massimo"}[source_key]
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
        venue={"fenice-opera-2026-27":"Teatro La Fenice",
               "parma-opera-2027":"Teatro Regio di Parma",
               "massimo-season-2026-27":"Teatro Massimo"}[item["source_key"]]
    else:
        rows=parse_showtimes(html,url=item["official_url"],title=info["title"],
                             composer=info["composer"],adapter=adapter)
        venue="Teatro alla Scala" if adapter=="scala" else "Arena di Verona"
    return [{"event_title":info["title"],"composer":info["composer"],
             "date":day,"starts_at":official_local_time(day,hour),
             "venue":venue} for day,hour in rows]

def parse_source_credited_opera_detail(source_key:str,url:str,html:str)->list[dict]:
    """Carry first-party composer evidence to independent authority research."""
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
    def has_card(item):
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
                if item["source_key"]=="carlo-felice-season-2026-27":
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
                retained[item["id"]]={
                    "candidate_id":item["id"],"source_key":item["source_key"],
                    "source_url":item["official_url"],"content_sha256":page.sha256,
                    "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "status":"needs_editorial_review","event_facts":facts,
                }
                health.append({"candidate_id":item["id"],"outcome":"facts_found",
                               "rows":len(facts)})
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                health.append({"candidate_id":item["id"],"outcome":"unavailable_or_unstructured",
                               "reason":type(exc).__name__,"rows":0})
    finally:
        db.close()
    return {"schema_version":1,"evidence":sorted(retained.values(),key=lambda x:x["candidate_id"])},health

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--allow-network",action="store_true")
    parsed=args.parse_args()
    candidates=json.loads(INDEX.read_text(encoding="utf-8"))
    previous=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {
        "schema_version":1,"evidence":[]}
    import time
    result,health=collect(candidates,previous,network_enabled=parsed.allow_network,
                          pause=time.sleep)
    _write_atomic(OUTPUT,result)
    _write_atomic(PUBLIC,result)
    _write_atomic(HEALTH,{"schema_version":1,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attempted":len(health),"outcomes":health})
    print(json.dumps({"evidence":len(result["evidence"]),"attempts":len(health),
                      "structured":sum(x["outcome"]=="facts_found" for x in health)}))

if __name__=="__main__":
    main()
