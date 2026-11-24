"""Read-only integration export. Run against a pinned published snapshot."""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
import unicodedata

ROOT = "https://opera.plus/atlas/"
SLUG = re.compile(r"[a-z0-9-]+")
ID = re.compile(r"[a-zA-Z0-9_-]+")
SHA = re.compile(r"[a-f0-9]{40}")

def read(path):
    return json.loads(path.read_bytes())

def require(condition, message):
    if not condition:
        raise ValueError(message)

def route(*parts):
    require(all(isinstance(p, str) and SLUG.fullmatch(p) for p in parts), "Invalid route")
    return ROOT + "/".join(parts) + "/"

def channel(base, manifest, key):
    spec = manifest["files"][key]
    require(re.fullmatch(r"data/" + key + r"\.[a-f0-9]{16}\.json", spec["path"]), "Invalid channel path")
    raw = (base / spec["path"]).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == spec["sha256"], "Channel digest mismatch")
    records = json.loads(raw)[key]
    require(isinstance(records, list) and len(records) == spec["count"], "Channel count mismatch")
    index(records)
    return records

def index(records):
    result = {}
    for item in records:
        key = item["id"]
        require(isinstance(key, str) and ID.fullmatch(key) and key not in result, "Invalid or duplicate ID")
        result[key] = item
    return result

def normalized_name(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

def resolve_mapping(works, composers, mapping):
    """Use exact normalized names/aliases only, never fuzzy matches."""
    lookup = {}
    for key, composer in composers.items():
        for name in [composer["name"], *composer.get("aliases", [])]:
            lookup.setdefault(normalized_name(name), set()).add(key)
    resolved = {}
    unresolved = []
    for key, work in works.items():
        if key in mapping:
            refs = mapping[key]
            require(isinstance(refs, list) and len(refs) == len(set(refs)), "Invalid composer mapping")
            require(all(ref in composers for ref in refs), "Unknown composer reference")
            if refs:
                resolved[key] = refs
                continue
        matches = lookup.get(normalized_name(work["composer"]), set())
        if len(matches) == 1:
            resolved[key] = sorted(matches)
        else:
            resolved[key] = []
            unresolved.append({"work_id": key, "composer": work["composer"]})
    return resolved, sorted(unresolved, key=lambda item: item["work_id"])

def safe_https(value):
    if not isinstance(value, str) or any(ord(ch) < 33 for ch in value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and u.hostname in {
            "commons.wikimedia.org", "upload.wikimedia.org", "thumb.wikimedia.org", "creativecommons.org",
            "rightsstatements.org", "opera.plus"
        } and not u.username and not u.password and u.port in (None, 443)
                and not u.fragment and "\\" not in value)
    except ValueError:
        return False

def verified_image(record):
    """Never infer reuse rights from a poster, credit or source URL."""
    if not isinstance(record, dict) or record.get("verified") is not True:
        return None
    fields = ("url", "alt", "source_url", "author", "license", "license_url", "credit")
    if not all(isinstance(record.get(k), str) and record[k].strip() for k in fields):
        return None
    if record["license"] not in {"Public Domain", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-3.0", "CC-BY-SA-3.0", "CC-BY-2.0", "CC-BY-SA-2.0", "CC-BY-2.5", "CC-BY-SA-2.5", "CC-BY-SA-3.0-DE"}:
        return None
    if not all(safe_https(record[k]) for k in ("url", "source_url", "license_url")):
        return None
    return {k: record[k] for k in fields}

def load_media(root, composers):
    path = root / "data/composer-portraits.json"
    registry = read(path) if path.is_file() else {"schema_version": 1, "portraits": {}}
    require(registry["schema_version"] == 1, "Unsupported portrait registry")
    require(isinstance(registry["portraits"], dict), "Invalid portrait registry")
    require(all(key in composers for key in registry["portraits"]), "Unknown portrait composer")
    return {key: verified_image(value) for key, value in registry["portraits"].items()}

def build(root, revision):
    require(SHA.fullmatch(revision), "Expected full revision SHA")
    catalog = root / "public/catalog"
    base = catalog / "v2"
    manifest = read(base / "manifest.json")
    require(manifest["schema_version"] == 2, "Unsupported catalog")
    works, venues, stages, events = (index(channel(base, manifest, k)) for k in ("works", "venues", "stagings", "performances"))
    for event in events.values():
        require(event["staging_id"] in stages, "Unknown performance staging")
    registry = read(root / "data/composer-registry.json")
    require(registry["schema_version"] == 1, "Unsupported composer registry")
    composers = index(registry["composers"])
    mapping, unresolved = resolve_mapping(works, composers, registry["work_composers"])
    portraits = load_media(root, composers)
    entities = []

    def add(kind, key, title, subtitle=None, url=None, composer_ids=(), aliases=(), image=None, fallback_image=None, **extra):
        require(isinstance(title, str) and title.strip(), "Missing title")
        require(ID.fullmatch(key), "Invalid entity ID")
        require(all(c in composers for c in composer_ids), "Unknown composer reference")
        entities.append(dict(type=kind, id=key, title=title, subtitle=subtitle, url=url,
                             composer_ids=list(composer_ids), image=image, fallback_image=fallback_image,
                             aliases=list(aliases), **extra))

    for key, c in composers.items():
        # No composer route is published yet.
        add("composer", key, c["name"], aliases=c.get("aliases", []), image=portraits.get(key))
    for key, w in works.items():
        refs = mapping.get(key, [])
        # New works must not prevent publication or acquire guessed composer IDs.
        add("opera", key, w["title"], w["composer"], route("opere", w.get("route_slug") or w["slug"]), refs,
            image=portraits.get(refs[0]) if len(refs) == 1 else None)
    directory = index(read(catalog / "venue-directory.json")["venues"])
    seen_venues = set()
    for key, v in directory.items():
        vid = v.get("canonical_venue_id") or key
        require(vid not in seen_venues, "Duplicate directory venue")
        seen_venues.add(vid)
        add("theatre", vid, v["name"], v["city"], route(v["city_slug"], v["slug"]))
    for key, v in venues.items():
        if key not in seen_venues:
            add("theatre", key, v.get("display_name") or v["name"], v["city"], route(v["city_slug"], v["slug"]))
    for key, s in stages.items():
        w, v = works[s["work_id"]], venues[s["venue_id"]]
        path = s["url"]
        require(isinstance(path, str) and re.fullmatch(r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+/", path), "Invalid staging route")
        add("production", key, w["title"], v.get("display_name") or v["name"], ROOT + path[1:], mapping.get(w["id"], []), production_kind="staging")
    groups = index(read(base / "production-groups.json")["groups"])
    for key, g in groups.items():
        w = works[g["work_id"]]
        require(g["staging_ids"] and all(s in stages for s in g["staging_ids"]), "Invalid group staging")
        add("production", key, g["name"], w["composer"], route("produzioni", key), mapping.get(w["id"], []), production_kind="group")
    programs = index(read(catalog / "programs.json")["programs"])
    for key, p in programs.items():
        if not p.get("performances"):
            continue
        refs = list(dict.fromkeys(c for w in p["components"] for c in mapping.get(w.get("work_id"), [])))
        add("production", key, p["title"], p["venue"], route("programmi", key), refs, production_kind="program")
    festivals = index(read(base / "festival-index.json")["festivals"])
    by_festival = {}
    for f in festivals.values():
        key = f["festival_id"]
        # The public directory routes by edition ID, not festival ID.
        previous = by_festival.get(key)
        if previous is None or (str(f["edition"]), f["id"]) > (str(previous["edition"]), previous["id"]):
            by_festival[key] = f
    for key, f in by_festival.items():
        add("festival", key, f["name"], f["city"], ROOT + "directory.html?section=festival&id=" + f["id"])
    keys = [(x["type"], x["id"]) for x in entities]
    require(len(keys) == len(set(keys)), "Duplicate entity")
    return dict(schema_version=1, source_revision=revision, catalog_reviewed_on=manifest["reviewed_on"],
                entities=sorted(entities, key=lambda x: (x["type"], x["id"])),
                diagnostics={"unresolved_composer_works": unresolved})

def publish(root, revision):
    data = build(root, revision)
    target = root / "public/integrations/v1/entities.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return len(data["entities"])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    print("Entities:", publish(args.root, args.revision))

if __name__ == "__main__":
    main()
