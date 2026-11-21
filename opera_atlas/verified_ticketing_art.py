"""Curated third-party ticketing artwork, strictly bound to an official opera.

Unlike automatic OG extraction, these entries require an exact official source,
exact title and composer, and a matching, independently verified ticketing
event landing page. The file is linked remotely, not copied or relicensed.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"verified-ticketing-art.json"
HOST="www.ticketone.it"
PREFIX="/obj/media/IT-eventim/teaser/evo/artwork/"

def verified_ticketing_image(*,source_url:str,title:str,composer:str)->dict|None:
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("images"),list):
        raise ValueError("invalid curated ticketing artwork registry")
    matches=[x for x in doc["images"]
             if x.get("source_url")==source_url and x.get("title")==title
             and x.get("composer")==composer]
    if len(matches)>1:
        raise ValueError("ambiguous curated event artwork")
    if not matches:return None
    row=matches[0]
    art=urlsplit(row.get("image_url",""))
    page=urlsplit(row.get("ticketing_page_url",""))
    official=urlsplit(source_url)
    # Don't ever accept a naked arbitrary image or a mistaken opera title.
    # The source's ticketing event landing page explicitly identifies the
    # production and dates; this is hand-reviewed evidence, not scraping.
    if (official.scheme!="https" or official.hostname is None
        or official.query or official.fragment
        or art.scheme!="https" or art.hostname!=HOST
        or art.query or art.fragment or art.username or art.password
        or not art.path.startswith(PREFIX)
        or not art.path.lower().endswith((".jpg",".jpeg",".png",".webp"))
        or page.scheme!="https" or page.hostname!=HOST
        or not page.path.startswith("/artist/") or page.query or page.fragment
        or row.get("kind")!="ticketing_event_artwork"
        or not row.get("credit") or not row.get("alt")
        or "code-unknown" not in page.path.lower()
        or "code-unknow" not in art.path.lower()):
        return None
    return {key:row[key] for key in
            ("image_url","source_url","ticketing_page_url","credit","alt","kind")}

def is_verified_ticketing_poster(poster:dict,*,title:str,composer:str)->bool:
    if not isinstance(poster,dict) or poster.get("kind")!="ticketing_event_artwork":
        return False
    validated=verified_ticketing_image(source_url=poster.get("source_url",""),
                                    title=title,composer=composer)
    return validated is not None and all(
        poster.get(key)==value for key,value in validated.items())
