"""Unattended, evidence-grounded discovery of *new* operas.

Wikidata resolves exact title, opera type and composer. A verified concise
identity introduction is produced locally, without paid services or models.
Nothing is published without exact source identity, structured date/time
evidence and the subsequent canonical transaction.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,quote,urlsplit
from urllib.request import Request,urlopen

from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import CONFIG,OUTPUT as INDEX,validate_config,eligible
from scripts.publish_catalog_v2 import ROOT,REGISTRY,slugify,normalized

OUT=ROOT/"data"/"auto-work-intelligence.json"
HEALTH=ROOT/"data"/"auto-work-intelligence-health.json"
MAX_RESEARCH=3  # bounded authority lookups for unknown works per day
MAX_PREVERIFIED=16  # bounded authority checks for pre-sourced works
MAX_BYTES=300_000
UA="OperaAtlasResearch/0.1 (+https://github.com/jeckodevelopment/opera-atlas)"

def read_api(url:str,*,max_bytes:int=MAX_BYTES):
    target=urlsplit(url)
    if target.scheme!="https" or target.hostname not in ("www.wikidata.org","it.wikipedia.org"):
        raise ValueError("unapproved knowledge API")
    with urlopen(Request(url,headers={"User-Agent":UA,"Accept":"application/json"}),
                 timeout=12) as resp:
        if resp.status!=200 or resp.headers.get("Content-Type","").split(";")[0] not in (
                "application/json","application/json;charset=utf-8"):
            raise ValueError("invalid external knowledge response")
        raw=resp.read(max_bytes+1)
        if len(raw)>max_bytes:raise ValueError("external knowledge response too large")
    return json.loads(raw.decode("utf-8"))

def wikidata_url(action:str,**params)->str:
    return "https://www.wikidata.org/w/api.php?"+urlencode({
        "action":action,"format":"json",**params})

def claim_ids(entity:dict,property_id:str)->set[str]:
    result=set()
    for claim in entity.get("claims",{}).get(property_id,[]):
        value=claim.get("mainsnak",{}).get("datavalue",{}).get("value",{})
        if isinstance(value,dict) and isinstance(value.get("id"),str):
            result.add(value["id"])
    return result

# The official venue occasionally embeds conductor/production names in an
# opaque URL slug. Use exact keys, then independently verify composer and
# dated performances; never infer genre from a fuzzy filename match.
OFFICIAL_TITLE_ALIASES={
    ("donizetti-opera-2026","l-esule-di-roma"):"L\u0027esule di Roma",
    ("donizetti-opera-2026","alahor-in-granata"):"Alahor in Granata",
    ("donizetti-opera-2026","le-convenienze-ed-inconvenienze-teatrali"):"Le convenienze ed inconvenienze teatrali",
    ("fenice-opera-2026-27","normatebar"):"Norma",
    ("fenice-opera-2026-27","ilbarbieredisivigliapercacciolo"):"Il barbiere di Siviglia",
}

def official_title_hint(candidate:dict,evidence:dict|None=None)->str|None:
    key=candidate.get("source_key","")
    url=candidate.get("official_url","")
    if not isinstance(url,str):return None
    approved={row["key"]:row for row in validate_config(
        json.loads(CONFIG.read_text(encoding="utf-8")))
        if row["access_status"]=="approved"}
    source=approved.get(key)
    target=urlsplit(url)
    if (source is None or target.scheme!="https" or
        target.hostname!=urlsplit(source["official_url"]).hostname or
        target.port is not None or target.username or target.password or
        target.query or target.fragment):
        return None
    parts=target.path.rstrip("/").split("/")
    path=(parts[-2] if key=="donizetti-opera-2026" and
          re.fullmatch(r"20\d{2}-\d{2}-\d{2}",parts[-1])
          else parts[-1]).removesuffix(".html")
    if not re.fullmatch(r"[a-z0-9-]{3,80}",path) or not eligible(key,url):
        return None
    if key=="petruzzelli-opera-2027":
        # A URL can identify several operas or a ballet. Never turn its
        # descriptive slug into a Wikidata title. Only verified first-party
        # source rows can provide an authoritative query and composer.
        rows=[x for x in (evidence or {}).get("evidence",[])
              if x.get("candidate_id")==candidate.get("id")
              and x.get("source_key")==key
              and x.get("source_url")==url
              and x.get("status")=="needs_editorial_review"]
        if len(rows)!=1:return None
        titles={x.get("event_title") for x in rows[0].get("event_facts",[])
                if isinstance(x,dict)}
        composers={x.get("composer") for x in rows[0].get("event_facts",[])
                   if isinstance(x,dict)}
        if (len(titles)!=1 or len(composers)!=1
            or not all(isinstance(x,str) and x.strip() for x in titles|composers)):
            return None
        return next(iter(titles))
    if key=="bologna-comunale-opera-2027" and re.search(r"-20\\d{2}$",path):
        path=re.sub(r"-20\\d{2}$","",path)
    if path.endswith("-anteprima-under30"):return None
    return OFFICIAL_TITLE_ALIASES.get((key,path),path.replace("-"," "))

def resolve_identity(title_hint:str,*,composer_hint:str|None=None,fetch=read_api)->dict|None:
    query=fetch(wikidata_url("wbsearchentities",search=title_hint,language="it",
                            uselang="it",type="item",limit=8))
    matches=[x for x in query.get("search",[])
             if isinstance(x.get("id"),str) and isinstance(x.get("label"),str)
             and x["label"].strip() and
             slugify(x["label"])==slugify(title_hint)]
    if not matches:return None
    ids="|".join(sorted({x["id"] for x in matches}))
    batch=fetch(wikidata_url("wbgetentities",ids=ids,
                            props="claims|labels|sitelinks",languages="it|en"))
    accepted=[]
    for qid,entity in batch.get("entities",{}).items():
        labels=entity.get("labels",{})
        label=labels.get("it",labels.get("en",{})).get("value","")
        if not label or slugify(label)!=slugify(title_hint):continue
        # Wikidata currently prefers P7937 (form of creative work) for opera;
        # historic entities may still use P31. Never infer from title only.
        if "Q1344" not in (claim_ids(entity,"P7937") | claim_ids(entity,"P31")):continue
        composers=claim_ids(entity,"P86")
        wiki=entity.get("sitelinks",{}).get("itwiki",{}).get("title")
        if len(composers)!=1:continue
        # Italian Wikipedia is optional: structured Wikidata attribution is
        # sufficient for a verified, factual opera introduction.
        if not isinstance(wiki,str) or len(wiki)>150:wiki=None
        accepted.append((qid,label,next(iter(composers)),wiki))
    if not accepted:return None
    # Resolve all composer entities, not merely the first title hit. A title
    # with multiple composers (Rossini/Paisiello, Puccini/Leoncavallo) cannot
    # establish a unique work without independent official composer evidence.
    composer_ids=sorted({item[2] for item in accepted})
    people=fetch(wikidata_url("wbgetentities",ids="|".join(composer_ids),
                                 props="labels",languages="it|en")).get("entities",{})
    verified=[]
    for qid,title,composer_id,wiki_title in accepted:
        labels=people.get(composer_id,{}).get("labels",{})
        composer=labels.get("it",labels.get("en",{})).get("value")
        if not isinstance(composer,str) or not 3<=len(composer)<=100:continue
        if composer_hint and slugify(composer)!=slugify(composer_hint):continue
        verified.append((qid,title,composer,wiki_title))
    if len(verified)!=1:return None
    qid,title,composer,wiki_title=verified[0]
    return {"title":title,"composer":composer,"wikidata_id":qid,
            "title_candidate_count":len(accepted),
            "wikipedia_title":wiki_title,
            "authority_url":"https://www.wikidata.org/wiki/"+qid,
            "wikipedia_url":("https://it.wikipedia.org/wiki/"+
                            quote(wiki_title.replace(" ","_"),safe="()_-")
                            if wiki_title else None)}

def wiki_excerpt(identity:dict,*,fetch=read_api)->str|None:
    result=fetch("https://it.wikipedia.org/w/api.php?"+urlencode({
        "action":"query","format":"json","prop":"extracts",
        "explaintext":"1","titles":identity["wikipedia_title"]}))
    pages=result.get("query",{}).get("pages",{})
    matches=[x.get("extract","") for x in pages.values() if isinstance(x,dict)]
    if len(matches)!=1:return None
    extract=" ".join(matches[0].split())
    if not 140<=len(extract)<=12000:return None
    return extract[:6000]

def preverified_work_material() -> dict[str, dict]:
    """Already-sourced original synopses and histories, outside canonical works.

    This reusable path performs no LLM calls and does not relax the composer
    check: Wikidata and the official theatre page still establish identity.
    """
    from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
    synopses=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    histories=json.loads(HISTORY.read_text(encoding="utf-8"))
    if synopses.get("schema_version")!=1 or histories.get("schema_version")!=1:
        raise ValueError("invalid preverified material")
    result={}
    for slug,summary in synopses["synopses"].items():
        record=histories["works"].get(slug)
        if (isinstance(summary,str) and 45<=len(summary.strip())<=300
                and validate_history(record)):
            result[slug]={"synopsis":summary.strip(),"history":record}
    return result

def choose_candidates(candidates:dict,existing:dict,known_slugs:set[str],
                      *,today:date,evidence:dict|None=None)->list[dict]:
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
             if x["access_status"]=="approved"}
    done={x["candidate_id"] for x in existing.get("works",[])
          if isinstance(x.get("wikidata_id"),str) and isinstance(x.get("synopsis"),str)}
    options=[]
    for item in candidates.get("candidates",[]):
        if item.get("status")!="needs_review" or item.get("id") in done:continue
        source=sources.get(item.get("source_key"))
        if source is None:continue
        uri=item.get("official_url","")
        if not isinstance(uri,str) or urlsplit(uri).hostname!=urlsplit(source["official_url"]).hostname:
            continue
        hint=official_title_hint(item,evidence)
        if hint is None:continue
        options.append(item)
    options.sort(key=lambda x:x["id"])
    if not options:return []
    # Advance by one position per day. The previous stride of MAX_RESEARCH
    # could starve candidates permanently whenever the queue length was a
    # multiple of that budget (3, 6, 9, ...).
    # Verified source material may already exist for an uncatalogued
    # work. Check those candidates first; all others retain fair rotation.
    prepared=preverified_work_material()
    ready=[x for x in options if slugify(official_title_hint(x,evidence)) in prepared]
    other=[x for x in options if slugify(official_title_hint(x,evidence)) not in prepared]
    def rotate(items):
        if not items:return []
        offset=today.toordinal()%len(items)
        return items[offset:]+items[:offset]
    # Bound API reads; public authority checks do not require model tokens.
    return rotate(ready)[:MAX_PREVERIFIED]+rotate(other)[:MAX_RESEARCH]

def identity_introduction(identity:dict)->str:
    """Original, factual two-sentence card from verified authority fields.

    Never invent a plot, setting, characters, premiere, or artistic interpretation.
    """
    title=identity["title"].strip()
    composer=identity["composer"].strip()
    if not 2<=len(title)<=180 or not 3<=len(composer)<=100:
        raise ValueError("invalid authority identity")
    return (f"«{title}» è un'opera di {composer}. "
            "Consulta le rappresentazioni verificate in programma nei teatri italiani.")

def research(candidates:dict,existing:dict,known_slugs:set[str],*,
             today:date,resolve=resolve_identity,extract=wiki_excerpt,
             evidence:dict|None=None,
             generate=None,generate_history=None,api_key:str="",
             allow_authority:bool=False,prepared:dict|None=None):
    existing_works={x["candidate_id"]:x.copy() for x in existing.get("works",[])}
    prepared=preverified_work_material() if prepared is None else prepared
    statuses=[]
    options=choose_candidates(candidates,existing,known_slugs,today=today,
                              evidence=evidence)
    # Move ready-made, sourced work cards to the front while retaining the
    # normal fair rotation for all remaining unseen operas.
    options.sort(key=lambda x:slugify(official_title_hint(x,evidence)) not in prepared)
    for item in options:
        cid=item["id"]
        slug=slugify(official_title_hint(item,evidence))
        # A prewritten title-keyed synopsis is not safe for a new homonym.
        # Resolve its own facts instead of copying the established work card.
        material=prepared.get(slug) if slug not in known_slugs else None
        detail=[x for x in (evidence or {}).get("evidence",[])
                if x.get("candidate_id")==cid
                and x.get("source_key")==item["source_key"]
                and x.get("source_url")==item["official_url"]
                and x.get("status")=="needs_editorial_review"]
        composers={normalized(x.get("composer","")):x.get("composer")
                   for d in detail for x in d.get("event_facts",[])
                   if isinstance(x,dict) and isinstance(x.get("composer"),str)
                   and x["composer"].strip()}
        # Multiple contradictory composer observations cannot be resolved.
        if len(composers)>1:
            statuses.append({"candidate_id":cid,"status":"automatic_retry",
                             "reason":"conflicting_official_composers"})
            continue
        composer_hint=next(iter(composers.values())) if len(composers)==1 else None
        try:
            identity=(resolve(official_title_hint(item,evidence),composer_hint=composer_hint)
                      if composer_hint else resolve(official_title_hint(item,evidence)))
            if identity is None:raise ValueError("authority_not_unique")
            # Preverified cards are keyed only by title. For multiple known
            # compositions, even an independently resolved composer must use
            # new composition-specific history and synopsis evidence.
            if identity.get("title_candidate_count",1)>1:
                material=None
            # The ordinary publishing path needs no model subscription.
            # A preverified summary/history is safe only when we have official
            # composer evidence matching the authority and no competing title.
            # Otherwise use a factual identity-only introduction, not a
            # made-up synopsis. Historical facts remain optional until sourced.
            if (material is not None and slugify(identity["title"])==slug
                    and identity.get("title_candidate_count",1)==1
                    and (not composer_hint or
                         slugify(composer_hint)==slugify(identity["composer"]))):
                summary=material["synopsis"]
                history=material["history"]
            else:
                summary=identity_introduction(identity)
                history=None
            existing_works[cid]={
                "candidate_id":cid,"source_key":item["source_key"],
                "source_url":item["official_url"],
                "title":identity["title"],"composer":identity["composer"],
                "synopsis":summary,"history":history,"wikidata_id":identity["wikidata_id"],
                "authority_url":identity["authority_url"],
                "wikipedia_url":identity["wikipedia_url"],
                "verified_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
            statuses.append({"candidate_id":cid,"status":"enriched"})
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,KeyError,
                json.JSONDecodeError) as exc:
            statuses.append({"candidate_id":cid,"status":"automatic_retry",
                             "reason":type(exc).__name__})
    return {"schema_version":1,"works":sorted(existing_works.values(),
                                             key=lambda x:x["candidate_id"])},statuses

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--allow-network",action="store_true")
    args=parser.parse_args()
    known=json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates=json.loads(INDEX.read_text(encoding="utf-8"))
    previous=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {
        "schema_version":1,"works":[]}
    from scripts.collect_candidate_details import OUTPUT as DETAIL_EVIDENCE
    evidence=json.loads(DETAIL_EVIDENCE.read_text(encoding="utf-8")) if DETAIL_EVIDENCE.exists() else {"evidence":[]}
    result,statuses=research(candidates,previous,{x["slug"] for x in known["works"].values()},
                             today=date.today(),evidence=evidence,
                             allow_authority=args.allow_network)
    _write_atomic(OUT,result)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":datetime.now(timezone.utc).isoformat(
        timespec="seconds"),"outcomes":statuses})
    print(json.dumps({"work_intelligence":len(result["works"]),"outcomes":statuses}))
if __name__=="__main__":
    main()
