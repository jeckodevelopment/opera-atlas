"""Read-only integration export. Run against a pinned published snapshot."""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

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
    mapping = registry["work_composers"]
    entities = []

    def add(kind, key, title, subtitle=None, url=None, composer_ids=(), aliases=(), **extra):
        require(isinstance(title, str) and title.strip(), "Missing title")
        require(ID.fullmatch(key), "Invalid entity ID")
        require(all(c in composers for c in composer_ids), "Unknown composer reference")
        entities.append(dict(type=kind, id=key, title=title, subtitle=subtitle, url=url,
                             composer_ids=list(composer_ids), image=None, fallback_image=None,
                             aliases=list(aliases), **extra))

    for key, c in composers.items():
        # No composer route is published yet.
        add("composer", key, c["name"], aliases=c.get("aliases", []))
    for key, w in works.items():
        refs = mapping.get(key, [])
        # New works must not prevent publication or acquire guessed composer IDs.
        add("opera", key, w["title"], w["composer"], route("opere", w.get("route_slug") or w["slug"]), refs)
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
                entities=sorted(entities, key=lambda x: (x["type"], x["id"])))

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
