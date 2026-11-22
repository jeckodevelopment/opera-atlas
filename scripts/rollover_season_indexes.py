"""Advance theatre season indexes automatically after verifying the next season.

No inferred page is activated unless its exact official HTTPS URL passes the
usual fresh robots gate AND yields a complete, nonempty production index.
The last known working season remains unchanged on any failure.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date,datetime,timezone
from urllib.parse import urlsplit
from opera_atlas.controlled_fetch import AccessDenied,FetchUnavailable,fetch_official_html
from opera_atlas.db import connect,migrate
from scripts.discover_season_indexes import CONFIG,validate_config,extract
from scripts.daily_ingest import _write_atomic
from scripts.publish_catalog_v2 import ROOT

HEALTH=ROOT/"data"/"season-rollover-health.json"
ROLLOVER_KEYS={
    "scala-season-2026-27",
    "fenice-opera-2026-27",
    "massimo-season-2026-27",
    "maggio-fiorentino-calendar-2027",
    "piacenza-opera-2026-27",
    "spoleto-tls-lirica-2026",
    "puccini-torre-del-lago-2027",
    "giglio-lucca-opera-2026-27",
    "carlo-felice-season-2026-27",
    "messina-vittorio-opera-2026-27",
    "petruzzelli-opera-2027",
    "donizetti-opera-2027",
}

def next_index(source:dict,*,today:date,allow_early:bool=False)->str|None:
    key=source["key"]
    if key not in ROLLOVER_KEYS or source["access_status"]!="approved":
        return None
    url=urlsplit(source["url"])
    if key=="donizetti-opera-2027":
        match=re.fullmatch(r"/it/opere-(20\d{2})/",url.path)
        if not match:return None
        year=int(match[1])
        if (year<2027 or year>=2099
                or (not allow_early and today<date(year,9,1))):
            return None
        return f"https://{url.hostname}/it/opere-{year+1}/"
    if key=="petruzzelli-opera-2027":
        match=re.fullmatch(r"/opera-e-balletto-(20\d{2})/",url.path)
        if not match:return None
        year=int(match[1])
        if (year<2027 or year>=2099
                or (not allow_early and today<date(year,9,1))):
            return None
        return f"https://{url.hostname}/opera-e-balletto-{year+1}/"
    if key=="messina-vittorio-opera-2026-27":
        match=re.fullmatch(r"/event_listing_type/opera-(\d{2})-(\d{2})/",url.path)
        if not match:return None
        start=2000+int(match[1])
        if (start<2026 or int(match[2])!=(start+1)%100 or start>=2098
                or (not allow_early and today<date(start+1,6,1))):
            return None
        return (f"https://{url.hostname}/event_listing_type/"
                f"opera-{(start+1)%100:02d}-{(start+2)%100:02d}/")
    if key=="carlo-felice-season-2026-27":
        match=re.fullmatch(
            r"/rassegna-stagione-opera-danza-musical-(20\d{2})-(\d{2})/",
            url.path)
        if not match:return None
        start=int(match[1])
        if (int(match[2])!=(start+1)%100 or start>=2098
                or (not allow_early and today<date(start+1,6,1))):
            return None
        return (f"https://{url.hostname}/"
                f"rassegna-stagione-opera-danza-musical-{start+1}-{(start+2)%100:02d}/")
    if key=="giglio-lucca-opera-2026-27":
        match=re.fullmatch(r"/it/cartellone/lirica/stagione-(20\d{2})-(20\d{2})/",url.path)
        if not match:return None
        start=int(match[1])
        if (int(match[2])!=start+1
                or (not allow_early and today<date(start+1,6,1)) or start>=2098):
            return None
        return (f"https://{url.hostname}/it/cartellone/lirica/"
                f"stagione-{start+1}-{start+2}/")
    if key=="puccini-torre-del-lago-2027":
        m=re.fullmatch(r"/en/(\d{2,3})(?:st|nd|rd|th)-puccini-festival-(20\d{2})/",url.path)
        if not m:return None
        edition,year=int(m[1]),int(m[2])
        if edition!=year-1954 or year>=2099 or (
            not allow_early and today<date(year,9,1)):
            return None
        nxt=edition+1
        suffix=("th" if nxt%100 in (11,12,13) else
                {1:"st",2:"nd",3:"rd"}.get(nxt%10,"th"))
        return f"https://{url.hostname}/en/{nxt}{suffix}-puccini-festival-{year+1}/"
    if key=="spoleto-tls-lirica-2026":
        match=re.fullmatch(r"/stagione-lirica-(20\d{2})/",url.path)
        if not match:return None
        year=int(match[1])
        if (not allow_early and today<date(year,10,1)) or year>=2099:return None
        return f"https://{url.hostname}/stagione-lirica-{year+1}/"
    if key=="piacenza-opera-2026-27":
        match=re.fullmatch(r"/stagioni/stagione-(\d{2})-(\d{2})/",url.path)
        if not match:return None
        start=2000+int(match[1])
        if (int(match[2])!=(start+1)%100
                or (not allow_early and today<date(start+1,6,1)) or start>=2098):
            return None
        return (f"https://{url.hostname}/stagioni/"
                f"stagione-{(start+1)%100:02d}-{(start+2)%100:02d}/")
    if key=="maggio-fiorentino-calendar-2027":
        match=re.fullmatch(r"/calendario/(20\d{2})/01/opera",url.path)
        if not match:return None
        year=int(match[1])
        if (not allow_early and today<date(year,6,1)) or year>=2099:return None
        return f"https://{url.hostname}/calendario/{year+1}/01/opera"
    if key=="scala-season-2026-27":
        match=re.fullmatch(r"/it/stagione/(20\d{2})-(20\d{2})/index\.html",url.path)
    elif key=="fenice-opera-2026-27":
        match=re.fullmatch(r"/event-category/opera-(20\d{2})-(\d{2})/",url.path)
    else:
        match=re.fullmatch(r"/la-stagione-(20\d{2})-(\d{2})/",url.path)
    if not match:return None
    start=int(match[1])
    if ((not allow_early and today<date(start+1,6,1)) or start>=2098):
        return None
    next_start=start+1
    if key=="scala-season-2026-27":
        path=f"/it/stagione/{next_start}-{next_start+1}/index.html"
    elif key=="fenice-opera-2026-27":
        path=f"/event-category/opera-{next_start}-{(next_start+1)%100:02d}/"
    else:
        path=f"/la-stagione-{next_start}-{(next_start+1)%100:02d}/"
    return f"https://{url.hostname}{path}"

def roll(config:dict,*,today:date,network_enabled:bool=False,
         fetcher=fetch_official_html)->tuple[dict,list[dict]]:
    entries=validate_config(config)
    updated=json.loads(json.dumps(config))
    statuses=[]
    db=connect()
    try:
        migrate(db)
        for item in updated["sources"]:
            prospective=next_index(item,today=today)
            if prospective is None:continue
            if not network_enabled:
                statuses.append({"key":item["key"],"status":"network_disabled"})
                continue
            try:
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                           (item["official_url"],))
                source_id=db.execute("SELECT id FROM sources WHERE official_url=?",
                              (item["official_url"],)).fetchone()["id"]
                page=fetcher(db,source_id=source_id,url=prospective,network_enabled=True)
                links=extract(item["key"],prospective,page.html,item["min_links"])
                # Index content must be structured and from the requested
                # official season, not a generic redirect or legacy index.
                if item["key"]=="scala-season-2026-27":
                    expected=urlsplit(prospective).path.replace("/index.html","/opera/")
                    if not all(urlsplit(x).path.startswith(expected) for x in links):
                        raise ValueError("mixed Scala season results")
                item["url"]=prospective
                statuses.append({"key":item["key"],"status":"rolled",
                                 "new_index_url":prospective,"links":len(links)})
            except (AccessDenied,FetchUnavailable,ValueError,OSError) as exc:
                statuses.append({"key":item["key"],"status":"kept_last_known_good",
                                 "reason":type(exc).__name__})
    finally:
        db.close()
    validate_config(updated)
    return updated,statuses

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    args=parser.parse_args()
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    updated,statuses=roll(config,today=date.today(),network_enabled=args.allow_network)
    if updated!=config:_write_atomic(CONFIG,updated)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":datetime.now(timezone.utc).isoformat(
        timespec="seconds"),"outcomes":statuses})
    print(json.dumps({"rollovers":sum(x["status"]=="rolled" for x in statuses),
                      "outcomes":statuses}))
if __name__=="__main__":
    main()
