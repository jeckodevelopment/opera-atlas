"""Reconcile the venue directory against configured and recently checked official connectors.

Statuses are evidence-based: an 'acquired' venue page is not proof of
automation. A season index success is not proof of complete recite coverage.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/venue-directory.json"
DAILY = ROOT / "data/daily-source-config.json"
DAILY_HEALTH = ROOT / "data/catalog-source-health.json"
INDEX = ROOT / "data/season-index-config.json"
INDEX_HEALTH = ROOT / "data/season-index-health.json"
OUT = ROOT / "public/catalog/source-automation.json"

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
    "pesaro-rof-2026": ("Pesaro|Teatro Gioachino Rossini",),
    "martina-valle-itria-2026": ("Martina Franca|Palazzo Ducale di Martina Franca",),
    "trapani-luglio-musicale-2026": ("Trapani|Teatro Giuseppe Di Stefano",),
    "haydn-rolling-opera": ("Bolzano|Teatro Comunale di Bolzano", "Trento|Teatro Sociale"),
    "asti-alfieri-rolling-opera": ("Asti|Teatro Alfieri",),
    "savona-giocosa-rolling-opera": ("Savona|Teatro Gabriello Chiabrera",),
    "sassari-de-carolis-opera-2026": ("Sassari|Teatro Comunale di Sassari",),
    "messina-vittorio-opera-2026-27": ("Messina|Teatro Vittorio Emanuele",),
    "lecce-apollo-pinocchio-2026": ("Lecce|Teatro Apollo",),
    "lecce-politeama-opera-2026": ("Lecce|Teatro Politeama Greco",),
    "lecce-provincia-politeama-2026": ("Lecce|Teatro Politeama Greco",),
    "rovigo-regione-programma-2026-27": ("Rovigo|Teatro Sociale",),
    "rovigo-sociale-opera-2026-27": ("Rovigo|Teatro Sociale",),
    "padova-verdi-opera-2026": ("Padova|Teatro Verdi",),
    "treviso-del-monaco-opera-2026-27": ("Treviso|Teatro Comunale Mario del Monaco",),
    "ravenna-alighieri-cherubini-2027": ("Ravenna|Teatro Dante Alighieri",),
    "coccia-novara-opera-2027": ("Novara|Teatro Coccia",),
    "filarmonico-verona-opera-2027": ("Verona|Teatro Filarmonico",),
    "pisa-verdi-opera-2026-27": ("Pisa|Teatro Verdi",),
    "salerno-verdi-opera-2026": ("Salerno|Teatro Municipale Giuseppe Verdi",),
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


def build(directory: dict, daily: dict, daily_health: dict, index: dict,
          index_health: dict) -> dict:
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
        "definition": "Operational means at least one explicitly mapped approved source with a successful latest scan; does not imply an exhaustive season.",
        "total_venues": len(rows),
        "operational": counts["operational"],
        "configured_not_operational": counts["configured_not_operational"],
        "not_automated": counts["not_automated"],
        "automation_remaining": counts["configured_not_operational"] + counts["not_automated"],
        "venues": rows,
    }


def publish(check: bool = False) -> dict:
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    report = build(read(DIRECTORY), read(DAILY), read(DAILY_HEALTH),
                   read(INDEX), read(INDEX_HEALTH))
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
