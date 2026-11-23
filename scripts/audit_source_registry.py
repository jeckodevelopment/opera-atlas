"""Read-only F1 audit of configured index sources and canonical physical venues.

Never infer a venue from a city, source URL, title, or festival organiser.
This tool performs no network calls and never rewrites the catalog.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from scripts.source_automation import INDEX_VENUES, DAILY_VENUES, ROOT


def audit(directory: dict, indexes: dict, daily: dict, health: dict,
          *, index_venues: dict | None = None,
          daily_venues: dict | None = None) -> dict:
    index_venues = INDEX_VENUES if index_venues is None else index_venues
    daily_venues = DAILY_VENUES if daily_venues is None else daily_venues
    venues = directory["venues"]
    configured = indexes["sources"]
    details = daily["sources"]
    checks = health["sources"]
    profiles = [v["city"] + "|" + v["name"] for v in venues]
    ids = [v["id"] for v in venues]
    index_keys = [s["key"] for s in configured]
    detail_keys = [s["key"] for s in details]
    health_keys = [s["key"] for s in checks]

    def duplicates(items):
        return sorted(k for k, n in Counter(items).items() if n > 1)

    index_set = set(index_keys)
    venue_set = set(profiles)
    detail_adapters = {s["adapter"] for s in details}
    index_missing_mapping = sorted(index_set - set(index_venues))
    index_stale_mapping = sorted(set(index_venues) - index_set)
    index_unknown_venues = sorted(
        (key, venue)
        for key, targets in index_venues.items()
        if key in index_set
        for venue in targets
        if venue not in venue_set
    )
    daily_unknown_adapters = sorted(detail_adapters - set(daily_venues))
    daily_unknown_venues = sorted(
        (adapter, venue)
        for adapter, targets in daily_venues.items()
        if adapter in detail_adapters
        for venue in targets
        if venue not in venue_set
    )
    invalid_urls = sorted(
        (s["key"], field)
        for s in configured
        for field in ("url", "official_url")
        if not _http_url(s.get(field))
    )
    health_missing = sorted(index_set - set(health_keys))
    health_stale = sorted(set(health_keys) - index_set)
    return {
        "scope": "read_only_source_to_venue_mapping",
        "venues": len(venues),
        "index_sources": len(configured),
        "detail_sources": len(details),
        "regions": len({v["region"] for v in venues}),
        "duplicate_venue_ids": duplicates(ids),
        "duplicate_venue_profiles": duplicates(profiles),
        "duplicate_index_keys": duplicates(index_keys),
        "duplicate_detail_keys": duplicates(detail_keys),
        "duplicate_health_keys": duplicates(health_keys),
        "index_missing_explicit_mapping": index_missing_mapping,
        "index_stale_mapping": index_stale_mapping,
        "index_unknown_venue_targets": index_unknown_venues,
        "daily_unmapped_adapters": daily_unknown_adapters,
        "daily_unknown_venue_targets": daily_unknown_venues,
        "index_invalid_urls": invalid_urls,
        "index_missing_health": health_missing,
        "index_stale_health": health_stale,
        "checked_at": health.get("checked_at"),
        "note": (
            "Unmapped source does not imply an inoperative venue; "
            "no association is inferred or changed."
        ),
    }


def _http_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return parsed.scheme in ("https", "http") and bool(parsed.hostname)


def main() -> None:
    def load(relative: str) -> dict:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))
    result = audit(
        load("data/venue-directory.json"),
        load("data/season-index-config.json"),
        load("data/daily-source-config.json"),
        load("data/season-index-health.json"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
