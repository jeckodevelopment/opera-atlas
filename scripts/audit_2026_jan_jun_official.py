"""Read-only batch of verified 2025/26 official archives for Jan-Jun 2026.

Only verified seed URLs; no fabricated archive permutations. Network requests
reuse the Atlas robots-gated, hostname-approved bounded fetcher. All extracted
event facts are *unverified* and never added to public catalog.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from scripts.audit_2026_mass_scan import fetch, valid_official_url, clean_facts
from scripts.collect_candidate_details import parse_event_facts
from scripts.discover_season_indexes import validate_config

ROOT=Path(__file__).resolve().parents[1]
SEEDS=ROOT/"data/official-2026-retrospective-season-seeds.json"
INDEX_CONFIG=ROOT/"data/season-index-config.json"
DIRECTORY=ROOT/"data/venue-directory.json"
HISTORICAL=ROOT/"data/historical-2026-official-evidence.json"
OUTPUT=ROOT/"public/diagnostics/atlas-2026-jan-jun-official-archive.json"
MAX_SEEDS=24
MAX_DETAILS=240
MAX_PER_HOST=60
MAX_WORKERS=5

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchor=None
        self.parts=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.anchor=dict(attrs).get("href")
            self.parts=[]
    def handle_data(self,data):
        if self.anchor is not None:
            self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.anchor is not None:
            self.links.append((self.anchor," ".join("".join(self.parts).split())))
            self.anchor=None
            self.parts=[]

def validate_seeds(doc,config,directory,historical=None):
    if doc.get("schema_version")!=1 or doc.get("year")!=2026:
        raise ValueError("invalid seed document")
    seeds=doc.get("seeds")
    if not isinstance(seeds,list) or not 1<=len(seeds)<=MAX_SEEDS:
        raise ValueError("seed list must be nonempty and bounded")
    approved={urlsplit(x["official_url"]).hostname for x in validate_config(config)
              if x["access_status"]=="approved"}
    by_id={v["id"]:v for v in directory["venues"]}
    # The Regio 2025/26 archive is already independently reviewed for
    # exact operatic performance dates, though it has no current-season
    # source-index adapter. Do not permit arbitrary unapproved domains:
    # allow only the venue-ID + official-host pairing from that signed-off
    # historical provenance register.
    historical_hosts=set()
    for record in (historical or {}).get("records",[]):
        vid=record.get("venue_id")
        parsed=urlsplit(record.get("source_url",""))
        if (vid in by_id and parsed.scheme=="https"
                and parsed.hostname and record.get("source_type")=="official_event_detail"
                and record.get("audience")=="general_public"
                and record.get("dates") and record.get("city")==by_id[vid].get("city")):
            historical_hosts.add((vid,parsed.hostname))
    seen=set()
    for s in seeds:
        if s["key"] in seen:
            raise ValueError("duplicate seed key")
        seen.add(s["key"])
        if (s.get("venue_id") not in by_id or
            s.get("city")!=by_id[s["venue_id"]].get("city") or
            s.get("season") not in ("2025/26","2026") or
            (urlsplit(s["official_url"]).hostname not in approved and
             (s["venue_id"],urlsplit(s["official_url"]).hostname) not in historical_hosts) or
            not valid_official_url(s["url"],s["official_url"])):
            raise ValueError("unapproved historical seed or mismatched venue")
    return seeds

def detail_links(html,page_url,official_url):
    parser=Anchors()
    parser.feed(html)
    found=set()
    for href,label in parser.links:
        if not isinstance(href,str):
            continue
        url=urljoin(page_url,href).split("#",1)[0]
        if not valid_official_url(url,official_url) or url==page_url:
            continue
        p=urlsplit(url)
        path=p.path.casefold()
        # Only discover likely specific opera event detail pages:
        # La Fenice /event/, Scala /opera/, Regio /opera-e-balletto,
        # Bologna /evento/opera/. Avoid generic current calendars, other
        # genres and pages linked off-domain.
        if any(t in path for t in (
            "/event/","/opera/","/opera-e-balletto-2025-2026/",
            "/evento/opera/","/eventi/opera/","/spettacolo/")):
            if not re.search(r"(?i)(cookie|privacy|newsletter|abbonament|bigliett)",path):
                found.add(url)
    return sorted(found)

def credited_official_opera_facts(html, url):
    """Reuse verified first-party Scala/Fenice/Bologna parsers, fail closed.

    A webpage's generic Event markup is not required to display all actual
    operatic performances. Only individually dated/timed credible opera
    credits from known source-specific structures are accepted.
    """
    from scripts.build_verified_catalog import official_local_time
    parsed=urlsplit(url)
    path=parsed.path
    if parsed.hostname=="www.teatrolafenice.it" and path.startswith("/event/"):
        from opera_atlas.national_detail_parser import (
            fenice_primary_credits, parse_national_showtimes,
        )
        title, composer, venue = fenice_primary_credits(html)
        dates = parse_national_showtimes(
            html, source_key="fenice-opera-2026-27", url=url,
            title=title, composer=composer)
    elif (parsed.hostname=="www.teatroallascala.org"
          and re.fullmatch(r"/it/stagione/2025-2026/opera/[a-z0-9-]+\.html",path)):
        from opera_atlas.scala_credited_detail import FirstH1
        from opera_atlas.national_detail_parser import clean
        from opera_atlas.scala_arena_parser import parse_showtimes
        heading=FirstH1()
        heading.feed(html)
        title=heading.value
        if not title or len(title)>140:
            raise ValueError("official Scala 2025/26 work heading absent")
        text=clean(html)
        m=re.search(r"\bOpera\s+"+re.escape(title)+
                    r"\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+){1,4})"
                    r"\s+Dal\s+\d{1,2}\s+",text)
        if not m:
            raise ValueError("official Scala 2025/26 work/composer header absent")
        composer=m.group(1).strip()
        venue="Teatro alla Scala"
        dates=parse_showtimes(html,url=url,title=title,composer=composer,adapter="scala")
    elif parsed.hostname=="www.tcbo.it" and path.startswith("/evento/opera/"):
        from opera_atlas.bologna_detail_parser import parse_detail
        title,composer,venue,dates=parse_detail(html,url=url)
    else:
        return []
    return clean_facts([{
        "event_title":title,"composer":composer,"venue":venue,
        "date":day,"starts_at":official_local_time(day,hour),
    } for day,hour in dates])


def scan(doc,config,directory,*,historical=None,fetch_page=fetch,workers=MAX_WORKERS,max_details=MAX_DETAILS):
    seeds=validate_seeds(doc,config,directory,historical)
    def index_one(seed):
        result={"key":seed["key"],"venue_id":seed["venue_id"],"url":seed["url"]}
        try:
            html=fetch_page(seed,seed["url"])
            result.update(status="scanned",links=detail_links(html,seed["url"],seed["official_url"]),
                          facts=clean_facts(parse_event_facts(html)))
        except (ValueError,OSError,RuntimeError) as exc:
            result.update(status="unverified",failure=type(exc).__name__,links=[],facts=[])
        return result
    with ThreadPoolExecutor(max_workers=workers) as ex:
        indexes=list(ex.map(index_one,seeds))
    seeds_by_key={x["key"]:x for x in seeds}
    links={}
    for entry in indexes:
        seed=seeds_by_key[entry["key"]]
        for url in entry["links"]:
            links.setdefault(url,(seed,url,entry["url"]))
    count=Counter()
    queue=[]
    deferred=Counter()
    for seed,url,index_url in sorted(links.values(),key=lambda t:t[1]):
        host=urlsplit(url).hostname
        if count[host]>=MAX_PER_HOST or len(queue)>=max_details:
            deferred[host]+=1
            continue
        count[host]+=1
        queue.append((seed,url,index_url))
    def detail_one(task):
        seed,url,index_url=task
        item={"source_key":seed["key"],"venue_id":seed["venue_id"],"url":url,
              "found_on":index_url}
        try:
            html=fetch_page(seed,url)
            generic=clean_facts(parse_event_facts(html))
            try:
                credited=credited_official_opera_facts(html,url)
                parser_status="credited_opera_parsed" if credited else "no_credited_opera_dates"
            except (ValueError,RuntimeError,TypeError) as exc:
                credited=[]
                parser_status="credited_opera_parser_unverified:" + type(exc).__name__
            # Prefer source-credited dates to general-purpose Event JSON-LD.
            # Preserve both when present, deduplicating identical timestamps
            # by source, title and date in the downstream reconciliation.
            fingerprints={(f["date"],f["event_title"],f.get("starts_at"))
                          for f in credited}
            facts=credited+[f for f in generic
                            if (f["date"],f["event_title"],f.get("starts_at"))
                            not in fingerprints]
            item.update(status="scanned",facts=facts,
                        credited_parser_status=parser_status,
                        credited_fact_count=len(credited))
        except (ValueError,OSError,RuntimeError) as exc:
            item.update(status="unverified",failure=type(exc).__name__,facts=[])
        return item
    with ThreadPoolExecutor(max_workers=workers) as ex:
        details=list(ex.map(detail_one,queue))
    observed=[]
    for item in details:
        for fact in item["facts"]:
            if fact["date"]<"2026-07-01":
                observed.append({**fact,"venue_id_candidate":item["venue_id"],
                                 "official_url":item["url"],"found_on":item["found_on"],
                                 "status":"needs_venue_work_audience_time_review"})
    for item in indexes:
        for fact in item["facts"]:
            if fact["date"]<"2026-07-01":
                observed.append({**fact,"venue_id_candidate":item["venue_id"],
                                 "official_url":item["url"],"found_on":item["url"],
                                 "status":"index_fact_needs_independent_detail"})
    venue_ids={x["venue_id"] for x in seeds}
    return {
        "schema_version":1,"year":2026,"period":"2026-01-01/2026-06-30",
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,
        "complete_seasons_certified":0,
        "historical_seed_count":len(seeds),"venues_seeded":len(venue_ids),
        "seed_pages_acquired":sum(x["status"]=="scanned" for x in indexes),
        "detail_pages_attempted":len(details),
        "detail_pages_acquired":sum(x["status"]=="scanned" for x in details),
        "credited_opera_observations":sum(x.get("credited_fact_count",0) for x in details),
        "jan_jun_unverified_event_observations":len(observed),
        "deferred_per_host":dict(sorted(deferred.items())),
        "seed_results":indexes,"detail_results":details,"observations":observed,
        "warning":"Only independently verified historical seed links were crawled; no full calendar certified. Event JSON-LD is not sufficient to prove opera, audience, venue or missing recita.",
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--allow-network",action="store_true")
    p.add_argument("--workers",type=int,default=MAX_WORKERS)
    p.add_argument("--max-details",type=int,default=MAX_DETAILS)
    p.add_argument("--output",type=Path,default=OUTPUT)
    a=p.parse_args()
    if not a.allow_network or not 1<=a.workers<=MAX_WORKERS or not 1<=a.max_details<=MAX_DETAILS:
        p.error("explicit network authorization and bounded limits required")
    def load(path):return json.loads(path.read_text(encoding="utf-8"))
    result=scan(load(SEEDS),load(INDEX_CONFIG),load(DIRECTORY),
                historical=load(HISTORICAL),workers=a.workers,max_details=a.max_details)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in (
        "historical_seed_count","venues_seeded","seed_pages_acquired",
        "detail_pages_acquired","credited_opera_observations","jan_jun_unverified_event_observations")}))
if __name__=="__main__":
    main()
