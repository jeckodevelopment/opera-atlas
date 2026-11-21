"""Verified first-party artwork from an official co-producing opera house.

A source-specific exception is allowed only when the production, composer and
the co-producer's published artwork are independently attributable to the
same opera. Never infer artistic identity from a picture or a bare slug.
Images are linked remotely; no file or publishing rights are transferred.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"verified-coproduction-art.json"
FIELDS=("image_url","source_url","coproduction_page_url","credit","alt","kind")
EXPECTED={
    "image_url":"https://opera.krakow.pl/media/spectacle_image/bona-finalny_detail_poster.jpg",
    "coproduction_page_url":"https://opera.krakow.pl/en/spectacles/bona-sforza-1",
    "source_url":"https://www.fondazionepetruzzelli.it/eventi/bona-sforza-krautze-14-20-settembre/",
    "title":"Bona Sforza",
    "composer":"Zygmunt Krauze",
}

def verified_coproduction_image(*,source_url:str,title:str,composer:str)->dict|None:
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("images"),list):
        raise ValueError("invalid official co-production image registry")
    rows=[x for x in doc["images"] if x.get("source_url")==source_url
          and x.get("title","").casefold()==title.casefold()
          and x.get("composer","").casefold()==composer.casefold()]
    if len(rows)>1:raise ValueError("ambiguous co-production artwork")
    if not rows:return None
    row=rows[0]
    # Strict independently corroborated cross-institution entry; never
    # accept a URL redirect, swapped title, alternate composer or untrusted
    # image host. Additional productions need a separately verified policy.
    if any(row.get(k)!=value for k,value in EXPECTED.items()):
        return None
    for key in ("image_url","source_url","coproduction_page_url"):
        url=urlsplit(row[key])
        if (url.scheme!="https" or not url.hostname or url.username
            or url.password or url.port is not None or url.query or url.fragment):
            return None
    if row.get("kind")!="official_coproduction_poster":
        return None
    if not all(isinstance(row.get(k),str) and row[k].strip()
               for k in ("credit","alt")):
        return None
    return {k:row[k] for k in FIELDS}

def is_verified_coproduction_poster(poster:dict,*,title:str,composer:str)->bool:
    if not isinstance(poster,dict) or poster.get("kind")!="official_coproduction_poster":
        return False
    verified=verified_coproduction_image(
        source_url=poster.get("source_url",""),title=title,composer=composer)
    return verified is not None and all(poster.get(k)==v for k,v in verified.items())
