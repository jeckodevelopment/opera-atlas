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
from scripts.discover_season_indexes import CONFIG,OUTPUT as INDEX,validate_config
from scripts.publish_catalog_v2 import ROOT

OUTPUT=ROOT/"data"/"candidate-detail-evidence.json"
PUBLIC=ROOT/"public"/"catalog"/"candidate-detail-evidence.json"
HEALTH=ROOT/"data"/"candidate-detail-health.json"
MAX_PAGES=10
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

def parse_event_facts(html:str)->list[dict]:
    parser=JsonLdReader()
    parser.feed(html)
    rows=[]
    for script in parser.scripts:
        try:loaded=json.loads(script)
        except (ValueError,TypeError):continue
        for event in _nodes(loaded):
            if not any(t in ("Event","MusicEvent","TheaterEvent") or t.endswith("/Event")
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
            if row not in rows:
                rows.append(row)
            if len(rows)>MAX_EVENTS:raise ValueError("too many structured event rows")
    rows.sort(key=lambda x:(x["date"],x["starts_at"] or "",x["event_title"]))
    return rows

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
        if (url.scheme!="https" or url.hostname!=parent.hostname or url.port is not None
            or url.query or url.fragment or url.username or url.password):continue
        possible.append(x)
    possible.sort(key=lambda x:x["id"])
    if not possible:return []
    offset=((today or date.today()).toordinal()*MAX_PAGES)%len(possible)
    ordered=possible[offset:]+possible[:offset]
    return ordered[:MAX_PAGES]

def collect(candidates:dict,previous:dict,*,network_enabled:bool,
            fetcher=fetch_official_html,today:date|None=None):
    if previous.get("schema_version")!=1 or not isinstance(previous.get("evidence"),list):
        raise ValueError("invalid previous evidence")
    retained={x["candidate_id"]:x.copy() for x in previous["evidence"]}
    chosen=selected_candidates(candidates,today=today)
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))}
    health=[]
    db=connect()
    try:
        migrate(db)
        for item in chosen:
            source=sources[item["source_key"]]
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                           (source["official_url"],))
                source_id=db.execute("SELECT id FROM sources WHERE official_url=?",
                                     (source["official_url"],)).fetchone()["id"]
                page=fetcher(db,source_id=source_id,url=item["official_url"],network_enabled=True)
                facts=parse_event_facts(page.html)
                if not facts:raise ValueError("no unambiguous structured event facts")
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
    result,health=collect(candidates,previous,network_enabled=parsed.allow_network)
    _write_atomic(OUTPUT,result)
    _write_atomic(PUBLIC,result)
    _write_atomic(HEALTH,{"schema_version":1,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attempted":len(health),"outcomes":health})
    print(json.dumps({"evidence":len(result["evidence"]),"attempts":len(health),
                      "structured":sum(x["outcome"]=="facts_found" for x in health)}))

if __name__=="__main__":
    main()
