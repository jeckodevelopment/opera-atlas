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
    value = unicodedata.normalize("NFKD", text.strip().casefold().replace("æ","ae").replace("œ","oe"))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"^l['’]", "", value)  # L’italiana -> italiana
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        raise ValueError("unrepresentable public slug")
    return value


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def assemble(facts: dict, registry: dict, *, approved_extra: set[str] | None = None) -> dict:
    legacy = legacy_build(facts, approved_extra=approved_extra)
    by_legacy = {item["id"]: item for item in legacy["performances"]}
    if registry.get("schema_version") != 1:
        raise ValueError("unknown identity registry")
    all_ids = []
    for channel in ("works", "venues", "stagings", "performances"):
        all_ids += [item["id"] for item in registry[channel].values()]
    reserved = registry.get("reserved_works", {})
    if not isinstance(reserved, dict):
        raise ValueError("invalid reserved work identity registry")
    all_ids += [item["id"] for item in reserved.values()]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("catalog IDs must be unique across entities")

    from scripts.publish_work_editorial import validate_history
    reviewed_path = ROOT / "data" / "reviewed-program-work-editorials.json"
    reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
    source_profiles = {(normalized(x["title"]), normalized(x["composer"])): x
                       for x in reviewed["works"]}
    for key, record in reserved.items():
        identity = (normalized(record["title"]), normalized(record["composer"]))
        profile = source_profiles.get(identity)
        if (key != "|".join(identity) or not profile
            or record.get("status") != "editorial_verified_pending_staging"
            or not validate_history(profile.get("history"))
            or not isinstance(profile.get("synopsis"), str)
            or len(profile["synopsis"].strip()) < 35
            or record["slug"] != slugify(record["title"])):
            raise ValueError("unverified or malformed reserved canonical work")
    works, venues, stagings, performances = {}, {}, {}, []
    used_keys = {channel: set() for channel in CHANNELS}
    route_keys = set()
    work_routes = {}
    for record in list(registry["works"].values()) + list(reserved.values()):
        base_slug=slugify(record["title"])
        public_slug=record.get("route_slug",record["slug"])
        if record["slug"] != base_slug or not isinstance(public_slug,str) or slugify(public_slug)!=public_slug:
            raise ValueError("invalid canonical work route")
        if public_slug in work_routes:
            raise ValueError("duplicate public work route: "+public_slug)
        work_routes[public_slug]=record["id"]
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
        work_record=dict(work)
        work_record["route_slug"]=work.get("route_slug",work["slug"])
        works[work["id"]] = work_record
        venues[venue["id"]] = dict(venue)
        # Existing URLs keep their exact three-segment route. Multiple
        # distinct stagings of the same work at one theatre receive a stable
        # approved edition slug in the *third* segment, so the static
        # frontend needs no SFTP or routing change.
        route_slug=staging.get("route_slug",work["slug"])
        if (not isinstance(route_slug,str) or not route_slug
            or slugify(route_slug)!=route_slug
            or (route_slug!=work["slug"] and
                not route_slug.startswith(work["slug"]+"-"))):
            raise ValueError("invalid official staging edition route slug")
        route = venue["city_slug"] + "/" + venue["slug"] + "/" + route_slug
        if route in route_keys:
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
            legacy_event = by_legacy[f"curated:{sk}:{day}"]
            item.update({
                "legacy_id": legacy_event["id"],
                "local_date": day,
                "starts_at": legacy_event["starts_at"],
                "time_known": legacy_event["time_known"],
                "sources": legacy_event["sources"],
                "status": legacy_event["status"],
            })
            performances.append(item)
    # Publish historically verified work identities without manufacturing a
    # staging or a separate ticket for each component of a multi-work program.
    for record in reserved.values():
        item={k:v for k,v in record.items() if k!="status"}
        item["route_slug"]=record.get("route_slug",record["slug"])
        item["catalog_status"]="program_component"
        works[item["id"]]=item
    expected_work_ids={p["id"] for p in registry["works"].values()}
    expected_work_ids.update(p["id"] for p in reserved.values())
    if set(works) != expected_work_ids:
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



def sync_festival_index(registry: dict, *, check: bool = False) -> None:
    """Regenerate confirmed festival editions from canonical, venue-specific stagings.

    The permanent festival is registered once. Future editions appear only after
    verified stagings from its restricted official source enter the registry.
    """
    from urllib.parse import urlsplit
    path = PUBLIC / "festival-index.json"
    config_path = ROOT / "data" / "festival-registry.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    rules = json.loads(config_path.read_text(encoding="utf-8"))
    if rules.get("schema_version") != 1:
        raise ValueError("unsupported permanent festival registry")
    existing = document["festivals"]
    by_id = {f["id"]: f for f in existing}
    if len(by_id) != len(existing):
        raise ValueError("duplicate festival edition id")
    generated = [dict(f) for f in existing if not f.get("automatically_generated")]
    generated_ids = {f["id"] for f in generated}
    for rule in rules["festivals"]:
        base = by_id.get(rule["template_id"])
        if base is None:
            raise ValueError("missing reviewed festival template: " + rule["template_id"])
        festival_id = rule["id"]
        hosts = rule["source_hosts"]
        prefixes = rule["source_path_prefixes"]
        if not hosts or not prefixes or not all(
            isinstance(h, str) and h and h == h.lower() for h in hosts
        ) or not all(isinstance(p, str) and p.startswith("/") for p in prefixes):
            raise ValueError("invalid official festival source rules: " + festival_id)
        editions = {}
        for staging in registry["stagings"].values():
            season = staging.get("season", "")
            if not isinstance(season, str) or not re.fullmatch(r"20[0-9]{2}", season):
                continue
            url = urlsplit(staging.get("source_url", ""))
            if url.scheme != "https" or url.hostname not in hosts or not any(
                url.path.startswith(prefix) for prefix in prefixes
            ):
                continue
            editions.setdefault(season, set()).add(staging["id"])
        # A reviewed template with no matching stagings is retained as metadata,
        # never promoted into an invented programme.
        for edition, ids in sorted(editions.items()):
            matches = [f for f in generated if f.get("festival_id", f["id"].removesuffix("-" + edition)) == festival_id
                       and f.get("edition") == edition]
            if len(matches) > 1:
                raise ValueError("duplicate edition: " + festival_id + " " + edition)
            if matches:
                matches[0]["staging_ids"] = sorted(set(matches[0]["staging_ids"]) | ids)
            else:
                new_id = festival_id + "-" + edition
                if new_id in generated_ids:
                    raise ValueError("festival identity collision: " + new_id)
                new = {k: v for k, v in base.items() if k not in
                       ("source_hosts", "source_path_prefixes")}
                new.update(id=new_id, festival_id=festival_id, edition=edition,
                           official_url=rule["official_url"],
                           staging_ids=sorted(ids), automatically_generated=True)
                generated.append(new)
                generated_ids.add(new_id)
    generated.sort(key=lambda f: f["id"])
    expected = dict(document)
    expected["festivals"] = generated
    if check:
        if sorted(existing, key=lambda f: f["id"]) != generated:
            raise ValueError("festival edition index differs from verified catalogue")
    else:
        path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


def publish(*, check: bool = False) -> dict:
    facts = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    blobs, manifest = release_parts(facts, registry)
    sync_festival_index(registry, check=check)
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
