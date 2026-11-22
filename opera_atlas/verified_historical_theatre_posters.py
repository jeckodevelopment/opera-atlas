"""Bind a historical, theatre-attributed Candide flyer to the exact composition.

Emerson Colonial Theatre identifies the 1956 promotional image as an
archival NYPL flyer of Candide. It is NOT an image of the 2027 Cagliari
production and is only hotlinked from the venue's image service.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"verified-historical-theatre-posters.json"
SOURCE="https://www.liricocagliari.it/evento/candide/"
PROVENANCE="https://www.emersoncolonialtheatre.com/about-us/emerson-colonial-theatre-blog/candide/"
IMAGE="https://res.cloudinary.com/dwzhqvxaz/image/upload/q_auto/f_auto/umbraco-prod/ogsfnsf4/candide-1.jpg"
TITLE="Candide"
COMPOSER="Leonard Bernstein"
KIND="verified_historical_theatre_poster"
FIELDS=("source_url","provenance_url","image_url","credit","alt","kind")


def verified_theatre_poster(*,source_url:str,title:str,composer:str)->dict|None:
    if (source_url!=SOURCE or title.casefold()!=TITLE.casefold()
        or composer.casefold()!=COMPOSER.casefold()):
        return None
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("images"),list):
        raise ValueError("invalid reviewed historical theatre art registry")
    rows=[row for row in doc["images"] if (
        row.get("source_url")==source_url
        and isinstance(row.get("title"),str)
        and row["title"].casefold()==title.casefold()
        and isinstance(row.get("composer"),str)
        and row["composer"].casefold()==composer.casefold())]
    if len(rows)!=1:
        return None
    row=rows[0]
    if (row.get("provenance_url")!=PROVENANCE
        or row.get("image_url")!=IMAGE or row.get("kind")!=KIND
        or not isinstance(row.get("credit"),str) or not row["credit"].strip()
        or not isinstance(row.get("alt"),str) or not row["alt"].strip()):
        return None
    for key,host in (("source_url","www.liricocagliari.it"),
                     ("provenance_url","www.emersoncolonialtheatre.com"),
                     ("image_url","res.cloudinary.com")):
        uri=urlsplit(row[key])
        if (uri.scheme!="https" or uri.hostname!=host
            or uri.port is not None or uri.username or uri.password
            or uri.fragment):
            return None
        if key!="image_url" and uri.query:
            return None
    if not row["image_url"].endswith("/candide-1.jpg"):
        return None
    return {k:row[k] for k in FIELDS}


def is_verified_theatre_poster(record:dict,*,title:str,composer:str)->bool:
    if not isinstance(record,dict) or record.get("kind")!=KIND:
        return False
    proof=verified_theatre_poster(source_url=record.get("source_url",""),
                                 title=title,composer=composer)
    return proof is not None and all(record.get(k)==v for k,v in proof.items())
