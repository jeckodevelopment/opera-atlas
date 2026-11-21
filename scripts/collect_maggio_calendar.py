"""Official Florence monthly opera calendars -> individually verified recite.

The source publishes exact date, clock, opera, composer and auditorium in
each linked calendar entry. Only independently canonical known works can
become promotable facts. Unknown works stay outside the canonical catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from opera_atlas.controlled_fetch import AccessDenied, FetchUnavailable, fetch_official_html
from opera_atlas.db import connect, migrate
from scripts.build_verified_catalog import official_local_time
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import CONFIG, OUTPUT as INDEX, PUBLIC as INDEX_PUBLIC, eligible, validate_config
from scripts.collect_candidate_details import OUTPUT as EVIDENCE, PUBLIC as EVIDENCE_PUBLIC
from scripts.publish_catalog_v2 import ROOT, REGISTRY, normalized

SOURCE="maggio-fiorentino-calendar-2027"
ORIGIN="https://www.maggiofiorentino.com/"
VENUE_LABEL="Teatro del Maggio - Sala Grande"
VENUE="Teatro del Maggio Musicale Fiorentino"
VENUES={VENUE_LABEL:VENUE,"Teatro Goldoni":"Teatro Goldoni"}
HEALTH=ROOT/"data"/"maggio-calendar-health.json"
MONTHS={"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
        "gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
        "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
DAYWORDS={"monday","tuesday","wednesday","thursday","friday","saturday","sunday",
          "lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"}
CARD=re.compile(
    r"^Opera\s+([0-3]?\d)\s+([A-Za-zÀ-ÿ]+)\s+([A-Za-zÀ-ÿ]+)\s+"
    r"([01]?\d|2[0-3]):([0-5]\d)\s+"
    r"(Teatro del Maggio\s*-\s*Sala Grande|Teatro Goldoni)\s+(.+)$",re.I)

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.link=None
        self.parts=[]
        self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a" and self.link is None:
            self.link=dict(attrs).get("href")
            self.parts=[]
    def handle_data(self,data):
        if self.link is not None:self.parts.append(' '+data+' ')
    def handle_endtag(self,tag):
        if tag=="a" and self.link is not None:
            self.items.append((self.link," ".join("".join(self.parts).split())))
            self.link=None
            self.parts=[]

def month_url(year:int,month:int)->str:
    if not 2026<=year<=2098 or not 1<=month<=12:
        raise ValueError("invalid Florence calendar month")
    return f"{ORIGIN}calendario/{year}/{month:02d}/opera"

def months_from(today:date,*,count:int=8)->list[str]:
    if not 1<=count<=12:raise ValueError("invalid bounded month count")
    return [month_url((today.year*12+today.month-1+i)//12,
                      (today.year*12+today.month-1+i)%12+1)
            for i in range(count)]

def canonical_key(value:str)->str:
    return " ".join(normalized(value).replace("’","'").split())

def parse_month(html:str,*,url:str,registry:dict,today:date,
                evidence:dict|None=None)->list[dict]:
    target=urlsplit(url)
    match=re.fullmatch(r"/calendario/(20\d{2})/(\d{2})/opera",target.path)
    if (target.scheme!="https" or target.hostname!="www.maggiofiorentino.com"
        or target.port is not None or target.username or target.password
        or target.query or target.fragment or not match):
        raise ValueError("untrusted Florence monthly source")
    year,month=int(match[1]),int(match[2])
    if not 2026<=year<=2098 or not 1<=month<=12:
        raise ValueError("unsupported Florence calendar year/month")
    known=list(registry.get("works",{}).values())
    # Official performance H1 and venue from detail identify the new title;
    # calendar cards independently credit its composer. Never parse URL slugs.
    credited={}
    for entry in (evidence or {}).get("evidence",[]):
        urlref=entry.get("source_url")
        if (entry.get("source_key")!=SOURCE or
            entry.get("status")!="needs_editorial_review" or
            not isinstance(urlref,str) or not eligible(SOURCE,urlref)):
            continue
        entries=entry.get("event_facts",[])
        if not isinstance(entries,list) or not entries or not all(
            isinstance(x,dict) for x in entries):continue
        titles={x.get("event_title") for x in entries}
        venues={x.get("venue") for x in entries}
        composers={x.get("composer") for x in entries if
                   isinstance(x.get("composer"),str) and x["composer"].strip()}
        if len(titles)!=1 or len(venues)!=1 or len(composers)>1:continue
        title=next(iter(titles))
        venue=next(iter(venues))
        if (not isinstance(title,str) or not title.strip() or
            venue not in VENUES.values()):continue
        credited[urlref]=(title,venue,next(iter(composers)) if composers else None)
    reader=Anchors()
    reader.feed(html)
    rows={}
    for href,label in reader.items:
        detail=urljoin(url,href)
        candidate=urlsplit(detail)
        if (candidate.scheme!="https" or candidate.hostname!="www.maggiofiorentino.com"
            or candidate.query or candidate.fragment or candidate.port is not None
            or candidate.username or candidate.password
            or not eligible(SOURCE,detail)):
            continue
        found=CARD.fullmatch(label)
        if not found:continue
        daytext,monthname,weekday,hh,mm,venue_label,credit=found.groups()
        if MONTHS.get(monthname.casefold())!=month or weekday.casefold() not in DAYWORDS:
            continue
        venue=VENUES.get(next((v for v in VENUES if v.casefold()==venue_label.casefold()),""))
        if venue is None:continue
        try:
            day=date(year,month,int(daytext))
        except ValueError:
            continue
        if day<today:continue
        # Explicit source card must state BOTH full title and composer,
        # immediately together in either order before any staff credits.
        credit=canonical_key(credit)
        matches=[]
        for work in known:
            title=canonical_key(work["title"])
            composer=canonical_key(work["composer"])
            if (credit.startswith(title+" "+composer)
                or credit.startswith(composer+" "+title)):
                matches.append(work)
        if len(matches)>1:continue
        if len(matches)==1:
            work=matches[0]
            title,composer=work["title"],work["composer"]
        else:
            verified=credited.get(detail)
            if not verified or verified[1]!=venue:continue
            title,_,old_composer=verified
            primary=canonical_key(title)
            if not credit.startswith(primary+" "):continue
            author=credit[len(primary)+1:]
            # Exact capitalized full person credit after independently checked
            # title; reject staff roles and any unstructured trailing details.
            if (not re.fullmatch(r"[a-zà-ÿ][\w'’.-]+(?:\s+[a-zà-ÿ][\w'’.-]+){1,4}",author,re.I)
                or author.split()[0] in {"direttore","regia","maestro","soprano",
                                          "tenore","baritono","coro","orchestra"}):
                continue
            if old_composer and canonical_key(old_composer)!=author:continue
            composer=old_composer or " ".join(token.capitalize() for token in author.split())
        key=(detail,day.isoformat())
        row={"official_url":detail,"event_title":title,
             "composer":composer,"venue":venue,
             "date":day.isoformat(),
             "starts_at":official_local_time(day.isoformat(),f"{int(hh):02d}:{mm}")}
        if key in rows and rows[key]!=row:
            raise ValueError("conflicting official Florence ticket card")
        rows[key]=row
    return sorted(rows.values(),key=lambda x:(x["official_url"],x["date"]))

def combine(candidates:dict,evidence:dict,observations:list[dict],*,at:str):
    """Atomically add official facts while retaining previous verified data."""
    if candidates.get("schema_version")!=1 or evidence.get("schema_version")!=1:
        raise ValueError("invalid existing candidate catalog")
    updated={x["id"]:dict(x) for x in candidates.get("candidates",[])}
    facts={x["candidate_id"]:dict(x) for x in evidence.get("evidence",[])}
    by_url={}
    for item in observations:
        if item["date"]!=item["starts_at"][:10] or not eligible(SOURCE,item["official_url"]):
            raise ValueError("invalid official Florence observation")
        by_url.setdefault(item["official_url"],[]).append(item)
    for url,rows in sorted(by_url.items()):
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+url).encode()).hexdigest()[:20]
        # The index can already have discovered this same URL.
        prev=updated.get(cid)
        if prev and (prev.get("source_key")!=SOURCE or prev.get("official_url")!=url):
            raise ValueError("candidate identifier collision")
        updated[cid]={**(prev or {"id":cid,"source_key":SOURCE,"official_url":url,
                                  "first_seen":at}),
                      "status":"needs_review","last_seen":at}
        previous=facts.get(cid)
        if previous and (previous.get("source_key")!=SOURCE or previous.get("source_url")!=url):
            raise ValueError("official detail identifier collision")
        merged={}
        for item in (previous or {}).get("event_facts",[]):
            if item["date"] in merged:raise ValueError("duplicate previously verified date")
            merged[item["date"]]=item
        for item in rows:
            fact={key:item[key] for key in ("event_title","composer","venue","date","starts_at")}
            day=item["date"]
            if day in merged and merged[day]!=fact:
                former=merged[day]
                only_missing_credit=(not former.get("composer") and
                    all(former.get(field)==fact.get(field) for field in
                        ("event_title","venue","date","starts_at")))
                if not only_missing_credit:
                    raise ValueError("conflicting published source timing requires review")
            merged[day]=fact
        facts[cid]={"candidate_id":cid,"source_key":SOURCE,"source_url":url,
                    "checked_at":at,"status":"needs_editorial_review",
                    "event_facts":[merged[day] for day in sorted(merged)]}
    return ({"schema_version":1,"candidates":sorted(updated.values(),key=lambda x:x["id"])},
            {"schema_version":1,"evidence":sorted(facts.values(),key=lambda x:x["candidate_id"])})

def scan(*,today:date,fetcher=fetch_official_html,network_enabled:bool=False,
         horizon:int=12):
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    source=next(x for x in validate_config(config) if x["key"]==SOURCE)
    if source["access_status"]!="approved":
        raise AccessDenied("Florence source not approved")
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates=json.loads(INDEX.read_text(encoding="utf-8"))
    evidence=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds")
    db=connect()
    observations=[]
    status=[]
    try:
        migrate(db)
        db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                   (ORIGIN,))
        sid=db.execute("SELECT id FROM sources WHERE official_url=?",(ORIGIN,)).fetchone()["id"]
        for url in months_from(today,count=horizon):
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                page=fetcher(db,source_id=sid,url=url,network_enabled=True)
                parsed=parse_month(page.html,url=url,registry=registry,
                                   today=today,evidence=evidence)
                observations.extend(parsed)
                status.append({"url":url,"status":"verified","known_recite":len(parsed)})
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                status.append({"url":url,"status":"unavailable_or_unstructured",
                               "reason":type(exc).__name__})
    finally:
        db.close()
    next_candidates,next_evidence=combine(candidates,evidence,observations,at=timestamp)
    return next_candidates,next_evidence,{"schema_version":1,"checked_at":timestamp,
                                          "sources":status,"observed_recite":len(observations)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    args=parser.parse_args()
    candidates,evidence,health=scan(today=date.today(),network_enabled=args.allow_network)
    _write_atomic(INDEX,candidates)
    _write_atomic(INDEX_PUBLIC,candidates)
    _write_atomic(EVIDENCE,evidence)
    _write_atomic(EVIDENCE_PUBLIC,evidence)
    _write_atomic(HEALTH,health)
    print(json.dumps({"florence_known_recite":health["observed_recite"],
                      "monthly_results":health["sources"]},ensure_ascii=False))

if __name__=="__main__":
    main()
