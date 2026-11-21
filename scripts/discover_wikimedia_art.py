"""Find authentic historical opera artwork on Wikimedia Commons without paid APIs.

Discovery is deliberately conservative: licence, stable Commons file identity,
opera title, composer surname and archival context must all independently match.
No ambiguous candidate is ever promoted as an illustration.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import time
import unicodedata
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode,urlsplit,quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.daily_ingest import _write_atomic

DETAILS=ROOT/"data"/"candidate-detail-evidence.json"
INTELLIGENCE=ROOT/"data"/"auto-work-intelligence.json"
OUTPUT=ROOT/"data"/"candidate-wikimedia-art.json"
HEALTH=ROOT/"data"/"candidate-wikimedia-art-health.json"
API="https://commons.wikimedia.org/w/api.php"
MAX_CANDIDATES=12
ARCHIVE_WORDS=frozenset({"poster","manifesto","locandina","libretto","librettos",
                          "titlepage","title","frontispiece","frontespizio","score",
                          "spartito","original","historical","historic","affiche"})
ALLOWED_LICENCES=frozenset({"cc0","cc by","cc by-sa","public domain","pd-old",
                             "pd-us","pd-art","pd-1923","pd-italy"})
BAD_WORDS=frozenset({"logo","portrait","headshot","conductor","interview",
                      "press conference","modern photo","performance photo"})

def norm(value):
    raw=unicodedata.normalize("NFKD",html.unescape(re.sub("<[^>]+>"," ",str(value))))
    return " ".join(re.findall(r"[a-z0-9]+","".join(c for c in raw.lower()
                           if not unicodedata.combining(c))))

def clean(value):
    return html.unescape(re.sub("<[^>]+>"," ",str(value))).strip()

def api_read(url):
    request=Request(url,headers={"User-Agent":"OperaAtlas/1.0 (public historical opera art research; contact via repository)"})
    with urlopen(request,timeout=15) as response:
        if response.status!=200:raise ValueError("Commons API returned an error")
        return json.loads(response.read(1_500_000))

def commons_url(title):
    if not isinstance(title,str) or not title.startswith("File:") or len(title)>240:
        return None
    filename=title[5:]
    if "/" in filename or "\\" in filename or not re.search(r"\.(?:jpe?g|png|webp)$",filename,re.I):
        return None
    return ("https://commons.wikimedia.org/wiki/File:"+
            quote(filename.replace(" ","_"),safe="()_'-"))

def licence(metadata):
    short=norm(metadata.get("LicenseShortName",{}).get("value",""))
    restrictions=norm(metadata.get("Restrictions",{}).get("value",""))
    if restrictions and restrictions!="none":return None
    if (short.startswith("cc by sa") or short=="cc by sa"):return "CC BY-SA"
    if short.startswith("cc by"):return "CC BY"
    if short in {"cc0","cc zero","cc0 1 0"}:return "CC0"
    if short.startswith(("public domain","pd old","pd us","pd art","pd 1923","pd italy")):
        return "Public domain (Commons declaration)"
    return None

def historical_candidate(page,*,title,composer):
    file_url=commons_url(page.get("title"))
    if not file_url:return None
    info=(page.get("imageinfo") or [{}])[0]
    meta=info.get("extmetadata") or {}
    license_label=licence(meta)
    if not license_label:return None
    file_name=page["title"][5:]
    description=clean(meta.get("ImageDescription",{}).get("value",""))
    object_name=clean(meta.get("ObjectName",{}).get("value",""))
    combined=norm(file_name+" "+description+" "+object_name)
    title_words=[w for w in norm(title).split() if w not in {"la","il","le","lo","di","de","in","and","the","l"}]
    surname=norm(composer).split()[-1:]  # explicit composer evidence prevents homonyms
    if not title_words or not surname or not all(x in combined.split() for x in title_words):
        return None
    if surname[0] not in combined.split():return None
    if any(word in combined for word in BAD_WORDS):return None
    archival=any(word in combined.split() for word in ARCHIVE_WORDS)
    archival=archival or bool(re.search(r"\b(?:1[5-9]\d\d|19[0-4]\d)\b",combined))
    if not archival:return None
    credit=clean(meta.get("Artist",{}).get("value",""))[:220] or "Autore non indicato, Wikimedia Commons"
    if len(credit)<3:return None
    thumb=info.get("thumburl","")
    if (not isinstance(thumb,str) or
            urlsplit(thumb).scheme!="https" or
            urlsplit(thumb).hostname not in ("upload.wikimedia.org","commons.wikimedia.org")):
        # Commons stable redirect is still valid if thumbnail metadata is absent.
        image=file_url.replace("/wiki/File:","/wiki/Special:Redirect/file/")+"?width=720"
    else:
        image=file_url.replace("/wiki/File:","/wiki/Special:Redirect/file/")+"?width=720"
    return {"kind":"archival_work_image","file":file_name,
            "source_url":file_url,"image_url":image,
            "alt":f"Documento storico relativo a {title} di {composer}; non rappresenta la produzione attuale",
            "credit":credit,"license":license_label,
            "composer":composer,"title":title}

def find_historical_art(title,composer,*,fetch=api_read,pause=lambda n:None):
    if not isinstance(title,str) or not isinstance(composer,str):return None
    surname=norm(composer).split()
    if not surname:return None
    for term in ("poster","libretto","titlepage"):
        query=" ".join([title,surname[-1],term])
        params=urlencode({"action":"query","generator":"search","gsrsearch":query,
                          "gsrnamespace":6,"gsrlimit":15,"prop":"imageinfo",
                          "iiprop":"url|extmetadata","iiurlwidth":720,"format":"json",
                          "formatversion":2})
        response=fetch(API+"?"+params)
        pages=response.get("query",{}).get("pages",[])
        accepted=[x for p in pages if
                  (x:=historical_candidate(p,title=title,composer=composer))]
        # Multiple different plausible historic images are not necessarily
        # the same composition: refuse a non-deterministic pick.
        accepted=sorted(accepted,key=lambda p:p["source_url"])
        if accepted:return accepted[0]
        pause(0.7)
    return None

def collect(works,details,known,*,fetch=api_read,pause=lambda n:None,max_candidates=MAX_CANDIDATES):
    indexed={e.get("candidate_id"):e for e in details.get("evidence",[])
             if e.get("status")=="needs_editorial_review"}
    existing={(norm(w["title"]),norm(w["composer"])) for w in known["works"].values()}
    results=[];outcomes=[]
    for w in sorted(works.get("works",[]),key=lambda x:x.get("candidate_id","")):
        if len(outcomes)>=max_candidates:break
        cid=w.get("candidate_id")
        detail=indexed.get(cid)
        pair=(norm(w.get("title","")),norm(w.get("composer","")))
        if not detail or not all(pair) or pair in existing:continue
        rows=detail.get("event_facts",[])
        if not rows or any((norm(x.get("event_title","")),norm(x.get("composer","")))!=pair
                           for x in rows if isinstance(x,dict)):
            continue
        try:
            art=find_historical_art(w["title"],w["composer"],fetch=fetch,pause=pause)
            outcomes.append({"candidate_id":cid,"status":"verified" if art else "no_reliable_archive"})
            if art:results.append({"candidate_id":cid,"source_url":detail.get("source_url"),
                                   "poster_evidence":art})
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,KeyError,
                TypeError,json.JSONDecodeError):
            outcomes.append({"candidate_id":cid,"status":"retry"})
    return {"schema_version":1,"art":results},outcomes

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    opts=parser.parse_args()
    works=json.loads(INTELLIGENCE.read_text(encoding="utf-8"))
    details=json.loads(DETAILS.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    data,status=collect(works,details,registry,
                        fetch=api_read if opts.allow_network else
                        (lambda url:{"query":{"pages":[]}}),
                        pause=time.sleep if opts.allow_network else (lambda n:None))
    _write_atomic(OUTPUT,data)
    _write_atomic(HEALTH,{"schema_version":1,
        "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "outcomes":status})
    print(json.dumps({"archive_images":len(data["art"]),"scanned":len(status)}))

if __name__=="__main__":main()
