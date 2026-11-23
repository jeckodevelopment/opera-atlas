"""Reconcile the venue directory against configured and recently checked official connectors.

Statuses are evidence-based: an 'acquired' venue page is not proof of
automation. A season index success is not proof of complete recite coverage.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/venue-directory.json"
DAILY = ROOT / "data/daily-source-config.json"
DAILY_HEALTH = ROOT / "data/catalog-source-health.json"
INDEX = ROOT / "data/season-index-config.json"
INDEX_HEALTH = ROOT / "data/season-index-health.json"
OUT = ROOT / "public/catalog/source-automation.json"
SAN_CARLO_SECONDARY = ROOT / "data/san-carlo-secondary-health.json"
SAN_CARLO_CANONICAL = ROOT / "data/san-carlo-canonical-review-health.json"
SAN_CARLO_CANDIDATES = ROOT / "data/season-index-candidates.json"
SAN_CARLO_PUBLIC = ROOT / "site/performances.json"
CANDIDATE_REGISTRY = ROOT / "data/season-index-candidates.json"

# Explicit links between sources and venues; never match unrelated theatres
# sharing a city, name, or festival organizer. Grouped sources are intentional.
INDEX_VENUES = {
    "cosenza-inprimafila-rolling-opera": ("Cosenza|Teatro Alfonso Rendano",),
    "taormina-arte-rolling-opera": ("Taormina|Teatro Antico di Taormina",),
    "taormina-opera-festival-rolling": ("Taormina|Teatro Antico di Taormina",),
    "taormina-fondazione-rolling-opera": ("Taormina|Teatro Antico di Taormina",),
    "sabbioneta-antica-rolling-opera": ("Sabbioneta|Teatro all\u0027Antica",),
    "vicenza-olimpico-rolling-opera": ("Vicenza|Teatro Olimpico",),
    "cosenza-rendano-rolling-opera": ("Cosenza|Teatro Alfonso Rendano",),
    "mantova-sociale-rolling-opera": ("Mantova|Teatro Sociale di Mantova",),
    "napoli-san-carlo-rolling-opera": ("Napoli|Teatro di San Carlo",),
    "pesaro-rof-2026": ("Pesaro|Teatro Gioachino Rossini",
                        "Pesaro|Auditorium Scavolini"),
    "martina-valle-itria-2026": ("Martina Franca|Palazzo Ducale di Martina Franca",
                              "Martina Franca|Chiostro del Carmine"),
    # Both physical venues are explicitly identified by the official programme parser.
    # Do not infer additional venues solely from the shared festival organizer.
    "trapani-luglio-musicale-2026": ("Trapani|Teatro Giuseppe Di Stefano",
                                     "Trapani|Teatro M° Tonino Pardo"),
    "haydn-rolling-opera": ("Bolzano|Teatro Comunale di Bolzano", "Trento|Teatro Sociale"),
    "asti-alfieri-rolling-opera": ("Asti|Teatro Alfieri",),
    "savona-giocosa-rolling-opera": ("Savona|Teatro Gabriello Chiabrera",),
    "sassari-de-carolis-opera-2026": ("Sassari|Teatro Comunale di Sassari",),
    "sassari-de-carolis-rolling-opera": ("Sassari|Teatro Comunale di Sassari",
                                        "Alghero|Forte della Maddalena"),
    "messina-vittorio-opera-2026-27": ("Messina|Teatro Vittorio Emanuele",),
    "lecce-apollo-pinocchio-2026": ("Lecce|Teatro Apollo",),
    "lecce-politeama-opera-2026": ("Lecce|Teatro Politeama Greco",),
    "lecce-provincia-politeama-2026": ("Lecce|Teatro Politeama Greco",),
    "rovigo-regione-programma-2026-27": ("Rovigo|Teatro Sociale",),
    "rovigo-sociale-opera-2026-27": ("Rovigo|Teatro Sociale",),
    "padova-verdi-opera-2026": ("Padova|Teatro Verdi",),
    "treviso-del-monaco-opera-2026-27": ("Treviso|Teatro Comunale Mario del Monaco",),
    "ravenna-alighieri-cherubini-2027": ("Ravenna|Teatro Dante Alighieri",),
    "ravenna-cherubini-rolling-opera": ("Ravenna|Teatro Dante Alighieri",),
    "coccia-novara-opera-2027": ("Novara|Teatro Coccia",),
    "coccia-novara-rolling-opera": ("Novara|Teatro Coccia",
                                    "Novara|Giardini di Palazzo Natta"),
    # Fondazione Arena explicitly separates the Teatro Filarmonico season from Arena amphitheatre events.
    "filarmonico-verona-rolling-opera": ("Verona|Teatro Filarmonico",),
    "filarmonico-verona-opera-2027": ("Verona|Teatro Filarmonico",),
    "pisa-verdi-opera-2026-27": ("Pisa|Teatro Verdi",),
    "pisa-future-calendar": ("Pisa|Teatro Verdi",),
    "salerno-verdi-opera-2026": ("Salerno|Teatro Municipale Giuseppe Verdi",),
    "festival-verdi-rolling": ("Parma|Teatro Regio di Parma", "Busseto|Teatro Giuseppe Verdi"),
    # The 2027 MOF season is explicitly hosted at the Arena Sferisterio on the official festival site.
    # This is a diagnostic source association, not a claim of season completeness.
    "macerata-festival-rolling": ("Macerata|Arena Sferisterio",),
    "macerata-festival-2027": ("Macerata|Arena Sferisterio",),
    "scala-season-2026-27": ("Milano|Teatro alla Scala",),
    "verdi-trieste-season-2026-27": ("Trieste|Teatro Lirico Giuseppe Verdi",),
    "lirico-cagliari-opera-2027": ("Cagliari|Teatro Lirico di Cagliari",),
    # Both Sangiorgi productions already have official Bellini event URLs
    # and individual recite in the immutable published catalog.
    "bellini-catania-opera-2026-27": ("Catania|Teatro Massimo Bellini",
                                      "Catania|Teatro Sangiorgi"),
    "modena-teatro-opera-2026-27": ("Modena|Teatro Comunale Pavarotti-Freni",),
    "puccini-torre-del-lago-2027": ("Torre del Lago Puccini|Gran Teatro Giacomo Puccini",),
    "spoleto-tls-lirica-2026": ("Spoleto|Teatro Nuovo Gian Carlo Menotti",),
    "chieti-marrucino-lirica-2026": ("Chieti|Teatro Marrucino",),
    "modena-opera-2026-27": ("Modena|Teatro Comunale Pavarotti-Freni",),
    "giglio-lucca-opera-2026-27": ("Lucca|Teatro del Giglio Giacomo Puccini",),
    "piacenza-opera-2026-27": ("Piacenza|Teatro Municipale",),
    # Veleno is officially published at Teatro Ariosto by I Teatri.
    "reggio-valli-opera-2026-27": ("Reggio Emilia|Teatro Valli",
                                   "Reggio Emilia|Teatro Ariosto"),
    "jesi-trittico-opera-2026": ("Jesi|Teatro Giovan Battista Pergolesi",),
    "jesi-don-pasquale-opera-2026": ("Jesi|Teatro Giovan Battista Pergolesi",),
    "jesi-esecuzione-opera-2026": ("Jesi|Teatro Giovan Battista Pergolesi",),
    "jesi-nabucco-opera-2026": ("Jesi|Teatro Giovan Battista Pergolesi",),
    "ancona-elisir-opera-2026": ("Ancona|Teatro delle Muse",),
    "ancona-cavalleria-program-2026": ("Ancona|Teatro delle Muse",),
    "goldoni-livorno-dido-2026-27": ("Livorno|Teatro Goldoni",),
    "goldoni-livorno-rolling-lirica": ("Livorno|Teatro Goldoni",
                                      "Livorno|Piazza Goldoni"),
    "goldoni-livorno-otello-2026-27": ("Livorno|Teatro Goldoni",),
    "goldoni-livorno-elisir-2026-27": ("Livorno|Teatro Goldoni",),
    "ferrara-macbeth-opera-2026-27": ("Ferrara|Teatro Comunale Claudio Abbado",),
    "ferrara-barbiere-opera-2026-27": ("Ferrara|Teatro Comunale Claudio Abbado",),
    "ferrara-dido-opera-2026-27": ("Ferrara|Teatro Comunale Claudio Abbado",),
    "ferrara-clemenza-opera-2026-27": ("Ferrara|Teatro Comunale Claudio Abbado",),
    "ferrara-boccanegra-opera-2026-27": ("Ferrara|Teatro Comunale Claudio Abbado",),
    "arena-festival-2027": ("Verona|Arena di Verona",),
    "fenice-opera-2026-27": ("Venezia|Teatro La Fenice", "Venezia|Teatro Malibran"),
    "parma-opera-2027": ("Parma|Teatro Regio di Parma",),
    "massimo-season-2026-27": ("Palermo|Teatro Massimo",),
    "carlo-felice-season-2026-27": ("Genova|Teatro Carlo Felice",),
    "donizetti-opera-2026": ("Bergamo|Teatro Donizetti",
                             "Bergamo|Teatro Sociale"),
    "teatro-grande-opera-2026": ("Brescia|Teatro Grande",),
    "maggio-fiorentino-calendar-2027": ("Firenze|Teatro del Maggio Musicale Fiorentino", "Firenze|Teatro Goldoni"),
    # Official production pages already identify both distinct venues:
    # Code: Unknown at Teatro Nazionale; La Cenerentola at Teatro Valle.
    "opera-roma-season-2026-27": ("Roma|Teatro dell'Opera di Roma",
                                   "Roma|Teatro Nazionale",
                                   "Roma|Teatro Valle Franca Valeri"),
    "petruzzelli-opera-2026": ("Bari|Teatro Petruzzelli",),
    "petruzzelli-opera-2027": ("Bari|Teatro Petruzzelli",),
    "bologna-comunale-opera-2026": ("Bologna|Teatro Comunale di Bologna", "Bologna|Teatro Auditorium Manzoni"),
    "bologna-comunale-opera-2027": ("Bologna|Teatro Comunale di Bologna", "Bologna|Teatro Auditorium Manzoni"),
}
DAILY_VENUES = {
    "regio": ("Torino|Teatro Regio di Torino",),
    "operalombardia": ("Como|Teatro Sociale", "Pavia|Teatro Fraschini",
                       "Brescia|Teatro Grande", "Cremona|Teatro Ponchielli"),
    "operalombardia_calendar": ("Como|Teatro Sociale", "Pavia|Teatro Fraschini",
                                "Brescia|Teatro Grande", "Cremona|Teatro Ponchielli"),
    "fraschini": ("Pavia|Teatro Fraschini",),
    "scala": ("Milano|Teatro alla Scala",),
    "arena": ("Verona|Arena di Verona",),
}


def san_carlo_verified_fallback(secondary: dict, canonical: dict,
                                candidates: dict, public: dict) -> dict | None:
    """Credit the already-published two-source pipeline, never a blocked official fetch.

    Require consistent checkpoint evidence AND actual canonical publication.
    An unverified secondary page, or a successful isolated probe without
    published recite, is insufficient to mark a venue operational.
    """
    if (secondary.get("schema_version") != 1
        or secondary.get("source_key") != "napoli-san-carlo-rolling-opera"
        or secondary.get("outcome") != "acquired_pending_primary_corroboration"
        or secondary.get("production_count") != 10
        or secondary.get("performance_count") != 58
        or canonical.get("schema_version") != 1
        or not isinstance(canonical.get("productions"), list)
        or not isinstance(candidates.get("candidates"), list)
        or not isinstance(public.get("performances"), list)):
        return None
    checked_at = secondary.get("checked_at")
    completed_at = canonical.get("checked_at")
    try:
        acquisition = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        if (acquisition.tzinfo is None or completed.tzinfo is None
            or completed < acquisition):
            return None
    except (AttributeError, ValueError, TypeError):
        return None
    processed = canonical["productions"]
    if (len(processed) != 10
        or len({p.get("title") for p in processed}) != 10
        or not all(p.get("status") == "already_processed" for p in processed)):
        return None
    local = [c for c in candidates["candidates"]
             if c.get("source_key") == "napoli-san-carlo-rolling-opera"]
    if (len(local) != 10
        or not all(c.get("status") == "already_catalogued" for c in local)
        or len({c.get("official_url") for c in local}) != 10):
        return None
    recite = [p for p in public["performances"]
              if p.get("venue") == "Teatro di San Carlo"
              and p.get("municipality") == "Napoli"]
    if (len(recite) != 58
        or len({(p.get("title"), p.get("local_date")) for p in recite}) != 58
        or len({p.get("title") for p in recite}) != 10
        or not all(p.get("time_known") is True for p in recite)):
        return None
    return {"source_key": "napoli-san-carlo-secondary-corroborated",
            "type": "secondary_cross_source_canonical",
            "configured": True, "last_status": "published_verified",
            "recent_success": True, "failure_reason": None,
            "last_attempt_at": completed_at,
            "published_productions": 10, "published_performances": 58,
            "direct_official_scan_verified": False}



def classify_index_scan(check: dict) -> str:
    """Distinguish technical failures from future programmes not yet verified."""
    if check.get("status") == "success" and check.get("current_scan_verified") is True:
        return "verified_success"
    if check.get("status") not in ("unavailable_or_invalid", "success"):
        return "not_checked"
    diagnostic = check.get("diagnostic")
    if diagnostic == "future_official_programme_unverified":
        return "future_programme_not_verified"
    if diagnostic in ("official_anti_bot_challenge", "access_denied_or_robots_disallowed"):
        return "access_blocked"
    if diagnostic in ("official_html_unavailable_or_invalid",
                      "official_robots_unavailable_or_invalid"):
        return "fetch_unavailable"
    if diagnostic == "rovigo_fallback_content_unverified":
        return "source_content_not_verified"
    return "parser_or_source_validation_failed"


def scan_attention(index: dict, index_health: dict, *, candidates: dict | None = None) -> dict:
    """Explain scan failures without disguising fallback coverage as a success.

    A missing future programme is not proof the season has been cancelled
    or published; alternate healthy feeds do not repair broken source URLs.
    """
    rows = {x["key"]: x for x in index_health.get("sources", [])}
    if len(rows) != len(index_health.get("sources", [])):
        raise ValueError("duplicate indexed scan health key")
    # A successful crawl reports links, not a confirmed count of operas.
    # Candidate states are independent and can remain in review even when
    # the index scan itself succeeded.
    candidate_counts = {}
    if candidates is not None:
        if candidates.get("schema_version") != 1 or not isinstance(candidates.get("candidates"), list):
            raise ValueError("invalid source candidate registry")
        for entry in candidates["candidates"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("source_key"), str):
                raise ValueError("invalid candidate entry")
            state = entry.get("status")
            if state not in ("needs_review", "already_catalogued",
                             "excluded_nonopera", "not_in_official_season"):
                raise ValueError("unknown candidate status")
            candidate_counts.setdefault(entry["source_key"], Counter())[state] += 1
    seen = set()
    items = []
    for source in index["sources"]:
        key = source["key"]
        if key in seen:
            raise ValueError("duplicate configured index key")
        seen.add(key)
        record = rows.get(key, {})
        category = classify_index_scan(record)
        venues = set(INDEX_VENUES.get(key, ()))
        alternatives = sorted(
            other["key"] for other in index["sources"]
            if other["key"] != key and
            set(INDEX_VENUES.get(other["key"], ())) & venues and
            classify_index_scan(rows.get(other["key"], {})) == "verified_success"
        ) if venues else []
        # A healthy index for the same venue does not prove that any opera
        # has passed canonical reconciliation. Track it separately.
        catalogued_alternatives = [
            other_key for other_key in alternatives
            if candidate_counts.get(other_key, {}).get("already_catalogued", 0) > 0
        ] if candidates is not None else []
        items.append({
            "source_key": key,
            "scan_classification": category,
            "status": record.get("status", "not_checked"),
            "diagnostic": record.get("diagnostic"),
            "reason": record.get("reason"),
            "last_attempt_at": record.get("last_attempt_at"),
            "last_success_at": record.get("last_success_at"),
            "other_successful_official_sources": alternatives,
            "has_healthy_alternative": bool(alternatives),
            "other_successful_catalogued_sources": catalogued_alternatives,
            "has_catalogued_alternative": bool(catalogued_alternatives),
            # This is candidate-registry evidence, not a deployed-site proof.
            "catalogued_alternative_evidence": "candidate_registry_only",
            "candidate_yield": (
                {"total": sum(candidate_counts.get(key, {}).values()),
                 "already_catalogued": candidate_counts.get(key, {}).get("already_catalogued", 0),
                 "needs_review": candidate_counts.get(key, {}).get("needs_review", 0),
                 "excluded_nonopera": candidate_counts.get(key, {}).get("excluded_nonopera", 0),
                 "not_in_official_season": candidate_counts.get(key, {}).get("not_in_official_season", 0)}
                if candidates is not None else None),
            "requires_technical_attention": category in (
                "access_blocked", "fetch_unavailable", "parser_or_source_validation_failed",
                "source_content_not_verified"),
        })
    counts = Counter(r["scan_classification"] for r in items)
    return {
        "total": len(items), "classifications": dict(sorted(counts.items())),
        "technical_attention": sum(r["requires_technical_attention"] for r in items),
        "future_programmes_not_verified": counts["future_programme_not_verified"],
        "sources_with_unresolved_candidates": sum(
            (r["candidate_yield"] or {}).get("needs_review", 0) > 0 for r in items),
        "sources": items,
    }


def build(directory: dict, daily: dict, daily_health: dict, index: dict,
          index_health: dict, *, san_carlo_fallback: dict | None = None,
          candidates: dict | None = None) -> dict:
    venues = directory["venues"]
    profiles = {v["city"] + "|" + v["name"]: v for v in venues}
    if len(profiles) != len(venues):
        raise ValueError("ambiguous duplicate venue profiles")
    for source, targets in INDEX_VENUES.items():
        for key in targets:
            if key not in profiles:
                raise ValueError(f"unknown mapped venue {source}: {key}")
    for adapter, targets in DAILY_VENUES.items():
        for key in targets:
            if key not in profiles:
                raise ValueError(f"unknown mapped adapter venue {adapter}: {key}")
    indexed = {x["key"]: x for x in index["sources"]}
    index_checks = {x["key"]: x for x in index_health.get("sources", [])}
    direct_checks = {x["key"]: x for x in daily_health.get("sources", [])}
    assignments = {key: [] for key in profiles}
    for entry in index["sources"]:
        for key in INDEX_VENUES.get(entry["key"], ()):
            check = index_checks.get(entry["key"], {})
            assignments[key].append({
                "source_key": entry["key"], "type": "season_index",
                "configured": entry.get("access_status") == "approved",
                "last_status": check.get("status", "not_checked"),
                "recent_success": bool(check.get("current_scan_verified")
                                       and check.get("status") == "success"),
                "failure_reason": (check.get("diagnostic") or check.get("reason")
                                   if check.get("status") not in (None, "success") else None),
                "last_attempt_at": check.get("last_attempt_at"),
            })
    for entry in daily["sources"]:
        for key in DAILY_VENUES.get(entry["adapter"], ()):
            check = direct_checks.get(entry["key"], {})
            assignments[key].append({
                "source_key": entry["key"], "type": "detail_or_calendar",
                "configured": entry.get("access_status") == "approved",
                "last_status": check.get("outcome", "not_checked"),
                "recent_success": check.get("outcome") == "success",
                "failure_reason": (check.get("reason") or check.get("error")
                                   if check.get("outcome") not in (None, "success") else None),
                "last_attempt_at": check.get("last_attempt_at"),
            })
    if san_carlo_fallback:
        assignments["Napoli|Teatro di San Carlo"].append(san_carlo_fallback)
    rows = []
    for key, venue in profiles.items():
        sources = assignments[key]
        successful = [s for s in sources if s["configured"] and s["recent_success"]]
        approved = [s for s in sources if s["configured"]]
        if successful:
            status = "operational"
        elif approved:
            status = "configured_not_operational"
        else:
            status = "not_automated"
        rows.append({
            "venue_id": venue["id"],
            "venue": venue["name"],
            "city": venue["city"],
            "region": venue["region"],
            "status": status,
            "configured_connectors": len(approved),
            "recent_successful_connectors": len(successful),
            "source_attention": ("none" if successful else
                                 "not_checked" if approved and all(
                                     s["last_status"] == "not_checked" for s in approved) else
                                 "scan_failed" if approved else "not_configured"),
            "sources": sources,
        })
    rows.sort(key=lambda v: (v["region"], v["city"], v["venue"]))
    counts = Counter(row["status"] for row in rows)
    return {
        "schema_version": 1,
        "reviewed_on": directory.get("reviewed_on"),
        "scope": "structured_venue_directory",
        "definition": "Operational means a successful approved scan, or a source-specific corroborated acquisition whose exact performances are already published and verified; this does not mean a blocked official site became accessible or an exhaustive future season.",
        "total_venues": len(rows),
        "operational": counts["operational"],
        "configured_not_operational": counts["configured_not_operational"],
        "not_automated": counts["not_automated"],
        "automation_remaining": counts["configured_not_operational"] + counts["not_automated"],
        "index_scan_attention": scan_attention(index, index_health, candidates=candidates),
        "venues": rows,
    }


def publish(check: bool = False) -> dict:
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    fallback = None
    if all(p.exists() for p in (SAN_CARLO_SECONDARY, SAN_CARLO_CANONICAL,
                                SAN_CARLO_CANDIDATES, SAN_CARLO_PUBLIC)):
        fallback = san_carlo_verified_fallback(
            read(SAN_CARLO_SECONDARY), read(SAN_CARLO_CANONICAL),
            read(SAN_CARLO_CANDIDATES), read(SAN_CARLO_PUBLIC))
    report = build(read(DIRECTORY), read(DAILY), read(DAILY_HEALTH),
                   read(INDEX), read(INDEX_HEALTH),
                   san_carlo_fallback=fallback,
                   candidates=read(CANDIDATE_REGISTRY) if CANDIDATE_REGISTRY.exists() else None)
    serialized = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")) + "\n").encode("utf-8")
    if check:
        if not OUT.exists() or OUT.read_bytes() != serialized:
            raise ValueError("source automation feed is out of sync")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(serialized)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = publish(check=args.check)
    print(json.dumps({k: result[k] for k in (
        "total_venues", "operational", "configured_not_operational",
        "not_automated", "automation_remaining")}))


if __name__ == "__main__":
    main()
