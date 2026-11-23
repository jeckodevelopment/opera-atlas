"""Read-only festival coverage audit: preserve edition and venue attribution."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(registry: dict, published: dict, targets: dict) -> dict:
    stagings = {item["id"]: item for item in registry["stagings"].values()}
    live = []
    for entry in published["festivals"]:
        linked = entry.get("staging_ids", [])
        if not entry.get("edition") or not linked:
            raise ValueError("empty festival edition: " + entry["id"])
        missing = sorted(set(linked) - stagings.keys())
        if missing:
            raise ValueError("unknown staging ids: " + ", ".join(missing))
        live.append({"id": entry["id"], "festival_id": entry["festival_id"],
                     "edition": entry["edition"], "linked_stagings": len(set(linked)),
                     "has_photo": bool(entry.get("photo_file") and entry.get("photo_source_url")
                                       and entry.get("photo_credit"))})
    published_ids = {entry["festival_id"] for entry in live}
    gaps = []
    for target in targets["targets"]:
        if target["id"] not in published_ids:
            gaps.append({"id": target["id"], "edition": target["edition"],
                         "city": target["city"], "official_program_url": target["official_program_url"],
                         "status": "edition_requires_verified_staging_linkage",
                         "note": target["note"]})
    return {"published_festivals": len(published_ids),
            "published_editions": len(live),
            "published_entries": live,
            "missing_festival_targets": gaps,
            "missing_count": len(gaps)}


def main() -> None:
    registry = json.loads((ROOT / "data/identity-registry.json").read_text(encoding="utf-8"))
    published = json.loads((ROOT / "public/catalog/v2/festival-index.json").read_text(encoding="utf-8"))
    targets = json.loads((ROOT / "data/festival-coverage-targets.json").read_text(encoding="utf-8"))
    print(json.dumps(audit(registry, published, targets), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
