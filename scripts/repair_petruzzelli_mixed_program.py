"""Quarantine Petruzzelli staging identities proven to be false.

The 2026 first-run parser matched the cross-linked title "La traviata" on
other operas' pages. In 2027 a combined L'Arlésienne/Pagliacci programme
was published as solo Pagliacci. Every immutable ID is checked before any
correction; authentic La traviata, Nabucco, Rossini's Barbiere and all other venues are retained.
"""
from __future__ import annotations
import copy
import json
from scripts.auto_catalogue import SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST,validate_auto_sources
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.daily_ingest import _write_atomic

BASE="https://www.fondazionepetruzzelli.it/eventi/"
# Each tuple: immutable staging key, official detail slug, *wrong* work,
# number of recite, exact date set (not the actual correct opera title).
WRONG=(
    ("auto-a12dbb283b490075","larlesienne-di-georges-bizet-pagliacci-di-ruggero-leoncavallo-13-20-ottobre",
     "Pagliacci","Ruggero Leoncavallo","2027-10-13,14,15,16,17,19,20"),
    ("auto-01efa4320f812042","le-lac-des-cygnes-il-lago-dei-cigni-12-15-novembre",
     "La traviata","Giuseppe Verdi","2026-11-12,13,14,15"),
    ("auto-207df538679e0065","bona-sforza-krautze-14-20-settembre",
     "La traviata","Giuseppe Verdi","2026-09-14,16,18,20"),
    ("auto-663c5bda82d136bb","il-gobbo-del-califfo-casavola-21-24-maggio",
     "La traviata","Giuseppe Verdi","2026-05-21,22,23,24"),
    ("auto-eedca6da108bd27e","il-trovatore-verdi-18-27-ottobre",
     "La traviata","Giuseppe Verdi","2026-10-18,20,21,23,25,27"),
)

def expected_dates(compact:str)->set[str]:
    first,*other=compact.split(",")
    prefix=first[:8]
    return {first,*[prefix+d for d in other]}

def independently_verified_correct_stage(stage:dict,evidence:dict)->bool:
    """Preserve a once-misattributed stable URL after verified reimport.

    A historical bad canonical work is identified by title/composer mismatch
    against full source evidence; a *new correct* stage with the same
    deterministic key must not be deleted or treated as corrupted.
    """
    import re
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from scripts.publish_catalog_v2 import normalized
    url=stage.get("source_url")
    rows=[x for x in evidence.get("evidence",[]) if
          x.get("source_url")==url and
          x.get("source_key") in ("petruzzelli-opera-2026","petruzzelli-opera-2027")
          and x.get("status")=="needs_editorial_review"
          and re.fullmatch(r"[0-9a-f]{64}",x.get("content_sha256",""))]
    if len(rows)!=1:return False
    facts=rows[0].get("event_facts")
    if not isinstance(facts,list) or not facts:return False
    actual={}
    try:
        for fact in facts:
            if (normalized(fact["event_title"])!=normalized(stage["title"])
                    or normalized(fact["composer"])!=normalized(stage["composer"])
                    or fact["venue"]!=stage["venue"]):
                return False
            stamp=datetime.fromisoformat(fact["starts_at"])
            if stamp.tzinfo is None:return False
            local=stamp.astimezone(ZoneInfo("Europe/Rome"))
            day=local.date().isoformat()
            if fact["date"]!=day or day in actual:return False
            actual[day]=local.strftime("%H:%M")
    except (KeyError,TypeError,ValueError):
        return False
    return actual==dict(stage.get("dates",[]))


def repair(facts:dict,registry:dict,approved_urls:list[str]):
    new_facts=copy.deepcopy(facts)
    new_ids=copy.deepcopy(registry)
    urls=list(approved_urls)
    deleted=0
    from scripts.collect_candidate_details import OUTPUT as SOURCE_DETAILS
    evidence=json.loads(SOURCE_DETAILS.read_text(encoding="utf-8"))
    # Validate ALL expected stages before mutating any, so a changed
    # title/venue/ID cannot cause a partially destructive repair.
    plans=[]
    for key,slug,title,composer,dates in WRONG:
        url=BASE+slug+"/"
        expected=expected_dates(dates)
        records=[x for x in new_facts.get("productions",[])
                 if x.get("key")==key]
        if len(records)>1:raise ValueError("duplicated repair stage")
        if not records:
            if key in new_ids["stagings"] or any(
                k.startswith(key+"|") for k in new_ids["performances"]):
                raise ValueError("partially removed repair target")
            continue
        stage=records[0]
        if (stage.get("source_url")==url
                and independently_verified_correct_stage(stage,evidence)):
            # The same stable deterministic key has now been correctly
            # reimported; deleting it would discard real opera recite.
            continue
        if (stage.get("source_url")!=url
            or stage.get("title")!=title
            or stage.get("composer")!=composer
            or stage.get("municipality")!="Bari"
            or stage.get("venue")!="Teatro Petruzzelli"
            or {d for d,_ in stage.get("dates",[])}!=expected
            or len(stage["dates"])!=len(expected)):
            raise ValueError("unexpected Petruzzelli staging; refusing to remove")
        info=new_ids["stagings"].get(key)
        work=new_ids["works"].get(title.casefold()+"|"+composer.casefold())
        venue=new_ids["venues"].get("Bari|Teatro Petruzzelli")
        if (not info or not work or not venue
            or info.get("source_url")!=url
            or info.get("work_id")!=work["id"]
            or info.get("venue_id")!=venue["id"]):
            raise ValueError("unexpected immutable Petruzzelli staging identity")
        registered={k for k,v in new_ids["performances"].items()
                    if v.get("staging_id")==info["id"]}
        keys={key+"|"+day for day in expected}
        if registered!=keys:raise ValueError("unexpected recite IDs for Petruzzelli stage")
        for performance_key in keys:
            row=new_ids["performances"].get(performance_key)
            if (not row or row.get("source_url")!=url
                or row.get("original_date")!=performance_key.split("|")[1]):
                raise ValueError("unexpected immutable Petruzzelli performance")
        plans.append((key,keys,url))
    for key,keys,url in plans:
        new_facts["productions"]=[p for p in new_facts["productions"]
                                   if p.get("key")!=key]
        del new_ids["stagings"][key]
        for performance_key in keys:
            del new_ids["performances"][performance_key]
        deleted+=len(keys)
        if url in urls and not any(p.get("source_url")==url
                                   for p in new_facts["productions"]):
            urls=[x for x in urls if x!=url]
    validate_auto_sources(urls)
    assemble(new_facts,new_ids,approved_extra=set(urls))
    return new_facts,new_ids,urls,deleted

def main():
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids=json.loads(REGISTRY.read_text(encoding="utf-8"))
    urls=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
    new_facts,new_ids,new_urls,removed=repair(facts,ids,urls)
    if removed:
        _write_atomic(MANIFEST,new_facts)
        _write_atomic(REGISTRY,new_ids)
        _write_atomic(SOURCE_ALLOWLIST,{"schema_version":1,"urls":new_urls})
    print(json.dumps({"quarantined_incorrectly_attributed_recite":removed}))

if __name__=="__main__":
    main()
