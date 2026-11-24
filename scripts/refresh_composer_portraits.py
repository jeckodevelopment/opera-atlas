"""Incremental Wikimedia portrait discovery; never writes canonical catalog data."""
import argparse
import json
import re
import time
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.publish_integration_index import normalized_name, verified_image

WD = "https://www.wikidata.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
LICENSES = {
    "CC BY 4.0": ("CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "CC BY-SA 4.0": ("CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "CC BY 3.0": ("CC-BY-3.0", "https://creativecommons.org/licenses/by/3.0/"),
    "CC BY-SA 3.0": ("CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/"),
    "CC0": ("CC0-1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
}
# Public domain notices require case-specific review, not a guessed license.
def api(endpoint, **params):
    if endpoint not in (WD, COMMONS):
        raise ValueError("Unsupported API endpoint")
    time.sleep(0.3)
    request = Request(endpoint + "?" + urlencode(dict(params, format="json", maxlag=5)),
                      headers={"User-Agent":"OperaAtlasPortraits/1.0 (https://github.com/jeckodevelopment/opera-atlas)"})
    with urlopen(request, timeout=25) as response:
        data = json.loads(response.read(4_000_001))
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data

def values(entity, prop):
    return [c.get("mainsnak", {}).get("datavalue", {}).get("value")
            for c in entity.get("claims", {}).get(prop, [])
            if c.get("rank") != "deprecated"]

def item_ids(entity, prop):
    return {v.get("id") for v in values(entity, prop) if isinstance(v, dict)}

def plain(value):
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", value or "")).split())

def find_person(composer, call=api):
    names = {normalized_name(n) for n in [composer["name"], *composer.get("aliases", [])]}
    ids = set()
    pinned = composer.get("wikidata_id")
    if pinned:
        if not re.fullmatch(r"Q[1-9][0-9]*", pinned):
            raise ValueError("Invalid pinned Wikidata ID")
        ids.add(pinned)
    else:
        for lang in ("it", "en"):
            result = call(WD, action="wbsearchentities", search=composer["name"], language=lang, type="item", limit=20)
            ids.update(x["id"] for x in result.get("search", []) if re.fullmatch(r"Q[1-9][0-9]*", x["id"]))
    if not ids:
        return None, "not_found"
    entities = call(WD, action="wbgetentities", ids="|".join(sorted(ids)), props="labels|aliases|claims", languages="it|en")["entities"]
    matches = []
    for qid, entity in entities.items():
        labels = [x["value"] for x in entity.get("labels", {}).values()]
        aliases = [x["value"] for group in entity.get("aliases", {}).values() for x in group]
        if not names.intersection(normalized_name(n) for n in labels + aliases):
            continue
        if "Q5" not in item_ids(entity, "P31") or "Q36834" not in item_ids(entity, "P106"):
            continue
        matches.append((qid, entity))
    if len(matches) != 1:
        return None, "ambiguous" if matches else "identity_unconfirmed"
    return matches[0], None

def portrait(composer, call=api):
    match, reason = find_person(composer, call)
    if not match:
        return None, reason
    qid, entity = match
    images = list(dict.fromkeys(v for v in values(entity, "P18") if isinstance(v, str)))
    if len(images) != 1:
        return None, "no_image" if not images else "multiple_images"
    pages = call(COMMONS, action="query", titles="File:" + images[0], prop="imageinfo",
                 iiprop="url|mime|extmetadata", iiurlwidth=720)["query"]["pages"]
    if len(pages) != 1:
        return None, "file_unconfirmed"
    info = next(iter(pages.values())).get("imageinfo", [])
    if len(info) != 1 or info[0].get("mime") not in ("image/jpeg", "image/png", "image/webp"):
        return None, "unsupported_image"
    image = info[0]
    meta = image.get("extmetadata", {})
    def field(k):
        return plain(meta.get(k, {}).get("value", ""))
    license = LICENSES.get(field("LicenseShortName"))
    if not license or field("LicenseUrl").rstrip("/") != license[1].rstrip("/"):
        return None, "license_review"
    if field("Restrictions") or field("Copyrighted").lower() not in ("true", "false"):
        return None, "rights_review"
    author = field("Artist")
    if not author or author.lower() in ("unknown", "unknown author", "anonymous", "sconosciuto"):
        return None, "author_review"
    record = dict(verified=True, url=image.get("thumburl") or image.get("url"),
                  alt="Ritratto di " + composer["name"], source_url=image.get("descriptionurl"),
                  author=author, license=license[0], license_url=license[1],
                  credit=author + " — Wikimedia Commons — " + license[0],
                  wikidata_id=qid, commons_file=images[0], reviewed_on=date.today().isoformat())
    return (record, None) if verified_image(record) else (None, "metadata_review")

def refresh(root, call=api):
    composers = json.loads((root / "data/composer-registry.json").read_text())["composers"]
    path = root / "data/composer-portraits.json"
    doc = json.loads(path.read_text())
    if doc["schema_version"] != 1:
        raise ValueError("Unsupported portrait registry")
    portraits = doc["portraits"]
    report = {}
    for composer in composers:
        key = composer["id"]
        if verified_image(portraits.get(key)):
            continue
        record, reason = portrait(composer, call)
        if record:
            portraits[key] = record
        else:
            report[key] = {"name":composer["name"], "reason":reason}
    # Network/API exceptions abort before either file is written.
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    report_path = root / "data/composer-portrait-review.json"
    report_path.write_text(json.dumps({"schema_version":1,"unresolved":report}, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print("Verified:", sum(bool(verified_image(p)) for p in portraits.values()), "Unresolved:", len(report))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    refresh(parser.parse_args().root)
