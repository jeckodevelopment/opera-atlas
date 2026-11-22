"""Merge only the two historically published Mascagni Festival ticket stagings.

Both events are first-party verified and were accidentally issued separate
staging IDs before rolling-source grouping was implemented. Retain recita IDs
and original ticket provenance; never merge editions based on title alone.
"""
from __future__ import annotations
import copy

URLS={
    "2026-08-19":"https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana/",
    "2026-08-20":"https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana-2/",
}

def consolidate(facts:dict,registry:dict)->tuple[dict,dict,int]:
    matching=[p for p in facts.get("productions",[])
              if p.get("municipality")=="Livorno"
              and p.get("venue")=="Piazza Goldoni"
              and p.get("title")=="Cavalleria rusticana"
              and p.get("composer")=="Pietro Mascagni"
              and p.get("source_url") in URLS.values()]
    if len(matching)!=2:
        return facts,registry,0
    mapped={}
    for p in matching:
        dates=p.get("dates")
        if (not isinstance(dates,list) or len(dates)!=1
            or not isinstance(dates[0],list) or len(dates[0])!=2):
            return facts,registry,0
        day,clock=dates[0]
        if (URLS.get(day)!=p.get("source_url") or clock!="21:30"
            or day in mapped):
            return facts,registry,0
        stage=registry.get("stagings",{}).get(p.get("key"))
        perf=registry.get("performances",{}).get(str(p.get("key"))+"|"+day)
        if (not stage or not perf
            or stage.get("source_url")!=p["source_url"]
            or stage.get("venue_id")!=perf.get("venue_id",stage.get("venue_id"))
            or perf.get("source_url")!=p["source_url"]
            or perf.get("original_date")!=day
            or perf.get("staging_id")!=stage.get("id")):
            return facts,registry,0
        mapped[day]=(p,stage,perf)
    if set(mapped)!=set(URLS):
        return facts,registry,0
    first,first_stage,first_perf=mapped["2026-08-19"]
    second,second_stage,second_perf=mapped["2026-08-20"]
    if (first_stage.get("work_id")!=second_stage.get("work_id")
        or first_stage.get("venue_id")!=second_stage.get("venue_id")
        or first_stage.get("season")!="2026"
        or second_stage.get("season")!="2026"
        or first_stage.get("id")==second_stage.get("id")):
        return facts,registry,0
    # Reuse the lower-numbered published staging ID; the two *recita*
    # identifiers remain stable. The retired staging URL is recorded as an
    # original ticket source in the migrated recita evidence.
    canonical,retired=sorted(
        [(first,first_stage,first_perf),(second,second_stage,second_perf)],
        key=lambda triple:triple[1]["id"])
    current,stage,_=canonical
    old,old_stage,old_perf=retired
    result=copy.deepcopy(facts)
    ids=copy.deepcopy(registry)
    canonical_row=next(p for p in result["productions"] if p["key"]==current["key"])
    canonical_row["dates"]=sorted([["2026-08-19","21:30"],["2026-08-20","21:30"]])
    result["productions"]=[p for p in result["productions"]
                          if p["key"]!=old["key"]]
    old_key=old["key"]+"|"+old["dates"][0][0]
    replacement=current["key"]+"|"+old["dates"][0][0]
    if replacement in ids["performances"]:
        return facts,registry,0
    moved=ids["performances"].pop(old_key)
    moved["staging_id"]=stage["id"]
    moved["original_ticket_source_url"]=moved["source_url"]
    moved["source_url"]=current["source_url"]
    ids["performances"][replacement]=moved
    del ids["stagings"][old["key"]]
    return result,ids,1
