"""Source-bound original artwork from an independently verified co-producer.

The image is embedded remotely, not copied or relicensed. Only an explicit
record for the same exact source production, title and composer can be used;
unrelated current staging photos or similarly named historical works cannot.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"verified-coproduction-posters.json"
APPROVED_PROVENANCE={
    ("https://www.fondazionepetruzzelli.it/eventi/bona-sforza-krautze-14-20-settembre/",
     "Bona Sforza","Zygmunt Krauze"):(
        "https://opera.krakow.pl/spektakle/bona-sforza",
        "https://opera.krakow.pl/media/gallery_image/12_d90d25d1097e683c30e5f2da8f9d71ee.jpg")
}

def verified_coproduction_poster(*,source_url:str,title:str,composer:str)->dict|None:
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("posters"),list):
        raise ValueError("invalid verified co-production poster registry")
    matches=[x for x in doc["posters"]
             if (x.get("source_url"),x.get("title"),x.get("composer"))
                ==(source_url,title,composer)]
    if len(matches)>1:raise ValueError("ambiguous co-production poster")
    if not matches:return None
    row=matches[0]
    expected=APPROVED_PROVENANCE.get((source_url,title,composer))
    if not expected or (row.get("provenance_url"),row.get("image_url"))!=expected:
        return None
    for key in ("image_url","source_url","provenance_url"):
        url=urlsplit(row[key])
        if (url.scheme!="https" or not url.hostname or url.port is not None
            or url.username or url.password or url.query or url.fragment):
            return None
    image=urlsplit(row["image_url"])
    if (image.hostname!="opera.krakow.pl"
            or not image.path.startswith("/media/gallery_image/")
            or not image.path.endswith((".jpg",".png",".webp"))
            or row.get("kind")!="official_coproduction_poster"
            or not row.get("credit") or not row.get("alt")):
        return None
    return {k:row[k] for k in (
        "image_url","source_url","provenance_url","credit","alt","kind")}

def is_verified_coproduction_poster(poster:dict,*,title:str,composer:str)->bool:
    if not isinstance(poster,dict) or poster.get("kind")!="official_coproduction_poster":
        return False
    record=verified_coproduction_poster(source_url=poster.get("source_url",""),
                                         title=title,composer=composer)
    return record is not None and all(poster.get(k)==v for k,v in record.items())
