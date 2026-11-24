"""Incremental Wikimedia portrait discovery; never writes canonical catalog data."""
import argparse
import json
import os
import tempfile
import re
import time
from datetime import datetime, timezone, date
from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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
# Require an explicit Commons public-domain mark and a non-copyrighted file.
PUBLIC_DOMAIN_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
TRANSIENT_CODES = {429, 500, 502, 503, 504}
class WikimediaError(RuntimeError):
    """A failed upstream request; never infer identity or rights from it."""

def atomic_json(path, doc):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        try:
            handle.write(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

def api(endpoint, **params):
    if endpoint not in (WD, COMMONS):
        raise ValueError("Unsupported API endpoint")
    request = Request(endpoint + "?" + urlencode(dict(params, format="json", maxlag=5)),
                      headers={"User-Agent":"OperaAtlasPortraits/1.0 (https://github.com/jeckodevelopment/opera-atlas)"})
    for attempt in range(3):
        time.sleep(0.3 if attempt == 0 else 2 ** attempt)
        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read(4_000_001))
            if "error" not in data:
                return data
            if data["error"].get("code") not in {"maxlag", "ratelimited", "readonly", "cirrussearch-too-busy-error"}:
                raise WikimediaError("Wikimedia API rejected request")
        except HTTPError as exc:
            if exc.code not in TRANSIENT_CODES:
                raise WikimediaError("Wikimedia HTTP request rejected") from exc
        except (URLError, TimeoutError, json.JSONDecodeError):
            pass
    raise WikimediaError("Wikimedia temporarily unavailable")

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
    if field("LicenseShortName").casefold() in {"public domain", "public domain mark"}:
        if field("Copyrighted").casefold() != "false":
            return None, "rights_review"
        license = ("Public Domain", PUBLIC_DOMAIN_URL)
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

def refresh(root, call=api, max_seconds=900):
    composers = json.loads((root / "data/composer-registry.json").read_text())["composers"]
    path = root / "data/composer-portraits.json"
    doc = json.loads(path.read_text())
    if doc["schema_version"] != 1:
        raise ValueError("Unsupported portrait registry")
    portraits = doc["portraits"]
    report_path = root / "data/composer-portrait-review.json"
    report = {c["id"]: {"name": c["name"], "reason": "not_attempted"}
              for c in composers if not verified_image(portraits.get(c["id"]))}
    started = time.monotonic()
    consecutive_errors = 0
    attempted = 0

    def checkpoint():
        total = len(composers)
        verified = sum(bool(verified_image(portraits.get(c["id"]))) for c in composers)
        atomic_json(path, doc)
        atomic_json(report_path, {"schema_version": 1, "total": total,
                    "verified": verified, "attempted": attempted,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "unresolved": report})

    for composer in composers:
        key = composer["id"]
        if verified_image(portraits.get(key)):
            continue
        if time.monotonic() - started >= max_seconds or consecutive_errors >= 3:
            break
        attempted += 1
        try:
            record, reason = portrait(composer, call)
            consecutive_errors = 0
        except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError):
            record, reason = None, "api_error"
            consecutive_errors += 1
        if record:
            portraits[key] = record
            report.pop(key, None)
        else:
            report[key] = {"name": composer["name"], "reason": reason}
        checkpoint()
    checkpoint()
    print("Verified:", sum(bool(verified_image(portraits.get(c["id"]))) for c in composers),
          "Unresolved:", len(report), "Attempted:", attempted,
          "API errors:", sum(v["reason"] == "api_error" for v in report.values()))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    refresh(args.root, max_seconds=args.max_seconds)
