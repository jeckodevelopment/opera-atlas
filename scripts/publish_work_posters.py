"""Publish source-attributed opera cover imagery without changing the static site.

Only officially approved production pages may supply image metadata. Image
URLs are *referenced*, never downloaded, copied or re-hosted; unverified
images leave the editorial illustration fallback in place.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date,datetime,timezone,timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from opera_atlas.controlled_fetch import (AccessDenied,FetchUnavailable,
                                           fetch_official_html)
from opera_atlas.db import connect,migrate
from scripts.daily_ingest import _write_atomic
from scripts.publish_catalog_v2 import ROOT,REGISTRY
from scripts.build_verified_catalog import MANIFEST
from scripts.discover_season_indexes import CONFIG,validate_config

EVIDENCE=ROOT/"data"/"work-poster-evidence.json"
OUTPUT=ROOT/"public"/"catalog"/"work-posters.json"
HEALTH=ROOT/"data"/"work-poster-health.json"
MAX_PAGES=18
RETRY_DAYS=7
# Common image CDNs accepted only when the image URL is declared explicitly
# by the approved official page. No arbitrary HTML img tags or tracking URLs.
IMAGE_CDNS=frozenset({
    "images.ctfassets.net","cdn.sanity.io","images.prismic.io",
    "static.wixstatic.com","res.cloudinary.com","www.teatroallascala.org",
})
BANNED_IMAGE_TOKENS=("logo","favicon","placeholder","avatar","tracking","pixel")

class ImageMeta(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values={}
    def handle_starttag(self,tag,attrs):
        if tag.lower()!="meta":return
        attrs={str(k).lower():v for k,v in attrs if isinstance(v,str)}
        name=(attrs.get("property") or attrs.get("name") or "").strip().lower()
        if name in {"og:image","og:image:secure_url","og:image:alt",
                    "og:image:width","og:image:height",
                    "twitter:image","twitter:image:alt"}:
            value=attrs.get("content","").strip()
            if value:self.values.setdefault(name,value)

def allowed_image_url(raw:str,official_url:str)->str|None:
    if not isinstance(raw,str) or len(raw)>1500:return None
    url=urljoin(official_url,raw)
    parts=urlsplit(url)
    official=urlsplit(official_url)
    if (parts.scheme!="https" or parts.username or parts.password or
            parts.port is not None or parts.fragment or not parts.hostname or
            parts.hostname in {"localhost","127.0.0.1"}):
        return None
    # The authority is the official production page; an approved source's
    # media subdomain, or one of a handful of media CDNs, may host the file.
    origin=official.hostname or ""
    if not (parts.hostname==origin or
            parts.hostname.endswith("."+origin) or
            parts.hostname in IMAGE_CDNS):
        return None
    if any(token in (parts.path+" "+parts.query).lower() for token in BANNED_IMAGE_TOKENS):
        return None
    if not re.search(r"\.(?:jpe?g|png|webp)(?:$|\?)",url,re.I) and parts.hostname not in IMAGE_CDNS:
        return None
    return url

def extract_official_poster(html:str,official_url:str,work_title:str)->dict|None:
    parser=ImageMeta()
    parser.feed(html[:250000])
    data=parser.values
    raw=(data.get("og:image:secure_url") or data.get("og:image") or
         data.get("twitter:image"))
    url=allowed_image_url(raw,official_url)
    if not url:return None
    alt=(data.get("og:image:alt") or data.get("twitter:image:alt") or "").strip()
    if any(word in alt.casefold() for word in ("logo","favicon","placeholder")):
        return None
    try:
        width,height=int(data.get("og:image:width","0")),int(data.get("og:image:height","0"))
    except ValueError:
        return None
    # Explicit landscape OG banners are not opera posters; do not present
    # them as portrait artwork. Unknown dimensions remain unverified art.
    if width>0 and height>0 and width>height*1.35:
        return None
    return {
        "image_url":url,"source_url":official_url,
        "credit":"Immagine della produzione dal sito ufficiale del teatro",
        "alt":"Immagine della produzione di "+work_title,
        "kind":"official_production_image",
    }

def canonical_sources()->list[dict]:
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    official={x["key"]:x for x in validate_config(
        json.loads(CONFIG.read_text(encoding="utf-8"))) if x["access_status"]=="approved"}
    by_host={urlsplit(x["official_url"]).hostname:x for x in official.values()}
    seen=set()
    rows=[]
    for production in reversed(facts["productions"]):
        url=production["source_url"]
        host=urlsplit(url).hostname
        source=by_host.get(host)
        if source is None:continue
        title=production["title"]
        composer=production["composer"]
        matches=[w for w in registry["works"].values()
                 if w["title"]==title and w["composer"]==composer]
        if len(matches)!=1:continue
        work=matches[0]
        slug=work["slug"]
        if (slug,url) in seen:continue
        seen.add((slug,url))
        rows.append({"slug":slug,"work_id":work["id"],"title":title,
                     "source_key":source["key"],
                     "official_root":source["official_url"],"source_url":url})
    return rows

def publish(*,network_enabled:bool=False,fetcher=fetch_official_html,
            today:date|None=None,max_pages:int=MAX_PAGES)->dict:
    if not 0<=max_pages<=MAX_PAGES:raise ValueError("invalid poster fetch limit")
    current=json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.exists() else {
        "schema_version":1,"posters":{},"checks":{}}
    if current.get("schema_version")!=1 or not isinstance(current.get("posters"),dict):
        raise ValueError("invalid poster evidence")
    posters={k:v.copy() for k,v in current["posters"].items()}
    checks=current.get("checks",{}).copy()
    sources=canonical_sources()
    source_slugs={x["slug"] for x in sources}
    # Candidate metadata must not leak into the published feed unless the
    # work already exists in the verified canonical manifest.
    known_slugs={x["slug"] for x in json.loads(
        REGISTRY.read_text(encoding="utf-8"))["works"].values()}
    posters={k:v for k,v in posters.items() if k in known_slugs}
    deadline=today or date.today()
    checked=0
    outcomes=[]
    db=connect()
    try:
        migrate(db)
        for row in sources:
            slug,url=row["slug"],row["source_url"]
            if slug in posters or checked>=max_pages:continue
            previous=checks.get(url,{})
            until=previous.get("retry_after")
            if isinstance(until,str) and until>deadline.isoformat():continue
            checked+=1
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                           (row["official_root"],))
                source_id=db.execute("SELECT id FROM sources WHERE official_url=?",
                                     (row["official_root"],)).fetchone()["id"]
                page=fetcher(db,source_id=source_id,url=url,network_enabled=True)
                found=extract_official_poster(page.html,url,row["title"])
                if found:
                    if any(x["image_url"]==found["image_url"] and k!=slug
                           for k,x in posters.items()):
                        raise ValueError("same promotional image already assigned to another opera")
                    posters[slug]={"work_id":row["work_id"],**found}
                    outcomes.append({"slug":slug,"status":"verified_official_metadata"})
                else:
                    outcomes.append({"slug":slug,"status":"no_suitable_official_poster"})
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                outcomes.append({"slug":slug,"status":"automatic_retry",
                                 "reason":type(exc).__name__})
            checks[url]={"retry_after":(deadline+timedelta(days=RETRY_DAYS)).isoformat()}
    finally:
        db.close()
    # Every published work has an image plan: official art if available,
    # otherwise the original editorial cover created by image-client.js.
    manifest={"schema_version":1,"works":{
        slug:posters.get(slug,{"kind":"original_editorial_cover",
              "alt":"Copertina editoriale originale per "+item["title"]})
        for slug,item in sorted(((w["slug"],w) for w in json.loads(
            REGISTRY.read_text(encoding="utf-8"))["works"].values()))}}
    _write_atomic(EVIDENCE,{"schema_version":1,"posters":posters,"checks":checks})
    _write_atomic(OUTPUT,manifest)
    _write_atomic(HEALTH,{"schema_version":1,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checked_pages":checked,"official_images":sum(
            row["kind"]=="official_production_image" for row in manifest["works"].values()),
        "editorial_fallbacks":sum(
            row["kind"]=="original_editorial_cover" for row in manifest["works"].values()),
        "outcomes":outcomes})
    return manifest

def check()->None:
    from scripts.publish_catalog_v2 import REGISTRY
    current=json.loads(OUTPUT.read_text(encoding="utf-8"))
    works=json.loads(REGISTRY.read_text(encoding="utf-8"))["works"]
    if current.get("schema_version")!=1 or set(current.get("works",{}))!={
        w["slug"] for w in works.values()}:
        raise ValueError("poster feed does not match published opera registry")
    for slug,item in current["works"].items():
        if item["kind"]=="official_production_image":
            if not allowed_image_url(item["image_url"],item["source_url"]):
                raise ValueError("unapproved official poster URL for "+slug)
        elif item["kind"]!="original_editorial_cover":
            raise ValueError("unrecognized poster provenance for "+slug)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    parser.add_argument("--check",action="store_true")
    opts=parser.parse_args()
    if opts.check:check()
    else:
        result=publish(network_enabled=opts.allow_network)
        print(json.dumps({"work_images":len(result["works"])}))
if __name__=="__main__":
    main()
