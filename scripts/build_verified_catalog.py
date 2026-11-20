"""Build initial editorial snapshot from individually verified official calendar facts.

This is a one-time curated seed, not a replacement for the monitored import
pipeline. Never infer missing hours; refuse arbitrary or unsafe URLs.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "verified-launch-catalog.json"
OUTPUT = ROOT / "site" / "performances.json"
APPROVED_PAGES = {
    "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata",
    "https://www.operalombardia.it/l-italiana-in-algeri/",
}


def build(manifest: dict) -> dict:
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("productions"), list):
        raise ValueError("invalid editorial manifest")
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
            uid = f"curated:{production['key']}:{local_day}"
            if uid in keys:
                raise ValueError("duplicate editorial performance")
            keys.add(uid)
            # The curated Regio dates are all outside Italy's DST period.
            if hour is not None and url != "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata":
                raise ValueError("no verified time for this source")
            if hour is None and url != "https://www.operalombardia.it/l-italiana-in-algeri/":
                raise ValueError("expected exact Regio performance hour")
            events.append({
                "id": uid,
                "starts_at": f"{local_day}T{hour}:00+01:00" if hour else None,
                "local_date": local_day,
                "time_known": hour is not None,
                "time_label": hour or "Orario da confermare",
                "status": "announced",
                "title": production["title"],
                "composer": production["composer"],
                "venue": production["venue"],
                "municipality": production["municipality"],
                "region": production["region"],
                "latitude": None,
                "longitude": None,
                "sources": [url],
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
