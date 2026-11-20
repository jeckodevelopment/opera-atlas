"""Honest, machine-readable coverage report for all eight agreed primary sources.

Coverage means how many reviewed facts and source URLs we currently track;
it never means a theatre's complete season is automatically covered.
The report is static JSON, generated on each Opera Atlas catalog refresh.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from scripts.build_verified_catalog import MANIFEST, build
from scripts.daily_ingest import CONFIG, HEALTH, validate_source_config
from scripts.publish_catalog_v2 import ROOT, REGISTRY, assemble, payload

SOURCES = ROOT / "data" / "sources.json"
OUT = ROOT / "public" / "catalog" / "coverage.json"
DOMAINS = {
    "regio-torino": {"teatroregio.torino.it"},
    "opera-lombardia": {"operalombardia.it", "teatrofraschini.it"},
    "rossini-opera-festival": {"rossinioperafestival.it"},
    "teatro-alla-scala": {"teatroallascala.org"},
    "teatro-la-fenice": {"teatrolafenice.it"},
    "fondazione-arena-verona": {"arena.it"},
    "teatro-regio-parma": {"teatroregioparma.it"},
    "teatro-massimo-palermo": {"teatromassimo.it"},
}


def hostname(url: str) -> str:
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("missing official source hostname")
    return host.lower().removeprefix("www.")


def build_coverage(sources: dict, facts: dict, config: dict, health: dict | None) -> dict:
    if sources.get("schema_version") != 1 or len(sources.get("sources", [])) != 8:
        raise ValueError("unexpected primary source registry")
    if set(p["key"] for p in sources["sources"]) != set(DOMAINS):
        raise ValueError("coverage map requires eight known primary sources")
    scheduled = validate_source_config(config)
    checks = {x["key"]: x for x in (health or {}).get("sources", [])}
    records = []
    for item in sources["sources"]:
        key = item["key"]
        official_hosts = DOMAINS[key]
        matching = [
            p for p in facts["productions"]
            if hostname(p["source_url"]) in official_hosts
        ]
        owned_urls = {p["source_url"] for p in matching}
        monitored = [
            s for s in scheduled if hostname(s["official_url"]) in official_hosts
        ]
        live_success = [s for s in monitored
                        if checks.get(s["key"], {}).get("outcome") == "success"]
        index_verified = any(s["adapter"] == "operalombardia_calendar"
                             and s in live_success for s in monitored)
        if index_verified:
            monitor = "calendar_index_verified"
        elif live_success:
            monitor = "detail_pages_verified"
        elif monitored:
            monitor = "configured_not_verified"
        elif matching:
            monitor = "editorial_only"
        else:
            monitor = "not_started"
        record = {
            "source_key":key,
            "name":item["name"],
            "kind":item["kind"],
            "region":item["region"],
            "calendar_url":item["calendar_url"],
            "monitoring":monitor,
            "verified_stagings":len(matching),
            "verified_recite":sum(len(p["dates"]) for p in matching),
            "verified_detail_pages":len(owned_urls),
            "scheduled_pages":len(monitored),
            "last_scan_outcomes":{
                s["key"]:checks.get(s["key"], {}).get("outcome", "not_checked")
                for s in monitored
            },
            "season_complete":False,
        }
        records.append(record)
    return {
        "schema_version":1,
        "reviewed_on":facts["reviewed_on"],
        "last_scan_at":(health or {}).get("checked_at"),
        "coverage_definition":"Only verified cataloged facts; no source marked season-complete without an independent title and date audit.",
        "sources":records,
    }


def publish(check: bool=False) -> dict:
    sources=json.loads(SOURCES.read_text(encoding="utf-8"))
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    health=json.loads(HEALTH.read_text(encoding="utf-8")) if HEALTH.exists() else None
    report=build_coverage(sources,facts,config,health)
    expected=payload(report)
    if check:
        if not OUT.exists() or OUT.read_bytes()!=expected:
            raise ValueError("source coverage feed is out of sync")
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_bytes(expected)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    r=publish(check=args.check)
    print(json.dumps({"sources":len(r["sources"]),
                      "verified_recite":sum(s["verified_recite"] for s in r["sources"]),
                      "not_started":[s["source_key"] for s in r["sources"] if s["monitoring"]=="not_started"]}))

if __name__=="__main__":
    main()
