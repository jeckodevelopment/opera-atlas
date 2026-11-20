"""Conservative, approval-gated daily source ingestion.

A stateless GitHub Actions runner reconstructs the input from two Git-tracked
JSON files: the curated observations and immutable-ID registry. No SQLite file
needs to be stored on the web server or in Git history.

Only already-curated production pages may be scanned; unknown venues, ambiguous
reschedules, changed times and unreachable pages are never auto-published.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from opera_atlas.controlled_fetch import (
    AccessDenied, FetchUnavailable, fetch_official_html,
)
from opera_atlas.db import connect, migrate
from opera_atlas.operalombardia import parse_dates_only
from opera_atlas.operalombardia_calendar import parse_calendar
from opera_atlas.fraschini_parser import parse_fraschini_detail
from opera_atlas.regio_parser import parse_regio_detail
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY, assemble

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "daily-source-config.json"
HEALTH = ROOT / "data" / "catalog-source-health.json"
VALID_ADAPTERS = {"regio", "operalombardia", "fraschini", "operalombardia_calendar"}


def validate_source_config(document: dict) -> list[dict]:
    if document.get("schema_version") != 1 or not isinstance(document.get("sources"), list):
        raise ValueError("unsupported source schedule")
    seen = set()
    sources = []
    required = {
        "key", "adapter", "url", "official_url", "title",
        "composer", "access_status", "approval_evidence",
    }
    for item in document["sources"]:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("invalid scheduled source entry")
        if item["key"] in seen or not item["key"]:
            raise ValueError("duplicate scheduled source key")
        seen.add(item["key"])
        if item["adapter"] not in VALID_ADAPTERS:
            raise ValueError("unsupported calendar adapter")
        if item["access_status"] not in ("pending", "approved", "blocked"):
            raise ValueError("unknown approval status")
        for field in ("url", "official_url", "title", "composer"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError("invalid " + field)
        url, official = urlsplit(item["url"]), urlsplit(item["official_url"])
        if (url.scheme != "https" or official.scheme != "https"
            or not url.hostname or url.hostname != official.hostname
            or url.username or url.password or url.port is not None
            or url.query or url.fragment):
            raise ValueError("URL not exact official HTTPS host")
        if item["adapter"] == "regio" and url.hostname not in (
            "www.teatroregio.torino.it", "teatroregio.torino.it"
        ):
            raise ValueError("Regio adapter host mismatch")
        if item["adapter"] == "fraschini" and url.hostname != "www.teatrofraschini.it":
            raise ValueError("Fraschini adapter host mismatch")
        if item["adapter"] == "operalombardia_calendar" and (
            url.hostname != "www.operalombardia.it" or url.path != "/calendario/"
        ):
            raise ValueError("OperaLombardia index host/path mismatch")
        if item["adapter"] == "operalombardia" and url.hostname != "www.operalombardia.it":
            raise ValueError("OperaLombardia adapter host mismatch")
        if item["access_status"] == "approved" and (
            not isinstance(item["approval_evidence"], str)
            or len(item["approval_evidence"].strip()) < 20
        ):
            raise ValueError("approved source must document robots/terms review")
        sources.append(item)
    if len(sources) > 20:
        raise ValueError("too many scans per daily run")
    return sources


def _find_production(facts: dict, item: dict, venue: str, city: str) -> dict | None:
    matches = [
        p for p in facts["productions"]
        if p["source_url"] == item["url"]
        and p["title"].casefold() == item["title"].casefold()
        and p["composer"].casefold() == item["composer"].casefold()
        and p["venue"].casefold() == venue.casefold()
        and p["municipality"].casefold() == city.casefold()
    ]
    if len(matches) > 1:
        raise ValueError("ambiguous curated venue/production")
    return matches[0] if matches else None


def _parse(item: dict, html: str) -> list[tuple[str, str, str, str | None]]:
    if item["adapter"] == "operalombardia_calendar":
        return parse_calendar(html)
    if item["adapter"] == "regio":
        parsed = parse_regio_detail(
            html, source_url=item["url"], expected_title=item["title"],
            expected_composer=item["composer"],
        )
        return [("Teatro Regio", "Torino",
                 fact.starts_at.date().isoformat(),
                 fact.starts_at.strftime("%H:%M")) for fact in parsed]
    if item["adapter"] == "fraschini":
        rows = parse_fraschini_detail(html, url=item["url"], title=item["title"], composer=item["composer"])
        return [("Teatro Fraschini", "Pavia", day, hour) for day, hour in rows]
    parsed = parse_dates_only(html, url=item["url"], title=item["title"])
    return [(fact.venue_name,fact.city,fact.local_date,None) for fact in parsed]


def _next_replica_id(registry: dict) -> int:
    ids = [
        int(obj["id"][5:]) for obj in registry["performances"].values()
        if obj["id"].startswith("oa-r-") and obj["id"][5:].isdigit()
    ]
    return max(ids, default=0) + 1


def scan_approved(
    facts: dict, registry: dict, scheduled: list[dict], *,
    network_enabled: bool, fetcher=fetch_official_html,
    today: date | None = None,
) -> tuple[dict, dict, list[dict], int]:
    """Return updated copies; errors and anomalies preserve previous facts."""
    current = today or date.today()
    updated_facts = copy.deepcopy(facts)
    updated_registry = copy.deepcopy(registry)
    health = []
    additions = 0
    db = connect()
    try:
        migrate(db)
        for item in scheduled:
            if item["access_status"] != "approved":
                health.append({"key":item["key"],"outcome":item["access_status"],
                               "added":0,"observed":0})
                continue
            db.execute(
                "INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                (item["official_url"],),
            )
            source_id = db.execute(
                "SELECT id FROM sources WHERE official_url=?", (item["official_url"],)
            ).fetchone()["id"]
            try:
                if not network_enabled:
                    raise AccessDenied("network access requires --allow-network")
                page = fetcher(
                    db, source_id=source_id, url=item["url"], network_enabled=True
                )
                parsed = _parse(item, page.html)
                if not parsed:
                    raise ValueError("zero recite from complete production page")
            except (AccessDenied, FetchUnavailable, ValueError, sqlite3.Error) as exc:
                health.append({"key":item["key"],"outcome":"unavailable_or_invalid",
                               "added":0,"observed":0,"reason":type(exc).__name__})
                continue
            # Build a complete source-scoped proposal before altering any facts.
            # A changed time, unknown venue, duplicate date or suspected move
            # must not cause unrelated partial additions from the same page.
            observed = {}
            anomalies = []
            mapped = {}
            for record in parsed:
                if item["adapter"] == "operalombardia_calendar":
                    title, venue, city, day, hour = record
                    matches = [
                        p for p in updated_facts["productions"]
                        if p["title"].casefold() == title.casefold()
                        and p["venue"].casefold() == venue.casefold()
                        and p["municipality"].casefold() == city.casefold()
                    ]
                    if len(matches) != 1:
                        anomalies.append({"kind":"unknown_or_ambiguous_staging",
                                          "title":title,"venue":venue,"city":city})
                        continue
                    product = matches[0]
                else:
                    venue, city, day, hour = record
                    product = _find_production(updated_facts, item, venue, city)
                if product is None:
                    anomalies.append({"kind":"unknown_staging","venue":venue,"city":city})
                    continue
                key = product["key"]
                if (key,day) in observed:
                    anomalies.append({"kind":"duplicate_or_conflicting_date",
                                      "production":key,"date":day})
                    continue
                observed[(key,day)] = hour
                mapped[key] = product

            candidate_dates = {}
            for prod_key, product in mapped.items():
                actual = {day:hour for (key,day),hour in observed.items() if key==prod_key}
                before = dict(product["dates"])
                missing = {
                    day for day in before if day not in actual and date.fromisoformat(day)>=current
                }
                added = set(actual)-set(before)
                if missing and added:
                    anomalies.append({"kind":"possible_reschedule",
                                      "production":prod_key,
                                      "missing":sorted(missing),"appeared":sorted(added)})
                elif missing:
                    anomalies.append({"kind":"missing_from_source",
                                      "production":prod_key,"dates":sorted(missing)})
                for day in sorted(set(before) & set(actual)):
                    if before[day] != actual[day]:
                        anomalies.append({"kind":"time_changed",
                                          "production":prod_key,"date":day})
                for day in sorted(added):
                    if (item["adapter"] == "operalombardia_calendar"
                        and product["source_url"] != item["url"]):
                        anomalies.append({"kind":"additional_secondary_source_date",
                                          "production":prod_key,"date":day})
                    if prod_key + "|" + day in updated_registry["performances"]:
                        anomalies.append({"kind":"registry_collision",
                                          "production":prod_key,"date":day})
                candidate_dates[prod_key] = [(day,actual[day]) for day in sorted(added)]

            # In particular, a page with both a valid new date and a
            # conflicting record publishes nothing until an operator reviews.
            new_for_source = 0
            if not anomalies:
                for prod_key, entries in candidate_dates.items():
                    product = mapped[prod_key]
                    for day,hour in entries:
                        item_id = _next_replica_id(updated_registry)
                        updated_registry["performances"][prod_key+"|"+day] = {
                            "id":f"oa-r-{item_id:06d}",
                            "staging_id":updated_registry["stagings"][prod_key]["id"],
                            "original_date":day,
                            "source_url":item["url"],
                        }
                        product["dates"].append([day,hour])
                        new_for_source += 1
                        additions += 1
                    product["dates"].sort(key=lambda v:v[0])
            health.append({"key":item["key"],"outcome":"review_required" if anomalies else "success",
                           "added":new_for_source,"observed":len(parsed),
                           "anomalies":anomalies})
        if additions:
            updated_facts["reviewed_on"] = current.isoformat()
        # Validate the entire canonical graph before allowing any write.
        assemble(updated_facts,updated_registry)
        return updated_facts,updated_registry,health,additions
    finally:
        db.close()


def _write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",encoding="utf-8",dir=path.parent,delete=False
    ) as writer:
        json.dump(data,writer,ensure_ascii=False,indent=2)
        writer.write("\n")
        temp=Path(writer.name)
    os.replace(temp,path)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    args=parser.parse_args()
    scheduled=validate_source_config(json.loads(CONFIG.read_text(encoding="utf-8")))
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    next_facts,next_registry,health,added=scan_approved(
        facts,registry,scheduled,network_enabled=args.allow_network
    )
    if added:
        _write_atomic(MANIFEST,next_facts)
        _write_atomic(REGISTRY,next_registry)
    # No daily commit if no approved source: pending entries carry no new info.
    if any(item["access_status"]=="approved" for item in scheduled):
        _write_atomic(HEALTH,{
            "schema_version":1,
            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sources":health,
        })
    print(json.dumps({"approved":sum(x["access_status"]=="approved" for x in scheduled),
                      "added":added,"source_outcomes":health},ensure_ascii=False))


if __name__=="__main__":
    main()
