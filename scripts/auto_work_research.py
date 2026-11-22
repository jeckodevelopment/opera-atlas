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
    if not matches and composer_hint:
        # The high-ranked results for frequent opera titles can be novels,
        # films or recordings. Re-query with the independently evidenced
        # composer, but still require the exact opera label/alias and QID.
        matches=exact_matches(fetch(wikidata_url(
            "wbsearchentities",search=title_hint+" "+composer_hint,
            language="it",uselang="it",type="item",limit=8)))
    if not matches:return None
    ids="|".join(sorted({x["id"] for x in matches}))
    try:
        batch=fetch(wikidata_url("wbgetentities",ids=ids,
                                props="claims|labels|aliases|sitelinks",languages="it|en"))
    except ValueError as exc:
        if str(exc)!="external knowledge response too large":
            raise
        # Popular operas may have enormous Wikidata statements. Fetch only
        # the identity claims required for this decision, one QID at a time.
        entities={}
        for qid in ids.split("|"):
            slim=fetch(wikidata_url("wbgetentities",ids=qid,
                                    props="labels|aliases|sitelinks",languages="it|en"))
            entity=slim.get("entities",{}).get(qid,{})
            if not isinstance(entity,dict):
                continue
            claims={}
            for prop in ("P31","P7937","P86"):
                specific=fetch(wikidata_url("wbgetclaims",entity=qid,property=prop))
                claims[prop]=specific.get("claims",{}).get(prop,[])
            entities[qid]={**entity,"claims":claims}
        batch={"entities":entities}
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
    """Read only a named plot section, never an enormous Wikipedia article.

    This avoids over-large article extracts and also reaches plots located
    after long introduction, performance or reception sections.
    """
    from html.parser import HTMLParser
    from html import unescape

    class PlotText(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts=[]
            self.skip=0
        def handle_starttag(self,tag,attrs):
            if tag in ("script","style","sup"):
                self.skip+=1
            elif tag in ("p","div","li","h2","h3","br") and not self.skip:
                self.parts.append("\n")
        def handle_endtag(self,tag):
            if tag in ("script","style","sup") and self.skip:
                self.skip-=1
        def handle_data(self,data):
            if not self.skip:
                self.parts.append(data)

    title=identity.get("wikipedia_title")
    if not isinstance(title,str) or not title or len(title)>150:
        return None
    base="https://it.wikipedia.org/w/api.php?"
    sections=fetch(base+urlencode({"action":"parse","format":"json",
                                   "page":title,"prop":"sections"}))
    match=[]
    for section in sections.get("parse",{}).get("sections",[]):
        heading=section.get("line","")
        index=str(section.get("index",""))
        if (isinstance(heading,str) and
                re.fullmatch(r"(?:La )?(?:trama|argomento|soggetto)(?: dell.opera)?",
                             heading.strip(),flags=re.I)
                and re.fullmatch(r"[1-9][0-9]{0,3}",index)):
            match.append(index)
    if len(match)!=1:
        return None
    page=fetch(base+urlencode({"action":"parse","format":"json",
                               "page":title,"prop":"text","section":match[0],
                               "disableeditsection":"1"}))
    html=page.get("parse",{}).get("text",{}).get("*","")
    if not isinstance(html,str) or not 90<=len(html)<=150000:
        return None
    parser=PlotText()
    parser.feed(html)
    content=" ".join(unescape("".join(parser.parts)).split())
    if not 90<=len(content)<=12000:
        return None
    return "== Trama == "+content[:9000]

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

def canonical_editorial_material(identity:dict)->dict|None:
    """Reuse validated canonical prose only for the same composition.

    Preserve the composition attribution contract: in the presence of an
    alias, homonym or competing Wikidata identity, require an explicit,
    matching QID. Never reuse title-only prose for an ambiguous work.
    """
    from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    synopses=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    histories=json.loads(HISTORY.read_text(encoding="utf-8"))
    attributions=validated_editorial_attributions()
    # Titles can differ across official calendars and Wikidata languages.
    # A cross-title match requires exact QID evidence; a title-only match
    # remains valid only with matching composer and no competing work.
    matches=[]
    for row in registry["works"].values():
        if normalized(row["composer"])!=normalized(identity["composer"]):
            continue
        attribution=attributions.get(row["slug"])
        qid=row.get("wikidata_id") or (
            attribution.get("wikidata_id") if attribution else None)
        same_qid=(isinstance(qid,str) and qid==identity.get("wikidata_id"))
        same_title=(normalized(row["title"])==normalized(identity["title"]))
        if same_qid or (same_title and not qid):
            matches.append(row)
    if len(matches)!=1:return None
    work=matches[0]
    slug,work_id=work["slug"],work["id"]
    same_slug=[w for w in registry["works"].values() if w["slug"]==slug]
    attribution=attributions.get(slug)
    if normalized(work["title"])!=normalized(identity["title"]) and (
            not attribution and not work.get("wikidata_id")):
        return None
    if attribution:
        if (attribution["wikidata_id"]!=identity["wikidata_id"]
                or normalized(attribution["composer"])!=normalized(identity["composer"])):
            return None
    elif work.get("wikidata_id"):
        if work["wikidata_id"]!=identity["wikidata_id"]:return None
    elif len(same_slug)>1 or identity.get("title_candidate_count",1)>1:
        return None
    by_id=synopses.get("synopses_by_id",{})
    historic_by_id=histories.get("works_by_id",{})
    summary=(by_id.get(work_id) if len(same_slug)>1 else
             by_id.get(work_id,synopses["synopses"].get(slug)))
    history=(historic_by_id.get(work_id) if len(same_slug)>1 else
             historic_by_id.get(work_id,histories["works"].get(slug)))
    if (not isinstance(summary,str) or not 45<=len(summary.strip())<=300
            or summary.strip().endswith(
                "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
            or not validate_history(history)):
        return None
    return {"synopsis":summary.strip(),"history":history}


def already_canonical(candidate:dict,evidence:dict|None,
                      registry:dict)->dict|None:
    """Identify existing published composition from official *structured* facts.

    This is not research into a new opera: the existing-work performance
    promoter processes its schedule independently. Never treat URL slugs
    or uncredited event titles as evidence of a canonical identity.
    """
    if evidence is None:return None
    rows=[entry for entry in evidence.get("evidence",[])
          if entry.get("candidate_id")==candidate.get("id")
          and entry.get("source_key")==candidate.get("source_key")
          and entry.get("source_url")==candidate.get("official_url")
          and entry.get("status")=="needs_editorial_review"]
    if len(rows)!=1:return None
    facts=rows[0].get("event_facts")
    if not isinstance(facts,list) or not facts:return None
    identities=set()
    for fact in facts:
        if (not isinstance(fact,dict) or
                not isinstance(fact.get("event_title"),str) or
                not isinstance(fact.get("composer"),str) or
                not fact["event_title"].strip() or not fact["composer"].strip()):
            return None
        identities.add((normalized(fact["event_title"]),
                        normalized(fact["composer"])))
    if len(identities)!=1:return None
    title,composer=next(iter(identities))
    matches=[work for work in registry.get("works",{}).values()
             if normalized(work["title"])==title
             and normalized(work["composer"])==composer]
    return matches[0] if len(matches)==1 else None


def official_identity_evidence(candidate:dict,evidence:dict|None)->bool:
    """Require exactly one attributed work/composer from the linked official page.

    A slug, marketing title, or URL mentioning a surname is not enough to
    identify new operas with recurring titles and artistic adaptations.
    """
    if evidence is None:return False
    records=[record for record in evidence.get("evidence",[])
             if record.get("candidate_id")==candidate.get("id")
             and record.get("source_key")==candidate.get("source_key")
             and record.get("source_url")==candidate.get("official_url")
             and record.get("status")=="needs_editorial_review"]
    if len(records)!=1:return False
    facts=records[0].get("event_facts")
    if not isinstance(facts,list) or not facts:return False
    identities=set()
    for fact in facts:
        if (not isinstance(fact,dict)
                or not isinstance(fact.get("event_title"),str)
                or not isinstance(fact.get("composer"),str)
                or not fact["event_title"].strip()
                or not fact["composer"].strip()):
            return False
        identities.add((normalized(fact["event_title"]),
                        normalized(fact["composer"])))
    return len(identities)==1


def choose_candidates(candidates:dict,existing:dict,known_slugs:set[str],
                      *,today:date,evidence:dict|None=None,
                      strict_evidence:bool=False)->list[dict]:
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
    # A known opera no longer needs new-opera authority requests; isolate
    # it before the bounded queue is chosen so existing theatre schedules
    # cannot starve genuinely uncatalogued compositions.
    registry=json.loads(REGISTRY.read_text(encoding="utf-8")) if evidence else None
    already=[x for x in options if registry and
             already_canonical(x,evidence,registry) is not None]
    known_ids={x["id"] for x in already}
    unseen=[x for x in options if x["id"] not in known_ids]
    waiting=[x for x in unseen if strict_evidence
             and not official_identity_evidence(x,evidence)]
    waiting_ids={x["id"] for x in waiting}
    unseen=[x for x in unseen if x["id"] not in waiting_ids]
    ready=[x for x in unseen if slugify(official_title_hint(x,evidence)) in prepared]
    other=[x for x in unseen if slugify(official_title_hint(x,evidence)) not in prepared]
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
    return (prioritized(ready)[:MAX_PREVERIFIED]
            +prioritized(other)[:MAX_RESEARCH]
            +prioritized(already)[:MAX_PREVERIFIED]
            +prioritized(waiting)[:MAX_PREVERIFIED])

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
    registry=json.loads(REGISTRY.read_text(encoding="utf-8")) if allow_authority else None
    options=choose_candidates(candidates,existing,known_slugs,
                              today=today,evidence=evidence,
                              strict_evidence=(allow_authority and evidence is not None))
    # Move ready-made, sourced work cards to the front while retaining the
    # normal fair rotation for all remaining unseen operas.
    options.sort(key=lambda x:slugify(official_title_hint(x,evidence) or "") not in prepared)
    for item in options:
        cid=item["id"]
        # Already catalogued works need no editorial/knowledge API retry:
        # verified official dates are handled by auto_catalogue.promote.
        known=already_canonical(item,evidence,registry) if registry else None
        if known is not None:
            statuses.append({"candidate_id":cid,"status":"existing_canonical_work",
                             "work_id":known["id"]})
            continue
        if allow_authority and evidence is not None and not official_identity_evidence(item,evidence):
            statuses.append({"candidate_id":cid,"status":"awaiting_official_identity_evidence"})
            continue
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
            canonical_material=canonical_editorial_material(identity) if allow_authority else None
            material=material or canonical_material
            from scripts.publish_work_editorial import validate_history
            # Share an already completed card only for the same QID and
            # independently verified composer, across theatre candidates.
            previous_matches=[entry for entry in existing_works.values()
                              if entry.get("wikidata_id")==identity["wikidata_id"]
                              and normalized(entry.get("composer",""))==
                                  normalized(identity["composer"])
                              and isinstance(entry.get("synopsis"),str)
                              and 45<=len(entry["synopsis"].strip())<=300
                              and not entry["synopsis"].endswith(
                                  "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
                              and validate_history(entry.get("history"))]
            exact_cached=False
            if material is None and previous_matches:
                first=previous_matches[0]
                if all(entry["synopsis"]==first["synopsis"] and
                       entry["history"]==first["history"] for entry in previous_matches):
                    material={"synopsis":first["synopsis"],"history":first["history"]}
                    exact_cached=True
            previous=existing_works.get(cid,{})
            same_identity=(previous.get("wikidata_id")==identity["wikidata_id"]
                           and normalized(previous.get("composer",""))==
                               normalized(identity["composer"]))
            material_ok=(material is not None
                         and (canonical_material is not None or exact_cached or
                              (slugify(identity["title"])==slug and
                               (identity.get("title_candidate_count",1)==1 or bound)))
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
        except ValueError as exc:
            reason=str(exc)
            if reason not in ("authority_not_unique","invalid external knowledge response",
                              "external knowledge response too large"):
                reason="invalid_authority_data"
            statuses.append({"candidate_id":cid,"status":"automatic_retry",
                             "reason":reason})
        except (HTTPError,URLError,TimeoutError,OSError,KeyError,
                json.JSONDecodeError) as exc:
            statuses.append({"candidate_id":cid,"status":"automatic_retry",
                             "reason":type(exc).__name__})
    # Include safe, source-scoped candidate context in every health outcome.
    # Do not expose untrusted error text or page content; these facts are
    # already part of the verified season-index candidate registry.
    by_id={row["id"]:row for row in candidates.get("candidates",[])
           if isinstance(row,dict) and isinstance(row.get("id"),str)}
    for status in statuses:
        item=by_id.get(status["candidate_id"],{})
        status["source_key"]=item.get("source_key")
        status["official_url"]=item.get("official_url")
        hint=official_title_hint(item,evidence)
        if isinstance(hint,str):
            status["title_hint"]=hint
    return {"schema_version":1,"works":sorted(existing_works.values(),
                                             key=lambda x:x["candidate_id"])},statuses

def reconcile_published_outcomes(candidates:dict, statuses:list[dict],
                                 registry:dict)->list[dict]:
    """Report committed source/staging identities instead of stale research waits.

    Only a candidate already marked catalogued AND an exact official source
    URL tied to one registered staging may be classified as published. Title
    similarity is never evidence; this preserves independent homonyms.
    """
    valid_works={w["id"] for w in registry.get("works",{}).values()}
    by_source={}
    for staging in registry.get("stagings",{}).values():
        if staging.get("work_id") in valid_works:
            by_source.setdefault(staging.get("source_url"),[]).append(staging)
    resolved={}
    for candidate in candidates.get("candidates",[]):
        if not isinstance(candidate,dict) or candidate.get("status")!="already_catalogued":
            continue
        matches=by_source.get(candidate.get("official_url"),[])
        if len(matches)!=1:continue
        resolved[candidate["id"]]={
            "candidate_id":candidate["id"],"status":"already_catalogued",
            "work_id":matches[0]["work_id"],"source_key":candidate.get("source_key"),
            "official_url":candidate["official_url"]}
    return ([status for status in statuses
             if status.get("candidate_id") not in resolved]
            +list(resolved.values()))


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
    statuses=reconcile_published_outcomes(candidates,statuses,known)
    _write_atomic(OUT,result)
    _write_atomic(HEALTH,{"schema_version":1,"checked_at":datetime.now(timezone.utc).isoformat(
        timespec="seconds"),"outcomes":statuses})
    print(json.dumps({"work_intelligence":len(result["works"]),"outcomes":statuses}))
if __name__=="__main__":
    main()
