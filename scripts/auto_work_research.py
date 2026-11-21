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
MAX_RESEARCH=12  # bounded lookups for unknown works per refresh
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
    if key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027") and re.search(r"-20\\d{2}$",path):
        path=re.sub(r"-20\\d{2}$","",path)
    if path.endswith("-anteprima-under30"):return None
    # All adapters deliver the same immutable candidate/source pairing.
    # An exact, fully structured official detail outranks the URL slug,
    # including venue, show date/time and unambiguous composer attribution.
    # which can carry dates, composer names, ballet labels or generic words.
    if evidence is not None:
        matching=[row for row in evidence.get("evidence",[])
                  if row.get("candidate_id")==candidate.get("id")
                  and row.get("source_key")==key
                  and row.get("source_url")==url
                  and row.get("status")=="needs_editorial_review"]
        if len(matching)==1:
            rows=matching[0].get("event_facts",[])
            if isinstance(rows,list) and rows and all(
                    isinstance(r,dict) and
                    isinstance(r.get("event_title"),str) and
                    isinstance(r.get("composer"),str) and
                    isinstance(r.get("venue"),str) and
                    isinstance(r.get("date"),str) and
                    isinstance(r.get("starts_at"),str) and
                    r["event_title"].strip() and r["composer"].strip() and
                    r["venue"].strip() for r in rows):
                identities={(normalized(r["event_title"]),
                             normalized(r["composer"])) for r in rows}
                names={r["event_title"].strip() for r in rows}
                if len(identities)==1 and len(names)==1:
                    return next(iter(names))
            # Never fall back to URL text for an ambiguous evidence record.
            return None
    return OFFICIAL_TITLE_ALIASES.get((key,path),path.replace("-"," "))

def resolve_identity(title_hint:str,*,composer_hint:str|None=None,fetch=read_api)->dict|None:
    query=fetch(wikidata_url("wbsearchentities",search=title_hint,language="it",
                            uselang="it",type="item",limit=8))
    def exact_matches(data):
        return [x for x in data.get("search",[])
                if isinstance(x,dict) and isinstance(x.get("id"),str)
                and ((isinstance(x.get("label"),str) and x["label"].strip()
                      and slugify(x["label"])==slugify(title_hint))
                     or (isinstance(x.get("match"),dict)
                         and isinstance(x["match"].get("text"),str)
                         and x["match"]["text"].strip()
                         and slugify(x["match"]["text"])==slugify(title_hint)))]
    matches=exact_matches(query)
    # Wikidata's Italian search sometimes gives translated labels while the
    # official theatre prints an English, German or French work title. Check
    # its English index only when the Italian index has no exact match.
    if not matches:
        matches=exact_matches(fetch(wikidata_url(
            "wbsearchentities",search=title_hint,language="en",
            uselang="en",type="item",limit=8)))
    if not matches:return None
    ids="|".join(sorted({x["id"] for x in matches}))
    batch=fetch(wikidata_url("wbgetentities",ids=ids,
                            props="claims|labels|aliases|sitelinks",languages="it|en"))
    accepted=[]
    for qid,entity in batch.get("entities",{}).items():
        labels=entity.get("labels",{})
        names=[labels.get(lang,{}).get("value","") for lang in ("it","en")]
        names += [a.get("value","") for lang in ("it","en")
                  for a in entity.get("aliases",{}).get(lang,[])
                  if isinstance(a,dict)]
        if not any(isinstance(n,str) and n.strip() and slugify(n)==slugify(title_hint)
                   for n in names):
            continue
        # Use the official title when the authority validates it as an exact
        # label or alias; never replace it with a translated unrelated title.
        label=next((n for n in names
                    if isinstance(n,str) and n.strip() and slugify(n)==slugify(title_hint)),None)
        if label is None:continue
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
    extract="\n".join(line.strip() for line in matches[0].splitlines() if line.strip())
    if not 140<=len(extract)<=12000:return None
    return extract[:6000]

ATTRIBUTION=ROOT/"data"/"verified-work-editorial-attribution.json"

def validated_editorial_attributions() -> dict[str,dict]:
    """Trusted source references bound to one exact composer and Wikidata QID."""
    if not ATTRIBUTION.exists():return {}
    doc=json.loads(ATTRIBUTION.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("works"),list):
        raise ValueError("invalid composition-specific editorial references")
    result={}
    for row in doc["works"]:
        if (not isinstance(row,dict) or set(row)!={"slug","composer","wikidata_id","synopsis_source"}
            or not isinstance(row["slug"],str) or not re.fullmatch(r"[a-z0-9-]+",row["slug"])
            or not isinstance(row["composer"],str) or not row["composer"].strip()
            or not isinstance(row["wikidata_id"],str) or not re.fullmatch(r"Q[1-9][0-9]*",row["wikidata_id"])
            or not isinstance(row["synopsis_source"],str) or not row["synopsis_source"].startswith("https://")
            or row["slug"] in result):
            raise ValueError("invalid or duplicate editorial attribution")
        result[row["slug"]]=row
    return result

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
    attributions=validated_editorial_attributions()
    for slug,summary in synopses["synopses"].items():
        record=histories["works"].get(slug)
        if (isinstance(summary,str) and 45<=len(summary.strip())<=300
                and validate_history(record)):
            result[slug]={"synopsis":summary.strip(),"history":record,
                          "attribution":attributions.get(slug)}
    return result

def choose_candidates(candidates:dict,existing:dict,known_slugs:set[str],
                      *,today:date,evidence:dict|None=None)->list[dict]:
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
             if x["access_status"]=="approved"}
    # An identity-only introduction must never suppress later editorial research.
    from scripts.publish_work_editorial import validate_history
    done={x["candidate_id"] for x in existing.get("works",[])
          if isinstance(x.get("wikidata_id"),str)
          and isinstance(x.get("synopsis"),str)
          and 45<=len(x["synopsis"].strip())<=300
          and not x["synopsis"].strip().endswith(
              "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
          and validate_history(x.get("history"))}
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
    # Priority is the earliest documented performance, regardless of source.
    # Undated candidates retain the daily fairness rotation.
    earliest={}
    for row in (evidence or {}).get("evidence",[]):
        if row.get("status")!="needs_editorial_review":continue
        days=[fact.get("date") for fact in row.get("event_facts",[])
              if isinstance(fact,dict) and isinstance(fact.get("date"),str)
              and re.fullmatch(r"20\d{2}-\d{2}-\d{2}",fact["date"])]
        if days:earliest[row.get("candidate_id")]=min(days)
    def prioritized(items):
        return sorted(rotate(items),key=lambda item:
                      earliest.get(item["id"],"9999-12-31"))
    return prioritized(ready)[:MAX_PREVERIFIED]+prioritized(other)[:MAX_RESEARCH]

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
             allow_authority:bool=False,prepared:dict|None=None,
             lookup_history=None):
    existing_works={x["candidate_id"]:x.copy() for x in existing.get("works",[])}
    prepared=preverified_work_material() if prepared is None else prepared
    statuses=[]
    options=choose_candidates(candidates,existing,known_slugs,today=today,evidence=evidence)
    # Move ready-made, sourced work cards to the front while retaining the
    # normal fair rotation for all remaining unseen operas.
    options.sort(key=lambda x:slugify(official_title_hint(x,evidence) or "") not in prepared)
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
        if item["source_key"] in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
            from opera_atlas.bologna_detail_parser import normalize_event_fact
            detail=[{**d,"event_facts":[normalize_event_fact(x)
                     for x in d.get("event_facts",[])]} for d in detail]
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
            # A title homonym may receive a prepared synopsis only when it is
            # explicitly bound to the exact independently resolved composition
            # (Wikidata QID) and an official, matching composer credit.
            attribution=(material or {}).get("attribution")
            bound=(isinstance(attribution,dict)
                   and attribution["wikidata_id"]==identity["wikidata_id"]
                   and slugify(attribution["composer"])==slugify(identity["composer"])
                   and composer_hint is not None
                   and slugify(composer_hint)==slugify(identity["composer"]))
            if identity.get("title_candidate_count",1)>1 and not bound:
                material=None
            from scripts.publish_work_editorial import validate_history
            previous=existing_works.get(cid,{})
            same_identity=(previous.get("wikidata_id")==identity["wikidata_id"]
                           and normalized(previous.get("composer",""))==
                               normalized(identity["composer"]))
            material_ok=(material is not None and slugify(identity["title"])==slug
                         and (identity.get("title_candidate_count",1)==1 or bound)
                         and (not composer_hint or
                              slugify(composer_hint)==slugify(identity["composer"])))
            summary=(material["synopsis"] if material_ok else None)
            history=(material["history"] if material_ok else None)
            if same_identity:
                cached=previous.get("synopsis")
                if summary is None and isinstance(cached,str) and (
                        45<=len(cached.strip())<=300 and not cached.endswith(
                            "Consulta le rappresentazioni verificate in programma nei teatri italiani.")):
                    summary=cached
                if history is None and validate_history(previous.get("history")):
                    history=previous["history"]
            if summary is None and allow_authority and identity.get("wikipedia_title"):
                from scripts.work_plot_generator import synopsis_from_wikipedia_plot
                # Only the exact Wikipedia sitelink of the corroborated QID.
                summary=synopsis_from_wikipedia_plot(extract(identity))
            if history is None and allow_authority:
                from scripts.work_history_research import wikidata_premiere
                reader=wikidata_premiere if lookup_history is None else lookup_history
                history=reader(identity)
            # A genuine plot and sourced premiere must both be present before
            # eligibility for promotion. Cache each separately so one failing
            # provider cannot force an unnecessary second research attempt.
            if summary is None or not validate_history(history):
                if summary is not None or validate_history(history):
                    existing_works[cid]={
                        **previous,"candidate_id":cid,"source_key":item["source_key"],
                        "source_url":item["official_url"],"title":identity["title"],
                        "composer":identity["composer"],"synopsis":summary,
                        "history":history if validate_history(history) else None,
                        "wikidata_id":identity["wikidata_id"],
                        "authority_url":identity["authority_url"],
                        "wikipedia_url":identity.get("wikipedia_url")}
                statuses.append({"candidate_id":cid,"status":"automatic_retry",
                                 "reason":("verified_plot_unavailable" if summary is None
                                           else "verified_premiere_history_unavailable")})
                continue
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
