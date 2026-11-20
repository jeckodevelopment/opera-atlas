"""Canonical public catalog v2: immutable IDs, content-addressed JSON feeds.

No crawling. Operates ONLY on reviewed editorial facts and persistent identity
registry. Content-addressed files are written before the manifest, preserving
the previous valid release if a generation fails. No server database needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from scripts.build_verified_catalog import MANIFEST, build as legacy_build

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "identity-registry.json"
PUBLIC = ROOT / "public" / "catalog" / "v2"
CHANNELS = ("works", "venues", "stagings", "performances")


def slugify(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("cannot slugify empty name")
    value = unicodedata.normalize("NFKD", text.strip().casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"^l['’]", "", value)  # L’italiana -> italiana
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        raise ValueError("unrepresentable public slug")
    return value


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def assemble(facts: dict, registry: dict) -> dict:
    legacy = legacy_build(facts)
    if registry.get("schema_version") != 1:
        raise ValueError("unknown identity registry")
    all_ids = []
    for channel in ("works", "venues", "stagings", "performances"):
        all_ids += [item["id"] for item in registry[channel].values()]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("catalog IDs must be unique across entities")

    works, venues, stagings, performances = {}, {}, {}, []
    used_keys = {channel: set() for channel in CHANNELS}
    route_keys = set()
    for product in facts["productions"]:
        wk = normalized(product["title"]) + "|" + normalized(product["composer"])
        vk = product["municipality"] + "|" + product["venue"]
        sk = product["key"]
        for channel, key in (("works", wk), ("venues", vk), ("stagings", sk)):
            if key not in registry[channel]:
                raise ValueError("new " + channel + " require a committed permanent ID: " + key)
            used_keys[channel].add(key)
        work = registry["works"][wk]
        venue = registry["venues"][vk]
        staging = registry["stagings"][sk]
        if (work["slug"] != slugify(product["title"])
                or venue["slug"] != slugify(product["venue"])
                or venue["city_slug"] != slugify(product["municipality"])
                or staging["work_id"] != work["id"]
                or staging["venue_id"] != venue["id"]):
            raise ValueError("identity and public route mapping require human review")
        works[work["id"]] = dict(work)
        venues[venue["id"]] = dict(venue)
        route = venue["city_slug"] + "/" + venue["slug"] + "/" + work["slug"]
        if route in route_keys:
            # A new staging in the same theatre needs a season-specific suffix.
            raise ValueError("ambiguous public staging URL: " + route)
        route_keys.add(route)
        staging_record = dict(staging)
        staging_record["url"] = "/" + route + "/"
        stagings[staging["id"]] = staging_record
        for day, time in product["dates"]:
            rk = sk + "|" + day
            if rk not in registry["performances"]:
                raise ValueError("new recita requires a permanent registry identity: " + rk)
            used_keys["performances"].add(rk)
            item = dict(registry["performances"][rk])
            if item["staging_id"] != staging["id"] or item["source_url"] != product["source_url"]:
                raise ValueError("recita identity or provenance changed unexpectedly")
            item.update({
                "legacy_id": f"curated:{sk}:{day}",
                "local_date": day,
                "starts_at": f"{day}T{time}:00+01:00" if time else None,
                "time_known": time is not None,
                "status": "announced",
            })
            performances.append(item)
    if set(works) != {p["id"] for p in registry["works"].values()}:
        raise ValueError("unexpected missing work ID")
    for channel in CHANNELS:
        if set(registry[channel]) != used_keys[channel]:
            raise ValueError("registry mismatch: removed/unknown " + channel + " require explicit review")
    if len(legacy["performances"]) != len(performances):
        raise ValueError("legacy catalog count differs")
    return {
        "works": sorted(works.values(), key=lambda x: x["id"]),
        "venues": sorted(venues.values(), key=lambda x: x["id"]),
        "stagings": sorted(stagings.values(), key=lambda x: x["id"]),
        "performances": sorted(performances, key=lambda x: (x["local_date"], x["id"])),
    }


def payload(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def release_parts(facts: dict, registry: dict) -> tuple[dict[str, bytes], dict]:
    channels = assemble(facts, registry)
    blobs = {}
    entries = {}
    for channel in CHANNELS:
        content = payload({"schema_version": 2, channel: channels[channel]})
        digest = hashlib.sha256(content).hexdigest()
        name = "data/" + channel + "." + digest[:16] + ".json"
        blobs[name] = content
        entries[channel] = {"path": name, "sha256": digest, "count": len(channels[channel])}
    manifest = {
        "schema_version": 2,
        "reviewed_on": facts["reviewed_on"],
        "source": "curated-official-observations",
        "files": entries,
    }
    return blobs, manifest


def publish(*, check: bool = False) -> dict:
    facts = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    blobs, manifest = release_parts(facts, registry)
    if check:
        for name, expected in blobs.items():
            if not (PUBLIC / name).is_file() or (PUBLIC / name).read_bytes() != expected:
                raise ValueError("missing or changed content-addressed feed: " + name)
        if not (PUBLIC / "manifest.json").is_file() or json.loads(
            (PUBLIC / "manifest.json").read_text(encoding="utf-8")
        ) != manifest:
            raise ValueError("public manifest differs from verified source")
    else:
        # Publishing the pointer last ensures failures cannot point at missing data.
        for name, content in blobs.items():
            path = PUBLIC / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != content:
                raise ValueError("content-addressed feed collision")
            if not path.exists():
                path.write_bytes(content)
        (PUBLIC / "manifest.json").write_bytes(payload(manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = publish(check=args.check)
    print(json.dumps({"catalog_schema": 2,
                      "reviewed_on": manifest["reviewed_on"],
                      "counts": {k: v["count"] for k, v in manifest["files"].items()}}))


if __name__ == "__main__":
    main()
