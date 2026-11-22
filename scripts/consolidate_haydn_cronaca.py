"""Consolidate only the two verified Haydn January 2027 ticket stagings.

Preserve the permanent IDs of both recite and their original source URLs;
never merge generic same-title theatre editions.
"""
from __future__ import annotations
import copy

URLS={
    "2027-01-29":"https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini",
    "2027-01-31":"https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini-2",
}
CLOCKS={"2027-01-29":"20:00","2027-01-31":"16:00"}
TITLE="Cronaca di un amore. Callas e Pasolini"
COMPOSER="Davide Tramontano"


def consolidate(facts:dict,registry:dict)->tuple[dict,dict,int]:
    matching=[p for p in facts.get("productions",[])
              if p.get("municipality")=="Trento"
              and p.get("venue")=="Teatro Sociale"
              and p.get("title")==TITLE
              and p.get("composer")==COMPOSER
              and p.get("source_url") in URLS.values()]
    if len(matching)!=2:
        return facts,registry,0
    mapped={}
    for p in matching:
        rows=p.get("dates")
        if (not isinstance(rows,list) or len(rows)!=1
            or not isinstance(rows[0],list) or len(rows[0])!=2):
            return facts,registry,0
        day,clock=rows[0]
        if URLS.get(day)!=p.get("source_url") or CLOCKS.get(day)!=clock or day in mapped:
            return facts,registry,0
        stage=registry.get("stagings",{}).get(p.get("key"))
        perf=registry.get("performances",{}).get(str(p.get("key"))+"|"+day)
        if (not stage or not perf
            or stage.get("source_url")!=p["source_url"]
            or perf.get("source_url")!=p["source_url"]
            or perf.get("original_date")!=day
            or perf.get("staging_id")!=stage.get("id")):
            return facts,registry,0
        mapped[day]=(p,stage,perf)
    if set(mapped)!=set(URLS):
        return facts,registry,0
    first,stage_first,_=mapped["2027-01-29"]
    second,stage_second,_=mapped["2027-01-31"]
    if (stage_first.get("work_id")!=stage_second.get("work_id")
        or stage_first.get("venue_id")!=stage_second.get("venue_id")
        or stage_first.get("season")!=stage_second.get("season")
        or stage_first.get("id")==stage_second.get("id")):
        return facts,registry,0
    result=copy.deepcopy(facts)
    ids=copy.deepcopy(registry)
    canonical=next(p for p in result["productions"] if p["key"]==first["key"])
    canonical["dates"]=sorted([[day,CLOCKS[day]] for day in URLS])
    result["productions"]=[p for p in result["productions"]
                           if p["key"]!=second["key"]]
    original_key=second["key"]+"|2027-01-31"
    replacement=first["key"]+"|2027-01-31"
    if replacement in ids["performances"]:
        return facts,registry,0
    moved=ids["performances"].pop(original_key)
    moved["staging_id"]=stage_first["id"]
    moved["original_ticket_source_url"]=moved["source_url"]
    moved["source_url"]=first["source_url"]
    ids["performances"][replacement]=moved
    del ids["stagings"][second["key"]]
    return result,ids,1
