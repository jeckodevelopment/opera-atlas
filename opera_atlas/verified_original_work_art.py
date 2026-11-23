"""First-party, original *work* artwork verified across exact seasonal pages.

A reused illustration must be of the same composition: independently
verified first-party older performance page, explicit same title/composer and
unchanged official artwork. It is a linked asset, never copied or relicensed.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"verified-original-work-art.json"
APPROVED={
 ("https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/",
  "Piccolo Orso e la montagna di ghiaccio","Giovanni Sollima"):(
  "https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/",
  "https://teatroregioparma.it/wp-content/uploads/2026/05/TRP-26-BANNER-ALPHA-REGIO-YOUNG-1080x1080-PICCOLO-ORSO.png"),
 ("https://www.provincia.le.it/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/",
  "Le avventure di Pinocchio","Antonio Cericola"):(
  "https://www.provincia.le.it/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/",
  "https://www.provincia.le.it/wp-content/uploads/2026/11/Locandina-PInocchio-240x300.png"),
 ("https://www.teatromassimobellini.it/eventi/il-quinto-moschettiere-2/",
  "Il quinto moschettiere","Matteo Musumeci"):(
  "https://www.teatromassimobellini.it/eventi/il-quinto-moschettiere/",
  "https://www.teatromassimobellini.it/media/2025/10/il-quinto-moschettiere.png"),
 ("https://www.teatromassimobellini.it/eventi/le-nozze-dellorso/",
  "Le nozze dell’orso","Joe Schittino"):(
  "https://www.teatromassimobellini.it/eventi/le-nozze-dellorso/",
  "https://www.teatromassimobellini.it/media/2026/11/PHOTO-2026-Orso.jpg"),
 ("https://www.teatroverdi-trieste.com/it/spettacoli/jeanne-darc-au-bucher-jeanne-dark/",
  "Jeanne Dark","Fabio Vacchi"):(
  "https://www.maggiofiorentino.com/events/jeanne-dark-5",
  "https://www.maggiofiorentino.com/uploads/JEANNE_DARK_70x100_INTERNO_ok_5b07c76e9f.jpg"),
 ("https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/ghost-cafe/",
  "Ghost Cafè","Carlo Galante"):(
  "https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/ghost-cafe/",
  "https://www.lugliomusicale.it/public/828w/260617-lug-manifesti-generale-17.jpg"),
 ("https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/fuori-fuoco/",
  "Fuori Fuoco","Diana Buscemi"):(
  "https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/fuori-fuoco/",
  "https://www.lugliomusicale.it/public/360w/260617-lug-manifesti-generale-19.jpg"),
 ("https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/magic-words-circus/",
  "Magic Words Circus","Orazio Sciortino"):(
  "https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/magic-words-circus/",
  "https://www.lugliomusicale.it/public/360w/260617-lug-manifesti-generale-16.jpg"),
 ("https://www.festivaldellavalleditria.it/spettacolo/il-schiavo-di-sua-moglie/2026-07-24",
  "Il schiavo di sua moglie","Francesco Provenzale"):(
  "https://www.festivaldellavalleditria.it/spettacolo/il-schiavo-di-sua-moglie/2026-07-24",
  "https://www.festivaldellavalleditria.it/wp-content/uploads/2024/02/16.jpg"), 
 ("https://www.festivaldellavalleditria.it/spettacolo/pulcinella-la-favola-di-orfeo/2026-07-14",
  "La favola di Orfeo","Alfredo Casella"):(
  "https://www.festivaldellavalleditria.it/spettacolo/pulcinella-la-favola-di-orfeo/2026-07-14",
  "https://www.festivaldellavalleditria.it/wp-content/uploads/2026/03/15.png"),
}
FIELDS=("image_url","source_url","original_source_url","credit","alt","kind")

def verified_original_art(*,source_url:str,title:str,composer:str)->dict|None:
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("art"),list):
        raise ValueError("invalid verified original work art registry")
    rows=[x for x in doc["art"] if x.get("source_url")==source_url and
          isinstance(x.get("title"),str) and isinstance(x.get("composer"),str)
          and x["title"].casefold()==title.casefold()
          and x["composer"].casefold()==composer.casefold()]
    if len(rows)>1:raise ValueError("ambiguous first-party original work artwork")
    if not rows:return None
    row=rows[0]
    expected=next((proof for (url,work,credit),proof in APPROVED.items()
                   if url==source_url and work.casefold()==title.casefold()
                   and credit.casefold()==composer.casefold()),None)
    if not expected or (row.get("original_source_url"),row.get("image_url"))!=expected:
        return None
    allowed_origins={
        "source_url":urlsplit(source_url).hostname,
        "original_source_url":urlsplit(expected[0]).hostname,
        "image_url":urlsplit(expected[1]).hostname}
    for field,hostname in allowed_origins.items():
        uri=urlsplit(row[field])
        if (uri.scheme!="https" or uri.hostname!=hostname
            or uri.port is not None or uri.query or uri.fragment or uri.username
            or uri.password):
            return None
    if (row.get("kind")!="official_original_work_artwork"
        or not all(isinstance(row.get(k),str) and row[k].strip()
                   for k in ("credit","alt"))):
        return None
    return {k:row[k] for k in FIELDS}

def is_verified_original_art(record:dict,*,title:str,composer:str)->bool:
    if not isinstance(record,dict) or record.get("kind")!="official_original_work_artwork":
        return False
    proof=verified_original_art(source_url=record.get("source_url",""),
                                title=title,composer=composer)
    return proof is not None and all(record.get(k)==v for k,v in proof.items())
