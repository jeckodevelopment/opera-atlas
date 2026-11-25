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
from urllib.parse import urlencode, urlsplit, urlunsplit, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from scripts.publish_integration_index import normalized_name, verified_image

WD = "https://www.wikidata.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA = ("https://it.wikipedia.org/w/api.php", "https://en.wikipedia.org/w/api.php")
ENTITY_DATA = "https://www.wikidata.org/wiki/Special:EntityData/"
QID = re.compile(r"Q[1-9][0-9]*")
LICENSES = {
    "CC BY 4.0": ("CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "CC BY-SA 4.0": ("CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "CC BY 3.0": ("CC-BY-3.0", "https://creativecommons.org/licenses/by/3.0/"),
    "CC BY-SA 3.0": ("CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/"),
    "CC0": ("CC0-1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    "CC BY 2.0": ("CC-BY-2.0", "https://creativecommons.org/licenses/by/2.0/"),
    "CC BY-SA 2.0": ("CC-BY-SA-2.0", "https://creativecommons.org/licenses/by-sa/2.0/"),
    "CC BY 2.5": ("CC-BY-2.5", "https://creativecommons.org/licenses/by/2.5/"),
    "CC BY-SA 2.5": ("CC-BY-SA-2.5", "https://creativecommons.org/licenses/by-sa/2.5/"),
    "CC BY-SA 3.0 de": ("CC-BY-SA-3.0-DE", "https://creativecommons.org/licenses/by-sa/3.0/de/"),
}
# These Commons categories explicitly cover both source-country and US terms.
# Do not infer public-domain status from a composer's death date or generic PD tags.
PD_CATEGORIES = {
    f"Category:{prefix}PD-old-{years}-expired{suffix}"
    for years in (70, 75, 80, 90, 95, 100)
    for prefix, suffix in (("", ""), ("PD-Art (", ")"), ("PD-scan (", ")"))
}
PD_MARK_CATEGORY = "Category:CC-PD-Mark"
REVIEW_CATEGORIES = {
    "Category:Copyright violations",
    "Category:Files with no license",
    "Category:Files with no source",
    "Category:Files with no machine-readable license",
    "Category:Files with no machine-readable author",
    "Category:Deletion requests",
    "Category:Template Unknown (source)",
    "Category:Template Unknown (author)",
}
IMAGE_HOSTS = ("upload.wikimedia.org", "thumb.wikimedia.org")
# A Public Domain Mark is an assertion, not a copyright license.
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
    if endpoint == ENTITY_DATA:
        qid = params.get("qid", "")
        if not QID.fullmatch(qid):
            raise ValueError("Invalid entity identifier")
        url = endpoint + qid + ".json"
    elif endpoint in (WD, COMMONS, *WIKIPEDIA):
        url = endpoint + "?" + urlencode(dict(params, format="json", maxlag=5))
    else:
        raise ValueError("Unsupported API endpoint")
    request = Request(url,
                      headers={"User-Agent":"OperaAtlasPortraits/1.0 (https://github.com/jeckodevelopment/opera-atlas)"})
    last_code = "unavailable"
    for attempt in range(3):
        time.sleep(0.3 if attempt == 0 else 2 ** attempt)
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read(16_000_001 if endpoint == ENTITY_DATA else 4_000_001)
                data = json.loads(raw)
            if not isinstance(data, dict):
                raise WikimediaError("invalid_response")
            if "error" not in data:
                return data
            last_code = data["error"].get("code", "unknown")
            if last_code not in {"maxlag", "ratelimited", "readonly", "cirrussearch-too-busy-error"}:
                raise WikimediaError("api_rejected")
        except HTTPError as exc:
            if exc.code not in TRANSIENT_CODES:
                raise WikimediaError("http_" + str(exc.code)) from exc
            last_code = "http_" + str(exc.code)
        except (URLError, TimeoutError, json.JSONDecodeError):
            last_code = "transport_error"
    raise WikimediaError(last_code)

def values(entity, prop):
    return [c.get("mainsnak", {}).get("datavalue", {}).get("value")
            for c in entity.get("claims", {}).get(prop, [])
            if c.get("rank") != "deprecated"]

def item_ids(entity, prop):
    return {v.get("id") for v in values(entity, prop) if isinstance(v, dict)}

def plain(value):
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", value or "")).split())

def wikipedia_ids(composer, call):
    """Resolve exact article titles and redirects, not full-text search."""
    ids = set()
    errors = []
    names = [composer["name"], *composer.get("aliases", [])]
    titles = "|".join(dict.fromkeys(names + [name + suffix for name in names for suffix in (" (composer)", " (compositore)")]))
    for endpoint in WIKIPEDIA:
        try:
            data = call(endpoint, action="query", titles=titles, redirects=1,
                        prop="pageprops", ppprop="wikibase_item|disambiguation")
            pages = data.get("query", {}).get("pages")
            if not isinstance(pages, dict):
                raise WikimediaError("invalid_wikipedia_response")
            for page in pages.values():
                props = page.get("pageprops", {})
                qid = props.get("wikibase_item", "")
                if "disambiguation" not in props and QID.fullmatch(qid):
                    ids.add(qid)
        except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(exc)
    if errors:
        raise WikimediaError("wikipedia_lookup_unavailable")
    return ids

def entity_records(ids, call):
    try:
        data = call(WD, action="wbgetentities", ids="|".join(sorted(ids)),
                    props="labels|aliases|claims|sitelinks")
        if not isinstance(data.get("entities"), dict):
            raise WikimediaError("invalid_wikidata_response")
        return data["entities"]
    except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError):
        # EntityData reads an existing QID without using Wikidata search.
        entities = {}
        for qid in sorted(ids):
            data = call(ENTITY_DATA, qid=qid)
            if not isinstance(data.get("entities"), dict):
                raise WikimediaError("invalid_entity_data_response")
            entities.update(data["entities"])
        return entities

def find_person(composer, call=api):
    names = {normalized_name(n) for n in [composer["name"], *composer.get("aliases", [])]}
    ids = set()
    pinned = composer.get("wikidata_id")
    if pinned:
        if not QID.fullmatch(pinned):
            raise ValueError("Invalid pinned Wikidata ID")
        ids.add(pinned)
    else:
        # Exact page titles resolve through MediaWiki's page index, avoiding
        # the CirrusSearch service that has repeatedly failed in production.
        lookup_error = False
        try:
            ids = wikipedia_ids(composer, call)
        except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError):
            lookup_error = True
        if not ids:
            try:
                for lang in ("it", "en"):
                    result = call(WD, action="wbsearchentities", search=composer["name"], language=lang, type="item", limit=20)
                    if not isinstance(result.get("search"), list):
                        raise WikimediaError("invalid_search_response")
                    ids.update(x["id"] for x in result["search"] if QID.fullmatch(x["id"]))
            except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise WikimediaError("identity_search_unavailable") from exc
            if lookup_error and not ids:
                raise WikimediaError("identity_lookup_incomplete")
    if not ids:
        return None, "not_found"
    entities = entity_records(ids, call)
    matches = []
    for qid, entity in entities.items():
        if qid not in ids or not QID.fullmatch(qid):
            continue
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
    return portrait_for_identity(composer, match, call)

def portrait_for_identity(composer, match, call, audits=None):
    qid, entity = match
    images = list(dict.fromkeys(v for v in values(entity, "P18") if isinstance(v, str)))
    preferred = [claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                 for claim in entity.get("claims", {}).get("P18", []) if claim.get("rank") == "preferred"]
    ordered = list(dict.fromkeys([v for v in preferred if v in images] + images))
    reasons = []
    seen = set()
    errors = []
    def try_files(files, evidence):
        for filename in files:
            key = filename.replace("_", " ").casefold()
            if key in seen:
                continue
            seen.add(key)
            audit = {"identity_evidence": evidence, "commons_file": filename}
            try:
                record, reason = commons_portrait(composer, qid, filename, call, audit)
            except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError):
                errors.append("candidate_api_error")
                record, reason = None, "api_error"
            if audits is not None:
                audits.append(dict(audit, reason=reason or "verified"))
            if record:
                record["identity_evidence"] = evidence
                return record
            reasons.append(reason)
        return None
    record = try_files(ordered[:8], "wikidata_p18")
    if record:
        return record, None
    # Only use Commons structured depicts (P180) for the exact verified QID.
    # Do not publish results based solely on a matching filename or category.
    try:
        alternatives = depicted_files(qid, call)
    except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError):
        alternatives = []
        errors.append("depicts_lookup_unavailable")
    record = try_files(alternatives, "commons_depicts_p180")
    if record:
        return record, None
    try:
        category_files = linked_category_files(entity, qid, call)
    except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError):
        category_files = []
        errors.append("category_lookup_unavailable")
    record = try_files(category_files, "commons_category_verified_depicts")
    if record:
        return record, None
    if errors:
        raise WikimediaError(errors[0])
    return None, reasons[0] if reasons else "no_image"

def depicted_files(qid, call):
    if not QID.fullmatch(qid):
        raise ValueError("Invalid depicts identifier")
    data = call(COMMONS, action="query", list="search", srnamespace=6,
                srsearch="haswbstatement:P180=" + qid, srlimit=20)
    results = data.get("query", {}).get("search")
    if not isinstance(results, list):
        raise WikimediaError("invalid_depicts_response")
    return verified_depictions(results, qid, call)

def verified_depictions(results, qid, call):
    # Verify the structured claim independently; search indexes can be stale.
    files = []
    for hit in results:
        title = hit.get("title", "")
        pageid = hit.get("pageid")
        if not title.startswith("File:") or not isinstance(pageid, int) or pageid <= 0:
            continue
        files.append((title[5:], "M" + str(pageid)))
    if not files:
        return []
    verified = call(COMMONS, action="wbgetentities", ids="|".join(mid for _, mid in files),
                    props="claims").get("entities")
    if not isinstance(verified, dict):
        raise WikimediaError("invalid_mediainfo_response")
    candidates = []
    for filename, mid in files:
        entity = verified.get(mid, {})
        # MediaInfo exposes statements rather than claims in some responses.
        statements = entity.get("statements", entity.get("claims", {}))
        if isinstance(statements, dict) and qid in item_ids({"claims": statements}, "P180"):
            # Reject any other structured depiction. No filename-only fallback.
            # This does not constitute visual verification of the file contents.
            depicts = item_ids({"claims": statements}, "P180")
            if depicts == {qid}:
                candidates.append(filename)
    return candidates[:8]

def linked_category_files(entity, qid, call):
    """Discover additional files through explicitly linked Commons categories."""
    categories = [v for v in values(entity, "P373") if isinstance(v, str) and v.strip()]
    sitelink = entity.get("sitelinks", {}).get("commonswiki", {}).get("title", "")
    if sitelink.startswith("Category:"):
        categories.append(sitelink[9:])
    results = []
    for category in list(dict.fromkeys(categories))[:2]:
        data = call(COMMONS, action="query", list="categorymembers",
                    cmtitle="Category:" + category.removeprefix("Category:"),
                    cmnamespace=6, cmtype="file", cmlimit=50)
        members = data.get("query", {}).get("categorymembers")
        if not isinstance(members, list):
            raise WikimediaError("invalid_category_response")
        results.extend(members)
    candidates = []
    for start in range(0, len(results), 20):
        candidates.extend(verified_depictions(results[start:start+20], qid, call))
        if len(candidates) >= 8:
            break
    return list(dict.fromkeys(candidates))[:8]

def canonical_cc_url(value):
    # Accept only the canonical Creative Commons domain and license/deed paths.
    if not value:
        return ""
    try:
        u = urlsplit(value)
        if u.scheme not in ("https", "http") or u.netloc != "creativecommons.org" or u.query or u.fragment:
            return None
        path = re.sub(r"/deed(?:\.[a-zA-Z-]+)?/?$", "/", u.path)
        return "https://creativecommons.org" + path.rstrip("/") + "/"
    except ValueError:
        return None

def commons_url(value, expected_host):
    if not isinstance(value, str):
        return None
    try:
        u = urlsplit(value)
        hosts = (expected_host,) if isinstance(expected_host, str) else expected_host
        if u.scheme != "https" or u.netloc not in hosts or u.fragment or "\\" in value:
            return None
        # Preserve existing percent escapes, encode literal Unicode and spaces.
        # Drop only known analytics parameters; preserve all other query data.
        path = quote(u.path, safe="/%:@!$&'()*+,;=-._~")
        query = "&".join(p for p in u.query.split("&")
                         if not p.split("=")[0].startswith("utm_"))
        return urlunsplit((u.scheme, u.netloc, path, query, ""))
    except ValueError:
        return None

def commons_portrait(composer, qid, filename, call, audit=None):
    response = call(COMMONS, action="query", titles="File:" + filename, redirects=1,
                    prop="imageinfo|categories", cllimit="max",
                    clcategories="|".join(sorted(PD_CATEGORIES | REVIEW_CATEGORIES | {PD_MARK_CATEGORY})),
                    iiprop="url|mime|extmetadata", iiurlwidth=720)
    pages = response.get("query", {}).get("pages")
    if not isinstance(pages, dict):
        raise WikimediaError("invalid_commons_response")
    if len(pages) != 1:
        return None, "file_unconfirmed"
    page = next(iter(pages.values()))
    info = page.get("imageinfo", [])
    if len(info) != 1:
        return None, "file_unconfirmed"
    image = info[0]
    meta = image.get("extmetadata", {})
    def field(k):
        return plain(meta.get(k, {}).get("value", ""))
    categories = {x.get("title") for x in page.get("categories", [])}
    source = commons_url(image.get("descriptionurl"), "commons.wikimedia.org")
    thumb_url = commons_url(image.get("thumburl"), IMAGE_HOSTS)
    original_url = commons_url(image.get("url"), "upload.wikimedia.org")
    url = thumb_url or original_url
    if audit is not None:
        # Keep decision inputs for editorial follow-up; never store raw HTML.
        audit.update({"commons_file": filename, "source_url": source,
                      "license_short_name": field("LicenseShortName")[:160],
                      "license_code": field("License")[:100],
                      "license_url_reported": field("LicenseUrl")[:300],
                      "copyrighted": field("Copyrighted")[:30],
                      "restrictions": field("Restrictions")[:200],
                      "author": field("Artist")[:300],
                      "rights_categories": sorted(categories & (PD_CATEGORIES | REVIEW_CATEGORIES | {PD_MARK_CATEGORY})),
                      "thumbnail_host": urlsplit(thumb_url).hostname if thumb_url else None,
                      "image_url": url})
    if image.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
        # Only consume a raster thumbnail generated by Commons, never an SVG/TIFF original.
        if not thumb_url or not urlsplit(thumb_url).path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return None, "unsupported_image"
    if field("Restrictions") or categories & REVIEW_CATEGORIES or field("Copyrighted").casefold() not in ("true", "false"):
        return None, "rights_review"
    short = field("LicenseShortName")
    supplied = field("LicenseUrl")
    canonical = canonical_cc_url(supplied)
    license = LICENSES.get(short)
    evidence = "commons_license_metadata"
    if short.casefold() in {"public domain", "public domain mark", "pdm"}:
        if field("Copyrighted").casefold() != "false":
            return None, "rights_review"
        if canonical == PUBLIC_DOMAIN_URL or (not supplied and field("License").casefold() == "pd" and PD_MARK_CATEGORY in categories):
            license = ("Public Domain", PUBLIC_DOMAIN_URL)
            evidence = "commons_public_domain_mark"
        elif not supplied and field("License").casefold() == "pd" and categories & PD_CATEGORIES and source:
            # Commons documents that PD files may not have a LicenseUrl.
            # Require a specific combined rights category, not just a generic PD label.
            license = ("Public Domain", source)
            evidence = "commons_combined_public_domain_category"
        else:
            return None, "license_review"
    elif not license or canonical != license[1]:
        return None, "license_review"
    author = field("Artist")
    if not author or re.fullmatch(r"(?:unknown(?: author)?|anonymous|unattributed|sconosciuto)(?:[ ,;/]+(?:unknown(?: author)?|anonymous|unattributed|sconosciuto))*", author.casefold()):
        return None, "author_review"
    record = dict(verified=True, url=url, alt="Ritratto di " + composer["name"],
                  source_url=source, author=author, license=license[0], license_url=license[1],
                  credit=author + " — Wikimedia Commons — " + license[0],
                  wikidata_id=qid, commons_file=filename, reviewed_on=date.today().isoformat(),
                  rights_evidence=evidence, rights_categories=sorted(categories & (PD_CATEGORIES | {PD_MARK_CATEGORY})))
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
    previous = json.loads(report_path.read_text()) if report_path.is_file() else {}
    identities = previous.get("identities", {})
    identities = {c["id"]: identities[c["id"]] for c in composers
                  if c["id"] in identities and identities[c["id"]].get("name") == c["name"]
                  and QID.fullmatch(identities[c["id"]].get("wikidata_id", ""))}
    prior = previous.get("unresolved", {})
    history = previous.get("last_attempted", {})
    if not history:
        history = {key: previous.get("updated_at", "") for key, value in prior.items()
                   if value.get("reason") != "not_attempted"}
    history = {c["id"]: history[c["id"]] for c in composers if c["id"] in history}
    composers = sorted(composers, key=lambda c: (history.get(c["id"], ""), c["id"]))
    started = time.monotonic()
    consecutive_errors = 0
    attempted = 0
    api_errors = 0

    def checkpoint():
        total = len(composers)
        verified = sum(bool(verified_image(portraits.get(c["id"]))) for c in composers)
        atomic_json(path, doc)
        atomic_json(report_path, {"schema_version": 1, "total": total,
                    "verified": verified, "attempted": attempted,
                    "api_errors": api_errors,
                    "status": ("blocked" if attempted and api_errors == attempted else
                               "partial" if api_errors or any(v["reason"] == "not_attempted" for v in report.values()) else "completed"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "identities": identities, "last_attempted": history, "unresolved": report})

    for composer in composers:
        key = composer["id"]
        if verified_image(portraits.get(key)):
            continue
        if time.monotonic() - started >= max_seconds or consecutive_errors >= 3:
            break
        attempted += 1
        history[key] = datetime.now(timezone.utc).isoformat()
        audits = []
        try:
            candidate = dict(composer)
            if key in identities and not candidate.get("wikidata_id"):
                candidate["wikidata_id"] = identities[key]["wikidata_id"]
            match, reason = find_person(candidate, call)
            if match:
                identities[key] = {"name": composer["name"], "wikidata_id": match[0]}
                record, reason = portrait_for_identity(composer, match, call, audits)
            else:
                identities.pop(key, None)
                record = None
            consecutive_errors = 0
        except (WikimediaError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            record, reason = None, "api_error"
            api_errors += 1
            consecutive_errors += 1
            # Only known, sanitized diagnostics are published.
            detail = str(exc) if isinstance(exc, WikimediaError) else "transport_error"
            report[key] = {"name": composer["name"], "reason": reason,
                           "detail": detail if re.fullmatch(r"[a-z0-9_-]{1,80}", detail) else "upstream_error",
                           "candidates": audits}
            checkpoint()
            continue
        if record:
            portraits[key] = record
            report.pop(key, None)
        else:
            report[key] = {"name": composer["name"], "reason": reason, "candidates": audits}
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
