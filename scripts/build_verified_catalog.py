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
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/edgar",
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/salome",
    "https://www.operalombardia.it/l-italiana-in-algeri/",
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
    "lombardia-italiana-cremona": {
        "https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-litaliana-algeri",
        "https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-litaliana-algeri-0",
    },
}


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
            valid[product["key"] + "|" + day] = (product, hour)
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


def build(manifest: dict, evidence: dict | None = None) -> dict:
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("productions"), list):
        raise ValueError("invalid editorial manifest")
    if evidence is None:
        evidence = json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
    showtimes = validate_time_evidence(manifest, evidence)
    events = []
    keys = set()
    for production in manifest["productions"]:
        url = production["source_url"]
        if url not in APPROVED_PAGES:
            raise ValueError("non-reviewed source page")
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
            evidence_entry = showtimes.get(production["key"] + "|" + local_day)
            effective_hour = evidence_entry["time"] if evidence_entry else hour
            uid = f"curated:{production['key']}:{local_day}"
            if uid in keys:
                raise ValueError("duplicate editorial performance")
            keys.add(uid)
            # The curated Regio dates are all outside Italy's DST period.
            if hour is not None and not url.startswith("https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/"):
                raise ValueError("no verified time for this source")
            if hour is None and url != "https://www.operalombardia.it/l-italiana-in-algeri/":
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
