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
}


# Exact evidence URLs are reviewed manually against the specific showtime.
# These are facts from the theatre/municipality, NOT crawler permissions.
TIME_EVIDENCE_URLS = {
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
        if (parsed.scheme != "https" or parsed.query or parsed.fragment
                or parsed.port is not None or parsed.username or parsed.password
                or not (scala or fenice or regio) or url in result):
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
    events = []
    keys = set()
    for production in manifest["productions"]:
        url = production["source_url"]
        if url not in permitted:
            raise ValueError("non-reviewed source page")
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
            if hour is not None and url not in permitted - {"https://www.operalombardia.it/l-italiana-in-algeri/", "https://www.operalombardia.it/calendario/"}:
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
