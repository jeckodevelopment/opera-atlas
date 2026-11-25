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

# Exact reviewed institutional asset; no general host-level licence inference.
PALERMO_MEDIA = {
    "url": "https://www.comune.palermo.it/wp-content/uploads/2025/01/ed028fbe-7149-4fc8-8f34-9f0fd415ffb6.jpg",
    "source_url": "https://www.comune.palermo.it/novita/consegnata-la-partitura-dellopera-la-sirena-di-palermo-scritta-dal-maestro-passantino-vincitore-del-concorso-bandito-dallassociazione-teatro-dei-ragazzi/",
    "rights_source_url": "https://www.comune.palermo.it/note-legali/",
    "license": "CC-BY-4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "media_kind": "documentary_photo",
}

def verified_image(record, composer_id=None):
    """Never infer reuse rights from a poster, credit or source URL."""
    if not isinstance(record, dict) or record.get("verified") is not True:
        return None
    fields = ("url", "alt", "source_url", "author", "license", "license_url", "credit")
    if not all(isinstance(record.get(k), str) and record[k].strip() for k in fields):
        return None
    if record["license"] not in {"Public Domain", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-3.0", "CC-BY-SA-3.0", "CC-BY-2.0", "CC-BY-SA-2.0", "CC-BY-2.5", "CC-BY-SA-2.5", "CC-BY-SA-3.0-DE"}:
        return None
    institutional = (composer_id == "oa-c-000065" and
                     all(record.get(k) == v for k, v in PALERMO_MEDIA.items()))
    if not institutional and not all(safe_https(record[k]) for k in ("url", "source_url", "license_url")):
        return None
    kind = record.get("media_kind", "portrait")
    if kind not in {"portrait", "documentary_photo", "archival_document"}:
        return None
    return {**{k: record[k] for k in fields}, "media_kind": kind,
            **({"rights_source_url": record["rights_source_url"]} if institutional else {})}

def load_media(root, composers):
    path = root / "data/composer-portraits.json"
    registry = read(path) if path.is_file() else {"schema_version": 1, "portraits": {}}
    require(registry["schema_version"] == 1, "Unsupported portrait registry")
    require(isinstance(registry["portraits"], dict), "Invalid portrait registry")
    require(all(key in composers for key in registry["portraits"]), "Unknown portrait composer")
    return {key: verified_image(value, key) for key, value in registry["portraits"].items()}

def load_editorial_media(root, composers):
    """Separate, opt-in editorial references; never promote to open-license image."""
    path = root / "data/composer-editorial-images.json"
    if not path.is_file():
        return {}
    doc = read(path)
    require(doc.get("schema_version") == 1 and isinstance(doc.get("images"), dict),
            "Invalid editorial image registry")
    providers = {
        "fenice_press_material_editorial": (
            "www.teatrolafenice.it", "/wp-content/uploads/2026/05/IMG_8887-scaled.jpg",
            "https://www.teatrolafenice.it/en/press-lafenice/",
            "Press material (editorial source)"),
        "gai_noncommercial_editorial": (
            "www.giovaniartisti.it", "/sites/default/files/styles/artisti_full/public/artisti/aloisi-gaia/",
            "https://www.giovaniartisti.it/note-legali", "GAI reproduction terms"),
        "press_material_noncommercial_editorial": (
            "ownetic.com", "/news/wp-content/uploads/2013/02/",
            "https://ownetic.com/news/2013/02/14/memories-of-the-east-zygmunt-krauze-chiny/",
            "Press material (editorial source)"),
        "noncommercial_public_interest_information": (
            "www.quirinale.it", "/APIRed/api/media/static/",
            "https://www.quirinale.it/it/pagine/guida-navigazione",
            "Institutional non-commercial editorial use"),
        "press_and_media_editorial": (
            "www.oraziosciortino.com", "/wp-content/uploads/",
            "https://www.oraziosciortino.com/media/", "Press and media use"),
    }
    # The press photo is served from a newspaper CDN, not the article host.
    # Pin the complete reviewed asset and source, including transformation query.
    furlati_asset = "https://immagini.unionesarda.it/version/c%3AZDhmNzY0ODctMTg0MS00%3AMTkzOWEyZTAtY2I4OC00/image.webp?f=3%3A2&q=0.75&w=3840"
    furlati_source = "https://www.unionesarda.it/cultura/creuza-de-ma-chiude-la-sua-19-edizione-a-cagliari-due-giorni-di-cinema-muto-e-musica-dal-vivo-f1duczxa"
    result = {}
    fields = ("url", "alt", "source_url", "author", "license", "license_url",
              "credit", "media_kind", "usage")
    for key, record in doc["images"].items():
        require(key in composers and isinstance(record, dict)
                and record.get("name") == composers[key]["name"], "Editorial image identity mismatch")
        require(all(isinstance(record.get(k), str) and record[k].strip() for k in fields),
                "Missing editorial image fields")
        if record["usage"] == "furlati_press_material_editorial":
            require(key == "oa-c-000016" and record["name"] == "Daniele Furlati"
                    and record["url"] == furlati_asset and record["source_url"] == furlati_source
                    and record["license_url"] == furlati_source
                    and record["license"] == "Press material (editorial source)"
                    and record["media_kind"] == "portrait"
                    and record.get("preserve_integrity") is True,
                    "Furlati press image identity or source mismatch")
            result[key] = {**{k: record[k] for k in fields}, "preserve_integrity": True}
            continue
        provider = providers.get(record["usage"])
        require(provider is not None and record.get("preserve_integrity") is True
                and record["media_kind"] in {"portrait", "documentary_photo"}, "Invalid editorial usage")
        host, prefix, terms, license_name = provider
        require(record["license_url"] == terms and record["license"] == license_name,
                "Editorial rights mismatch")
        for field in ("url", "source_url"):
            value = record[field]
            parsed = urlsplit(value)
            allowed_query = (record["usage"] == "gai_noncommercial_editorial" and field == "url"
                             and parsed.path == "/sites/default/files/styles/artisti_full/public/artisti/aloisi-gaia/gaia-aloisi0.png"
                             and parsed.query == "h=5871340f&itok=uJcpNeYj")
            require(parsed.scheme == "https" and parsed.netloc == host
                    and not parsed.fragment and (not parsed.query or allowed_query) and chr(92) not in value
                    and not any(ord(ch) < 33 for ch in value), "Invalid editorial URL")
        require(urlsplit(record["url"]).path.startswith(prefix), "Invalid editorial image path")
        if record["usage"] == "fenice_press_material_editorial":
            require(key == "oa-c-000018" and urlsplit(record["url"]).path == prefix
                    and record["source_url"] == "https://www.teatrolafenice.it/event/premio-una-vita-nella-musica-2026/",
                    "Fenice press image identity mismatch")
        result[key] = {**{k: record[k] for k in fields}, "preserve_integrity": True}
    return result

def load_source_references(root, composers):
    """Public source links, not permission to display or reproduce photographs."""
    path = root / "data/composer-source-references.json"
    if not path.is_file():
        return {}
    doc = read(path)
    require(doc.get("schema_version") == 1 and isinstance(doc.get("references"), dict),
            "Invalid composer source registry")
    result = {}
    for key, record in doc["references"].items():
        require(key in composers and isinstance(record, dict)
                and record.get("name") == composers[key]["name"], "Source reference identity mismatch")
        require(record.get("usage") == "external_link_only"
                and record.get("rights_status") == "reuse_not_established"
                and record.get("kind") in {"profile", "portrait"}, "Invalid source reference")
        fields = ["source_url", "source", "kind", "usage", "rights_status"]
        if record["kind"] == "portrait":
            fields.extend(("image_url", "author"))
        else:
            require("image_url" not in record, "Unexpected image reference")
        require(all(isinstance(record.get(k), str) and record[k].strip() for k in fields),
                "Missing source reference fields")
        for field in ("source_url", "image_url"):
            if field not in fields:
                continue
            value = record[field]
            parsed = urlsplit(value)
            require(parsed.scheme == "https" and bool(parsed.hostname)
                    and not parsed.username and not parsed.password and parsed.port in (None, 443)
                    and not parsed.fragment and chr(92) not in value
                    and not any(ord(ch) < 33 for ch in value), "Invalid external source URL")
        result[key] = {k: record[k] for k in fields}
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
    mapping, unresolved = resolve_mapping(works, composers, registry["work_composers"])
    portraits = load_media(root, composers)
    editorial = load_editorial_media(root, composers)
    source_references = load_source_references(root, composers)
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
        add("composer", key, c["name"], aliases=c.get("aliases", []), image=portraits.get(key),
            **({"editorial_image": editorial[key]} if key in editorial else {}),
            **({"source_reference": source_references[key]} if key in source_references and not portraits.get(key) and key not in editorial else {}))
    for key, w in works.items():
        refs = mapping.get(key, [])
        # New works must not prevent publication or acquire guessed composer IDs.
        add("opera", key, w["title"], w["composer"], route("opere", w.get("route_slug") or w["slug"]), refs,
            image=(portraits.get(refs[0]) if len(refs) == 1 and
                   (portraits.get(refs[0]) or {}).get("media_kind") != "archival_document" else None))
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
    composer_entities = [e for e in entities if e["type"] == "composer"]
    missing_media = [e for e in composer_entities if not e["image"] and not e.get("editorial_image")]
    media_coverage = {"total": len(composer_entities),
                      "with_image": len(composer_entities) - len(missing_media),
                      "default_image": sum(bool(e["image"]) for e in composer_entities),
                      "editorial_image": sum(bool(e.get("editorial_image")) for e in composer_entities),
                      "missing": sorted(e["id"] for e in missing_media)}
    return dict(schema_version=1, source_revision=revision, catalog_reviewed_on=manifest["reviewed_on"],
                entities=sorted(entities, key=lambda x: (x["type"], x["id"])),
                diagnostics={"unresolved_composer_works": unresolved, "composer_media_coverage": media_coverage})

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
