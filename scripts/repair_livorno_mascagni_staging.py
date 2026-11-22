"""Consolidate two first-party Mascagni Festival ticket URLs into one staging.

The Goldoni publishes one ticket page per recita for Cavalleria rusticana at
Piazza Goldoni (19/20 August 2026). The pages were previously imported as two
different stagings, though they belong to one work, venue and production.
This repair is intentionally limited to the two already verified official
URLs and exact dates; it never merges unrelated later productions.
"""
from __future__ import annotations

import copy
import json

from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY

FIRST="https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana/"
SECOND="https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana-2/"
VENUE="Piazza Goldoni"
DAY_FIRST="2026-08-19"
DAY_SECOND="2026-08-20"
HOUR="21:30"


def consolidate(facts:dict,registry:dict)->tuple[dict,dict,bool]:
    """Pure, repeat-safe migration; fail closed on unexpected provenance."""
    rows=[x for x in facts.get("productions",[])
          if x.get("municipality")=="Livorno" and x.get("venue")==VENUE
          and x.get("title")=="Cavalleria rusticana"
          and x.get("composer")=="Pietro Mascagni"
          and x.get("source_url") in (FIRST,SECOND)]
    if len(rows)==1:
        row=rows[0]
        if (row.get("source_url")==SECOND and row.get("dates")==
                [[DAY_FIRST,HOUR],[DAY_SECOND,HOUR]]):
            return facts,registry,False
        raise ValueError("unexpected existing Livorno Mascagni single staging")
    if len(rows)!=2 or {x.get("source_url") for x in rows}!={FIRST,SECOND}:
        raise ValueError("missing or ambiguous Livorno Mascagni ticket staging")
    first=next(x for x in rows if x["source_url"]==FIRST)
    second=next(x for x in rows if x["source_url"]==SECOND)
    if (first.get("dates")!=[[DAY_FIRST,HOUR]]
        or second.get("dates")!=[[DAY_SECOND,HOUR]]
        or first.get("key")==second.get("key")):
        raise ValueError("Livorno Mascagni dates/production keys changed")
    first_key,second_key=first["key"],second["key"]
    staging_first=registry["stagings"].get(first_key)
    staging_second=registry["stagings"].get(second_key)
    if (not isinstance(staging_first,dict) or not isinstance(staging_second,dict)
        or staging_first.get("work_id")!=staging_second.get("work_id")
        or staging_first.get("venue_id")!=staging_second.get("venue_id")
        or staging_first.get("source_url")!=FIRST
        or staging_second.get("source_url")!=SECOND):
        raise ValueError("Livorno Mascagni canonical staging identity conflict")
    recital_first=registry["performances"].get(first_key+"|"+DAY_FIRST)
    recital_second=registry["performances"].get(second_key+"|"+DAY_SECOND)
    if (not isinstance(recital_first,dict)
        or not isinstance(recital_second,dict)
        or recital_first.get("staging_id")!=staging_first["id"]
        or recital_second.get("staging_id")!=staging_second["id"]
        or recital_first.get("source_url")!=FIRST
        or recital_second.get("source_url")!=SECOND
        or second_key+"|"+DAY_FIRST in registry["performances"]):
        raise ValueError("Livorno Mascagni recital provenance conflict")
    result=copy.deepcopy(facts)
    ids=copy.deepcopy(registry)
    result["productions"]=[x for x in result["productions"]
                           if x["key"]!=first_key]
    retained=next(x for x in result["productions"] if x["key"]==second_key)
    retained["dates"]=[[DAY_FIRST,HOUR],[DAY_SECOND,HOUR]]
    # Preserve both immutable recita IDs. One staging has one canonical
    # source URL, while the first-party independent ticket URL remains in
    # candidate-detail-evidence.json for provenance/diagnostic purposes.
    merged=ids["performances"].pop(first_key+"|"+DAY_FIRST)
    merged["staging_id"]=staging_second["id"]
    merged["source_url"]=SECOND
    ids["performances"][second_key+"|"+DAY_FIRST]=merged
    del ids["stagings"][first_key]
    return result,ids,True


def main():
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    fixed,ids,changed=consolidate(facts,registry)
    if changed:
        MANIFEST.write_text(json.dumps(fixed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        REGISTRY.write_text(json.dumps(ids,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"livorno_mascagni_staging_consolidated":changed}))


if __name__=="__main__":
    main()
