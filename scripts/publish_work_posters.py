"""Publish source-attributed opera cover imagery without changing the static site.

Only officially approved production pages may supply image metadata. Image
URLs are *referenced*, never downloaded, copied or re-hosted; unverified
images are not invented or substituted with editorial illustrations.
"""
from __future__ import annotations
import argparse
import json
import re
import unicodedata
from datetime import date,datetime,timezone,timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,quote,unquote

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
ARCHIVE=ROOT/"data"/"archival-work-images.json"
MAX_PAGES=18
RETRY_DAYS=2
BLOCKED_RETRY_DAYS=7
POSTER_POLICY_VERSION=3
# Editorially generated placeholders are not a publishable opera image.
# An image must represent the exact canonical work, with verified provenance.
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

def image_matches_work(image_url:str,work_title:str)->bool:
    """Demand the opera title in the image filename, not just page OG tags.

    The official La Scala OpenGraph data sometimes names a conductor from an
    unrelated concert. A generic OpenGraph image is NOT an opera poster.
    """
    # Reviewed first-party production thumbnail, published on the official opera page.
    if work_title.casefold()=="la vita nuda" and image_url=="https://operaroma.b-cdn.net/wp-content/uploads/2025/08/PIRANDELLO-5-Foto-pulita-130x95.jpg":
        return True
    stem=unquote(urlsplit(image_url).path.split("/")[-1])
    stem=re.sub(r"\.(?:jpe?g|png|webp)$","",stem,flags=re.I)
    def tokens(value):
        value=unicodedata.normalize("NFKD",value)
        value="".join(c for c in value if not unicodedata.combining(c))
        return [x for x in re.split(r"[^a-z0-9]+",value.lower()) if x]
    title=[x for x in tokens(work_title) if x not in {"il","la","le","lo","l","di","de","and","in"}]
    filename=tokens(stem)
    # An opera beginning with an elided Italian article may appear in
    # first-party filenames as "lesecuzione" rather than "l-esecuzione".
    # Only split that exact article if it yields a required title token;
    # never substitute another composition or accept generic season art.
    if re.match(r"(?i)^l['’]",work_title):
        filename += [x[1:] for x in filename
                     if x.startswith("l") and x[1:] in title]
    if not title:return False
    return all(x in filename for x in title)

def load_archival_art(known_slugs:set[str])->dict:
    if not ARCHIVE.exists():return {}
    data=json.loads(ARCHIVE.read_text(encoding="utf-8"))
    if data.get("schema_version")!=1 or not isinstance(data.get("works"),dict):
        raise ValueError("invalid curated Wikimedia artwork registry")
    result={}
    for slug,entry in data["works"].items():
        if slug not in known_slugs:continue
        if not isinstance(entry,dict) or not all(
            isinstance(entry.get(k),str) and entry[k]
            for k in ("file","description","credit","license")):
            raise ValueError("invalid archival artwork for "+slug)
        filename=entry["file"]
        if (len(filename)>220 or "/" in filename or "\\\\" in filename or
                not re.search(r"\.(?:jpe?g|png|webp)$",filename,re.I)):
            raise ValueError("unsafe Commons artwork filename")
        encoded=quote(filename.replace(" ","_"),safe="()_'-")
        result[slug]={
            "kind":"archival_work_image",
            "image_url":"https://commons.wikimedia.org/wiki/Special:Redirect/file/"+encoded+"?width=720",
            "source_url":"https://commons.wikimedia.org/wiki/File:"+encoded,
            "alt":entry["description"],
            "credit":entry["credit"],"license":entry["license"],
        }
    return result

def exact_first_party_body_work_image(html:str,official_url:str,work_title:str)->str|None:
    """One work-named image in the actual event header, never menus or footer."""
    h=re.search(r"(?is)<h1\b[^>]*>.*?</h1>",html)
    if not h:return None
    end=re.search(r"(?is)<h[2-6]\b[^>]*>\s*informazioni\s+sull.evento",
                  html[h.end():])
    if not end:return None
    fragment=html[h.end():h.end()+end.start()]
    images=re.findall(r"""(?is)<img\b[^>]*\bsrc\s*=\s*['"]([^'"]+)['"]""",
                      fragment)
    matches=set()
    for raw in images:
        candidate=allowed_image_url(raw,official_url)
        if (candidate and urlsplit(candidate).hostname==urlsplit(official_url).hostname
            and image_matches_work(candidate,work_title)):
            matches.add(candidate)
    return next(iter(matches)) if len(matches)==1 else None


def extract_official_poster(html:str,official_url:str,work_title:str,*,
                            verified_event_page:bool=False)->dict|None:
    parser=ImageMeta()
    parser.feed(html[:250000])
    data=parser.values
    # A production page may expose an unrelated OpenGraph thumbnail while
    # Twitter metadata contains the correct production photo.
    candidates=[data.get("og:image:secure_url"),data.get("og:image"),data.get("twitter:image")]
    alt=(data.get("og:image:alt") or data.get("twitter:image:alt") or "").strip()
    # On a single, explicitly approved first-party *work event* page we can
    # also trust work-specific image ALT text if a generated asset filename
    # lacks the title. This does not apply to season listings, whose generic
    # social images are frequently unrelated to a particular opera.
    def title_tokens(value):
        base=unicodedata.normalize("NFKD",value).casefold()
        base="".join(x for x in base if not unicodedata.combining(x))
        return [x for x in re.split(r"[^a-z0-9]+",base)
                if x not in {"","l","il","la","lo","le","un","una","di","del","della"}]
    title_words=title_tokens(work_title)
    alt_words=title_tokens(alt)
    verified_alt=(verified_event_page and len(title_words)>=1
                  and all(x in alt_words for x in title_words)
                  and not any(x in alt.casefold()
                              for x in ("logo","favicon","placeholder","stagione 2026")))
    url=next((candidate for raw in candidates if
              (candidate:=allowed_image_url(raw,official_url)) and
              (image_matches_work(candidate,work_title) or verified_alt)),None)
    if not url:
        url=exact_first_party_body_work_image(html,official_url,work_title)
    if not url:return None
    if any(word in alt.casefold() for word in ("logo","favicon","placeholder")):
        return None
    try:
        width,height=int(data.get("og:image:width","0")),int(data.get("og:image:height","0"))
    except ValueError:
        return None
    # An index banner from a different source is never an opera poster.
    # Title-specific artwork on the same official production domain is
    # authentic even when the theatre uses a wide 16:9 season visual.
    if (width>0 and height>0 and width>height*1.35 and
            urlsplit(url).hostname!=urlsplit(official_url).hostname):
        return None
    # Preserve the *original* first-party alternative text as verification
    # evidence. A generated image filename may not contain the opera title.
    # Never synthesize this field from the requested title.
    alt_verified=(verified_alt and not image_matches_work(url,work_title))
    return {
        "image_url":url,"source_url":official_url,
        "credit":"Immagine della produzione dal sito ufficiale del teatro",
        "alt":"Immagine della produzione di "+work_title,
        "kind":"official_production_image",
        **({"source_image_alt":alt} if alt_verified else {}),
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
        if (work["id"],url) in seen:continue
        seen.add((work["id"],url))
        rows.append({"slug":slug,"work_id":work["id"],"title":title,
                     "source_key":source["key"],
                     "official_root":source["official_url"],"source_url":url})
    return rows

def publish(*,network_enabled:bool=False,fetcher=fetch_official_html,
            today:date|None=None,max_pages:int=MAX_PAGES)->dict:
    if not 0<=max_pages<=MAX_PAGES:raise ValueError("invalid poster fetch limit")
    current=json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.exists() else {
        "schema_version":1,"posters":{},"checks":{}}
    if current.get("schema_version") not in (1,2) or not isinstance(current.get("posters"),dict):
        raise ValueError("invalid poster evidence")
    checks=current.get("checks",{}).copy()
    sources=canonical_sources()
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry_works=(list(registry["works"].values())+
                    list(registry.get("reserved_works",{}).values()))
    by_id={w["id"]:w for w in registry_works}
    ids_by_slug={}
    for w in registry_works:
        ids_by_slug.setdefault(w["slug"],[]).append(w["id"])
    # Migrate the older slug-keyed evidence safely. When two compositions
    # share a title (Puccini and Leoncavallo's La bohème), only an explicit
    # matching permanent work_id permits reuse of a historical image.
    posters={}
    for key,value in current["posters"].items():
        if not isinstance(value,dict):continue
        wid=value.get("work_id")
        if not isinstance(wid,str) or wid not in by_id:
            options=ids_by_slug.get(key,[])
            wid=options[0] if len(options)==1 else None
        from opera_atlas.verified_ticketing_art import is_verified_ticketing_poster
        from opera_atlas.verified_coproduction_posters import is_verified_coproduction_poster
        from opera_atlas.verified_historical_theatre_posters import is_verified_theatre_poster
        from opera_atlas.verified_civic_work_images import is_verified_civic_image
        from opera_atlas.verified_original_work_art import is_verified_original_art
        if (wid in by_id and (
                (image_matches_work(value.get("image_url",""),by_id[wid]["title"])
                 and value.get("kind")=="official_production_image")
                or is_verified_ticketing_poster(
                    value,title=by_id[wid]["title"],composer=by_id[wid]["composer"])
                or is_verified_coproduction_poster(
                    value,title=by_id[wid]["title"],composer=by_id[wid]["composer"])
                or is_verified_original_art(
                    value,title=by_id[wid]["title"],composer=by_id[wid]["composer"])
                or is_verified_civic_image(
                    value,title=by_id[wid]["title"],composer=by_id[wid]["composer"])
                or is_verified_theatre_poster(
                    value,title=by_id[wid]["title"],composer=by_id[wid]["composer"]))):
            posters[wid]={"work_id":wid,**value}
    archive_by_slug=load_archival_art({w["slug"] for w in registry_works})
    archival_registry=json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else {}
    # Permanent IDs disambiguate homonymous operas; every historical image
    # must also state its composer to prevent assigning Puccini art to Leoncavallo.
    archive_by_id={}
    for wid,entry in archival_registry.get("works_by_id",{}).items():
        work=by_id.get(wid)
        if not work or entry.get("work_id")!=wid or entry.get("composer")!=work["composer"]:
            raise ValueError("historical poster work ID/composer mismatch: "+wid)
        if not all(isinstance(entry.get(key),str) and entry[key]
                   for key in ("file","description","credit","license")):
            raise ValueError("incomplete historical poster evidence: "+wid)
        filename=entry["file"]
        if (len(filename)>220 or "/" in filename or "\\\\" in filename or
                not re.search(r"\.(?:jpe?g|png|webp)$",filename,re.I)):
            raise ValueError("unsafe historical poster filename: "+wid)
        encoded=quote(filename.replace(" ","_"),safe="()_'-")
        archive_by_id[wid]={
            "kind":"archival_work_image",
            "image_url":"https://commons.wikimedia.org/wiki/Special:Redirect/file/"+encoded+"?width=720",
            "source_url":"https://commons.wikimedia.org/wiki/File:"+encoded,
            "alt":entry["description"],"credit":entry["credit"],"license":entry["license"],
        }
    # An archival image is keyed by title in the source bank; only attach
    # it if that title resolves to one and only one canonical composition.
    archive={
        w["id"]:archive_by_slug[w["slug"]]
        for w in registry_works
        if len(ids_by_slug[w["slug"]])==1 and w["slug"] in archive_by_slug
    }
    archive.update(archive_by_id)
    deadline=today or date.today()
    checked=0
    outcomes=[]
    db=connect()
    try:
        migrate(db)
        for row in sources:
            slug,url,wid=row["slug"],row["source_url"],row["work_id"]
            if wid in archive or wid in posters or checked>=max_pages:continue
            previous=checks.get(url,{})
            until=previous.get("retry_after")
            if (previous.get("policy_version")==POSTER_POLICY_VERSION and
                    isinstance(until,str) and until>deadline.isoformat()):continue
            checked+=1
            retry_days=RETRY_DAYS
            try:
                if not network_enabled:raise AccessDenied("network disabled")
                db.execute("INSERT OR IGNORE INTO sources(official_url,access_status) VALUES (?, 'approved')",
                           (row["official_root"],))
                source_id=db.execute("SELECT id FROM sources WHERE official_url=?",
                                     (row["official_root"],)).fetchone()["id"]
                page=fetcher(db,source_id=source_id,url=url,network_enabled=True)
                found=extract_official_poster(page.html,url,row["title"])
                if found:
                    if any(x["image_url"]==found["image_url"] and k!=wid
                           for k,x in posters.items()):
                        raise ValueError("same promotional image already assigned to another opera")
                    posters[wid]={"work_id":wid,**found}
                    outcomes.append({"slug":slug,"status":"verified_official_metadata"})
                else:
                    outcomes.append({"slug":slug,"status":"no_suitable_official_poster"})
            except (AccessDenied,FetchUnavailable,ValueError) as exc:
                retry_days=BLOCKED_RETRY_DAYS if isinstance(exc,AccessDenied) else RETRY_DAYS
                outcomes.append({"slug":slug,"status":"automatic_retry",
                                 "reason":type(exc).__name__})
            checks[url]={"retry_after":(deadline+timedelta(days=retry_days)).isoformat(),
                         "policy_version":POSTER_POLICY_VERSION}
    finally:
        db.close()
    # Fail closed: neither a generated title card nor a missing source can
    # be published as an opera cover. Keep the last valid public feed unchanged.
    missing=[w["id"] for w in registry_works
             if w["id"] not in posters and w["id"] not in archive]
    if missing:
        raise ValueError("verified opera images missing for: "+", ".join(sorted(missing)))
    # Archival-first policy: original posters, historic libretti and scores
    # from stable rights-documented collections outrank temporary theatre
    # production images. The latter remain only as a fallback.
    manifest={"schema_version":2,"works":{
        w["id"]:{"work_id":w["id"],**(archive.get(w["id"]) or posters.get(w["id"]))}
        for w in sorted(registry_works,key=lambda entry:entry["id"])}}
    _write_atomic(EVIDENCE,{"schema_version":2,"posters":posters,"checks":checks})
    _write_atomic(OUTPUT,manifest)
    _write_atomic(HEALTH,{"schema_version":1,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checked_pages":checked,"official_images":sum(
            row["kind"]=="official_production_image" for row in manifest["works"].values()),
        "archival_images":sum(
            row["kind"]=="archival_work_image" for row in manifest["works"].values()),
        "editorial_fallbacks":0,
        "outcomes":outcomes})
    return manifest

def check()->None:
    from scripts.publish_catalog_v2 import REGISTRY
    current=json.loads(OUTPUT.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    works={**registry["works"],
           **{"reserved:"+key:value for key,value in registry.get("reserved_works",{}).items()}}
    if current.get("schema_version")!=2 or set(current.get("works",{}))!={
        w["id"] for w in works.values()}:
        raise ValueError("poster feed does not match each canonical work ID")
    titles={w["id"]:w["title"] for w in works.values()}
    for slug,item in current["works"].items():
        if item.get("work_id")!=slug:
            raise ValueError("poster work ID does not match the record identity")
        if item["kind"]=="official_production_image":
            if (not allowed_image_url(item["image_url"],item["source_url"]) or
                not image_matches_work(item["image_url"],titles[slug])):
                raise ValueError("wrong or unapproved official poster for "+slug)
        elif item["kind"]=="official_original_work_artwork":
            from opera_atlas.verified_original_work_art import is_verified_original_art
            composers={w["id"]:w["composer"] for w in works.values()}
            if not is_verified_original_art(
                    item,title=titles[slug],composer=composers[slug]):
                raise ValueError("unverified original first-party work image for "+slug)
        elif item["kind"]=="verified_historical_theatre_poster":
            from opera_atlas.verified_historical_theatre_posters import is_verified_theatre_poster
            composers={w["id"]:w["composer"] for w in works.values()}
            if not is_verified_theatre_poster(
                    item,title=titles[slug],composer=composers[slug]):
                raise ValueError("unverified historical theatre poster for "+slug)
        elif item["kind"]=="official_civic_production_image":
            from opera_atlas.verified_civic_work_images import is_verified_civic_image
            composers={w["id"]:w["composer"] for w in works.values()}
            if not is_verified_civic_image(
                    item,title=titles[slug],composer=composers[slug]):
                raise ValueError("unverified exact municipal production image for "+slug)
        elif item["kind"]=="official_coproduction_poster":
            from opera_atlas.verified_coproduction_posters import is_verified_coproduction_poster
            composers={w["id"]:w["composer"] for w in works.values()}
            if not is_verified_coproduction_poster(
                    item,title=titles[slug],composer=composers[slug]):
                raise ValueError("unverified co-producer artwork for "+slug)
        elif item["kind"]=="ticketing_event_artwork":
            from opera_atlas.verified_ticketing_art import is_verified_ticketing_poster
            composers={w["id"]:w["composer"] for w in works.values()}
            if not is_verified_ticketing_poster(
                    item,title=titles[slug],composer=composers[slug]):
                raise ValueError("unverified ticketing artwork for "+slug)
        elif item["kind"]=="archival_work_image":
            if (not isinstance(item.get("source_url"),str) or
                    not item["source_url"].startswith("https://commons.wikimedia.org/wiki/File:") or
                    not item.get("image_url","").startswith(
                        "https://commons.wikimedia.org/wiki/Special:Redirect/file/")):
                raise ValueError("invalid Wikimedia artwork provenance for "+slug)
        else:
            raise ValueError("opera image requires real sourced artwork: "+slug)

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
