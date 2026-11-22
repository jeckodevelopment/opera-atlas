"""Exact municipal image provenance for a first-party opera production.

The Comune supplies an image of the same Modena staging, but its published
clock conflicts with the theatre's ticketed showtime. Treat it as artwork
provenance ONLY. Never infer or overwrite a recita from this record.
"""
from __future__ import annotations
from urllib.parse import urlsplit

SOURCE="https://www.teatrocomunalemodena.it/spettacolo/daniele-furlati-i-salvatori-della-mezzanotte/"
PROVENANCE=("https://www.comune.modena.it/vivere-modena/eventi/2026/"
            "stagione-opera-2026-2027/i-salvatori-della-mezzanotte")
IMAGE=PROVENANCE+"/@@images/image-890-b23142f8fa819a2626774dd548fd87e1.jpeg"
TITLE="I salvatori della mezzanotte"
COMPOSER="Daniele Furlati"
KIND="official_municipal_production_image"

def verified_municipal_art(*,source_url:str,title:str,composer:str)->dict|None:
    if (source_url!=SOURCE or title!=TITLE or composer!=COMPOSER):
        return None
    for link in (SOURCE,PROVENANCE,IMAGE):
        parsed=urlsplit(link)
        if (parsed.scheme!="https" or parsed.port is not None or
                parsed.query or parsed.fragment or parsed.username or parsed.password):
            return None
    if (urlsplit(PROVENANCE).hostname!="www.comune.modena.it"
            or urlsplit(IMAGE).hostname!="www.comune.modena.it"
            or not urlsplit(IMAGE).path.startswith(
                urlsplit(PROVENANCE).path+"/@@images/")
            or not urlsplit(IMAGE).path.lower().endswith(".jpeg")):
        return None
    return {
        "image_url":IMAGE,
        "source_url":SOURCE,
        "provenance_url":PROVENANCE,
        "credit":"Fotografia dello spettacolo dalla scheda ufficiale del Comune di Modena",
        "alt":"Allestimento di I salvatori della mezzanotte al Teatro Comunale di Modena",
        "kind":KIND,
    }

def is_verified_municipal_art(record:dict,*,title:str,composer:str)->bool:
    if not isinstance(record,dict) or record.get("kind")!=KIND:
        return False
    expected=verified_municipal_art(
        source_url=record.get("source_url",""),title=title,composer=composer)
    return expected is not None and record==expected
