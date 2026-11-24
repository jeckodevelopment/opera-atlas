"""Exact, separately verified city-published photography of a named opera.

This is not a historical poster or a made-up cover. Only the exact
municipal event page and its photograph can represent this composition.
The image is linked remotely and not copied or relicensed.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"verified-civic-work-images.json"
SOURCE="https://www.teatrocomunalemodena.it/spettacolo/daniele-furlati-i-salvatori-della-mezzanotte/"
PROVENANCE=("https://www.comune.modena.it/vivere-modena/eventi/2026/"
            "stagione-opera-2026-2027/i-salvatori-della-mezzanotte")
IMAGE=(PROVENANCE+"/@@images/image-890-b23142f8fa819a2626774dd548fd87e1.jpeg")
TITLE="I salvatori della mezzanotte"
COMPOSER="Daniele Furlati"
KIND="official_civic_production_image"
PISA_SOURCE="https://teatrodipisa.it/the-turn-of-the-screw-a-50-anni-dalla-morte-di-britten-per-la-prima-volta-al-teatro-verdi/"
PISA_PROVENANCE="https://www.comune.pisa.it/Novita/Notizie/Turn-of-the-Screw-il-capolavoro-di-Britten-per-la-prima-volta-sul-palco-del-Verdi"
PISA_IMAGE="https://s3-eu-west-1.amazonaws.com/static.opencity.opencontent.it/var/pisa/storage/images/media/images/teatro-verdi-davide-livermore/662059-1-ita-IT/Teatro-verdi-Davide-Livermore_reference.jpg"
PISA_TITLE="The Turn of the Screw"
PISA_COMPOSER="Benjamin Britten"
FIELDS=("source_url","provenance_url","image_url","credit","alt","kind")


def verified_civic_image(*,source_url:str,title:str,composer:str)->dict|None:
    approved={
        (SOURCE,TITLE.casefold(),COMPOSER.casefold()):
            (PROVENANCE,IMAGE,"www.teatrocomunalemodena.it",
             "www.comune.modena.it","www.comune.modena.it"),
        (PISA_SOURCE,PISA_TITLE.casefold(),PISA_COMPOSER.casefold()):
            (PISA_PROVENANCE,PISA_IMAGE,"teatrodipisa.it",
             "www.comune.pisa.it","s3-eu-west-1.amazonaws.com"),
    }
    expected=approved.get((source_url,title.casefold(),composer.casefold()))
    if expected is None:
        return None
    provenance,image,source_host,provenance_host,image_host=expected
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("images"),list):
        raise ValueError("invalid reviewed municipal image registry")
    rows=[row for row in doc["images"] if (
        row.get("source_url")==source_url
        and row.get("title","").casefold()==title.casefold()
        and row.get("composer","").casefold()==composer.casefold())]
    if len(rows)!=1:
        return None
    row=rows[0]
    if (row.get("provenance_url")!=provenance
        or row.get("image_url")!=image or row.get("kind")!=KIND
        or not isinstance(row.get("credit"),str) or not row["credit"].strip()
        or not isinstance(row.get("alt"),str) or not row["alt"].strip()):
        return None
    for key,host in (("source_url",source_host),
                     ("provenance_url",provenance_host),
                     ("image_url",image_host)):
        uri=urlsplit(row[key])
        if (uri.scheme!="https" or uri.hostname!=host
            or uri.port is not None or uri.username or uri.password
            or uri.query or uri.fragment):
            return None
    return {k:row[k] for k in FIELDS}


def is_verified_civic_image(record:dict,*,title:str,composer:str)->bool:
    if not isinstance(record,dict) or record.get("kind")!=KIND:
        return False
    proof=verified_civic_image(source_url=record.get("source_url",""),
                               title=title,composer=composer)
    return proof is not None and all(record.get(k)==v for k,v in proof.items())
