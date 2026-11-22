"""Apply reviewed Rovigo opera performances through the central reconciler.

The issuer establishes the 2026/27 repertory; independent event listings
supply dated clocks. No claim of reading currently inaccessible Comune event
HTML is made. This module only adds source-labelled candidates and evidence,
not canonical productions.
"""
from __future__ import annotations
import hashlib
import json
from datetime import date,datetime,timezone
from urllib.parse import urlsplit

from scripts.publish_catalog_v2 import ROOT
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import eligible,OUTPUT as CANDIDATES,PUBLIC as PUBLIC_CANDIDATES
from scripts.collect_candidate_details import OUTPUT as EVIDENCE,PUBLIC as PUBLIC_EVIDENCE
from scripts.build_verified_catalog import official_local_time

CONFIG=ROOT/"data/rovigo-reviewed-additional-productions.json"
KEY="rovigo-sociale-opera-2026-27"
EXPECTED={
    "Aida":("Giuseppe Verdi","aida",(("2027-02-26","20:30"),("2027-02-28","16:00"))),
    "La Cenerentola":("Gioachino Rossini","cenerentola",(("2027-04-23","20:30"),("2027-04-25","16:00"))),
}
PREFIX="https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/eventi/"
SECONDARY="https://www.classicalive.it/it/eventi/"

def validate(doc:dict)->None:
    if (doc.get("schema_version")!=1 or doc.get("reviewed_on")!="2026-11-22"
        or doc.get("issuer_repertoire_url")!="https://artbonus.gov.it/1319-comune-di-rovigo.html"
        or doc.get("secondary_season_url")!="https://www.operamundus.com/comunicati-stampa/un-fiore-di-stagione-211esima-stagione-lirica-al-teatro-sociale-di-rovigo/"
        or not isinstance(doc.get("review_provenance"),str)
        or not doc["review_provenance"].strip()
        or not isinstance(doc.get("cases"),list)
        or {x.get("title") for x in doc["cases"]}!=set(EXPECTED)
        or len(doc["cases"])!=len(EXPECTED)):
        raise ValueError("unknown or incomplete reviewed Rovigo season")
    for case in doc["cases"]:
        composer,slug,clocks=EXPECTED[case["title"]]
        url=PREFIX+slug
        if (case.get("composer")!=composer or case.get("source_key")!=KEY
            or case.get("official_event_url")!=url
            or not eligible(KEY,url)
            or case.get("city")!="Rovigo" or case.get("venue")!="Teatro Sociale"):
            raise ValueError("unapproved Rovigo work, source or venue")
        recite=case.get("performances")
        if not isinstance(recite,list) or len(recite)!=2:
            raise ValueError("two public performances required")
        dates={}
        for p in recite:
            if not isinstance(p,dict) or set(p)!={"date","time","secondary_event_url"}:
                raise ValueError("malformed performance")
            day=p["date"]
            if day in dates or (day,p["time"]) not in clocks:
                raise ValueError("unexpected, repeated or mismatched performance")
            if p["secondary_event_url"]!=SECONDARY+day+"/"+slug+"/":
                raise ValueError("unapproved secondary event URL")
            date.fromisoformat(day)
            dates[day]=p["time"]
        if dates!=dict(clocks):
            raise ValueError("incomplete canonical showtime set")

def apply(doc:dict,candidates:dict,evidence:dict,*,now:str):
    validate(doc)
    cand={x["id"]:dict(x) for x in candidates["candidates"]}
    observed={x["candidate_id"]:dict(x) for x in evidence["evidence"]}
    result=[]
    for case in doc["cases"]:
        key,url=case["source_key"],case["official_event_url"]
        cid="oa-index-"+hashlib.sha256((key+"|"+url).encode()).hexdigest()[:20]
        existing=cand.get(cid)
        if existing and (existing.get("source_key")!=key or existing.get("official_url")!=url):
            raise ValueError("conflicting existing candidate")
        if existing and existing.get("status")!="needs_review":
            result.append({"title":case["title"],"status":"already_processed"})
            continue
        old=observed.get(cid)
        if old and (old.get("source_key")!=key or old.get("source_url")!=url):
            raise ValueError("conflicting existing evidence")
        if old and old.get("status")=="needs_editorial_review":
            result.append({"title":case["title"],"status":"existing_evidence_preserved"})
            continue
        cand[cid]=existing or {
            "id":cid,"source_key":key,"official_url":url,"status":"needs_review",
            "first_seen":now,"last_seen":now}
        digest=hashlib.sha256(json.dumps(case,sort_keys=True,ensure_ascii=False,
                        separators=(",",":")).encode()).hexdigest()
        observed[cid]={
            "candidate_id":cid,"source_key":key,"source_url":url,
            "content_sha256":digest,"content_hash_scope":"reviewed_secondary_evidence_not_official_html",
            "reviewed_on":doc["reviewed_on"],"status":"needs_editorial_review",
            "event_facts":[{
                "event_title":case["title"],"composer":case["composer"],
                "venue":case["venue"],"date":r["date"],
                "starts_at":official_local_time(r["date"],r["time"])
            } for r in sorted(case["performances"],key=lambda x:x["date"])],
            "corroboration":{
                "method":"reviewed_issuer_repertoire_plus_external_event_cards",
                "official_event_page_retrieved":False,
                "issuer_url":doc["issuer_repertoire_url"],
                "season_cross_check_url":doc["secondary_season_url"],
                "publisher_urls":[p["secondary_event_url"]
                                  for p in case["performances"]],
                "independence_note":doc["review_provenance"],
                "reviewed_on":doc["reviewed_on"],
            },
        }
        result.append({"title":case["title"],"status":"reviewed_candidate_added"})
    return ({"schema_version":1,
             "candidates":sorted(cand.values(),key=lambda x:x["id"])},
            {"schema_version":1,
             "evidence":sorted(observed.values(),key=lambda x:x["candidate_id"])},
            result)

def main():
    doc=json.loads(CONFIG.read_text(encoding="utf-8"))
    c=json.loads(CANDIDATES.read_text(encoding="utf-8"))
    e=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    after_c,after_e,result=apply(doc,c,e,
        now=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _write_atomic(CANDIDATES,after_c)
    _write_atomic(PUBLIC_CANDIDATES,after_c)
    _write_atomic(EVIDENCE,after_e)
    _write_atomic(PUBLIC_EVIDENCE,after_e)
    print(json.dumps({"reviewed_rovigo":result},ensure_ascii=False))

if __name__=="__main__":
    main()
