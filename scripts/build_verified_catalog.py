"""Build initial editorial snapshot from individually verified official calendar facts.

This is a one-time curated seed, not a replacement for the monitored import
pipeline. Never infer missing hours; refuse arbitrary or unsafe URLs.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "verified-launch-catalog.json"
OUTPUT = ROOT / "site" / "performances.json"
TIME_EVIDENCE = ROOT / "data" / "verified-time-evidence.json"
APPROVED_PAGES = {
    "https://www.teatroallascala.org/it/stagione/2026-2027/opera/don-giovanni.html",
    "https://www.teatrocomunalemodena.it/spettacolo/la-costanza-trionfante/",
    "https://www.teatroallascala.org/it/stagione/2026-2027/opera/la-boheme.html",
    "https://www.arena.it/arena-opera-festival/nabucco/",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/edgar",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/salome",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/cavalleria-rusticana",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/pagliacci",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-boheme",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/iris",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/carmen",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/evgenij-onegin",
    "https://www.operalombardia.it/l-italiana-in-algeri/",
    "https://www.operalombardia.it/calendario/",
    "https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello.html",
    "https://www.arena.it/arena-opera-festival/aida-ed-gianfranco-de-bosio/",
    "https://www.teatrolafenice.it/event/fedora/",
    "https://www.teatromassimo.it/event/samson-et-dalila/",
    "https://www.teatromassimo.it/event/macbeth/",
    "https://teatroregioparma.it/spettacolo/madama-butterfly/",
    "https://teatroregioparma.it/spettacolo/alzira/",
    "https://teatroregioparma.it/spettacolo/nabucodonosor/",
    "https://teatroregioparma.it/spettacolo/aida/",
    "https://www.teatrolafenice.it/event/jenufa/",
    "https://www.teatrolafenice.it/event/madamabutterflycallegari/",
    "https://www.teatrolafenice.it/event/carmenaxelrod/",
    "https://www.teatromassimo.it/event/lucia-di-lammermoor-2/",
    "https://www.teatromassimo.it/event/tosca-2/",
    "https://www.teatrofraschini.it/programma/turandot/",
    "https://www.teatrofraschini.it/programma/cavalleria-rusticana-pagliacci/",
    "https://www.teatrofraschini.it/programma/un-ballo-in-maschera/",
    "https://www.teatrofraschini.it/programma/death-in-venice/",
    "https://www.teatromassimobellini.it/eventi/aida-2026/",
    "https://www.teatromassimobellini.it/eventi/la-vedova-allegra-2026/",
    "https://www.teatromassimobellini.it/eventi/andrea-chenier-2026/",
    "https://www.teatromassimo.it/event/dido-and-aeneas-2/",
    "https://www.teatromassimo.it/event/semiramide/",
    "https://www.teatromassimo.it/event/aida/",
    "https://www.teatrolafenice.it/event/stagione-25-26-venere-e-adone/",
}


# Exact evidence URLs are reviewed manually against the specific showtime.
# These are facts from the theatre/municipality, NOT crawler permissions.
TIME_EVIDENCE_URLS = {
    "lombardia-turandot-como": {"https://teatrosocialecomo.it/spettacoli/turandot-2/"},
    "lombardia-ballo-cremona": {"https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-un-ballo-maschera"},
    "lombardia-italiana-como": {
        "https://teatrosocialecomo.it/spettacoli/l-italiana-in-algeri/",
    },
    "lombardia-italiana-pavia": {
        "https://www.teatrofraschini.it/programma/litaliana-in-algeri/",
    },
    "lombardia-italiana-brescia": {
        "https://teatrogrande.it/it/stagioni/2026/l-italiana-in-algeri",
    },
    "lombardia-italiana-cremona": {
        "https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-litaliana-algeri",
        "https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-litaliana-algeri-0",
    },
}


HISTORICAL_H1_APPROVAL = ROOT / "data" / "approved-2026-h1-opera-recitals.json"


def approved_historical_h1() -> dict[str, dict]:
    """Exact, frozen, first-party 2025/26 opera recite already reviewed.

    Never enable a whole hostname, path family, or unreviewed work. The
    acceptance gate is per official production URL, title, composer, actual
    performing theatre and *all* exact dates/times. The 2026 H1 archival
    observations are not automatically promoted.
    """
    import re
    document = json.loads(HISTORICAL_H1_APPROVAL.read_text(encoding="utf-8"))
    if (document.get("schema_version") != 1 or document.get("year") != 2026
            or not isinstance(document.get("records"), list)):
        raise ValueError("invalid 2026 historical publication approval")
    result = {}
    for record in document["records"]:
        url = record.get("source_url")
        if not isinstance(url, str):
            raise ValueError("missing historical opera source URL")
        parsed = urlsplit(url)
        scala = (parsed.hostname == "www.teatroallascala.org"
                 and re.fullmatch(r"/it/stagione/2025-2026/opera/[a-z0-9-]+\.html", parsed.path)
                 and record.get("city") == "Milano"
                 and record.get("venue") == "Teatro alla Scala")
        fenice = (parsed.hostname == "www.teatrolafenice.it"
                  and re.fullmatch(r"/event/stagione-25-26-[a-z0-9-]+/", parsed.path)
                  and record.get("city") == "Venezia"
                  and record.get("venue") in {"Teatro La Fenice", "Teatro Malibran"})
        regio = (parsed.hostname == "www.teatroregio.torino.it"
                 and re.fullmatch(r"/opera-e-balletto-2025-2026/[a-z0-9-]+", parsed.path)
                 and record.get("city") == "Torino"
                 and record.get("venue") == "Teatro Regio"
                 and record.get("source_venue") == "Teatro Regio di Torino")
        # Pisa 2025/26 first-party opera production / official season press:
        # Exact titles, composers, general-public clocks and venue only.
        pisa_2026 = {
            "https://teatrodipisa.it/spettacolo/carmen/":
                ("Carmen", "Georges Bizet", [("2026-01-23","20:30"),("2026-01-25","15:30")]),
            "https://teatrodipisa.it/the-turn-of-the-screw-a-50-anni-dalla-morte-di-britten-per-la-prima-volta-al-teatro-verdi/":
                ("The Turn of the Screw", "Benjamin Britten",
                 [("2026-02-27","20:30"),("2026-03-01","15:30")]),
            "https://teatrodipisa.it/spettacolo/lelisir-damore/":
                ("L’elisir d’amore", "Gaetano Donizetti",
                 [("2026-03-27","20:30"),("2026-03-29","15:30")]),
        }
        pisa = (url in pisa_2026 and parsed.hostname == "teatrodipisa.it"
                and record.get("city") == "Pisa"
                and record.get("venue") == "Teatro Verdi"
                and record.get("source_venue") == "Teatro Verdi di Pisa"
                and record.get("audience") == "general_public")
        if pisa:
            pisa_title, pisa_composer, pisa_dates = pisa_2026[url]
            if (record.get("canonical_title") != pisa_title
                    or record.get("official_source_title") != pisa_title
                    or record.get("composer") != pisa_composer
                    or sorted(record.get("dates",[])) != sorted(map(list,pisa_dates))):
                raise ValueError("unverified Pisa 2026 H1 production or showtimes")
        if (parsed.scheme != "https" or parsed.query or parsed.fragment
                or parsed.port is not None or parsed.username or parsed.password
                or not (scala or fenice or regio or pisa) or url in result):
            raise ValueError("unapproved historical opera source")
        title, original, composer = (record.get(k) for k in
                                     ("canonical_title", "official_source_title", "composer"))
        if not all(isinstance(x,str) and x.strip() for x in (title,original,composer)):
            raise ValueError("historical work identity required")
        # Parenthesized Ring cycle headings describe FOUR canonical operas,
        # not four new titles containing the production-series heading.
        exact_ring_aliases={
            ("Das Rheingold","Das Rheingold (Der Ring des Nibelungen)","Richard Wagner"),
            ("Die Walküre","Die Walküre (Der Ring des Nibelungen)","Richard Wagner"),
            ("Siegfried","Siegfried (Der Ring des Nibelungen)","Richard Wagner"),
            ("Götterdämmerung","Götterdämmerung (Der Ring des Nibelungen)","Richard Wagner"),
        }
        if (title != original and
                (title, original, composer) not in exact_ring_aliases
                and (title, original, composer) !=
                ("Nabucco", "Nabucodonosor", "Giuseppe Verdi")):
            raise ValueError("unapproved historical work alias")
        dates = record.get("dates")
        if not isinstance(dates,list) or not dates or len(dates)>40:
            raise ValueError("invalid historical performance list")
        seen = set()
        for row in dates:
            if not isinstance(row,list) or len(row)!=2:
                raise ValueError("invalid historical date/time")
            day,hour=row
            if (not isinstance(day,str) or not ("2026-01-01" <= day <= "2026-06-30")
                    or date.fromisoformat(day).isoformat()!=day
                    or not isinstance(hour,str)
                    or datetime.strptime(hour,"%H:%M").strftime("%H:%M")!=hour
                    or (day,hour) in seen):
                raise ValueError("unreviewed historical recita or time")
            seen.add((day,hour))
        # Every newly admitted 2025/26 Scala/Fenice opera must match
        # the already checked retrospective source-extracted showtimes.
        # Do not authorize extra dates through a conveniently shaped URL.
        if (scala or fenice) and title in {
                "Das Rheingold","Die Walküre","Siegfried",
                "Götterdämmerung","Pelléas et Mélisande",
                "Enrico di Borgogna","Ottone in villa"}:
            retrospective=json.loads((ROOT/"public"/"diagnostics"/
                "atlas-2026-jan-jun-official-archive.json").read_text(encoding="utf-8"))
            source_facts=[x for x in retrospective.get("observations",[])
                          if x.get("official_url")==url
                          and x.get("event_title")==original
                          and x.get("composer")==composer
                          and x.get("venue")==record.get("venue")]
            verified=sorted([[x["date"],x["starts_at"][11:16]] for x in source_facts])
            if verified != sorted(dates):
                raise ValueError("historical 2026 production dates differ from official parser facts")
        if regio:
            # Independent official archive evidence is the ONLY authorization
            # for these exact Torino dates. No newly discovered or preview
            # performances can enter the canonical catalog by URL pattern.
            historical = json.loads((ROOT / "data" /
                "historical-2026-official-evidence.json").read_text(encoding="utf-8"))
            evidence = [x for x in historical.get("records", [])
                        if x.get("source_url") == url
                        and x.get("venue_id") == "oa-v-000001"
                        and x.get("venue") == record["source_venue"]
                        and x.get("city") == "Torino"
                        and x.get("title") == title
                        and x.get("composer") == composer
                        and x.get("audience") == "general_public"
                        and x.get("source_type") == "official_event_detail"]
            if (len(evidence) != 1 or
                sorted([[x["date"],x["time"]] for x in evidence[0]["dates"]])
                    != sorted(dates)):
                raise ValueError("Torino date/time differs from reviewed official evidence")
        result[url]=record
    return result


AUTO_SOURCE_URLS = ROOT / "data" / "auto-source-urls.json"

def validate_auto_sources(urls: list[str]) -> set[str]:
    """Only exact official production URLs from approved national indexes."""
    from scripts.discover_season_indexes import CONFIG, validate_config, eligible
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    sources = [x for x in validate_config(config) if x["access_status"] == "approved"]
    if not isinstance(urls,list) or len(urls)!=len(set(urls)):
        raise ValueError("invalid auto source registry")
    allowed = set()
    for url in urls:
        if not isinstance(url,str) or not url.startswith("https://"):
            raise ValueError("invalid automatic official URL")
        parsed=urlsplit(url)
        # Sassari's three approved opera pages use stable ?id=NNN URLs.
        # A general query ban incorrectly rejected them *after* their
        # source adapter had already verified exact title, clocks and venue.
        permitted_query=(
            parsed.query and any((x["key"]=="sassari-de-carolis-opera-2026"
                                  or (x["key"]=="sassari-de-carolis-rolling-opera"
                                      and url in {
                                          "https://www.marialisadecarolis.it/opera-lirica.aspx?id=370",
                                          "https://www.marialisadecarolis.it/opera-lirica.aspx?id=371"}))
                                 and parsed.hostname==urlsplit(x["official_url"]).hostname
                                 and eligible(x["key"],url) for x in sources))
        # The municipality is an exact, verified fallback for the Spoleto
        # TLS source, not a broad exception for municipal hostnames.
        from opera_atlas.spoleto_municipal_parser import URL as spoleto_notice
        exact_municipal_fallback=(
            url==spoleto_notice and any(
                x["key"]=="spoleto-tls-lirica-2026"
                and eligible(x["key"],url) for x in sources))
        if ((parsed.query and not permitted_query)
            or parsed.fragment or parsed.username or parsed.password
            or parsed.port is not None or not (
                exact_municipal_fallback or any(
                    parsed.hostname==urlsplit(x["official_url"]).hostname
                    and eligible(x["key"],url) for x in sources))):
            raise ValueError(f"automatic source outside an approved official production section: {url}")
        allowed.add(url)
    return allowed

def auto_approved_pages() -> set[str]:
    if not AUTO_SOURCE_URLS.exists():return set()
    doc=json.loads(AUTO_SOURCE_URLS.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1:return set()
    return validate_auto_sources(doc["urls"])

def replica_registry_key(production:dict,day:str,hour:str|None)->str:
    """Keep historical day-only IDs; disambiguate only same-day recite."""
    slots=[row for row in production["dates"] if row[0]==day]
    if len(slots)>1:
        if hour is None or len({row[1] for row in slots})!=len(slots):
            raise ValueError("same-day recite require unique verified clocks")
        return production["key"]+"|"+day+"|"+hour
    return production["key"]+"|"+day


def validate_time_evidence(manifest: dict, evidence: dict) -> dict:
    """Validate additional official showtimes, bound to known staging/date.

    Reject typos, unreviewed URLs and contradictory upstream source times.
    The same stable performance ID is used after enrichment.
    """
    if evidence.get("schema_version") != 1 or not isinstance(evidence.get("times"), dict):
        raise ValueError("invalid time evidence document")
    valid = {}
    for product in manifest["productions"]:
        for day, hour in product["dates"]:
            valid[replica_registry_key(product,day,hour)] = (product, hour)
    seen = set()
    for key, entry in evidence["times"].items():
        if key in seen or key not in valid:
            raise ValueError("time evidence must identify one known replica")
        seen.add(key)
        product, old_hour = valid[key]
        if not isinstance(entry, dict) or set(entry) != {"time", "url"}:
            raise ValueError("invalid official time evidence fields")
        if entry["url"] not in TIME_EVIDENCE_URLS.get(product["key"], set()):
            raise ValueError("unreviewed evidence URL for this theatre")
        if not isinstance(entry["time"], str):
            raise ValueError("invalid verified showtime")
        try:
            parsed = datetime.strptime(entry["time"], "%H:%M").strftime("%H:%M")
        except ValueError as exc:
            raise ValueError("invalid verified showtime") from exc
        if parsed != entry["time"] or (old_hour is not None and old_hour != parsed):
            raise ValueError("contradictory verified showtime")
    return evidence["times"]


ITALIAN_TIMEZONE = ZoneInfo("Europe/Rome")


def official_local_time(day: str, clock: str) -> str:
    """Create an offset-aware Italian start time; reject DST gaps/overlaps.

    An absent hour is intentionally represented as null upstream.
    """
    naive = datetime.fromisoformat(day + "T" + clock + ":00")
    local = naive.replace(tzinfo=ITALIAN_TIMEZONE)
    if local.astimezone(timezone.utc).astimezone(ITALIAN_TIMEZONE).replace(
        tzinfo=None
    ) != naive:
        raise ValueError("nonexistent Italian local performance time")
    alternate = local.replace(fold=1)
    if alternate.utcoffset() != local.utcoffset():
        raise ValueError("ambiguous Italian local performance time")
    return local.isoformat(timespec="seconds")


def build(manifest: dict, evidence: dict | None = None, *, approved_extra: set[str] | None = None) -> dict:
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("productions"), list):
        raise ValueError("invalid editorial manifest")
    if evidence is None:
        evidence = json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
    showtimes = validate_time_evidence(manifest, evidence)
    # Extra in-memory URLs for the pending transaction must NOT replace the
    # already-persisted approved URLs: after a successful import tests rebuild
    # the expanded canonical catalog, not the original static launch seed.
    historical_approved = approved_historical_h1()
    permitted = APPROVED_PAGES | auto_approved_pages() | set(historical_approved) | (approved_extra or set())
    cagliari_archive = "https://www.liricocagliari.it/archivio/it/spettacoli/2026_lirica.html"
    cagliari_approved = {
        "historical-2026-cagliari-norma": {
            "title": "Norma",
            "composer": "Vincenzo Bellini",
            "dates": [
                [
                    "2026-03-18",
                    "20:00"
                ],
                [
                    "2026-03-19",
                    "19:00"
                ],
                [
                    "2026-03-20",
                    "20:00"
                ],
                [
                    "2026-03-21",
                    "19:00"
                ],
                [
                    "2026-03-22",
                    "17:00"
                ]
            ]
        },
        "historical-2026-cagliari-turandot": {
            "title": "Turandot",
            "composer": "Giacomo Puccini",
            "dates": [
                [
                    "2026-06-24",
                    "20:00"
                ],
                [
                    "2026-06-25",
                    "19:00"
                ],
                [
                    "2026-06-26",
                    "20:00"
                ],
                [
                    "2026-06-27",
                    "19:00"
                ],
                [
                    "2026-06-28",
                    "17:00"
                ],
                [
                    "2026-06-30",
                    "20:00"
                ],
                [
                    "2026-07-01",
                    "20:00"
                ],
                [
                    "2026-07-02",
                    "20:00"
                ]
            ]
        },
        "historical-2026-cagliari-rigoletto": {
            "title": "Rigoletto",
            "composer": "Giuseppe Verdi",
            "dates": [
                [
                    "2026-11-11",
                    "20:00"
                ],
                [
                    "2026-11-12",
                    "19:00"
                ],
                [
                    "2026-11-13",
                    "20:00"
                ],
                [
                    "2026-11-14",
                    "19:00"
                ],
                [
                    "2026-11-15",
                    "17:00"
                ],
                [
                    "2026-11-19",
                    "20:00"
                ],
                [
                    "2026-11-21",
                    "19:00"
                ]
            ]
        }
    }
    cagliari_approved.update({
        "historical-2026-cagliari-lucrezia-borgia": {
            "title": "Lucrezia Borgia",
            "composer": "Gaetano Donizetti",
            "dates": [
                [
                    "2026-01-28",
                    "20:00"
                ],
                [
                    "2026-01-29",
                    "19:00"
                ],
                [
                    "2026-01-30",
                    "20:00"
                ],
                [
                    "2026-01-31",
                    "19:00"
                ],
                [
                    "2026-02-01",
                    "17:00"
                ]
            ]
        },
        "historical-2026-cagliari-cosi-fan-tutte": {
            "title": "Così fan tutte",
            "composer": "Wolfgang Amadeus Mozart",
            "dates": [
                [
                    "2026-04-17",
                    "20:00"
                ],
                [
                    "2026-04-18",
                    "19:00"
                ],
                [
                    "2026-04-19",
                    "17:00"
                ],
                [
                    "2026-04-21",
                    "20:00"
                ],
                [
                    "2026-04-22",
                    "20:00"
                ]
            ]
        },
        "historical-2026-cagliari-il-cappello-di-paglia-di-firenze": {
            "title": "Il cappello di paglia di Firenze",
            "composer": "Nino Rota",
            "dates": [
                [
                    "2026-09-23",
                    "20:00"
                ],
                [
                    "2026-09-24",
                    "19:00"
                ],
                [
                    "2026-09-25",
                    "20:00"
                ],
                [
                    "2026-09-26",
                    "19:00"
                ],
                [
                    "2026-09-27",
                    "17:00"
                ]
            ]
        }
    })
    permitted.add(cagliari_archive)
    reconciled_2026 = {
        "historical-2026-como-teatro-sociale-don-quichotte": {
            "title": "Don Quichotte",
            "composer": "Jules Massenet",
            "venue": "Teatro Sociale",
            "municipality": "Como",
            "region": "Lombardia",
            "source_url": "https://teatrosocialecomo.it/spettacoli/don-quichotte/",
            "dates": [
                [
                    "2026-01-16",
                    "20:00"
                ],
                [
                    "2026-01-18",
                    "15:30"
                ]
            ]
        },
        "historical-2026-verona-arena-di-verona-aida": {
            "title": "Aida",
            "composer": "Giuseppe Verdi",
            "venue": "Arena di Verona",
            "municipality": "Verona",
            "region": "Veneto",
            "source_url": "https://www.arena.it/magazine/news/arena-a-tutto-verdi-dal-25-al-27-giugno/",
            "dates": [
                [
                    "2026-06-25",
                    "21:15"
                ]
            ]
        },
        "historical-2026-verona-arena-di-verona-nabucco": {
            "title": "Nabucco",
            "composer": "Giuseppe Verdi",
            "venue": "Arena di Verona",
            "municipality": "Verona",
            "region": "Veneto",
            "source_url": "https://www.arena.it/magazine/news/arena-a-tutto-verdi-dal-25-al-27-giugno/",
            "dates": [
                [
                    "2026-06-26",
                    "21:15"
                ]
            ]
        },
        "historical-2026-verona-arena-di-verona-la-traviata": {
            "title": "La traviata",
            "composer": "Giuseppe Verdi",
            "venue": "Arena di Verona",
            "municipality": "Verona",
            "region": "Veneto",
            "source_url": "https://www.arena.it/magazine/news/arena-a-tutto-verdi-dal-25-al-27-giugno/",
            "dates": [
                [
                    "2026-06-27",
                    "21:15"
                ]
            ]
        },
        "historical-2026-verona-teatro-filarmonico-don-giovanni": {
            "title": "Don Giovanni",
            "composer": "Wolfgang Amadeus Mozart",
            "venue": "Teatro Filarmonico",
            "municipality": "Verona",
            "region": "Veneto",
            "source_url": "https://www.arena.it/magazine/news/don-giovanni-il-capolavoro-di-mozart-inaugura-la-stagione-2026-del-teatro-filarmonico/",
            "dates": [
                [
                    "2026-01-18",
                    "15:30"
                ],
                [
                    "2026-01-21",
                    "19:00"
                ],
                [
                    "2026-01-23",
                    "20:00"
                ],
                [
                    "2026-01-25",
                    "15:30"
                ]
            ]
        },
        "historical-2026-messina-teatro-vittorio-emanuele-turandot": {
            "title": "Turandot",
            "composer": "Giacomo Puccini",
            "venue": "Teatro Vittorio Emanuele",
            "municipality": "Messina",
            "region": "Sicilia",
            "source_url": "https://www.teatrovittorioemanuele.it/evento/turandot/",
            "dates": [
                [
                    "2026-02-13",
                    "21:00"
                ],
                [
                    "2026-02-15",
                    "17:30"
                ]
            ]
        },
        "historical-2026-lucca-teatro-del-giglio-giacomo-puccini-nabucco": {
            "title": "Nabucco",
            "composer": "Giuseppe Verdi",
            "venue": "Teatro del Giglio Giacomo Puccini",
            "municipality": "Lucca",
            "region": "Toscana",
            "source_url": "https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/lirica/stagione-2025-2026/",
            "dates": [
                [
                    "2026-01-04",
                    "18:00"
                ],
                [
                    "2026-01-05",
                    "16:00"
                ]
            ]
        },
        "historical-2026-lucca-teatro-del-giglio-giacomo-puccini-turandot": {
            "title": "Turandot",
            "composer": "Giacomo Puccini",
            "venue": "Teatro del Giglio Giacomo Puccini",
            "municipality": "Lucca",
            "region": "Toscana",
            "source_url": "https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/lirica/stagione-2025-2026/",
            "dates": [
                [
                    "2026-04-25",
                    "18:00"
                ],
                [
                    "2026-04-26",
                    "16:00"
                ]
            ]
        },
        "lombardia-turandot-como": {
            "title": "Turandot",
            "composer": "Giacomo Puccini",
            "venue": "Teatro Sociale",
            "municipality": "Como",
            "region": "Lombardia",
            "source_url": "https://www.operalombardia.it/calendario/",
            "dates": [
                [
                    "2026-09-24",
                    None
                ],
                [
                    "2026-09-26",
                    None
                ]
            ]
        },
        "lombardia-ballo-cremona": {
            "title": "Un ballo in maschera",
            "composer": "Giuseppe Verdi",
            "venue": "Teatro Ponchielli",
            "municipality": "Cremona",
            "region": "Lombardia",
            "source_url": "https://www.operalombardia.it/calendario/",
            "dates": [
                [
                    "2026-11-27",
                    None
                ],
                [
                    "2026-11-29",
                    None
                ]
            ]
        }
    }
    reconciled_2026.update({
        "historical-2026-novara-don-pasquale": {
            "title": "Don Pasquale",
            "composer": "Gaetano Donizetti",
            "venue": "Teatro Coccia",
            "municipality": "Novara",
            "region": "Piemonte",
            "source_url": "https://www.fondazioneteatrococcia.it/stagione-26-don-pasquale.html",
            "dates": [
                [
                    "2026-11-21",
                    "20:30"
                ],
                [
                    "2026-11-22",
                    "16:00"
                ]
            ]
        },
        "historical-2026-mantova-la-traviata": {
            "title": "La traviata",
            "composer": "Giuseppe Verdi",
            "venue": "Teatro Sociale di Mantova",
            "municipality": "Mantova",
            "region": "Lombardia",
            "source_url": "https://www.teatrosocialemantova.it/it-it/la-traviata-v3.aspx",
            "dates": [
                [
                    "2026-12-20",
                    "17:30"
                ]
            ]
        },
        "historical-2026-asti-la-boheme": {
            "title": "La bohème",
            "composer": "Giacomo Puccini",
            "venue": "Teatro Alfieri",
            "municipality": "Asti",
            "region": "Piemonte",
            "source_url": "https://www.comune.asti.it/novita/comunicati/boheme-giacomo-puccini",
            "dates": [
                [
                    "2026-02-14",
                    "21:00"
                ]
            ]
        }
    })
    reconciled_2026.update({
        "historical-2026-macerata-nabucco": {
            "title": "Nabucco",
            "composer": "Giuseppe Verdi",
            "venue": "Arena Sferisterio",
            "municipality": "Macerata",
            "region": "Marche",
            "source_url": "https://www.sferisterio.it/macerata-opera-festival/nabucco",
            "dates": [
                [
                    "2026-07-17",
                    "21:00"
                ],
                [
                    "2026-07-26",
                    "21:00"
                ],
                [
                    "2026-08-01",
                    "21:00"
                ],
                [
                    "2026-08-09",
                    "21:00"
                ]
            ]
        },
        "historical-2026-macerata-il-barbiere-di-siviglia": {
            "title": "Il barbiere di Siviglia",
            "composer": "Gioachino Rossini",
            "venue": "Arena Sferisterio",
            "municipality": "Macerata",
            "region": "Marche",
            "source_url": "https://www.sferisterio.it/macerata-opera-festival/il-barbiere-di-siviglia-2026",
            "dates": [
                [
                    "2026-07-18",
                    "21:00"
                ],
                [
                    "2026-07-24",
                    "21:00"
                ],
                [
                    "2026-08-02",
                    "21:00"
                ],
                [
                    "2026-08-08",
                    "21:00"
                ]
            ]
        },
        "historical-2026-macerata-il-trovatore": {
            "title": "Il trovatore",
            "composer": "Giuseppe Verdi",
            "venue": "Arena Sferisterio",
            "municipality": "Macerata",
            "region": "Marche",
            "source_url": "https://www.sferisterio.it/macerata-opera-festival/il-trovatore-2026",
            "dates": [
                [
                    "2026-07-19",
                    "21:00"
                ],
                [
                    "2026-07-25",
                    "21:00"
                ],
                [
                    "2026-07-31",
                    "21:00"
                ]
            ]
        },
        "historical-2026-torre-del-lago-puccini-turandot": {
            "title": "Turandot",
            "composer": "Giacomo Puccini",
            "venue": "Gran Teatro Giacomo Puccini",
            "municipality": "Torre del Lago Puccini",
            "region": "Toscana",
            "source_url": "https://www.comune.viareggio.lu.it/eventi/CLT-Puccini-Festival-2031.html",
            "dates": [
                [
                    "2026-07-17",
                    "21:15"
                ],
                [
                    "2026-07-24",
                    "21:15"
                ],
                [
                    "2026-08-01",
                    "21:15"
                ],
                [
                    "2026-08-09",
                    "21:15"
                ]
            ]
        },
        "historical-2026-torre-del-lago-puccini-tosca": {
            "title": "Tosca",
            "composer": "Giacomo Puccini",
            "venue": "Gran Teatro Giacomo Puccini",
            "municipality": "Torre del Lago Puccini",
            "region": "Toscana",
            "source_url": "https://www.comune.viareggio.lu.it/eventi/CLT-Puccini-Festival-2031.html",
            "dates": [
                [
                    "2026-07-18",
                    "21:15"
                ],
                [
                    "2026-07-31",
                    "21:15"
                ],
                [
                    "2026-08-08",
                    "21:15"
                ],
                [
                    "2026-08-21",
                    "21:15"
                ]
            ]
        },
        "historical-2026-torre-del-lago-puccini-madama-butterfly": {
            "title": "Madama Butterfly",
            "composer": "Giacomo Puccini",
            "venue": "Gran Teatro Giacomo Puccini",
            "municipality": "Torre del Lago Puccini",
            "region": "Toscana",
            "source_url": "https://www.comune.viareggio.lu.it/eventi/CLT-Puccini-Festival-2031.html",
            "dates": [
                [
                    "2026-08-07",
                    "21:15"
                ],
                [
                    "2026-08-22",
                    "21:15"
                ],
                [
                    "2026-09-04",
                    "21:15"
                ]
            ]
        },
        "historical-2026-torre-del-lago-puccini-la-boheme": {
            "title": "La bohème",
            "composer": "Giacomo Puccini",
            "venue": "Gran Teatro Giacomo Puccini",
            "municipality": "Torre del Lago Puccini",
            "region": "Toscana",
            "source_url": "https://www.comune.viareggio.lu.it/eventi/CLT-Puccini-Festival-2031.html",
            "dates": [
                [
                    "2026-07-25",
                    "21:15"
                ],
                [
                    "2026-08-06",
                    "21:15"
                ],
                [
                    "2026-08-28",
                    "21:15"
                ]
            ]
        },
        "historical-2026-ravenna-macbeth": {
            "title": "Macbeth",
            "composer": "Giuseppe Verdi",
            "venue": "Teatro Dante Alighieri",
            "municipality": "Ravenna",
            "region": "Emilia-Romagna",
            "source_url": "https://www.turismo.ra.it/eventi/teatro-opera-danza/stagione-opera-e-danza/",
            "dates": [
                [
                    "2026-01-30",
                    "20:00"
                ],
                [
                    "2026-02-01",
                    "15:30"
                ]
            ]
        },
        "historical-2026-ravenna-italiana-in-algeri": {
            "title": "L’italiana in Algeri",
            "composer": "Gioachino Rossini",
            "venue": "Teatro Dante Alighieri",
            "municipality": "Ravenna",
            "region": "Emilia-Romagna",
            "source_url": "https://www.turismo.ra.it/eventi/teatro-opera-danza/stagione-opera-e-danza/",
            "dates": [
                [
                    "2026-03-13",
                    "20:00"
                ],
                [
                    "2026-03-15",
                    "15:30"
                ]
            ]
        },
        "historical-2026-ravenna-carmen": {
            "title": "Carmen",
            "composer": "Georges Bizet",
            "venue": "Teatro Dante Alighieri",
            "municipality": "Ravenna",
            "region": "Emilia-Romagna",
            "source_url": "https://www.turismo.ra.it/eventi/teatro-opera-danza/stagione-opera-e-danza/",
            "dates": [
                [
                    "2026-04-24",
                    "20:00"
                ],
                [
                    "2026-04-26",
                    "15:30"
                ]
            ]
        }
    })
    reconciled_2026.update({
        "historical-2026-torre-del-lago-puccini-la-fanciulla-del-west": {
            "title": "La fanciulla del West",
            "composer": "Giacomo Puccini",
            "venue": "Gran Teatro Giacomo Puccini",
            "municipality": "Torre del Lago Puccini",
            "region": "Toscana",
            "source_url": "https://www.comune.viareggio.lu.it/eventi/CLT-Puccini-Festival-2031.html",
            "dates": [
                [
                    "2026-08-29",
                    "21:15"
                ],
                [
                    "2026-09-05",
                    "21:15"
                ]
            ]
        }
    })
    reconciled_2026.update({
        "historical-2026-sabbioneta-orfeo": {
            "title": "L'Orfeo",
            "composer": "Claudio Monteverdi",
            "venue": "Teatro all'Antica",
            "municipality": "Sabbioneta",
            "region": "Lombardia",
            "source_url": "https://www.comune.sabbioneta.mn.it/index.php/it/news/2043432",
            "dates": [
                [
                    "2026-09-19",
                    "20:30"
                ]
            ]
        },
        "historical-2026-sabbioneta-il-barbiere-di-siviglia": {
            "title": "Il barbiere di Siviglia",
            "composer": "Gioachino Rossini",
            "venue": "Teatro all'Antica",
            "municipality": "Sabbioneta",
            "region": "Lombardia",
            "source_url": "https://www.comune.sabbioneta.mn.it/it/news/il-barbiere-di-siviglia-al-teatro-allantica",
            "dates": [
                [
                    "2026-11-14",
                    "20:30"
                ]
            ]
        }
    })
    reconciled_urls = {row["source_url"] for row in reconciled_2026.values()}
    permitted.update(reconciled_urls)
    events = []
    keys = set()
    for production in manifest["productions"]:
        url = production["source_url"]
        reviewed_2026 = reconciled_2026.get(production.get("key"))
        if reviewed_2026 is not None:
            if any(production.get(field) != reviewed_2026[field] for field in
                   ("title", "composer", "venue", "municipality", "region", "source_url")) or sorted(production.get("dates", [])) != sorted(reviewed_2026["dates"]):
                raise ValueError("unreviewed reconciled 2026 production")
        elif url in reconciled_urls - {"https://www.operalombardia.it/calendario/"}:
            raise ValueError("unreviewed reconciled 2026 source identity")
        if url == cagliari_archive:
            reviewed = cagliari_approved.get(production.get("key"))
            if (reviewed is None or production.get("title") != reviewed["title"]
                    or production.get("composer") != reviewed["composer"]
                    or production.get("municipality") != "Cagliari"
                    or production.get("venue") != "Teatro Lirico di Cagliari"
                    or production.get("region") != "Sardegna"
                    or sorted(production.get("dates", [])) != sorted(reviewed["dates"])):
                raise ValueError("unreviewed Cagliari archive production")
        if url not in permitted:
            raise ValueError("non-reviewed source page")
        # Modena Belcanto 2026: an opera, not a symphonic concert. The
        # surviving RV 706-A music was staged semiscenically with missing
        # sections narrated by Federico Maria Sardelli. One verified showtime,
        # and no permission to infer further dates or an integral staging.
        if url == "https://www.teatrocomunalemodena.it/spettacolo/la-costanza-trionfante/":
            if (production.get("title") != "La costanza trionfante"
                    or production.get("composer") != "Antonio Vivaldi"
                    or production.get("municipality") != "Modena"
                    or production.get("venue") != "Teatro Comunale Pavarotti-Freni"
                    or production.get("region") != "Emilia-Romagna"
                    or production.get("performance_format") !=
                        "semiscenica_musica_superstite_parti_mancanti_narrate"
                    or production.get("festival") != "Modena Belcanto Festival 2026"
                    or production.get("dates") != [["2026-09-25","20:30"]]):
                raise ValueError("La costanza trionfante: only reviewed 2026 semiscenic staging permitted")
        # Manually reviewed first Italian staging of Sciarrino's 2023 opera.
        # A single approved first-party URL MUST NOT license other dates, works
        # or venues; the fifth performance is 1 July, after the H1 boundary.
        if url == "https://www.teatrolafenice.it/event/stagione-25-26-venere-e-adone/":
            if (production.get("title") != "Venere e Adone"
                    or production.get("composer") != "Salvatore Sciarrino"
                    or production.get("venue") != "Teatro La Fenice"
                    or production.get("municipality") != "Venezia"
                    or production.get("region") != "Veneto"
                    or sorted(production.get("dates", [])) != sorted([
                        ["2026-06-26", "19:00"], ["2026-06-27", "17:00"],
                        ["2026-06-28", "17:00"], ["2026-06-30", "19:00"],
                        ["2026-07-01", "19:00"],
                    ])):
                raise ValueError("Venere e Adone must match five official Fenice showtimes")
        # Exact verified 2026 Teatro Massimo Palermo general-public showtimes.
        # Aida's 26 May Turno Scuola is intentionally excluded.
        palermo_2026 = {
                "https://www.teatromassimo.it/event/dido-and-aeneas-2/": {
                        "title": "Dido and Æneas",
                        "composer": "Henry Purcell",
                        "dates": [
                                [
                                        "2026-02-20",
                                        "20:00"
                                ],
                                [
                                        "2026-02-21",
                                        "18:30"
                                ],
                                [
                                        "2026-02-22",
                                        "17:30"
                                ],
                                [
                                        "2026-02-24",
                                        "18:30"
                                ]
                        ]
                },
                "https://www.teatromassimo.it/event/semiramide/": {
                        "title": "Semiramide",
                        "composer": "Gioachino Rossini",
                        "dates": [
                                [
                                        "2026-03-11",
                                        "20:00"
                                ],
                                [
                                        "2026-03-12",
                                        "18:30"
                                ],
                                [
                                        "2026-03-13",
                                        "18:30"
                                ],
                                [
                                        "2026-03-14",
                                        "20:00"
                                ],
                                [
                                        "2026-03-15",
                                        "17:30"
                                ],
                                [
                                        "2026-03-17",
                                        "18:30"
                                ],
                                [
                                        "2026-03-18",
                                        "18:30"
                                ]
                        ]
                },
                "https://www.teatromassimo.it/event/aida/": {
                        "title": "Aida",
                        "composer": "Giuseppe Verdi",
                        "dates": [
                                [
                                        "2026-05-22",
                                        "20:00"
                                ],
                                [
                                        "2026-05-23",
                                        "18:30"
                                ],
                                [
                                        "2026-05-24",
                                        "17:30"
                                ],
                                [
                                        "2026-05-27",
                                        "18:30"
                                ],
                                [
                                        "2026-05-28",
                                        "20:00"
                                ],
                                [
                                        "2026-05-29",
                                        "18:30"
                                ],
                                [
                                        "2026-05-30",
                                        "20:00"
                                ],
                                [
                                        "2026-05-31",
                                        "18:30"
                                ]
                        ]
                }
        }
        if url in palermo_2026:
            approved=palermo_2026[url]
            if (production.get("title")!=approved["title"]
                    or production.get("composer")!=approved["composer"]
                    or production.get("municipality")!="Palermo"
                    or production.get("venue")!="Teatro Massimo"
                    or production.get("region")!="Sicilia"
                    or sorted(production.get("dates",[]))!=sorted(approved["dates"])):
                raise ValueError("unverified 2026 Teatro Massimo Palermo production")
        # Three first-party Catania 2026 work details have independently
        # reviewed tickets for all seven dates. S1/S2 are general-public
        # ticket categories at this theatre, not a school-only programme.
        bellini_2026 = {"https://www.teatromassimobellini.it/eventi/aida-2026/":{"title":"Aida","composer":"Giuseppe Verdi","dates":[["2026-01-20","20:30"],["2026-01-21","17:30"],["2026-01-22","17:30"],["2026-01-24","17:30"],["2026-01-25","17:30"],["2026-01-27","17:30"],["2026-01-28","20:30"]]},"https://www.teatromassimobellini.it/eventi/la-vedova-allegra-2026/":{"title":"La vedova allegra","composer":"Franz Lehár","dates":[["2026-03-06","20:30"],["2026-03-07","17:30"],["2026-03-08","17:30"],["2026-03-10","17:30"],["2026-03-11","20:30"],["2026-03-12","17:30"],["2026-03-13","17:30"]]},"https://www.teatromassimobellini.it/eventi/andrea-chenier-2026/":{"title":"Andrea Chénier","composer":"Umberto Giordano","dates":[["2026-04-10","20:30"],["2026-04-11","17:30"],["2026-04-12","17:30"],["2026-04-14","17:30"],["2026-04-15","20:30"],["2026-04-16","17:30"],["2026-04-18","17:30"]]}}
        if url in bellini_2026:
            reviewed=bellini_2026[url]
            if (production.get("title")!=reviewed["title"]
                    or production.get("composer")!=reviewed["composer"]
                    or production.get("municipality")!="Catania"
                    or production.get("venue")!="Teatro Massimo Bellini"
                    or production.get("region")!="Sicilia"
                    or sorted(production.get("dates",[]))!=sorted(reviewed["dates"])):
                raise ValueError("unverified Teatro Massimo Bellini 2026 production")
        if url in historical_approved:
            reviewed = historical_approved[url]
            if (production.get("title") != reviewed["canonical_title"]
                    or production.get("composer") != reviewed["composer"]
                    or production.get("municipality") != reviewed["city"]
                    or production.get("venue") != reviewed["venue"]
                    or sorted(production.get("dates",[])) != sorted(reviewed["dates"])):
                raise ValueError("historical source identity, venue or exact showtimes changed")
        for field in ("key", "title", "composer", "venue", "municipality", "region"):
            if not isinstance(production.get(field), str) or not production[field].strip():
                raise ValueError(f"missing verified {field}")
        if not isinstance(production.get("dates"), list) or not production["dates"]:
            raise ValueError("verified dates required")
        for entry in production["dates"]:
            if not isinstance(entry, list) or len(entry) != 2:
                raise ValueError("recita must contain exact day and optional time")
            local_day, hour = entry
            if date.fromisoformat(local_day).isoformat() != local_day:
                raise ValueError("invalid calendar date")
            if hour is not None and (not isinstance(hour, str)
                                    or datetime.strptime(hour, "%H:%M").strftime("%H:%M") != hour):
                raise ValueError("invalid time")
            replica_key = replica_registry_key(production,local_day,hour)
            evidence_entry = showtimes.get(replica_key)
            effective_hour = evidence_entry["time"] if evidence_entry else hour
            uid = "curated:"+replica_key.replace("|",":")
            if uid in keys:
                raise ValueError("duplicate editorial performance")
            keys.add(uid)
            # The curated Regio dates are all outside Italy's DST period.
            if (hour is not None and url not in permitted - {"https://www.operalombardia.it/l-italiana-in-algeri/", "https://www.operalombardia.it/calendario/"}):
                raise ValueError("no verified time for this source")
            if hour is None and url not in {"https://www.operalombardia.it/l-italiana-in-algeri/", "https://www.operalombardia.it/calendario/"}:
                raise ValueError("expected exact Regio performance hour")
            events.append({
                "id": uid,
                "starts_at": official_local_time(local_day, effective_hour) if effective_hour else None,
                "local_date": local_day,
                "time_known": effective_hour is not None,
                "time_label": effective_hour or "Orario da confermare",
                "status": "announced",
                "title": production["title"],
                "composer": production["composer"],
                "venue": production["venue"],
                "municipality": production["municipality"],
                "region": production["region"],
                "latitude": None,
                "longitude": None,
                "sources": [url] + ([evidence_entry["url"]] if evidence_entry else []),
            })
    events.sort(key=lambda e: (e["local_date"], e["starts_at"] or "", e["id"]))
    return {"schema_version": 1, "performances": events}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Verify committed export matches reviewed manifest")
    args = parser.parse_args()
    expected = build(json.loads(MANIFEST.read_text(encoding="utf-8")))
    if args.check:
        actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if actual != expected:
            raise SystemExit("Public catalog differs from reviewed source manifest")
        print(f"Verified {len(expected['performances'])} reviewed recite in public catalog")
    else:
        OUTPUT.write_text(json.dumps(expected, ensure_ascii=False, indent=2)+"\n",
                          encoding="utf-8")
        print(f"Wrote {len(expected['performances'])} reviewed recite")


if __name__ == "__main__":
    main()
