"""Cross-source evidence gate for otherwise unreachable first-party event pages.

The issuer certifies season/repertoire. Two distinct publisher domains must
separately provide exact public recite clocks; these are explicitly tagged as
secondary evidence. No unauthenticated search cache is used. Accepted facts
flow through the existing *central* auto_catalogue.promote reconciliation.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime,timezone,date
from urllib.parse import urlsplit

from opera_atlas.controlled_fetch import fetch_official_html,AccessDenied,FetchUnavailable
from opera_atlas.db import connect,migrate
from opera_atlas.national_detail_parser import clean
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import CONFIG as INDEX_CONFIG,eligible
from scripts.collect_candidate_details import OUTPUT as DETAIL_EVIDENCE,PUBLIC as PUBLIC_EVIDENCE
from scripts.discover_season_indexes import OUTPUT as CANDIDATES,PUBLIC as PUBLIC_CANDIDATES
from scripts.publish_catalog_v2 import ROOT
from scripts.build_verified_catalog import official_local_time

CONFIG=ROOT/"data/corroborated-performance-config.json"
HEALTH=ROOT/"data/corroborated-performance-health.json"
ROLES={
    "issuer_repertoire_url":("artbonus.gov.it","/1319-comune-di-rovigo.html"),
    "independent_event_url":("veneto.piazzainfesta.it","/rovigo/la-traviata-118403"),
}
# Exact pre-approved publication pages, never arbitrary domains or user URLs.
PUBLISHERS={
    "2027-01-22":("www.classicalive.it","/it/eventi/2027-01-22/la-traviata/"),
    "2027-01-24":("www.classicalive.it","/it/eventi/2027-01-24/la-traviata/"),
}
CITY="Rovigo"
TITLE="La traviata"
COMPOSER="Giuseppe Verdi"
VENUE="Teatro Sociale"
OFFICIAL_URL="https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/eventi/la-traviata-2027"
EXPECTED={"2027-01-22":"20:30","2027-01-24":"16:00"}
MONTH={"gennaio":"01"}

def _exact_url(url:str,host:str,path:str)->bool:
    parsed=urlsplit(url)
    return (parsed.scheme=="https" and parsed.hostname==host
            and parsed.path==path and not parsed.query and not parsed.fragment
            and not parsed.username and not parsed.password
            and parsed.port is None)

def validate_case(case:dict)->None:
    if (case.get("id")!="rovigo-traviata-2027"
        or case.get("source_key")!="rovigo-sociale-opera-2026-27"
        or (case.get("title"),case.get("composer"),case.get("venue"),case.get("city"))
           !=(TITLE,COMPOSER,VENUE,CITY)
        or case.get("season")!="2026/27"
        or case.get("school_date")!="2027-01-21"
        or case.get("official_event_url")!=OFFICIAL_URL
        or not eligible(case["source_key"],OFFICIAL_URL)):
        raise ValueError("unsupported corroboration identity or official origin")
    for role,(host,path) in ROLES.items():
        if not _exact_url(case.get(role,""),host,path):
            raise ValueError("corroboration URL outside exact approved source")
    rows=case.get("publisher_events")
    if not isinstance(rows,list) or len(rows)!=2:
        raise ValueError("two public publisher recite records required")
    clocks={}
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"date","time","url"}:
            raise ValueError("invalid corroborated showtime record")
        day=row["date"]
        if day not in PUBLISHERS or day in clocks:
            raise ValueError("unapproved or duplicate performance date")
        if not _exact_url(row["url"],*PUBLISHERS[day]):
            raise ValueError("unexpected external publisher URL")
        clocks[day]=row["time"]
    if clocks!=EXPECTED:
        raise ValueError("unsupported or incomplete public performance clock")

def verify_pages(case:dict,pages:dict[str,str])->list[dict]:
    """Validate ALL required pages before accepting any performance."""
    validate_case(case)
    urls=[case["issuer_repertoire_url"],case["independent_event_url"]]
    urls.extend(row["url"] for row in case["publisher_events"])
    if set(pages)!=set(urls) or len(set(urls))!=4:
        raise ValueError("four distinct live source pages required")
    text={url:clean(pages[url]) for url in urls}
    issuer=text[case["issuer_repertoire_url"]]
    # Constrain the claim to the 2026/27 season paragraph: this page also
    # contains an archived 2021 Traviata and must not leak its performances.
    m=re.search(r"(?is)La stagione 2026\s*/\s*2027 del Teatro Sociale(.{0,1400})",issuer)
    if not m or not re.search(r"(?i)Traviata\W+di\s+G\.?\s*Verdi",m[1]):
        raise ValueError("issuer has not confirmed current season repertoire")
    independent=text[case["independent_event_url"]]
    if not (re.search(r"(?i)La Traviata",independent)
            and re.search(r"(?i)Giuseppe Verdi",independent)
            and re.search(r"(?i)Teatro Sociale.{0,30}Rovigo",independent)
            and re.search(r"(?i)recite pubbliche.{0,90}22 gennaio.{0,30}20:30"
                          r".{0,50}24 gennaio.{0,30}16:00",independent)
            and re.search(r"(?i)(?:prova generale|anteprima).{0,45}21 gennaio",independent)):
        raise ValueError("independent event listing lacks matching public times")
    facts=[]
    for row in sorted(case["publisher_events"],key=lambda x:x["date"]):
        day,clock=row["date"],row["time"]
        text_body=text[row["url"]]
        label=("venerdì 22 gennaio 2027" if day.endswith("-22")
               else "domenica 24 gennaio 2027")
        # Require exact title/composer/venue/time in the event's own header.
        header=text_body[:1000]
        if not (re.search(re.escape(label),header,re.I)
                and re.search(r"(?i)\bore\s+"+re.escape(clock)+r"\b",header)
                and re.search(r"(?i)\bRovigo\b",header)
                and re.search(r"(?i)\bTeatro Sociale\b",header)
                and re.search(r"(?i)\bGiuseppe Verdi\b",header)
                and re.search(r"(?i)\bLa traviata\b",header)
                and OFFICIAL_URL in text_body):
            raise ValueError("publisher has not confirmed exact source-bound recita")
        if not date.fromisoformat(day).weekday()==(4 if day.endswith("-22") else 6):
            raise ValueError("calendar day/weekday conflict")
        facts.append({"event_title":TITLE,"composer":COMPOSER,
                      "venue":VENUE,"date":day,
                      "starts_at":official_local_time(day,clock)})
    return facts

def integrate(case:dict,pages:dict[str,str],existing:dict,details:dict,now:str):
    facts=verify_pages(case,pages)
    candidate_id="oa-index-"+hashlib.sha256(
        (case["source_key"]+"|"+OFFICIAL_URL).encode()).hexdigest()[:20]
    # Preserve all unrelated candidates/evidence and do not overwrite a
    # previously verified first-party record with secondary corroboration.
    candidates={x["id"]:x for x in existing["candidates"]}
    evidence={x["candidate_id"]:x for x in details["evidence"]}
    old=evidence.get(candidate_id)
    if old and old.get("status")=="needs_editorial_review" and not old.get("corroboration"):
        return existing,details,"already_verified_primary"
    prev=candidates.get(candidate_id,{})
    candidates[candidate_id]={
        "id":candidate_id,"source_key":case["source_key"],
        "official_url":OFFICIAL_URL,
        "status":prev.get("status","needs_review"),
        "first_seen":prev.get("first_seen",now),"last_seen":now,
    }
    if candidates[candidate_id]["status"]=="already_catalogued":
        return existing,details,"already_catalogued"
    urls=sorted(pages)
    digest=hashlib.sha256()
    for url in urls:
        digest.update(url.encode());digest.update(b"\0")
        digest.update(pages[url].encode());digest.update(b"\0")
    evidence[candidate_id]={
        "candidate_id":candidate_id,"source_key":case["source_key"],
        "source_url":OFFICIAL_URL,"content_sha256":digest.hexdigest(),
        "checked_at":now,"status":"needs_editorial_review",
        "event_facts":facts,
        # Explicit transparency: this URL is the source to check/book, not
        # a claim that its HTML was accessible during this acquisition.
        "corroboration":{
            "method":"issuer_repertoire_plus_two_secondary_publishers",
            "official_event_page_retrieved":False,
            "issuer_url":case["issuer_repertoire_url"],
            "publisher_urls":[r["url"] for r in case["publisher_events"]],
            "cross_check_url":case["independent_event_url"],
            "excluded_school_date":case["school_date"],
        },
    }
    return (
        {"schema_version":1,"candidates":sorted(candidates.values(),key=lambda x:x["id"])},
        {"schema_version":1,"evidence":sorted(evidence.values(),key=lambda x:x["candidate_id"])},
        "corroborated"
    )

def acquire(case:dict,*,fetcher=fetch_official_html):
    """Fetch each preapproved issuer and publisher page with robots gates."""
    validate_case(case)
    urls=[case["issuer_repertoire_url"],
          *(r["url"] for r in case["publisher_events"]),
          case["independent_event_url"]]
    pages={}
    db=connect()
    try:
        migrate(db)
        for url in urls:
            p=urlsplit(url)
            origin=f"https://{p.hostname}/"
            db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) "
                       "VALUES (?, 'approved')",(origin,))
            sid=db.execute("SELECT id FROM sources WHERE official_url=?",
                           (origin,)).fetchone()["id"]
            page=fetcher(db,source_id=sid,url=url,network_enabled=True)
            pages[url]=page.html
    finally:
        db.close()
    return pages

def main():
    doc=json.loads(CONFIG.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("cases"),list):
        raise ValueError("invalid cross-source case configuration")
    candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
    details=json.loads(DETAIL_EVIDENCE.read_text(encoding="utf-8"))
    statuses=[]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    for case in doc["cases"]:
        try:
            pages=acquire(case)
            candidates,details,status=integrate(case,pages,candidates,details,now)
        except (ValueError,AccessDenied,FetchUnavailable) as exc:
            # No source HTML or external exception body in operational feed.
            status=("access_denied" if isinstance(exc,AccessDenied) else
                    "fetch_unavailable" if isinstance(exc,FetchUnavailable) else
                    "insufficient_corrob")
        statuses.append({"case_id":case.get("id","invalid"),"status":status})
    _write_atomic(CANDIDATES,candidates)
    _write_atomic(PUBLIC_CANDIDATES,candidates)
    _write_atomic(DETAIL_EVIDENCE,details)
    _write_atomic(PUBLIC_EVIDENCE,details)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":now,"cases":statuses})
    print(json.dumps({"corroborated_sources":statuses}))

if __name__=="__main__":
    main()
