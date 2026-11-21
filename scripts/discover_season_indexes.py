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
    "donizetti-opera-2026": frozenset(),
    "teatro-grande-opera-2026": frozenset(),
    "carlo-felice-season-2026-27": frozenset({
        "lo-schiaccianoci", "giselle", "il-lago-dei-cigni",
        "deledda", "sergio-bernal-dance-company",
        "the-phantom-of-the-opera",
    }),
    "petruzzelli-opera-2026": frozenset({
        # Official programme title is the classical ballet, not an opera.
        "le-lac-des-cygnes-il-lago-dei-cigni-12-15-novembre",
    }),
    "petruzzelli-opera-2027": frozenset({
        # Tchaikovsky\u0027s Nutcracker is a ballet, even in an opera/ballet index.
        "lo-schiaccianoci-di-petr-ilic-cajkovskij-11-14-febbraio",
    }),
    "opera-roma-season-2026-27": frozenset({
        # The official production credits specify a spoken theatrical text
        # with music by various authors, not an individually composed opera.
        # Never conflate this title with Rossini's La Cenerentola.
        "le-cenerentole-quattro-donne-una-storia",
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
    """URLs already published as a canonical opera OR a verified program.

    A multi-work program is one ticketed event. Its official URL must leave
    the candidate queue just as a solo staging does; never infer publication
    merely from the presence of a source URL in an evidence checkpoint.
    """
    from scripts.build_verified_catalog import MANIFEST
    document=json.loads(MANIFEST.read_text(encoding="utf-8"))
    reviewed={row["source_url"] for row in document["productions"]}
    programs=ROOT/"public"/"catalog"/"programs.json"
    if programs.exists():
        feed=json.loads(programs.read_text(encoding="utf-8"))
        if feed.get("schema_version")!=1 or not isinstance(feed.get("programs"),list):
            raise ValueError("invalid published program feed")
        for item in feed["programs"]:
            if (not isinstance(item,dict)
                or not isinstance(item.get("source_url"),str)
                or not isinstance(item.get("source_key"),str)
                or not eligible(item["source_key"],item["source_url"])
                or not isinstance(item.get("components"),list)
                or len(item["components"])<2
                or not isinstance(item.get("performances"),list)
                or not item["performances"]):
                raise ValueError("unverified program in published feed")
            reviewed.add(item["source_url"])
    return reviewed

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
        self.in_anchor=0
        self.in_navigation=0
        self.season_heading_tail=""
    def handle_starttag(self,tag,attrs):
        if tag in ("h1","h2"):
            self.heading=tag
            self.heading_text=[]
        if tag in ("nav","footer"):
            self.in_navigation+=1
            if tag=="footer":self.in_section=False
        if tag=="a":
            if self.in_section and not self.in_navigation:
                href=dict(attrs).get("href")
                if isinstance(href,str):self.links.append(href)
            self.in_anchor+=1
    def handle_data(self,data):
        if self.heading is not None:self.heading_text.append(data)
        if (self.key in ("petruzzelli-opera-2026","petruzzelli-opera-2027")
                and not self.in_anchor and not self.in_navigation):
            # The live Petruzzelli WordPress page renders the year-specific
            # label as an ordinary element, not necessarily as h1/h2.
            # Only an exact, non-navigation year heading opens the scope.
            # The year and label may arrive as separate HTML text nodes
            # (for example inside nested Elementor spans). Limit buffered
            # context to one short heading, never matching navigation links.
            self.season_heading_tail=(" ".join(
                (self.season_heading_tail+" "+data.upper()).split()))[-160:]
            year=self.key.rsplit("-",1)[-1]
            for match in re.finditer(r"(?<![A-Z0-9])OPERA E BALLETTO (20[0-9]{2})(?![0-9])",
                                     self.season_heading_tail):
                self.in_section=(match.group(1)==year)
                self.season_heading_tail=""
                break
    def handle_endtag(self,tag):
        if tag=="a":
            self.in_anchor=max(0,self.in_anchor-1)
        if tag in ("nav","footer"):
            self.in_navigation=max(0,self.in_navigation-1)
        if tag==self.heading:
            label=" ".join(" ".join(self.heading_text).upper().split())
            if self.key=="parma-opera-2027" and tag=="h1":
                if label=="OPERA":self.in_section=True
                elif self.in_section:self.in_section=False
            if self.key=="donizetti-opera-2026" and tag=="h1":
                if label=="OPERE 2026":self.in_section=True
                elif self.in_section:self.in_section=False
            if self.key=="teatro-grande-opera-2026" and tag=="h2":
                if label=="OPERA E BALLETTO":self.in_section=True
                elif self.in_section:self.in_section=False
            if self.key=="massimo-season-2026-27" and tag=="h2":
                if "CALENDARIO OPERE E BALLETTI" in label:self.in_section=True
                elif self.in_section:self.in_section=False
            self.heading=None
            self.heading_text=[]

def eligible(key:str,url:str)->bool:
    parsed=urlsplit(url)
    if parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port is not None:
        return False
    path=parsed.path.lower().rstrip("/")
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
    if key=="donizetti-opera-2026":
        # The official 2026 programme links Alahor to a dated event URL.
        # Accept only the three independently identified opera titles,
        # never general festival events such as brunches or youth previews.
        match=re.fullmatch(
            r"/it/evento/(l-esule-di-roma|alahor-in-granata|"
            r"le-convenienze-ed-inconvenienze-teatrali)"
            r"(?:/(20\d{2}-\d{2}-\d{2}))?",path)
        if not match:return False
        if match[2]:
            from datetime import date
            try:
                if date.fromisoformat(match[2]).year!=2026:return False
            except ValueError:return False
        return True
    if key=="teatro-grande-opera-2026":
        return bool(re.fullmatch(r"/it/stagioni/20\d{2}/[a-z0-9-]+",path))
    if key=="maggio-fiorentino-calendar-2027":
        return bool(re.fullmatch(r"/events/[a-z0-9-]+",path))
    if key=="opera-roma-season-2026-27":
        return bool(re.fullmatch(r"/spettacoli/[a-z0-9-]+",path))
    if key in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
        return bool(re.fullmatch(r"/eventi/[a-z0-9-]+",path))
    if key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
        return bool(re.fullmatch(r"/evento/opera/[a-z0-9-]+-20\d{2}",path))
    if key=="giglio-lucca-opera-2026-27":
        return bool(re.fullmatch(r"/it/cartellone/lirica/stagione-2026-2027/[a-z0-9-]+",path))
    if key=="modena-opera-2026-27":
        return bool(re.fullmatch(
            r"/vivere-modena/eventi/2026/stagione-opera-2026-2027/[a-z0-9-]+",path))
    if key=="bellini-catania-opera-2026-27":
        return bool(re.fullmatch(r"/eventi/[a-z0-9-]+",path))
    if key=="lirico-cagliari-opera-2027":
        return (bool(re.fullmatch(r"/evento/[a-z0-9-]+",path))
                and not path.startswith("/evento/parliamo-dopera")
                and not path.startswith("/evento/parliamo-d-opera"))
    if key=="verdi-trieste-season-2026-27":
        return bool(re.fullmatch(r"/it/spettacoli/[a-z0-9-]+",path))
    if key=="carlo-felice-season-2026-27":
        return bool(re.fullmatch(r"/spettacolo/[a-z0-9-]+",path))
    if key=="parma-opera-2027":
        return path.startswith("/spettacolo/") and bool(path.removeprefix("/spettacolo/"))
    if key=="massimo-season-2026-27":
        return path.startswith("/event/") and bool(path.removeprefix("/event/"))
    raise ValueError("unknown season index key")

def extract(key:str,index_url:str,html:str,min_links:int)->list[str]:
    parser=(ScopedSeasonAnchors(key)
            if key in {"parma-opera-2027","massimo-season-2026-27",
                       "donizetti-opera-2026","teatro-grande-opera-2026",
                       "petruzzelli-opera-2026","petruzzelli-opera-2027"}
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
        "donizetti-opera-2026":("www.donizettiopera.org","/it/opere-2026/"),
        "teatro-grande-opera-2026":("teatrogrande.it","/it"),
        "maggio-fiorentino-calendar-2027":("www.maggiofiorentino.com","/calendario/2027/01/opera"),
        "opera-roma-season-2026-27":("www.operaroma.it","/genre/opera/"),
        "bologna-comunale-opera-2026":("www.tcbo.it","/stagione-presente/"),
        "bologna-comunale-opera-2027":("www.tcbo.it","/stagione-futura/"),
        "petruzzelli-opera-2026":("www.fondazionepetruzzelli.it","/opera-e-balletto-2026/"),
        "petruzzelli-opera-2027":("www.fondazionepetruzzelli.it","/opera-e-balletto-2027/"),
        "verdi-trieste-season-2026-27":("www.teatroverdi-trieste.com","/it/calendario-spettacoli/"),
        "lirico-cagliari-opera-2027":("www.liricocagliari.it","/categoria-evento/opera/"),
        "bellini-catania-opera-2026-27":("www.teatromassimobellini.it","/opere-e-balletto/"),
        "modena-opera-2026-27":("www.comune.modena.it","/vivere-modena/eventi/2026/stagione-opera-2026-2027"),
        "giglio-lucca-opera-2026-27":("www.teatrodelgigliogiacomopuccini.it","/it/cartellone/lirica/stagione-2026-2027/"),
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
        elif key=="donizetti-opera-2026":
            season=re.fullmatch(r"/it/opere-(20\d{2})/",index.path)
            valid_season=bool(season and 2026<=int(season[1])<=2098)
        elif key=="teatro-grande-opera-2026":
            valid_season=index.path=="/it"
        elif key=="maggio-fiorentino-calendar-2027":
            valid_season=bool(re.fullmatch(r"/calendario/20\d{2}/01/opera",index.path)
                              and index.path.startswith("/calendario/2027/"))
        elif key=="giglio-lucca-opera-2026-27":
            valid_season=(index.path=="/it/cartellone/lirica/stagione-2026-2027/" and not index.query)
        elif key=="modena-opera-2026-27":
            valid_season=(index.path=="/vivere-modena/eventi/2026/stagione-opera-2026-2027"
                          and not index.query)
        elif key=="bellini-catania-opera-2026-27":
            valid_season=index.path=="/opere-e-balletto/" and not index.query
        elif key=="lirico-cagliari-opera-2027":
            valid_season=index.path=="/categoria-evento/opera/" and not index.query
        elif key=="verdi-trieste-season-2026-27":
            valid_season=(index.path=="/it/calendario-spettacoli/" and
                          index.query=="a=0&t=lirica")
        elif key=="opera-roma-season-2026-27":
            valid_season=index.path=="/genre/opera/"
        elif key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
            valid_season=(index.path==("/stagione-presente/" if key.endswith("-2026") else "/stagione-futura/")
                          and index.query=="_tipo=opera")
        elif key in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
            valid_season=bool(re.fullmatch(r"/opera-e-balletto-20\d{2}/",index.path)
                              and index.path=="/opera-e-balletto-"+key.rsplit("-",1)[-1]+"/")
        elif key=="carlo-felice-season-2026-27":
            season=re.fullmatch(r"/rassegna-stagione-opera-danza-musical-(20\d{2})-(\d{2})/",index.path)
            valid_season=bool(season and (int(season[1])+1)%100==int(season[2]) and 2026<=int(season[1])<=2098)
        else:
            valid_season=index.path==path
        if (index.scheme!="https" or index.hostname!=host or not valid_season
            or (index.query and key not in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027","verdi-trieste-season-2026-27")) or index.fragment or index.port is not None
            or item["official_url"]!="https://"+host+"/"):
            raise ValueError("index URL outside exact official allowlist")
        if item["access_status"] not in {"approved","pending","blocked"}:
            raise ValueError("invalid access status")
        if not isinstance(item["min_links"],int) or not 1<=item["min_links"]<=30:
            raise ValueError("invalid index completeness threshold")
    if seen!=set(allowed):raise ValueError("missing national index source")
    return config["sources"]

def reconcile_season_absences(seen:dict,source_key:str,verified_urls:list[str])->None:
    """Audit obsolete Petruzzelli links only after a verified season scan.

    An old production linked in unrelated navigation is not evidence of a
    performance in 2027. Preserve its record but stop scheduling editorial
    retries. If it reappears in a later official season scan, restore it.
    """
    if source_key not in ("petruzzelli-opera-2026","petruzzelli-opera-2027"):
        return
    current=set(verified_urls)
    reviewed=reviewed_source_urls()
    for record in seen.values():
        if record.get("source_key")!=source_key:
            continue
        if record.get("official_url") in current:
            if record.get("status")=="not_in_official_season":
                record["status"]=classify(source_key,record["official_url"],reviewed)
        elif record.get("status")=="needs_review":
            record["status"]="not_in_official_season"


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
                primary_unavailable=False
                index_url=item["url"]
                min_links=item["min_links"]
                try:
                    page=fetcher(db,source_id=row["id"],url=index_url,network_enabled=True)
                except FetchUnavailable as original:
                    # A failed HTML response on Rome's first official index
                    # need not lose all coverage: the *same* approved theatre
                    # has a second page, read through the same robots gate.
                    # Never retry or switch URLs if robots is inaccessible.
                    if (item["key"]!="opera-roma-season-2026-27" or
                        str(original) not in (
                          "page unavailable","unexpected HTTP status",
                          "not an HTML page","HTML response too large")):
                        raise
                    index_url=index_url.rstrip("/")+"/page/2/"
                    page=fetcher(db,source_id=row["id"],url=index_url,network_enabled=True)
                    min_links=1
                    primary_unavailable=True
                try:
                    urls=extract(item["key"],index_url,page.html,min_links)
                except ValueError as exc:
                    # TCBO's current-season opera filter explicitly reports
                    # zero results when its programme has no remaining operas.
                    # Accept only this exact filtered empty state and only if
                    # no eligible opera links were present in the HTML.
                    if (item["key"]=="bologna-comunale-opera-2026"
                        and str(exc)=="season index incomplete or structure changed"
                        and "Nessun evento trovato" in page.html):
                        anchors=AnchorParser()
                        anchors.feed(page.html)
                        actual=[href for href in anchors.links
                                if eligible(item["key"],urljoin(item["url"],href))]
                        if not actual:
                            urls=[]
                        else:
                            raise
                    else:
                        raise
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                # Keep exceptions from upstream retrieval out of public
                # diagnostics. Report deterministic, actionable failure
                # categories without exposing source content or tokens.
                if isinstance(exc,AccessDenied):
                    diagnostic="access_denied_or_robots_disallowed"
                elif isinstance(exc,FetchUnavailable):
                    # Preserve operational stage without copying the remote
                    # exception body, response or page contents into health.
                    # Every source uses exactly the same safe taxonomy.
                    cause=str(exc)
                    if cause.startswith("robots.txt"):
                        diagnostic="official_robots_unavailable_or_invalid"
                    elif cause in ("page unavailable","unexpected HTTP status",
                                   "not an HTML page","HTML response too large"):
                        diagnostic="official_html_unavailable_or_invalid"
                    else:
                        diagnostic="official_source_unavailable"
                elif str(exc)=="season index incomplete or structure changed":
                    diagnostic="index_incomplete_or_markup_changed"
                else:
                    diagnostic="invalid_index_or_source_config"
                statuses.append({"key":item["key"],"status":"unavailable_or_invalid",
                                 "reason":type(exc).__name__,"diagnostic":diagnostic,
                                 "required_links":item["min_links"],"links":0})
                continue
            page_health={}
            if primary_unavailable:
                page_health={"pages_checked":1,"pagination_complete":False,
                             "diagnostic":"primary_official_html_unavailable"}
            elif item["key"]=="opera-roma-season-2026-27":
                # The official genre lists the current season across two
                # pages. Read both from the exact approved host, with the
                # ordinary per-request robots gate and a hard two-page cap.
                # An unavailable second page makes coverage explicitly
                # partial, without dropping the verified first-page links.
                second=item["url"].rstrip("/")+"/page/2/"
                try:
                    other=fetcher(db,source_id=row["id"],url=second,network_enabled=True)
                    extra=extract(item["key"],second,other.html,1)
                    urls=sorted(set(urls).union(extra))
                    page_health={"pages_checked":2,"pagination_complete":True}
                except (AccessDenied,FetchUnavailable,ValueError):
                    page_health={"pages_checked":1,"pagination_complete":False,
                                 "diagnostic":"secondary_page_unavailable_or_invalid"}
            reconcile_season_absences(seen,item["key"],urls)
            for url in urls:
                uid="oa-index-"+hashlib.sha256((item["key"]+"|"+url).encode()).hexdigest()[:20]
                if uid not in seen:
                    seen[uid]={"id":uid,"source_key":item["key"],
                               "official_url":url,"status":classify(item["key"],url,reviewed),
                               "first_seen":timestamp,"last_seen":timestamp}
                elif seen[uid]["status"]=="needs_review":
                    seen[uid]["last_seen"]=timestamp
            statuses.append({"key":item["key"],
                             "status":("partial_pagination" if page_health and
                                       not page_health["pagination_complete"] else "success"),
                             **page_health,
                             "links":len(urls),
                             "empty_official_opera_calendar":(
                                 item["key"]=="bologna-comunale-opera-2026" and len(urls)==0),
                             "required_links":item["min_links"],
                             "new_review_candidates":sum(
                                 x["source_key"]==item["key"] and x["status"]=="needs_review"
                                 for x in seen.values())})
    finally:
        db.close()
    return {"schema_version":1,"candidates":sorted(seen.values(),key=lambda x:x["id"])},statuses

def source_health_history(current:list[dict],previous:dict,*,checked_at:str):
    """Remember the last verified index independently of today's failures.

    A failed scan leaves candidate URLs intact but is NOT labelled healthy.
    last_success_at is never manufactured for sources with no prior success.
    """
    prior_rows=previous.get("sources",[]) if previous.get("schema_version")==1 else []
    prior={item["key"]:item for item in prior_rows
           if isinstance(item,dict) and isinstance(item.get("key"),str)}
    rows=[]
    for row in current:
        old=prior.get(row["key"],{})
        previous_ok=old.get("last_success_at")
        if previous_ok is None and old.get("status")=="success":
            previous_ok=previous.get("checked_at")
        last_links=old.get("last_successful_links")
        if last_links is None and old.get("status")=="success":
            last_links=old.get("links")
        fresh=row.get("status")=="success"
        rows.append({**row,
                     "last_attempt_at":checked_at,
                     "last_success_at":checked_at if fresh else previous_ok,
                     "last_successful_links":row["links"] if fresh else last_links,
                     "current_scan_verified":fresh})
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    args=parser.parse_args()
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    current=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"schema_version":1,"candidates":[]}
    result,health=scan(config,current,network_enabled=args.allow_network)
    checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    previous=json.loads(HEALTH.read_text(encoding="utf-8")) if HEALTH.exists() else {}
    health=source_health_history(health,previous,checked_at=checked_at)
    _write_atomic(OUTPUT,result)
    _write_atomic(PUBLIC,result)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":checked_at,"sources":health})
    print(json.dumps({"candidates":len(result["candidates"]),
                      "healthy_sources":sum(x["current_scan_verified"] for x in health),
                      "unverified_sources":[{"key":x["key"],"diagnostic":x.get("diagnostic","not_approved")}
                                            for x in health if not x["current_scan_verified"]],
                      "sources":health}))

if __name__=="__main__":
    main()
