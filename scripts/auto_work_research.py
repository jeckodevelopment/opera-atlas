"""Unattended, evidence-grounded discovery of *new* operas.

Wikidata resolves exact title, opera type and composer; Wikipedia provides
an attributable article excerpt only as model context. A language model
writes one original short Italian synopsis. No excerpt is persisted.
Nothing is published without exact source identity, structured date/time
evidence and the subsequent canonical transaction.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
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
MAX_RESEARCH=3
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

def official_title_hint(candidate:dict)->str|None:
    key=candidate.get("source_key","")
    url=candidate.get("official_url","")
    if not isinstance(url,str):return None
    path=urlsplit(url).path.rstrip("/").split("/")[-1].removesuffix(".html")
    if not re.fullmatch(r"[a-z0-9-]{3,80}",path) or not eligible(key,url):
        return None
    if path.endswith("-anteprima-under30"):return None
    return path.replace("-"," ")

def resolve_identity(title_hint:str,*,fetch=read_api)->dict|None:
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
        if len(composers)!=1 or not isinstance(wiki,str) or len(wiki)>150:continue
        accepted.append((qid,label,next(iter(composers)),wiki))
    if len(accepted)!=1:return None
    qid,title,composer_id,wiki_title=accepted[0]
    composer_entity=fetch(wikidata_url("wbgetentities",ids=composer_id,
                                      props="labels",languages="it|en")).get(
                                          "entities",{}).get(composer_id,{})
    labels=composer_entity.get("labels",{})
    composer=labels.get("it",labels.get("en",{})).get("value")
    if not isinstance(composer,str) or not 3<=len(composer)<=100:return None
    return {"title":title,"composer":composer,"wikidata_id":qid,
            "wikipedia_title":wiki_title,
            "authority_url":"https://www.wikidata.org/wiki/"+qid,
            "wikipedia_url":"https://it.wikipedia.org/wiki/"+
                            quote(wiki_title.replace(" ","_"),safe="()_-")}

def wiki_excerpt(identity:dict,*,fetch=read_api)->str|None:
    result=fetch("https://it.wikipedia.org/w/api.php?"+urlencode({
        "action":"query","format":"json","prop":"extracts",
        "exintro":"1","explaintext":"1","titles":identity["wikipedia_title"]}))
    pages=result.get("query",{}).get("pages",{})
    matches=[x.get("extract","") for x in pages.values() if isinstance(x,dict)]
    if len(matches)!=1:return None
    extract=" ".join(matches[0].split())
    if not 140<=len(extract)<=12000:return None
    return extract[:3000]

def make_synopsis(identity:dict,article_text:str,*,api_key:str,model:str="gpt-6-luna")->str|None:
    """Low-cost JSON-schema output; model may decline if the plot is absent."""
    if not api_key:return None
    schema={"type":"object","properties":{
        "supported":{"type":"boolean"},"synopsis":{"type":"string"}},
        "required":["supported","synopsis"],"additionalProperties":False}
    payload={"model":model,"max_output_tokens":350,"reasoning":{"effort":"none"},
             "input":[
                 {"role":"system","content":
                  "Scrivi SOLO in italiano una sinossi originale di una o due frasi per una scheda "
                  "che invita a teatro. Usa esclusivamente fatti espliciti nel testo fornito, "
                  "non copiare frasi, non aggiungere episodi o personaggi, non fare didattica. "
                  "Se il testo non contiene abbastanza trama, supported=false e synopsis vuota."},
                 {"role":"user","content":
                  "Opera: "+identity["title"]+"; compositore: "+identity["composer"]+
                  "; fonte enciclopedica: "+article_text[:3000]}],
             "text":{"format":{"type":"json_schema","name":"opera_synopsis",
                               "strict":True,"schema":schema}}}
    req=Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),
                headers={"Authorization":"Bearer "+api_key,
                         "Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=35) as response:
        raw=response.read(80_001)
        if len(raw)>80_000:raise ValueError("model response too large")
    result=json.loads(raw.decode("utf-8"))
    output=[c.get("text","") for o in result.get("output",[])
            for c in o.get("content",[]) if c.get("type")=="output_text"]
    if len(output)!=1:return None
    parsed=json.loads(output[0])
    if parsed.get("supported") is not True:return None
    summary=parsed.get("synopsis","").strip()
    if not 45<=len(summary)<=300 or summary.count(".")>3:return None
    # Enforce original language, not a copied 12-word fragment.
    words=re.findall(r"\w+",article_text.casefold(),flags=re.UNICODE)
    actual=re.findall(r"\w+",summary.casefold(),flags=re.UNICODE)
    fragments={" ".join(words[i:i+12]) for i in range(max(0,len(words)-11))}
    if any(" ".join(actual[i:i+12]) in fragments
           for i in range(max(0,len(actual)-11))):return None
    return summary

def make_history(identity:dict, article_text:str, *,api_key:str,
                 model:str="gpt-6-luna")->dict|None:
    """Only publish historical facts paired with verbatim evidence from the article.

    A missing composition year is explicit null, never copied from the premiere.
    A candidate lacking premiere/libretto evidence remains unpublished for a later
    automatic retry rather than receiving a fictional biography.
    """
    if not api_key:return None
    schema={"type":"object","properties":{
        "supported":{"type":"boolean"},
        "librettist":{"type":"string"},
        "premiere_year":{"type":"integer"},
        "premiere_venue":{"type":"string"},
        "premiere_city":{"type":"string"},
        "composition_year":{"type":["integer","null"]},
        "libretto_evidence":{"type":"string"},
        "premiere_evidence":{"type":"string"},
        "composition_evidence":{"type":"string"}},
        "required":["supported","librettist","premiere_year","premiere_venue",
                    "premiere_city","composition_year","libretto_evidence",
                    "premiere_evidence","composition_evidence"],
        "additionalProperties":False}
    data={"model":model,"max_output_tokens":750,"reasoning":{"effort":"none"},
          "input":[{"role":"system","content":
            "Sei un estrattore di fatti d'archivio, non uno scrittore creativo. "
            "Usa SOLO il testo fornito. supported=true soltanto se il testo "
            "dichiara chiaramente librettista, anno, teatro e città della PRIMA "
            "rappresentazione mondiale. Per ogni fatto indica un estratto ESATTO "
            "dal testo, copiato letteralmente, rispettivamente nei campi evidence. "
            "Se assente un dato obbligatorio: supported=false. "
            "Non dedurre mai l'anno di composizione dall'anno di debutto; "
            "se non esplicito usa null e composition_evidence vuota."},
                   {"role":"user","content":"Opera: "+identity["title"]+
                    "; composer: "+identity["composer"]+
                    "; source: "+article_text[:3000]}],
          "text":{"format":{"type":"json_schema","name":"opera_history",
                             "strict":True,"schema":schema}}}
    request=Request("https://api.openai.com/v1/responses",
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Authorization":"Bearer "+api_key,
                             "Content-Type":"application/json"},method="POST")
    with urlopen(request,timeout=35) as response:
        raw=response.read(80_001)
        if len(raw)>80_000:raise ValueError("historical extraction too large")
    result=json.loads(raw.decode("utf-8"))
    output=[x.get("text","") for o in result.get("output",[])
            for x in o.get("content",[]) if x.get("type")=="output_text"]
    if len(output)!=1:return None
    parsed=json.loads(output[0])
    if parsed.get("supported") is not True:return None
    for key in ("librettist","premiere_venue","premiere_city"):
        if not isinstance(parsed.get(key),str) or not 3<=len(parsed[key].strip())<=140:
            return None
    year=parsed.get("premiere_year")
    composed=parsed.get("composition_year")
    if type(year)!=int or not 1600<=year<=date.today().year:return None
    if composed is not None and (type(composed)!=int or not 1500<=composed<=year):
        return None
    normalized_source=" ".join(article_text.casefold().split())
    for key in ("libretto_evidence","premiere_evidence"):
        evidence=parsed.get(key,"")
        if not isinstance(evidence,str) or len(evidence.strip())<15 or (
            " ".join(evidence.casefold().split()) not in normalized_source):
            return None
    if composed is not None:
        evidence=parsed.get("composition_evidence","")
        if not isinstance(evidence,str) or str(composed) not in evidence or (
            " ".join(evidence.casefold().split()) not in normalized_source):
            return None
    if str(year) not in parsed["premiere_evidence"]:return None
    # Keep evidence text private to evaluation; publish only facts and provenance.
    return {"librettist":parsed["librettist"].strip(),
            "premiere_year":year,"premiere_venue":parsed["premiere_venue"].strip(),
            "premiere_city":parsed["premiere_city"].strip(),
            **({"composition_year":composed} if composed is not None else {}),
            "sources":[identity["authority_url"],identity["wikipedia_url"]]}


def choose_candidates(candidates:dict,existing:dict,known_slugs:set[str],
                      *,today:date)->list[dict]:
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
             if x["access_status"]=="approved"}
    done={x["candidate_id"] for x in existing.get("works",[])
          if isinstance(x.get("history"),dict)}
    options=[]
    for item in candidates.get("candidates",[]):
        if item.get("status")!="needs_review" or item.get("id") in done:continue
        source=sources.get(item.get("source_key"))
        if source is None:continue
        uri=item.get("official_url","")
        if not isinstance(uri,str) or urlsplit(uri).hostname!=urlsplit(source["official_url"]).hostname:
            continue
        hint=official_title_hint(item)
        if hint is None or slugify(hint) in known_slugs:continue
        options.append(item)
    options.sort(key=lambda x:x["id"])
    if not options:return []
    # Advance by one position per day. The previous stride of MAX_RESEARCH
    # could starve candidates permanently whenever the queue length was a
    # multiple of that budget (3, 6, 9, ...).
    offset=today.toordinal()%len(options)
    return (options[offset:]+options[:offset])[:MAX_RESEARCH]

def research(candidates:dict,existing:dict,known_slugs:set[str],*,
             today:date,resolve=resolve_identity,extract=wiki_excerpt,
             generate=make_synopsis,generate_history=make_history,api_key:str=""):
    existing_works={x["candidate_id"]:x.copy() for x in existing.get("works",[])}
    statuses=[]
    for item in choose_candidates(candidates,existing,known_slugs,today=today):
        cid=item["id"]
        if not api_key:
            statuses.append({"candidate_id":cid,"status":"model_not_configured"})
            continue
        try:
            identity=resolve(official_title_hint(item))
            if identity is None:raise ValueError("authority_not_unique")
            excerpt=extract(identity)
            if not excerpt:raise ValueError("no_sufficient_plot_source")
            summary=generate(identity,excerpt,api_key=api_key)
            if not summary:raise ValueError("synopsis_not_supported")
            history=generate_history(identity,excerpt,api_key=api_key)
            if not history:raise ValueError("history_not_supported")
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
    api_key=os.environ.get("ATLAS_OPENAI_API_KEY","") if args.allow_network else ""
    result,statuses=research(candidates,previous,{x["slug"] for x in known["works"].values()},
                             today=date.today(),api_key=api_key)
    _write_atomic(OUT,result)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":datetime.now(timezone.utc).isoformat(
        timespec="seconds"),"outcomes":statuses})
    print(json.dumps({"work_intelligence":len(result["works"]),"outcomes":statuses}))
if __name__=="__main__":
    main()
