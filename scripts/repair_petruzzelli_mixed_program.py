"""Remove one mislabelled Petruzzelli composite bill from canonical opera feed.

This is not a deletion of the source event. L'Arlésienne/Pagliacci is kept
as review-only evidence until Atlas supports a bill linked to both works.
Do not treat seven October 2027 performances as Pagliacci alone.
"""
from __future__ import annotations

import copy
import json
from scripts.auto_catalogue import SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST,validate_auto_sources
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.daily_ingest import _write_atomic

MIXED_KEY="auto-a12dbb283b490075"
MIXED_URL=("https://www.fondazionepetruzzelli.it/eventi/"
           "larlesienne-di-georges-bizet-pagliacci-di-ruggero-leoncavallo-13-20-ottobre/")
OCTOBER={"2027-10-13","2027-10-14","2027-10-15","2027-10-16",
         "2027-10-17","2027-10-19","2027-10-20"}

def repair(facts:dict,registry:dict,approved_urls:list[str]):
    """Fail closed unless every existing ID belongs to the exact bad stage."""
    next_facts=copy.deepcopy(facts)
    next_ids=copy.deepcopy(registry)
    urls=list(approved_urls)
    matching=[x for x in next_facts.get("productions",[])
              if x.get("key")==MIXED_KEY]
    if len(matching)>1:
        raise ValueError("duplicate composite staging identity")
    if not matching:
        # Already repaired, but never silently accept a half-removed registry.
        if MIXED_KEY in next_ids["stagings"] or any(
            key.startswith(MIXED_KEY+"|")
            for key in next_ids["performances"]):
            raise ValueError("orphaned composite staging registry")
        return next_facts,next_ids,urls,0
    stage=matching[0]
    if (stage.get("source_url")!=MIXED_URL
        or stage.get("title")!="Pagliacci"
        or stage.get("composer")!="Ruggero Leoncavallo"
        or stage.get("municipality")!="Bari"
        or stage.get("venue")!="Teatro Petruzzelli"
        or {day for day,_ in stage.get("dates",[])}!=OCTOBER
        or len(stage["dates"])!=7):
        raise ValueError("unexpected composite bill; refusing automatic repair")
    stage_info=next_ids["stagings"].get(MIXED_KEY)
    expected_work=next_ids["works"].get("pagliacci|ruggero leoncavallo")
    expected_venue=next_ids["venues"].get("Bari|Teatro Petruzzelli")
    if (not stage_info or not expected_work or not expected_venue
        or stage_info.get("source_url")!=MIXED_URL
        or stage_info.get("work_id")!=expected_work["id"]
        or stage_info.get("venue_id")!=expected_venue["id"]):
        raise ValueError("unexpected official composite staging graph")
    staging_id=stage_info["id"]
    keys=[MIXED_KEY+"|"+day for day in sorted(OCTOBER)]
    for key in keys:
        recite=next_ids["performances"].get(key)
        if (not recite or recite["staging_id"]!=staging_id
            or recite.get("source_url")!=MIXED_URL):
            raise ValueError("unexpected composite performance ID mapping")
    if set(k for k,v in next_ids["performances"].items()
           if v.get("staging_id")==staging_id)!=set(keys):
        raise ValueError("other performances use the quarantined stage")
    next_facts["productions"]=[x for x in next_facts["productions"]
                               if x.get("key")!=MIXED_KEY]
    del next_ids["stagings"][MIXED_KEY]
    for key in keys:del next_ids["performances"][key]
    if MIXED_URL in urls and not any(
        p.get("source_url")==MIXED_URL for p in next_facts["productions"]):
        urls=[x for x in urls if x!=MIXED_URL]
    validate_auto_sources(urls)
    assemble(next_facts,next_ids,approved_extra=set(urls))
    return next_facts,next_ids,urls,len(keys)

def main():
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids=json.loads(REGISTRY.read_text(encoding="utf-8"))
    urls=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
    new_facts,new_ids,new_urls,removed=repair(facts,ids,urls)
    if removed:
        _write_atomic(MANIFEST,new_facts)
        _write_atomic(REGISTRY,new_ids)
        _write_atomic(SOURCE_ALLOWLIST,{"schema_version":1,"urls":new_urls})
    print(json.dumps({"quarantined_mislabelled_mixed_bill_recite":removed}))

if __name__=="__main__":
    main()
