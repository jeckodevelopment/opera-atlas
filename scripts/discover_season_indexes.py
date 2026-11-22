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
EXCLUDED_HAYDN_ANCILLARY=re.compile(
    r"(?i)^(?:oper-a-intro(?:-[0-9]+)?|oper-a-backstage-under-35(?:-[0-9]+)?|"
    r"dai-libri-allopera(?:-[0-9]+)?)$"
)
EXCLUDED_PATHS={
    # Exact published 2026 ROF concert, outreach and recital pages.
    # Keep productions such as Il viaggio a Reims, La scala di seta,
    # L'occasione fa il ladro and Le siège de Corinthe eligible.
    "pesaro-rof-2026": frozenset({
        "concerti-di-belcanto", "festival-giovane", "stabat-mater",
        "florez-30",
        "incontri", "rossinimania",
    }),
    # The festival mixes opera with chamber concerts, pop and jazz.
    # Exclusions require individually recognisable original programme slugs;
    # no global keyword or "family" exclusion is permitted.
    "trapani-luglio-musicale-2026": frozenset({
        "new-saxophone-orchestra",
        "duo-resonans",
        "duo-monica-leone-michele-campanella",
        "quartetto-vocale-faraualla",
        "omaggio-a-lelio-luttazzi",
        "orchestra-nazionale-barocca-dei-conservatori",
        "concerto-di-natale",
        "concerto-di-capodanno",
        "sicily-jazz-concert",
        # The official 2026 genre index labels these as dance and concerts.
        "romeo-e-giulietta", "food-ensemble", "quintetto-sospeso",
        # First-party 2026 season lists these as chamber/choral concerts,
        # not operatic productions.
        "american-dream", "requiem-k-626", "verdi-sogno-e-passione",
        "passantino-incontra-brioschi",
        "bruno-canino",
        "omaggio-a-bowie-cohen-michael-e-prince",
        "lidia-schillaci-canta-i-grandi-cantautori-italiani",
    }),
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
        # Official RegioInsieme describes this as a transmedia,
        # site-specific reinterpretation using selected Otello numbers,
        # not a ticket for Verdi's complete canonical opera.
        "otello-gamification",

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
    "bellini-catania-opera-2026-27": frozenset({
        # Official Bellini season press release identifies La bella
        # addormentata (1–6 December 2026, Metropolitan) as a ballet in
        # three acts by Tchaikovsky. An Opera e Balletto calendar alone
        # cannot establish operatic genre. The two Sangiorgi chamber operas
        # from the same official index remain reviewable.
        "la-bella-addormentata-5",
    }),
    # Confirmed non-lyric stage production: Lucio Dalla songs are arranged
    # into a contemporary pop-opera. Atlas indexes only lyric operas.
    "modena-teatro-opera-2026-27": frozenset({"lanno-che-verra", "leos-janacek-thomas-ades-vanishings"}),
    "giglio-lucca-opera-2026-27": frozenset({"lanno-che-verra"}),
    "piacenza-opera-2026-27": frozenset({"lanno-che-verra"}),
    "donizetti-opera-2026": frozenset(),
    "teatro-grande-opera-2026": frozenset(),
    "coccia-novara-rolling-opera": frozenset({
        # Exact 2027 Coccia production pages. The official breadcrumb
        # identifies the first two as Danza, and Beethoven 200 as Concerto.
        # Never exclude other works from this mixed-genre theatre index.
        "stagione-27-la-bella-addormentata.html",
        "stagione-27-il-lago-dei-cigni.html",
        "stagione-27-beethoven-200.html",
    }),
    "carlo-felice-season-2026-27": frozenset({
        "lo-schiaccianoci", "giselle", "il-lago-dei-cigni",
        "deledda", "sergio-bernal-dance-company",
        "the-phantom-of-the-opera",
    }),
    "petruzzelli-opera-2026": frozenset({
        # Official programme title is the classical ballet, not an opera.
        "le-lac-des-cygnes-il-lago-dei-cigni-12-15-novembre",
    }),
    # The Haydn first-party page identifies a children's *interactive musical*
    # based on Rossini, rather than a full staging of his canonical opera.
    # Ticketed Family access does not by itself establish operatic identity.
    "haydn-rolling-opera": frozenset({
        "il-barbiere-di-siviglia-e-la-rosa-incantata",
    }),
    "asti-alfieri-rolling-opera": frozenset({"concerto-di-capodanno"}),
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
    # Valle d'Itria individual entries end in an ISO date, so classification
    # must compare the full approved production URL rather than its final slug.
    if key=="martina-valle-itria-2026" and url in {
        "https://www.festivaldellavalleditria.it/spettacolo/vennero-da-ogni-dove/2026-07-20",
        "https://www.festivaldellavalleditria.it/spettacolo/approfondimenti/2026-07-18",
        "https://www.festivaldellavalleditria.it/spettacolo/in-orbita-naufragi/2026-07-10",
    }:
        return True
    slug=urlsplit(url).path.rstrip("/").split("/")[-1]
    # The Haydn Opera-area index includes independent educational talks,
    # backstage events and reading events, not ticketed operas. Classify only
    # those exact evergreen title families as ancillary; never use a broad
    # keyword such as "opera", which would hide genuine new commissions.
    if key=="haydn-rolling-opera" and EXCLUDED_HAYDN_ANCILLARY.fullmatch(slug):
        return True
    return slug in EXCLUDED_PATHS.get(key,frozenset())

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
    # Keep this exact regional season URL eligible as a programme/PDF
    # discovery source, but never treat its full-season date range as a
    # single opera ticket. Individual municipal opera candidates remain live.
    if (key=="rovigo-regione-programma-2026-27"
        and url=="https://www.culturaveneto.it/spettacoli/musica/3563a671-d9b2-46bf-a10d-776af9ab17bc"):
        return "excluded_nonopera"
    if key=="savona-giocosa-rolling-opera":
        # One evergreen index contains independent works and recite; an URL
        # match to one published staging never closes the entire source.
        return "needs_review"
    if excluded_nonopera(key,url):
        return "excluded_nonopera"
    if key in {
        "jesi-trittico-opera-2026","jesi-don-pasquale-opera-2026",
        "jesi-esecuzione-opera-2026","jesi-nabucco-opera-2026",
        "ancona-elisir-opera-2026","ancona-cavalleria-program-2026"}:
        from opera_atlas.marche_2026_parser import PRODUCTIONS,canon
        from scripts.build_verified_catalog import MANIFEST
        selected=PRODUCTIONS[key]
        if selected[5] is not None:
            programs=ROOT/"public"/"catalog"/"programs.json"
            if programs.exists():
                data=json.loads(programs.read_text(encoding="utf-8"))
                if any(x.get("source_key")==key and x.get("source_url")==url
                       for x in data.get("programs",[])):
                    return "already_catalogued"
            return "needs_review"
        catalog=json.loads(MANIFEST.read_text(encoding="utf-8"))
        matches=[x for x in catalog.get("productions",[])
                 if x.get("source_url")==url
                 and x.get("municipality")==("Jesi" if key.startswith("jesi-") else "Ancona")
                 and x.get("venue")==selected[1]
                 and canon(x.get("title",""))==canon(selected[2])
                 and canon(x.get("composer",""))==canon(selected[3])]
        return "already_catalogued" if len(matches)==1 else "needs_review"
    if key.startswith("goldoni-livorno-") and key.endswith("-2026-27"):
        from opera_atlas.livorno_opera_parser import SOURCES
        from scripts.build_verified_catalog import MANIFEST
        from scripts.publish_catalog_v2 import normalized
        identity=SOURCES.get(key)
        if identity is None:return "needs_review"
        published=json.loads(MANIFEST.read_text(encoding="utf-8"))
        matching=[p for p in published.get("productions",[])
                  if p.get("source_url")==url and p.get("municipality")=="Livorno"
                  and p.get("venue")=="Teatro Goldoni"
                  and normalized(p.get("title",""))==normalized(identity[0])
                  and normalized(p.get("composer",""))==normalized(identity[1])]
        return "already_catalogued" if len(matching)==1 else "needs_review"
    if key.startswith("ferrara-") and key.endswith("-opera-2026-27"):
        # All five independently verified works share the same exact regional
        # season URL. A published Macbeth must never close the other four
        # candidates merely because they share that official page.
        from opera_atlas.ferrara_regional_parser import records,fold
        from scripts.build_verified_catalog import MANIFEST
        work=records().get(key)
        if work is None:return "needs_review"
        published=json.loads(MANIFEST.read_text(encoding="utf-8"))
        matching=[x for x in published.get("productions",[])
                  if x.get("source_url")==url
                  and fold(x.get("title",""))==fold(work["title"])
                  and fold(x.get("composer",""))==fold(work["composer"])
                  and x.get("municipality")=="Ferrara"
                  and x.get("venue")=="Teatro Comunale Claudio Abbado"]
        return "already_catalogued" if len(matching)==1 else "needs_review"
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
    def __init__(self,key:str,season_year:int|None=None):
        super().__init__(convert_charrefs=True)
        self.key=key
        self.season_year=season_year
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
            year=str(self.season_year) if self.season_year is not None else self.key.rsplit("-",1)[-1]
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
            if self.key in ("donizetti-opera-2026","donizetti-opera-2027") and tag=="h1":
                year=self.season_year or (2027 if self.key.endswith("2027") else 2026)
                if label=="OPERE "+str(year):self.in_section=True
                elif self.in_section:self.in_section=False
            if self.key=="teatro-grande-opera-2026" and tag=="h2":
                if label=="OPERA E BALLETTO":self.in_section=True
                elif self.in_section:self.in_section=False
            if self.key=="reggio-valli-opera-2026-27":
                if tag=="h1" and label.startswith("OPERA STAGIONE"):
                    self.in_section=True
                if tag=="h2" and label=="IN EVIDENZA":
                    self.in_section=False
            if self.key=="piacenza-opera-2026-27" and tag=="h2":
                # The Fondazione season mixes Opera with Concerti, Danza,
                # Young and Eventi. Only the Opera section is approved.
                self.in_section=(label=="OPERA")
            if self.key=="massimo-season-2026-27" and tag=="h2":
                if "CALENDARIO OPERE E BALLETTI" in label:self.in_section=True
                elif self.in_section:self.in_section=False
            self.heading=None
            self.heading_text=[]

def eligible(key:str,url:str)->bool:
    parsed=urlsplit(url)
    if key=="mantova-sociale-rolling-opera":
        from opera_atlas.mantova_sociale_opera import eligible_detail
        return eligible_detail(url)
    if key=="napoli-san-carlo-rolling-opera":
        from opera_atlas.napoli_san_carlo import eligible_detail
        return eligible_detail(url)
    if key=="pesaro-rof-2026":
        from opera_atlas.pesaro_rof import eligible_detail
        return eligible_detail(url)
    if key=="martina-valle-itria-2026":
        from opera_atlas.martina_valle_itria import eligible_detail
        return eligible_detail(url)
    if key=="trapani-luglio-musicale-2026":
        from opera_atlas.trapani_luglio_opera import eligible_detail
        return eligible_detail(url)
    if key=="haydn-rolling-opera":
        from opera_atlas.haydn_rolling_opera import eligible_detail
        return eligible_detail(url)
    if key=="asti-alfieri-rolling-opera":
        from opera_atlas.asti_alfieri_parser import eligible_detail
        return eligible_detail(url)
    if key=="savona-giocosa-rolling-opera":
        return (parsed.scheme=="https" and parsed.hostname=="operagiocosa.it"
                and parsed.path=="/" and not parsed.query and not parsed.fragment
                and not parsed.username and not parsed.password and parsed.port is None)
    if key=="sassari-de-carolis-rolling-opera":
        from opera_atlas.sassari_future_parser import eligible_detail
        return eligible_detail(url)
    if key=="goldoni-livorno-rolling-lirica":
        from opera_atlas.livorno_future_parser import eligible_detail
        return eligible_detail(url)
    if key=="ravenna-cherubini-rolling-opera":
        from opera_atlas.ravenna_future_parser import eligible_detail
        return eligible_detail(url)
    if key=="macerata-festival-rolling":
        from opera_atlas.macerata_future_parser import eligible_detail
        return eligible_detail(url)
    if key=="salerno-verdi-rolling-opera":
        from opera_atlas.salerno_future_parser import eligible_detail
        return eligible_detail(url)
    if key=="filarmonico-verona-rolling-opera":
        from opera_atlas.verona_rolling_opera import eligible_detail
        return eligible_detail(url)
    if key=="coccia-novara-rolling-opera":
        from opera_atlas.novara_future_parser import eligible_detail
        return eligible_detail(url)
    if key=="pisa-future-calendar":
        from opera_atlas.pisa_future_calendar import eligible_detail
        return eligible_detail(url)
    if key in {"chieti-marrucino-season-2027","modena-municipal-opera-2027-28",
          "rovigo-sociale-season-2027-28","treviso-del-monaco-season-2027-28",
          "padova-verdi-season-2027","lecce-provincia-season-2027"}:
        from opera_atlas.six_future_seasons import index_year, SOURCES
        host,kind,_,_=SOURCES[key]
        if kind=="search":
            # The search index itself is explicitly approved, and the
            # discovered official article is checked again on detail fetch.
            try:
                index_year(key,url)
                return True
            except ValueError:
                parsed=urlsplit(url)
                if parsed.scheme!="https" or parsed.hostname!=host or parsed.query or parsed.fragment:
                    return False
                if key.startswith("chieti-"):
                    return bool(re.fullmatch(r"/novita/[a-z0-9-]+/",parsed.path)
                                and re.search(r"stagione-lirica-20\d{2}",parsed.path)
                                and "marrucino" in parsed.path)
                return bool(re.fullmatch(r"/[a-z0-9-]+/",parsed.path)
                            and re.search(r"stagione-lirica",parsed.path)
                            and re.search(r"20\d{2}",parsed.path))
        try:
            index_year(key,url)
            return True
        except ValueError:
            return False
    if key=="sassari-de-carolis-opera-2026":
        return (parsed.scheme=="https" and parsed.hostname=="www.marialisadecarolis.it"
                and parsed.path=="/opera-lirica.aspx"
                and parsed.query in {"id=372","id=373","id=375"}
                and not parsed.fragment and not parsed.username and not parsed.password
                and parsed.port is None)
    if key=="lecce-politeama-opera-2026":
        return (parsed.scheme=="https" and parsed.hostname=="www.politeamagreco.it"
                and parsed.path=="/scheda.asp" and parsed.query in {"id=1147","id=1148","id=1149"}
                and not parsed.fragment and not parsed.username and not parsed.password
                and parsed.port is None)
    if parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port is not None:
        return False
    path=parsed.path.lower().rstrip("/")
    if excluded_nonopera(key,url):
        return False
    if key=="messina-vittorio-opera-2026-27":
        return (parsed.scheme=="https" and parsed.hostname=="www.teatrovittorioemanuele.it"
                and path in {"/evento/madama-butterfly", "/evento/la-traviata",
                             "/evento/al-cavallino-bianco"})
    if key=="puccini-torre-del-lago-2027":
        edition=re.fullmatch(r"/en/(\d{2,3})(?:st|nd|rd|th)-puccini-festival-(20\d{2})/?",parsed.path)
        return bool(parsed.scheme=="https" and
                    parsed.hostname=="www.puccinifestival.it" and edition
                    and 2027<=int(edition[2])<=2099
                    and int(edition[1])==int(edition[2])-1954)
    if key=="spoleto-tls-lirica-2026":
        from opera_atlas.spoleto_municipal_parser import URL as municipal
        return (url==municipal or bool(re.fullmatch(
            r"https://www\.tls-belli\.it/stagione-lirica-20\d{2}/",url)))
    if key=="chieti-marrucino-lirica-2026":
        from opera_atlas.chieti_marrucino_parser import URL
        return url.rstrip("/")==URL.rstrip("/")
    if key=="lecce-provincia-politeama-2026":
        from opera_atlas.lecce_provincia_parser import URL
        return url==URL
    if key=="lecce-apollo-pinocchio-2026":
        return (parsed.scheme=="https" and parsed.hostname=="www.provincia.le.it"
                and path=="/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini")
    if key=="rovigo-regione-programma-2026-27":
        from opera_atlas.rovigo_regional_program import URL
        return url==URL
    if key=="rovigo-sociale-opera-2026-27":
        from opera_atlas.rovigo_traviata_official import OFFICIAL_URLS
        return (url in OFFICIAL_URLS
                or (parsed.scheme=="https" and parsed.hostname=="www.comune.rovigo.it"
                    and not parsed.query and not parsed.fragment
                    and not parsed.username and not parsed.password
                    and parsed.port is None
                    and path in {
                        "/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-2026-2027",
                        "/teatrosociale/dettaglio-teatro/eventi/aida",
                        "/teatrosociale/dettaglio-teatro/eventi/cenerentola",
                    }))
    if key=="padova-verdi-opera-2026":
        return (parsed.scheme=="https" and parsed.hostname=="padovacultura.padovanet.it"
                and path=="/it/attivita-culturali/stagione-lirica-di-padova-2026")
    if key=="treviso-del-monaco-opera-2026-27":
        return path=="/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27"
    if key=="ravenna-alighieri-cherubini-2027":
        return path in {"/eventi/pagliacci-2", "/eventi/la-cenerentola-4"}
    if key=="coccia-novara-opera-2027":
        return path in {"/stagione-27-rigoletto.html",
                        "/stagione-27-il-barbiere-di-siviglia.html",
                        "/stagione-27-le-nozze-di-figaro.html"}
    if key=="filarmonico-verona-opera-2027":
        return path in {"/teatro-filarmonico-verona/2027/il-ratto-dal-serraglio",
                        "/teatro-filarmonico-verona/2027/alzira",
                        "/teatro-filarmonico-verona/2027/fidelio",
                        "/teatro-filarmonico-verona/2027/il-signor-bruschino",
                        "/teatro-filarmonico-verona/2027/cristoforo-colombo"}
    if key=="pisa-verdi-opera-2026-27":
        return path in {"/spettacolo/dido-and-aeneas",
                        "/spettacolo/loccasione-fa-il-ladro-ossia-il-cambio-della-valigia",
                        "/spettacolo/otello", "/spettacolo/aida",
                        "/spettacolo/la-clemenza-di-tito"}
    if key=="salerno-verdi-opera-2026":
        return path in {"/eventi/trovatore-2026", "/eventi/il-signor-bruschino-2026",
                        "/eventi/il-barbiere-di-siviglia-2026", "/eventi/macbeth-2026",
                        "/eventi/la-vedova-allegra-2026", "/eventi/turandot-2026"}
    if key=="macerata-festival-2027":
        return path in {"/macerata-opera-festival/tosca",
                        "/macerata-opera-festival/la-traviata",
                        "/macerata-opera-festival/elisir-damore"}
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
    if key=="donizetti-opera-2027":
        # Candidate links are accepted only after extraction from the
        # exact future-year official OPERE section, never generic site crawl.
        match=re.fullmatch(r"/it/evento/[a-z0-9-]+(?:/(20\d{2}-\d{2}-\d{2}))?",path)
        if not match:return False
        if match[1]:
            from datetime import date
            try:
                if date.fromisoformat(match[1]).year<2027:return False
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
    if key in ("jesi-opera-season-2027","ancona-opera-season-2027"):
        from opera_atlas.marche_future_parser import SOURCES
        host,venue,pattern,tag=SOURCES[key]
        return parsed.scheme=="https" and parsed.hostname==host and bool(re.fullmatch(pattern,parsed.path))
    if key.startswith("jesi-") and key.endswith("-opera-2026"):
        return path=="/lirica/programma-stagione-lirica-2026"
    if key.startswith("ancona-") and key.endswith("-2026"):
        return path=="/stagione-lirica-2026"
    if key.startswith("goldoni-livorno-") and key.endswith("-2026-27"):
        return path=="/notizie/la-stagione-lirica"
    if key=="ferrara-season-opera-2027-28":
        return (parsed.scheme=="https" and
                parsed.hostname=="spettacolo.emiliaromagnacultura.it" and
                bool(re.fullmatch(
                    r"/it/rassegna/teatro-comunale-ferrara-opera-danza-(20\d{2})-(20\d{2})",
                    path)) and not parsed.query and not parsed.fragment)
    if key.startswith("ferrara-") and key.endswith("-opera-2026-27"):
        return path=="/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027"
    if key=="reggio-valli-opera-2026-27":
        return bool(re.fullmatch(r"/spettacolo/[a-z0-9-]+",path))
    if key=="piacenza-opera-2026-27":
        return bool(re.fullmatch(r"/event/[a-z0-9-]+",path))
    if key=="giglio-lucca-opera-2026-27":
        match=re.fullmatch(
            r"/it/cartellone/lirica/stagione-(20\d{2})-(20\d{2})/[a-z0-9-]+",path)
        return bool(match and 2026<=int(match[1])<=2098
                    and int(match[2])==int(match[1])+1)
    if key=="modena-teatro-opera-2026-27":
        return (parsed.scheme=="https"
                and parsed.hostname=="www.teatrocomunalemodena.it"
                and bool(re.fullmatch(r"/spettacolo/[a-z0-9-]+",path)))
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

def _messina_future_links(index_url:str,html:str,min_links:int)->list[str]:
    """Review-only links from the official opera category, not its site navigation.

    Unlike the known 26/27 three-production allowlist, next year's titles are
    unknown in advance. The category and its exact season heading must agree.
    """
    index=urlsplit(index_url)
    year=re.fullmatch(r"/event_listing_type/opera-(\d{2})-(\d{2})/",index.path)
    if (index.scheme!="https" or index.hostname!="www.teatrovittorioemanuele.it"
            or not year or int(year[1])<27 or int(year[2])!=(int(year[1])+1)%100):
        raise ValueError("invalid future Messina opera season URL")
    if not re.search(r"Tipo\s+di\s+evento:\s*Opera\s+"+year[1]+r"\s*/\s*"+year[2],
                     re.sub(r"<[^>]*>"," ",html),re.IGNORECASE):
        raise ValueError("official Messina opera season heading not confirmed")
    parser=AnchorParser()
    parser.feed(html)
    urls=set()
    for href in parser.links:
        url=urljoin(index_url,href)
        candidate=urlsplit(url)
        if (candidate.scheme=="https" and candidate.hostname==index.hostname
                and not candidate.query and not candidate.fragment
                and not candidate.username and not candidate.password
                and candidate.port is None and
                re.fullmatch(r"/evento/[a-z0-9-]+/",candidate.path)
                and not excluded_nonopera("messina-vittorio-opera-2026-27",url)):
            urls.add(url)
    if len(urls)<min_links:
        raise ValueError("season index incomplete or structure changed")
    return sorted(urls)


def _donizetti_future_links(index_url:str,html:str,min_links:int)->list[str]:
    """Only cards under the matching future OPERE heading become candidates."""
    index=urlsplit(index_url)
    season=re.fullmatch(r"/it/opere-(20\d{2})/",index.path)
    if (index.scheme!="https" or index.hostname!="www.donizettiopera.org"
        or index.query or index.fragment or not season
        or not 2027<=int(season[1])<=2099):
        raise ValueError("invalid official Donizetti future index")
    year=int(season[1])
    parser=ScopedSeasonAnchors("donizetti-opera-2027",season_year=year)
    parser.feed(html)
    results=set()
    for href in parser.links:
        target=urljoin(index_url,href)
        path=urlsplit(target).path.rstrip("/").split("/")
        if len(path)>4 and re.fullmatch(r"20\d{2}-\d{2}-\d{2}",path[-1]):
            if path[-1][:4]!=str(year):continue
        if eligible("donizetti-opera-2027",target):
            results.add(target)
    if len(results)<min_links:
        raise ValueError("season index incomplete or structure changed")
    return sorted(results)


def extract(key:str,index_url:str,html:str,min_links:int)->list[str]:
    if key=="mantova-sociale-rolling-opera":
        from opera_atlas.mantova_sociale_opera import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="napoli-san-carlo-rolling-opera":
        from opera_atlas.napoli_san_carlo import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="pesaro-rof-2026":
        from opera_atlas.pesaro_rof import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="martina-valle-itria-2026":
        from opera_atlas.martina_valle_itria import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="trapani-luglio-musicale-2026":
        from opera_atlas.trapani_luglio_opera import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="haydn-rolling-opera":
        from opera_atlas.haydn_rolling_opera import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="asti-alfieri-rolling-opera":
        from opera_atlas.asti_alfieri_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="savona-giocosa-rolling-opera":
        from opera_atlas.savona_opera_giocosa_parser import parse_homepage
        if len(parse_homepage(html,url=index_url))<min_links:
            raise ValueError("season index incomplete or structure changed")
        return [index_url]
    if key=="sassari-de-carolis-rolling-opera":
        from opera_atlas.sassari_future_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="goldoni-livorno-rolling-lirica":
        from opera_atlas.livorno_future_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="ravenna-cherubini-rolling-opera":
        from opera_atlas.ravenna_future_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="macerata-festival-rolling":
        from opera_atlas.macerata_future_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="salerno-verdi-rolling-opera":
        from opera_atlas.salerno_future_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="filarmonico-verona-rolling-opera":
        from opera_atlas.verona_rolling_opera import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="coccia-novara-rolling-opera":
        from opera_atlas.novara_future_parser import extract_index
        return extract_index(html,url=index_url,min_links=min_links)
    if key=="pisa-future-calendar":
        from opera_atlas.pisa_future_calendar import extract_calendar
        return extract_calendar(html,url=index_url,min_links=min_links)
    if key in {"chieti-marrucino-season-2027","modena-municipal-opera-2027-28",
          "rovigo-sociale-season-2027-28","treviso-del-monaco-season-2027-28",
          "padova-verdi-season-2027","lecce-provincia-season-2027"}:
        from opera_atlas.six_future_seasons import extract_index
        return extract_index(key,index_url,html,min_links)
    if key=="ferrara-season-opera-2027-28":
        from opera_atlas.ferrara_future_parser import verify_index
        verify_index(html,url=index_url)
        return [index_url]
    if key in ("jesi-opera-season-2027","ancona-opera-season-2027"):
        from opera_atlas.marche_future_parser import verify_index
        verify_index(html,url=index_url,source_key=key)
        return [index_url]
    if key=="donizetti-opera-2027":
        return _donizetti_future_links(index_url,html,min_links)
    if key=="messina-vittorio-opera-2026-27" and "/opera-26-27/" not in index_url:
        return _messina_future_links(index_url,html,min_links)
    if key=="puccini-torre-del-lago-2027":
        from opera_atlas.puccini_festival_parser import parse_program
        if len(parse_program(html,url=index_url))!=15:
            raise ValueError("Puccini 2027 incomplete official opera calendar")
        return [index_url]
    if key=="spoleto-tls-lirica-2026":
        from opera_atlas.spoleto_municipal_parser import URL as municipal,parse_program as parse_municipal
        if index_url==municipal:
            if len(parse_municipal(html,url=index_url))!=3:
                raise ValueError("municipal Spoleto three recite incomplete")
            return [index_url]
        from opera_atlas.spoleto_tls_parser import parse_program
        if not parse_program(html,url=index_url):
            raise ValueError("no verified Spoleto Teatro Nuovo opera showtimes")
        return [index_url]
    if key=="chieti-marrucino-lirica-2026":
        from opera_atlas.chieti_marrucino_parser import parse_program
        if len(parse_program(html,url=index_url))!=7:
            raise ValueError("Chieti official seven recite incomplete")
        return [index_url]
    if key=="lecce-provincia-politeama-2026":
        from opera_atlas.lecce_provincia_parser import parse_program
        if len(parse_program(html,url=index_url))!=6:
            raise ValueError("Province of Lecce six opera showtimes incomplete")
        return [index_url]
    if key=="lecce-apollo-pinocchio-2026":
        from opera_atlas.lecce_apollo_parser import parse_detail
        parse_detail(html,url=index_url)
        return [index_url]
    if key=="rovigo-regione-programma-2026-27":
        from opera_atlas.rovigo_regional_program import approved_programme
        approved_programme(html,url=index_url)
        # The regional article is a verified *programme pointer*, not
        # evidence of any dated performances inside the linked PDF.
        return [index_url]
    if key=="rovigo-sociale-opera-2026-27":
        from opera_atlas.rovigo_traviata_official import OFFICIAL_URLS,parse_official_traviata
        if index_url in OFFICIAL_URLS:
            parse_official_traviata(html,url=index_url)
            return [index_url]
        from opera_atlas.rovigo_opera_parser import identify_season
        identify_season(html,url=index_url)
        return [index_url]

    if key=="padova-verdi-opera-2026":
        from opera_atlas.padova_opera_parser import parse_program
        if len(parse_program(html,url=index_url))!=5:
            raise ValueError("Padova five opera showtimes incomplete")
        return [index_url]
    if key=="treviso-del-monaco-opera-2026-27":
        from opera_atlas.treviso_opera_parser import parse_program
        if len(parse_program(html,url=index_url))!=6:
            raise ValueError("Treviso three-opera calendar is incomplete")
        return [index_url]
    if key.startswith(("jesi-","ancona-")) and key.endswith(("-opera-2026","-program-2026")):
        from opera_atlas.marche_2026_parser import read_program
        read_program(html,source_key=key,url=index_url)
        return [index_url]
    if key.startswith("goldoni-livorno-") and key.endswith("-2026-27"):
        from opera_atlas.livorno_opera_parser import parse_detail
        parse_detail(html,url=index_url,source_key=key)
        return [index_url]
    if key.startswith("ferrara-") and key.endswith("-opera-2026-27"):
        from opera_atlas.ferrara_regional_parser import verified_index_candidate
        if verified_index_candidate(html,source_key=key,url=index_url):
            return [index_url]
        raise ValueError("official Ferrara opera not independently verified")
    season_year=(int(re.fullmatch(r"/opera-e-balletto-(20\d{2})/",urlsplit(index_url).path)[1])
                 if key in ("petruzzelli-opera-2026","petruzzelli-opera-2027")
                 and re.fullmatch(r"/opera-e-balletto-(20\d{2})/",urlsplit(index_url).path)
                 else None)
    parser=(ScopedSeasonAnchors(key,season_year=season_year)
            if key in {"parma-opera-2027","massimo-season-2026-27",
                       "donizetti-opera-2026","teatro-grande-opera-2026",
                       "petruzzelli-opera-2026","petruzzelli-opera-2027",
                       "piacenza-opera-2026-27","reggio-valli-opera-2026-27"}
            else AnchorParser())
    parser.feed(html)
    hostname=urlsplit(index_url).hostname
    result=set()
    for href in parser.links:
        url=urljoin(index_url,href)
        parsed=urlsplit(url)
        if parsed.scheme!="https" or parsed.hostname!=hostname or parsed.username or parsed.password or parsed.port is not None:
            continue
        if (parsed.query and key not in {"lecce-politeama-opera-2026",
                                          "sassari-de-carolis-opera-2026",
                                          "sassari-de-carolis-rolling-opera"}) or parsed.fragment:
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
        "mantova-sociale-rolling-opera":("www.teatrosocialemantova.it","/it-it/ricerca.aspx"),
        "napoli-san-carlo-rolling-opera":("www.teatrosancarlo.it","/spettacoli/"),
        "pesaro-rof-2026":("www.rossinioperafestival.it","/archivio/stagione-2026/"),
        "martina-valle-itria-2026":("www.festivaldellavalleditria.it","/programma-2026"),
        "trapani-luglio-musicale-2026":("www.lugliomusicale.it","/it/luglio-musicale-stagioni/stagione-2026/"),
        "haydn-rolling-opera":("www.haydn.it","/eventi/area/opera"),
        "asti-alfieri-rolling-opera":("www.teatroalfieriasti.it","/events/categoria/fuori-abbonamento/"),
        "savona-giocosa-rolling-opera":("operagiocosa.it","/"),
        "sassari-de-carolis-opera-2026":("www.marialisadecarolis.it","/opere-liriche.aspx"),
        "sassari-de-carolis-rolling-opera":("www.marialisadecarolis.it","/opere-liriche.aspx"),
        "messina-vittorio-opera-2026-27":("www.teatrovittorioemanuele.it","/event_listing_type/opera-26-27/"),
        "lecce-apollo-pinocchio-2026":("www.provincia.le.it","/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/"),
        "lecce-politeama-opera-2026":("www.politeamagreco.it","/programmazione.asp"),
        "lecce-provincia-politeama-2026":("www.provincia.le.it","/https-www-provincia-le-it-al-via-la-51-stagione-lirica-della-provincia-di-lecce-lunedi-9-novembre-la-conferenza-stampa-di-presentazione-del-cartellone-2026/"),
        "puccini-torre-del-lago-2027":("www.puccinifestival.it","/en/73rd-puccini-festival-2027/"),
        "spoleto-tls-lirica-2026":("www.tls-belli.it","/stagione-lirica-2026/"),
        "chieti-marrucino-lirica-2026":("comune.chieti.it","/novita/presentata-la-stagione-lirica-2026-del-teatro-marrucino-tra-tradizione-innovazione-e-celebrazioni-culturali/"),
        "chieti-marrucino-season-2027":("comune.chieti.it","/"),
        "modena-municipal-opera-2027-28":("www.comune.modena.it","/vivere-modena/eventi/2027/stagione-opera-2027-2028"),
        "rovigo-sociale-season-2027-28":("www.comune.rovigo.it","/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-2027-2028"),
        "treviso-del-monaco-season-2027-28":("risorse.teatrostabileveneto.it","/treviso-teatro-del-monaco-stagione-lirica-concertistica-27-28"),
        "padova-verdi-season-2027":("padovacultura.padovanet.it","/it/attivita-culturali/stagione-lirica-di-padova-2027"),
        "lecce-provincia-season-2027":("www.provincia.le.it","/"),
        "rovigo-regione-programma-2026-27":("www.culturaveneto.it","/spettacoli/musica/3563a671-d9b2-46bf-a10d-776af9ab17bc"),
        "rovigo-sociale-opera-2026-27":("www.comune.rovigo.it","/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-2026-2027"),
        "padova-verdi-opera-2026":("padovacultura.padovanet.it","/it/attivita-culturali/stagione-lirica-di-padova-2026"),
        "treviso-del-monaco-opera-2026-27":("risorse.teatrostabileveneto.it","/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27"),
        "ravenna-alighieri-cherubini-2027":("www.orchestracherubini.it","/eventi/tpl/list/"),
        "ravenna-cherubini-rolling-opera":("www.orchestracherubini.it","/eventi/tpl/list/"),
        "coccia-novara-opera-2027":("www.fondazioneteatrococcia.it","/spettacoli.html"),
        "coccia-novara-rolling-opera":("www.fondazioneteatrococcia.it","/spettacoli_opera_danza_concerti.html"),
        "filarmonico-verona-opera-2027":("www.arena.it","/teatro-filarmonico-verona/spettacoli-prossima-stagione/"),
        "filarmonico-verona-rolling-opera":("www.arena.it","/prossime-stagioni/"),
        "pisa-verdi-opera-2026-27":("teatrodipisa.it","/tipologia-spettacolo/opera/"),
        "pisa-future-calendar":("teatrodipisa.it","/calendario/categoria/opera/elenco/"),
        "salerno-verdi-opera-2026":("cultura.comune.salerno.it","/teatro-verdi/la-stagione/"),
        "salerno-verdi-rolling-opera":("cultura.comune.salerno.it","/teatro-verdi/la-stagione/"),
        "macerata-festival-2027":("www.sferisterio.it","/"),
        "macerata-festival-rolling":("www.sferisterio.it","/macerata-opera-festival-2027"),
        "scala-season-2026-27":("www.teatroallascala.org","/it/stagione/2026-2027/index.html"),
        "arena-festival-2027":("www.arena.it","/arena-opera-festival/spettacoli/"),
        "fenice-opera-2026-27":("www.teatrolafenice.it","/event-category/opera-2026-27/"),
        "parma-opera-2027":("teatroregioparma.it","/categoria-spettacoli/opera/"),
        "massimo-season-2026-27":("www.teatromassimo.it","/la-stagione-2026-27/"),
        "carlo-felice-season-2026-27":("www.carlofelice.it","/rassegna-stagione-opera-danza-musical-2026-27/"),
        "donizetti-opera-2026":("www.donizettiopera.org","/it/opere-2026/"),
        "donizetti-opera-2027":("www.donizettiopera.org","/it/opere-2027/"),
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
        "modena-teatro-opera-2026-27":("www.teatrocomunalemodena.it","/opera/"),
        "modena-opera-2026-27":("www.comune.modena.it","/vivere-modena/eventi/2026/stagione-opera-2026-2027"),
        "giglio-lucca-opera-2026-27":("www.teatrodelgigliogiacomopuccini.it","/it/cartellone/lirica/stagione-2026-2027/"),
        "piacenza-opera-2026-27":("teatripiacenza.it","/stagioni/stagione-26-27/"),
        "jesi-trittico-opera-2026":("www.fondazionepergolesispontini.com","/lirica/programma-stagione-lirica-2026/"),
        "jesi-opera-season-2027":("www.fondazionepergolesispontini.com","/lirica/programma-stagione-lirica-2027/"),
        "ancona-opera-season-2027":("www.fondazionemuse.org","/stagione-lirica-2027/"),
        "jesi-don-pasquale-opera-2026":("www.fondazionepergolesispontini.com","/lirica/programma-stagione-lirica-2026/"),
        "jesi-esecuzione-opera-2026":("www.fondazionepergolesispontini.com","/lirica/programma-stagione-lirica-2026/"),
        "jesi-nabucco-opera-2026":("www.fondazionepergolesispontini.com","/lirica/programma-stagione-lirica-2026/"),
        "ancona-elisir-opera-2026":("www.fondazionemuse.org","/stagione-lirica-2026/"),
        "ancona-cavalleria-program-2026":("www.fondazionemuse.org","/stagione-lirica-2026/"),
        "goldoni-livorno-dido-2026-27":("www.goldoniteatro.it","/notizie/la-stagione-lirica/"),
        "goldoni-livorno-rolling-lirica":("www.goldoniteatro.it","/tipo-spettacolo/lirica/"),
        "goldoni-livorno-otello-2026-27":("www.goldoniteatro.it","/notizie/la-stagione-lirica/"),
        "goldoni-livorno-elisir-2026-27":("www.goldoniteatro.it","/notizie/la-stagione-lirica/"),
        "ferrara-macbeth-opera-2026-27":("spettacolo.emiliaromagnacultura.it","/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"),
        "ferrara-season-opera-2027-28":("spettacolo.emiliaromagnacultura.it","/it/rassegna/teatro-comunale-ferrara-opera-danza-2027-2028/"),
        "ferrara-barbiere-opera-2026-27":("spettacolo.emiliaromagnacultura.it","/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"),
        "ferrara-dido-opera-2026-27":("spettacolo.emiliaromagnacultura.it","/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"),
        "ferrara-clemenza-opera-2026-27":("spettacolo.emiliaromagnacultura.it","/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"),
        "ferrara-boccanegra-opera-2026-27":("spettacolo.emiliaromagnacultura.it","/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/"),
        "reggio-valli-opera-2026-27":("www.iteatri.re.it","/tipo/opera/"),
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
        if key=="mantova-sociale-rolling-opera":
            valid_season=(index.path=="/it-it/ricerca.aspx"
                          and index.query=="fti=opera+lirica")
        elif key in ("scala-season-2026-27","fenice-opera-2026-27",
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
        elif key in ("jesi-opera-season-2027","ancona-opera-season-2027"):
            pattern=(r"/lirica/programma-stagione-lirica-(20\d{2})/"
                     if key.startswith("jesi-") else r"/stagione-lirica-(20\d{2})/")
            season=re.fullmatch(pattern,index.path)
            valid_season=bool(season and 2027<=int(season[1])<=2099)
        elif key=="donizetti-opera-2027":
            season=re.fullmatch(r"/it/opere-(20\d{2})/",index.path)
            valid_season=bool(season and 2027<=int(season[1])<=2099)
        elif key=="donizetti-opera-2026":
            season=re.fullmatch(r"/it/opere-(20\d{2})/",index.path)
            valid_season=bool(season and 2026<=int(season[1])<=2098)
        elif key=="teatro-grande-opera-2026":
            valid_season=index.path=="/it"
        elif key=="maggio-fiorentino-calendar-2027":
            season=re.fullmatch(r"/calendario/(20\d{2})/01/opera",index.path)
            valid_season=bool(season and 2027<=int(season[1])<=2099
                              and not index.query)
        elif key.startswith("jesi-") and key.endswith("-opera-2026"):
            valid_season=index.path=="/lirica/programma-stagione-lirica-2026/" and not index.query
        elif key.startswith("ancona-") and key.endswith("-2026"):
            valid_season=index.path=="/stagione-lirica-2026/" and not index.query
        elif key=="goldoni-livorno-rolling-lirica":
            valid_season=index.path=="/tipo-spettacolo/lirica/" and not index.query
        elif key.startswith("goldoni-livorno-") and key.endswith("-2026-27"):
            valid_season=index.path=="/notizie/la-stagione-lirica/" and not index.query
        elif key=="ferrara-season-opera-2027-28":
            match=re.fullmatch(
                r"/it/rassegna/teatro-comunale-ferrara-opera-danza-(20\d{2})-(20\d{2})/",
                index.path)
            valid_season=bool(match and 2027<=int(match[1])<2099
                              and int(match[2])==int(match[1])+1
                              and not index.query)
        elif key.startswith("ferrara-") and key.endswith("-opera-2026-27"):
            valid_season=index.path=="/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/" and not index.query
        elif key=="sassari-de-carolis-rolling-opera":
            valid_season=index.path=="/opere-liriche.aspx" and not index.query
        elif key=="sassari-de-carolis-opera-2026":
            valid_season=index.path=="/opere-liriche.aspx" and not index.query
        elif key=="messina-vittorio-opera-2026-27":
            season=re.fullmatch(r"/event_listing_type/opera-(\d{2})-(\d{2})/",index.path)
            valid_season=bool(season and 26<=int(season[1])<=98
                              and int(season[2])==(int(season[1])+1)%100
                              and not index.query)
        elif key=="lecce-apollo-pinocchio-2026":
            valid_season=index.path=="/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/" and not index.query
        elif key=="lecce-politeama-opera-2026":
            valid_season=index.path=="/programmazione.asp" and not index.query
        elif key=="lecce-provincia-politeama-2026":
            valid_season=index.path=="/https-www-provincia-le-it-al-via-la-51-stagione-lirica-della-provincia-di-lecce-lunedi-9-novembre-la-conferenza-stampa-di-presentazione-del-cartellone-2026/" and not index.query
        elif key=="puccini-torre-del-lago-2027":
            edition=re.fullmatch(r"/en/(\d{2,3})(?:st|nd|rd|th)-puccini-festival-(20\d{2})/",index.path)
            valid_season=bool(edition and 2027<=int(edition[2])<=2099
                              and int(edition[1])==int(edition[2])-1954
                              and not index.query)
        elif key=="spoleto-tls-lirica-2026":
            valid_season=bool(re.fullmatch(r"/stagione-lirica-20\d{2}/",index.path)
                              and not index.query)
        elif key in {"chieti-marrucino-season-2027","modena-municipal-opera-2027-28",
          "rovigo-sociale-season-2027-28","treviso-del-monaco-season-2027-28",
          "padova-verdi-season-2027","lecce-provincia-season-2027"}:
            from opera_atlas.six_future_seasons import index_year
            try:
                index_year(key,item["url"])
                valid_season=True
            except ValueError:
                valid_season=False
        elif key=="chieti-marrucino-lirica-2026":
            valid_season=index.path=="/novita/presentata-la-stagione-lirica-2026-del-teatro-marrucino-tra-tradizione-innovazione-e-celebrazioni-culturali/" and not index.query
        elif key=="rovigo-regione-programma-2026-27":
            valid_season=(index.path=="/spettacoli/musica/3563a671-d9b2-46bf-a10d-776af9ab17bc"
                          and not index.query)
        elif key=="rovigo-sociale-opera-2026-27":
            valid_season=index.path=="/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-2026-2027" and not index.query
        elif key=="padova-verdi-opera-2026":
            valid_season=index.path=="/it/attivita-culturali/stagione-lirica-di-padova-2026" and not index.query
        elif key=="treviso-del-monaco-opera-2026-27":
            valid_season=index.path=="/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27" and not index.query
        elif key=="ravenna-cherubini-rolling-opera":
            valid_season=index.path=="/eventi/tpl/list/" and not index.query
        elif key=="ravenna-alighieri-cherubini-2027":
            valid_season=index.path=="/eventi/tpl/list/" and not index.query
        elif key=="coccia-novara-rolling-opera":
            valid_season=index.path=="/spettacoli_opera_danza_concerti.html" and not index.query
        elif key=="coccia-novara-opera-2027":
            valid_season=index.path=="/spettacoli.html" and not index.query
        elif key=="filarmonico-verona-rolling-opera":
            valid_season=index.path=="/prossime-stagioni/" and not index.query
        elif key=="filarmonico-verona-opera-2027":
            valid_season=index.path=="/teatro-filarmonico-verona/spettacoli-prossima-stagione/" and not index.query
        elif key=="pisa-future-calendar":
            valid_season=index.path=="/calendario/categoria/opera/elenco/" and not index.query
        elif key=="pisa-verdi-opera-2026-27":
            valid_season=index.path=="/tipologia-spettacolo/opera/" and not index.query
        elif key=="salerno-verdi-rolling-opera":
            valid_season=index.path=="/teatro-verdi/la-stagione/" and not index.query
        elif key=="salerno-verdi-opera-2026":
            valid_season=index.path=="/teatro-verdi/la-stagione/" and not index.query
        elif key=="macerata-festival-rolling":
            from opera_atlas.macerata_future_parser import edition_year
            try:
                edition_year(item["url"])
                valid_season=True
            except ValueError:
                valid_season=False
        elif key=="macerata-festival-2027":
            valid_season=index.path=="/" and not index.query
        elif key=="savona-giocosa-rolling-opera":
            valid_season=index.path=="/" and not index.query
        elif key=="asti-alfieri-rolling-opera":
            valid_season=index.path=="/events/categoria/fuori-abbonamento/" and not index.query
        elif key=="haydn-rolling-opera":
            valid_season=index.path=="/eventi/area/opera" and not index.query
        elif key=="napoli-san-carlo-rolling-opera":
            valid_season=index.path=="/spettacoli/" and not index.query
        elif key=="pesaro-rof-2026":
            match=re.fullmatch(r"/archivio/stagione-(20\d{2})/",index.path)
            valid_season=bool(match and 2026<=int(match[1])<=2099 and not index.query)
        elif key=="martina-valle-itria-2026":
            match=re.fullmatch(r"/programma-(20\d{2})",index.path)
            valid_season=bool(match and 2026<=int(match[1])<=2099 and not index.query)
        elif key=="trapani-luglio-musicale-2026":
            year=re.fullmatch(
                r"/it/luglio-musicale-stagioni/stagione-(20\d{2})/",index.path)
            valid_season=bool(year and 2026<=int(year[1])<=2099
                              and not index.query)
        elif key=="reggio-valli-opera-2026-27":
            valid_season=index.path=="/tipo/opera/" and not index.query
        elif key=="piacenza-opera-2026-27":
            season=re.fullmatch(r"/stagioni/stagione-(\d{2})-(\d{2})/",index.path)
            valid_season=bool(season and int(season[1])>=26
                              and int(season[2])==(int(season[1])+1)%100
                              and not index.query)
        elif key=="giglio-lucca-opera-2026-27":
            season=re.fullmatch(
                r"/it/cartellone/lirica/stagione-(20\d{2})-(20\d{2})/",index.path)
            valid_season=bool(season and 2026<=int(season[1])<=2098
                              and int(season[2])==int(season[1])+1
                              and not index.query)
        elif key=="modena-teatro-opera-2026-27":
            valid_season=index.path=="/opera/" and not index.query
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
                              and (key=="petruzzelli-opera-2027" and
                                   2027<=int(index.path.split("-")[-1].strip("/"))<=2099
                                   or index.path=="/opera-e-balletto-"+key.rsplit("-",1)[-1]+"/"))
        elif key=="carlo-felice-season-2026-27":
            season=re.fullmatch(r"/rassegna-stagione-opera-danza-musical-(20\d{2})-(\d{2})/",index.path)
            valid_season=bool(season and (int(season[1])+1)%100==int(season[2]) and 2026<=int(season[1])<=2098)
        else:
            valid_season=index.path==path
        if (index.scheme!="https" or index.hostname!=host or not valid_season
            or (index.query and key not in ("mantova-sociale-rolling-opera","bologna-comunale-opera-2026","bologna-comunale-opera-2027","verdi-trieste-season-2026-27","chieti-marrucino-season-2027","lecce-provincia-season-2027")) or index.fragment or index.port is not None
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


def _probe_future_season(item:dict,db,source_id:int,fetcher,*,enabled:bool):
    """Check the next season independently of current-season availability."""
    if not enabled:
        return [],{}
    from datetime import date
    from scripts.rollover_season_indexes import next_index
    target=next_index(item,today=date.today(),allow_early=True)
    if not target or target==item["url"]:
        return [],{}
    try:
        page=fetcher(db,source_id=source_id,url=target,network_enabled=True)
        links=extract(item["key"],target,page.html,item["min_links"])
        if item["key"]=="scala-season-2026-27":
            prefix=urlsplit(target).path.replace("/index.html","/opera/")
            if not all(urlsplit(link).path.startswith(prefix) for link in links):
                raise ValueError("mixed Scala season results")
        return links,{"next_season_status":"verified",
                      "next_season_url":target,"next_season_links":len(links)}
    except (AccessDenied,FetchUnavailable,ValueError):
        return [],{"next_season_status":"unavailable_or_invalid",
                  "next_season_url":target,"next_season_links":0}


class RovigoFallbackNotVerified(ValueError):
    """Safe per-endpoint acquisition diagnostics; no source HTML or URLs."""

    def __init__(self,reason:str,checks:dict[str,str]):
        super().__init__(reason)
        self.checks=checks


def _rovigo_verified_detail_fallback(db,source_id:int,fetcher):
    """Check both exact official routes; retain bounded acquisition stages.

    A blank municipal HTML shell is not composer, venue or recital evidence.
    Never substitute cached search results, third-party HTML or inferred data.
    """
    from opera_atlas.rovigo_traviata_official import OFFICIAL_URLS
    checks={}
    for name,detail_url in zip(("social_api","event_page"),OFFICIAL_URLS):
        try:
            page=fetcher(db,source_id=source_id,url=detail_url,
                         network_enabled=True)
        except FetchUnavailable:
            checks[name]="fetch_unavailable"
            continue
        except AccessDenied:
            # Respect explicit disallows; do not probe alternate paths.
            raise
        # The parser owns all title, composer, venue and showtime rules.
        try:
            urls=extract("rovigo-sociale-opera-2026-27",
                         detail_url,page.html,1)
        except ValueError as exc:
            from opera_atlas.rovigo_traviata_official import failure_stage
            checks[name]=failure_stage(exc)
            continue
        return page,detail_url,urls
    unavailable=all(status=="fetch_unavailable" for status in checks.values())
    reason=("rovigo_fallback_fetch_unavailable" if unavailable
            else "rovigo_fallback_content_unverified")
    raise RovigoFallbackNotVerified(reason,checks)


def unscanned_source_keys(config:dict,previous:dict)->set[str]:
    """Prefer newly configured indexes, without mistaking an old scan for success."""
    rows=validate_config(config)
    checked={row["key"] for row in previous.get("sources",[])
             if isinstance(row,dict) and row.get("last_attempt_at")}
    return {row["key"] for row in rows
            if row["access_status"]=="approved" and row["key"] not in checked}


def scan(config:dict,existing:dict,*,fetcher=fetch_official_html,
         network_enabled:bool=False,now:str|None=None,
         check_next_season:bool=False,
         source_keys:set[str]|None=None,priority_keys:set[str]|None=None):
    entries=validate_config(config)
    if source_keys is not None:
        approved={row["key"] for row in entries if row["access_status"]=="approved"}
        if not source_keys or not source_keys<=approved:
            raise ValueError("source-specific scan requires approved index keys")
        entries=[row for row in entries if row["key"] in source_keys]
    if priority_keys:
        entries.sort(key=lambda row:0 if row["key"] in priority_keys else 1)
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
            future_urls,future_health=[],{}
            if item["access_status"]!="approved":
                statuses.append({"key":item["key"],"status":item["access_status"],"links":0})
                continue
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",(item["official_url"],))
                row=db.execute("SELECT id FROM sources WHERE official_url=?",(item["official_url"],)).fetchone()
                future_urls,future_health=_probe_future_season(
                    item,db,row["id"],fetcher,
                    enabled=check_next_season and network_enabled)
                primary_unavailable=False
                municipal_fallback=False
                index_url=item["url"]
                min_links=item["min_links"]
                try:
                    page=fetcher(db,source_id=row["id"],url=index_url,network_enabled=True)
                except FetchUnavailable as original:
                    if item["key"]=="rovigo-sociale-opera-2026-27":
                        page,index_url,preverified_urls=_rovigo_verified_detail_fallback(
                            db,row["id"],fetcher)
                        min_links=1
                        municipal_fallback=True
                    elif item["key"]=="spoleto-tls-lirica-2026" and (
                        item["url"]=="https://www.tls-belli.it/stagione-lirica-2026/"):
                        # The primary theatre calendar may reject the CI runner.
                        # The Comune is an independent OFFICIAL source, with a
                        # separate exact-origin approved source record.
                        from opera_atlas.spoleto_municipal_parser import URL,ORIGIN
                        db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",(ORIGIN,))
                        alternate_id=db.execute("SELECT id FROM sources WHERE official_url=?",(ORIGIN,)).fetchone()["id"]
                        index_url=URL
                        page=fetcher(db,source_id=alternate_id,url=URL,network_enabled=True)
                        min_links=1
                        municipal_fallback=True
                    else:
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
                    urls=(preverified_urls if municipal_fallback and
                          item["key"]=="rovigo-sociale-opera-2026-27"
                          else extract(item["key"],index_url,page.html,min_links))
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
                    elif item["key"]=="rovigo-sociale-opera-2026-27":
                        # The legacy slider can lose its theatre identity.
                        # A separate exact first-party event document provides
                        # dated ticket evidence through the same robots gate.
                        page,index_url,urls=_rovigo_verified_detail_fallback(
                            db,row["id"],fetcher)
                        min_links=1
                        municipal_fallback=True
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
                elif item["key"]=="napoli-san-carlo-rolling-opera" and str(exc).startswith("San Carlo security challenge"):
                    diagnostic="official_anti_bot_challenge"
                elif item["key"]=="rovigo-sociale-opera-2026-27":
                    # The official municipal page changes format regularly.
                    # Publish only stable parser-stage codes, never page HTML.
                    diagnostic={
                        "unapproved Rovigo municipal season URL":"rovigo_url_validation_failed",
                        "Rovigo Teatro Sociale not identified":"rovigo_venue_missing",
                        "official Rovigo season 2026/27 not established":"rovigo_season_missing",
                        "no recognised season opera titles":"rovigo_opera_titles_missing",
                        "rovigo_fallback_fetch_unavailable":"rovigo_fallback_fetch_unavailable",
                        "rovigo_fallback_content_unverified":"rovigo_fallback_content_unverified",
                    }.get(str(exc),"rovigo_index_structure_changed")
                elif item["key"] in {
                        "chieti-marrucino-season-2027",
                        "modena-municipal-opera-2027-28",
                        "rovigo-sociale-season-2027-28",
                        "treviso-del-monaco-season-2027-28",
                        "padova-verdi-season-2027",
                        "lecce-provincia-season-2027"}:
                    # The URL and approved origin were already validated
                    # before fetching. Failure to confirm an h1, genre and
                    # first-party opera content on a *future* page means
                    # "not verified yet", not a bad source configuration.
                    # Leave it unpublished and retain the diagnostic.
                    diagnostic="future_official_programme_unverified"
                elif str(exc)=="season index incomplete or structure changed":
                    diagnostic="index_incomplete_or_markup_changed"
                else:
                    diagnostic="invalid_index_or_source_config"
                # A failed old index does not prevent publishing already
                # verified future-season links to the review-only registry.
                for future in future_urls:
                    uid="oa-index-"+hashlib.sha256(
                        (item["key"]+"|"+future).encode()).hexdigest()[:20]
                    if uid not in seen:
                        seen[uid]={"id":uid,"source_key":item["key"],
                                   "official_url":future,
                                   "status":classify(item["key"],future,reviewed),
                                   "first_seen":timestamp,"last_seen":timestamp}
                    elif seen[uid]["status"]=="needs_review":
                        seen[uid]["last_seen"]=timestamp
                fallback_checks=(exc.checks if isinstance(
                    exc,RovigoFallbackNotVerified) else None)
                statuses.append({"key":item["key"],"status":"unavailable_or_invalid",
                                 "reason":type(exc).__name__,"diagnostic":diagnostic,
                                 "required_links":item["min_links"],"links":0,
                                 **({"fallback_checks":fallback_checks}
                                    if fallback_checks is not None else {}),
                                 **future_health})
                continue
            page_health={}
            if municipal_fallback:
                page_health={"pages_checked":1,"pagination_complete":True,
                             "fallback_official_source":(
                                 "comune.rovigo.it" if item["key"]=="rovigo-sociale-opera-2026-27"
                                 else "comune.spoleto.pg.it")}
            elif primary_unavailable:
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
            # Merge only links that passed the independent future probe.
            urls=sorted(set(urls).union(future_urls))
            next_season_health=future_health
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
                             **next_season_health,
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
    parser.add_argument("--source-key",default=None,
                        help="Scan one approved index before the full crawl")
    parser.add_argument("--dry-run",action="store_true",
                        help="Check a source without committing candidates or health files")
    args=parser.parse_args()
    if args.dry_run and args.source_key is None:
        parser.error("--dry-run requires --source-key: select exactly one connector")
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    current=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"schema_version":1,"candidates":[]}
    previous=json.loads(HEALTH.read_text(encoding="utf-8")) if HEALTH.exists() else {}
    priorities=unscanned_source_keys(config,previous) if args.source_key is None else set()
    result,health=scan(
        config,current,network_enabled=args.allow_network,
        check_next_season=args.allow_network,
        source_keys={args.source_key} if args.source_key is not None else None,
        priority_keys=priorities)
    checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    health=source_health_history(health,previous,checked_at=checked_at)
    if args.source_key is not None:
        # A priority source cannot erase health for theatres not rescanned.
        old=previous.get("sources",[]) if previous.get("schema_version")==1 else []
        by_key={row["key"]:row for row in old
                if isinstance(row,dict) and isinstance(row.get("key"),str)}
        by_key.update({row["key"]:row for row in health})
        health=[by_key[key] for key in sorted(by_key)]
    if not args.dry_run:
        _write_atomic(OUTPUT,result)
        _write_atomic(PUBLIC,result)
        _write_atomic(HEALTH,{"schema_version":1,"checked_at":checked_at,"sources":health})
    print(json.dumps({"dry_run":args.dry_run,
                      "candidates":len(result["candidates"]),
                      "healthy_sources":sum(x["current_scan_verified"] for x in health),
                      "unverified_sources":[{"key":x["key"],"diagnostic":x.get("diagnostic","not_approved")}
                                            for x in health if not x["current_scan_verified"]],
                      "sources":health}))

if __name__=="__main__":
    main()
