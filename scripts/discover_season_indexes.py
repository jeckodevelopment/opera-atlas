"""Conservative discovery of official season production links; no recita publication.

Three explicitly listed index pages are robots-gated at every run. We record
only exact-origin candidate URLs, never follow them or infer performance data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from opera_atlas.controlled_fetch import AccessDenied,FetchUnavailable,fetch_official_html
from opera_atlas.db import connect,migrate
from scripts.daily_ingest import _write_atomic
from scripts.publish_catalog_v2 import ROOT

# Explicitly reviewed non-operatic/utility links encountered in the first
# successful live scan. Future unknown URLs remain candidates for review.
# A URL is never considered an opera merely because it shares a URL prefix.
EXCLUDED_PATHS={
    "scala-season-2026-27": frozenset({
        "otello-anteprima-under30.html",
    }),
    "arena-festival-2027": frozenset({
        # Explicitly classified non-opera events, never a generic genre guess.
        "romeo-e-giulietta",

        "regolamento", "preparati-allopera", "spettacoli-prossima-stagione",
        "roberto-bolle-friends", "carmina-burana", "kaufmann",
        "paganini-paradise", "domande-frequenti", "artisti",
        "viva-vivaldi",
    }),
    "parma-opera-2027": frozenset({
        # Explicitly classified non-opera events, never a generic genre guess.
        "concerto-di-capodanno-27",
        "prima-che-si-alzi-il-sipario-2",
        "orchestra-e-corpo-di-ballo-della-fondazione-arena-di-verona",
        "regio-in-tour-aspettando-mondi-lontani",
        "natale-insieme-2026",
        "verdi-off-los-angeles",

        "prima-che-si-alzi-il-sipario", "prove-under30", "prove-aperte",
        "lanno-che-verra", "veleno", "regio198", "la-principessa-sissi",
    }),
    "massimo-season-2026-27": frozenset({
        # Explicitly classified non-opera events, never a generic genre guess.
        "orchestra-jazz-siciliana-the-brass-group-3",
        "gabriele-ferro-adagi",
        "fabio-biondi-beethoven",
        "nuovo-cinema-paradiso",
        "gaetano-despinosa-beethoven",
        "giovanni-sollima-beethoven",
        "robert-trevino-ravel",
        "despinosa-beethoven-settima",
        "recital-minasyan-brownlee",
        "concerto-di-capodanno-3",
        "orchestra-nazionale-dei-conservatori-2",
        "omaggio-a-salvatore-sciarrino-klangforum-wien",
        "orchestra-nazionale-barocca-dei-conservatori-4",
        "orchestra-del-conservatorio-scarlatti-2",
        "biancaneve-2",
        "recital-daniil-trifonov",
        "lo-schiaccianoci-4",
        "gabriele-ferro-beethoven",
        "non-dirmi-che-hai-paura",

        "biancaneve", "il-grande-gatsby", "sylvia", "balanchine-caikovskij",
        "lo-schiaccianoci",
    }),
    "carlo-felice-season-2026-27": frozenset({
        "lo-schiaccianoci", "giselle", "il-lago-dei-cigni",
        "deledda", "sergio-bernal-dance-company",
        "the-phantom-of-the-opera",
    }),
    "fenice-opera-2026-27": frozenset({
        "piccolo-orso-e-la-montagna-di-ghiaccio",
        "zsigmond-gerloczy",
        "percorsi-della-danza-cinema-e-danza-il-musical",
        "concertoriccardofrizzasinopoliperosi",
    }),
}

def excluded_nonopera(key:str,url:str)->bool:
    return urlsplit(url).path.rstrip("/").split("/")[-1] in EXCLUDED_PATHS.get(key,frozenset())

def reviewed_source_urls()->set[str]:
    # Catalog identity comes from verified official production entries, not
    # slug matching, so a similarly named new staging stays in review.
    from scripts.build_verified_catalog import MANIFEST
    document=json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {row["source_url"] for row in document["productions"]}

def classify(key:str,url:str,reviewed:set[str])->str:
    if excluded_nonopera(key,url):
        return "excluded_nonopera"
    if url in reviewed:
        return "already_catalogued"
    return "needs_review"

CONFIG=ROOT/"data"/"season-index-config.json"
OUTPUT=ROOT/"data"/"season-index-candidates.json"
PUBLIC=ROOT/"public"/"catalog"/"season-index-candidates.json"
HEALTH=ROOT/"data"/"season-index-health.json"

class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            url=dict(attrs).get("href")
            if isinstance(url,str):self.links.append(url)

class ScopedSeasonAnchors(HTMLParser):
    """Read production anchors only from the official season content block.

    Parma mixes footer/sidebar links with the opera card list; Palermo's
    season page contains a distinct concerts section after opere e balletti.
    """
    def __init__(self,key:str):
        super().__init__(convert_charrefs=True)
        self.key=key
        self.links=[]
        self.in_section=False
        self.heading=None
        self.heading_text=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("h1","h2"):
            self.heading=tag
            self.heading_text=[]
        if tag=="footer":
            self.in_section=False
        if tag=="a" and self.in_section:
            href=dict(attrs).get("href")
            if isinstance(href,str):self.links.append(href)
    def handle_data(self,data):
        if self.heading is not None:self.heading_text.append(data)
    def handle_endtag(self,tag):
        if tag==self.heading:
            label=" ".join(" ".join(self.heading_text).upper().split())
            if self.key=="parma-opera-2027" and tag=="h1":
                if label=="OPERA":self.in_section=True
                elif self.in_section:self.in_section=False
            if self.key=="massimo-season-2026-27" and tag=="h2":
                if "CALENDARIO OPERE E BALLETTI" in label:self.in_section=True
                elif self.in_section:self.in_section=False
            self.heading=None
            self.heading_text=[]

def eligible(key:str,url:str)->bool:
    path=urlsplit(url).path.lower().rstrip("/")
    if excluded_nonopera(key,url):
        return False
    if key=="scala-season-2026-27":
        match=re.fullmatch(r"/it/stagione/(20\d{2})-(20\d{2})/opera/[a-z0-9-]+\.html",path)
        return bool(match and int(match.group(2))==int(match.group(1))+1)
    if key=="arena-festival-2027":
        rest=path.removeprefix("/arena-opera-festival/")
        return (path.startswith("/arena-opera-festival/") and
                bool(rest) and "/" not in rest and
                rest not in {"spettacoli","calendario","biglietti",
                             "arena-per-tutti","programma","festival"})
    if key=="fenice-opera-2026-27":
        return path.startswith("/event/") and bool(path.removeprefix("/event/"))
    if key=="carlo-felice-season-2026-27":
        return bool(re.fullmatch(r"/spettacolo/[a-z0-9-]+",path))
    if key=="parma-opera-2027":
        return path.startswith("/spettacolo/") and bool(path.removeprefix("/spettacolo/"))
    if key=="massimo-season-2026-27":
        return path.startswith("/event/") and bool(path.removeprefix("/event/"))
    raise ValueError("unknown season index key")

def extract(key:str,index_url:str,html:str,min_links:int)->list[str]:
    parser=(ScopedSeasonAnchors(key)
            if key in {"parma-opera-2027","massimo-season-2026-27"}
            else AnchorParser())
    parser.feed(html)
    hostname=urlsplit(index_url).hostname
    result=set()
    for href in parser.links:
        url=urljoin(index_url,href)
        parsed=urlsplit(url)
        if parsed.scheme!="https" or parsed.hostname!=hostname or parsed.username or parsed.password or parsed.port is not None:
            continue
        if parsed.query or parsed.fragment:
            continue
        if eligible(key,url):
            result.add(url)
    if len(result)<min_links:
        raise ValueError("season index incomplete or structure changed")
    return sorted(result)

def validate_config(config:dict)->list[dict]:
    if config.get("schema_version")!=1 or not isinstance(config.get("sources"),list):
        raise ValueError("invalid season index configuration")
    allowed={
        "scala-season-2026-27":("www.teatroallascala.org","/it/stagione/2026-2027/index.html"),
        "arena-festival-2027":("www.arena.it","/arena-opera-festival/spettacoli/"),
        "fenice-opera-2026-27":("www.teatrolafenice.it","/event-category/opera-2026-27/"),
        "parma-opera-2027":("teatroregioparma.it","/categoria-spettacoli/opera/"),
        "massimo-season-2026-27":("www.teatromassimo.it","/la-stagione-2026-27/"),
        "carlo-felice-season-2026-27":("www.carlofelice.it","/rassegna-stagione-opera-danza-musical-2026-27/"),
    }
    seen=set()
    for item in config["sources"]:
        if set(item)!={"key","url","official_url","access_status","min_links"}:
            raise ValueError("invalid index source fields")
        key=item["key"]
        if key not in allowed or key in seen:raise ValueError("unknown or duplicate index")
        seen.add(key)
        index=urlsplit(item["url"])
        host,path=allowed[key]
        if key in ("scala-season-2026-27","fenice-opera-2026-27",
                   "massimo-season-2026-27"):
            if key=="scala-season-2026-27":
                season=re.fullmatch(r"/it/stagione/(20\d{2})-(20\d{2})/index\.html",
                                    index.path)
                valid_season=bool(season and int(season[2])==int(season[1])+1
                                  and 2026<=int(season[1])<=2098)
            else:
                pattern=(r"/event-category/opera-(20\d{2})-(\d{2})/"
                         if key=="fenice-opera-2026-27"
                         else r"/la-stagione-(20\d{2})-(\d{2})/")
                season=re.fullmatch(pattern,index.path)
                valid_season=bool(season and
                    (int(season[1])+1)%100==int(season[2]) and
                    2026<=int(season[1])<=2098)
        elif key=="carlo-felice-season-2026-27":
            season=re.fullmatch(r"/rassegna-stagione-opera-danza-musical-(20\d{2})-(\d{2})/",index.path)
            valid_season=bool(season and (int(season[1])+1)%100==int(season[2]) and 2026<=int(season[1])<=2098)
        else:
            valid_season=index.path==path
        if (index.scheme!="https" or index.hostname!=host or not valid_season
            or index.query or index.fragment or index.port is not None
            or item["official_url"]!="https://"+host+"/"):
            raise ValueError("index URL outside exact official allowlist")
        if item["access_status"] not in {"approved","pending","blocked"}:
            raise ValueError("invalid access status")
        if not isinstance(item["min_links"],int) or not 1<=item["min_links"]<=30:
            raise ValueError("invalid index completeness threshold")
    if seen!=set(allowed):raise ValueError("missing national index source")
    return config["sources"]

def scan(config:dict,existing:dict,*,fetcher=fetch_official_html,
         network_enabled:bool=False,now:str|None=None):
    entries=validate_config(config)
    if existing.get("schema_version")!=1 or not isinstance(existing.get("candidates"),list):
        raise ValueError("invalid index candidate registry")
    seen={x["id"]:x.copy() for x in existing["candidates"]}
    reviewed=reviewed_source_urls()
    # Reconcile the historical 45 raw links from the first successful live
    # scan, keeping the audit trail rather than silently deleting entries.
    for candidate in seen.values():
        if candidate.get("status") in ("needs_review","excluded_nonopera","already_catalogued"):
            candidate["status"]=classify(candidate["source_key"],candidate["official_url"],reviewed)
    statuses=[]
    timestamp=now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    db=connect()
    try:
        migrate(db)
        for item in entries:
            if item["access_status"]!="approved":
                statuses.append({"key":item["key"],"status":item["access_status"],"links":0})
                continue
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",(item["official_url"],))
                row=db.execute("SELECT id FROM sources WHERE official_url=?",(item["official_url"],)).fetchone()
                page=fetcher(db,source_id=row["id"],url=item["url"],network_enabled=True)
                urls=extract(item["key"],item["url"],page.html,item["min_links"])
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                statuses.append({"key":item["key"],"status":"unavailable_or_invalid",
                                 "reason":type(exc).__name__,"links":0})
                continue
            for url in urls:
                uid="oa-index-"+hashlib.sha256((item["key"]+"|"+url).encode()).hexdigest()[:20]
                if uid not in seen:
                    seen[uid]={"id":uid,"source_key":item["key"],
                               "official_url":url,"status":classify(item["key"],url,reviewed),
                               "first_seen":timestamp,"last_seen":timestamp}
                elif seen[uid]["status"]=="needs_review":
                    seen[uid]["last_seen"]=timestamp
            statuses.append({"key":item["key"],"status":"success","links":len(urls),
                             "new_review_candidates":sum(
                                 x["source_key"]==item["key"] and x["status"]=="needs_review"
                                 for x in seen.values())})
    finally:
        db.close()
    return {"schema_version":1,"candidates":sorted(seen.values(),key=lambda x:x["id"])},statuses

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    args=parser.parse_args()
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    current=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"schema_version":1,"candidates":[]}
    result,health=scan(config,current,network_enabled=args.allow_network)
    _write_atomic(OUTPUT,result)
    _write_atomic(PUBLIC,result)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"sources":health})
    print(json.dumps({"candidates":len(result["candidates"]),"sources":health}))

if __name__=="__main__":
    main()
