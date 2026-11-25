"""Source-reviewed Haydn ticket identities, distinct from staging identities."""
from __future__ import annotations
import copy
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

TITLE = "La clemenza di Tito"
COMPOSER = "Wolfgang Amadeus Mozart"
CANONICAL_KEY = "auto-0e8fc70d8165e8a2"
RETIRED_KEY = "auto-f3d0b1311d04c3e4"
CANONICAL_ID = "oa-s-000245"
RETIRED_ID = "oa-s-000246"
TICKETS = {
    "2026-11-27": "https://www.haydn.it/eventi/la-clemenza-di-tito",
    "2026-11-29": "https://www.haydn.it/eventi/la-clemenza-di-tito-2",
}
CLOCKS = {"2026-11-27": "20:00", "2026-11-29": "16:00"}
REPLICA_GROUP = "https://www.haydn.it/eventi/area/opera?repliche=la-clemenza-di-tito"
GROUP = re.compile(r"https://www\.haydn\.it/eventi/area/opera\?repliche=[a-z0-9][a-z0-9-]*")


def valid_group(value):
    return isinstance(value,str) and bool(GROUP.fullmatch(value))


def consolidate(facts:dict, registry:dict):
    """Retain the originally published canonical URL and both recita IDs."""
    current = {p["key"]:p for p in facts["productions"]}
    if RETIRED_KEY not in current:
        return facts,registry,0
    if CANONICAL_KEY not in current:
        raise ValueError("missing canonical Tito staging")
    for key,day,sid in ((CANONICAL_KEY,"2026-11-29",CANONICAL_ID),
                        (RETIRED_KEY,"2026-11-27",RETIRED_ID)):
        p=current[key]
        s=registry["stagings"][key]
        r=registry["performances"][key+"|"+day]
        if ((p["title"],p["composer"],p["municipality"],p["venue"],p["source_url"],p["dates"])
            != (TITLE,COMPOSER,"Trento","Teatro Sociale",TICKETS[day],[[day,CLOCKS[day]]])
            or (s["id"],s["work_id"],s["venue_id"],s["season"],s["source_url"])
            != (sid,"oa-w-000066","oa-v-000055","2026",TICKETS[day])
            or r["staging_id"]!=sid or r["original_date"]!=day
            or r["source_url"]!=TICKETS[day]):
            raise ValueError("Tito replica migration no longer matches reviewed evidence")
    f=copy.deepcopy(facts)
    ids=copy.deepcopy(registry)
    canonical=next(p for p in f["productions"] if p["key"]==CANONICAL_KEY)
    canonical["dates"]=[[day,CLOCKS[day]] for day in sorted(CLOCKS)]
    canonical["ticket_source_urls"]=dict(TICKETS)
    f["productions"]=[p for p in f["productions"] if p["key"]!=RETIRED_KEY]
    stage=ids["stagings"][CANONICAL_KEY]
    stage["supporting_source_urls"]=sorted(TICKETS.values())
    stage["replica_group_url"]=REPLICA_GROUP
    # Preserve the retired identity for audit; never allocate it again.
    retired=ids.setdefault("retired_stagings",{})
    retired[RETIRED_ID]={"canonical_id":CANONICAL_ID,"reason":"verified_haydn_replicas"}
    moved=ids["performances"].pop(RETIRED_KEY+"|2026-11-27")
    replacement=CANONICAL_KEY+"|2026-11-27"
    if replacement in ids["performances"]:
        raise ValueError("duplicate Tito replica registry key")
    moved["staging_id"]=CANONICAL_ID
    moved["original_ticket_source_url"]=moved["source_url"]
    moved["source_url"]=canonical["source_url"]
    ids["performances"][replacement]=moved
    del ids["stagings"][RETIRED_KEY]
    return f,ids,1


def reviewed_match(item, production, dates):
    """Explicitly reviewed pair: neither slug suffix nor time proximity proves identity."""
    return (item.get("source_key")=="haydn-rolling-opera"
            and production.get("title")==TITLE and production.get("composer")==COMPOSER
            and production.get("municipality")=="Trento" and production.get("venue")=="Teatro Sociale"
            and production.get("source_url") in TICKETS.values()
            and all(CLOCKS.get(d)==h and TICKETS.get(d)==item.get("source_url")
                    for d,h in dates.items())
            and bool(dates)
            and all(CLOCKS.get(d)==h for d,h in production["dates"]))


def same_replica_group(item, other, production, dates):
    """Both first-party detail observations must link the same explicit replica group.
    Never merge across venues, compositions, or a distant season.
    """
    from opera_atlas.haydn_rolling_opera import eligible_detail
    group=item.get("replica_group_url")
    if (item.get("source_key")!="haydn-rolling-opera"
        or other.get("source_key")!="haydn-rolling-opera"
        or item.get("status")!="needs_editorial_review"
        or other.get("status")!="needs_editorial_review"
        or not valid_group(group) or other.get("replica_group_url")!=group
        or not eligible_detail(item.get("source_url",""))
        or not eligible_detail(other.get("source_url",""))
        or other.get("source_url")!=production.get("source_url")
        or not all(re.fullmatch(r"[0-9a-f]{64}",str(x.get("content_sha256",""))) for x in (item,other))):
        return False
    rows=other.get("event_facts",[])
    if len(rows)!=1:return False
    row=rows[0]
    if not isinstance(row,dict):return False
    if (row.get("event_title")!=production["title"] or row.get("composer")!=production["composer"]
        or row.get("venue")!=production["venue"] or row.get("date") not in dict(production["dates"])):
        return False
    try:
        stamp=datetime.fromisoformat(row["starts_at"])
        if stamp.tzinfo is None:return False
        local=stamp.astimezone(ZoneInfo("Europe/Rome"))
        if local.date().isoformat()!=row["date"] or local.strftime("%H:%M")!=dict(production["dates"])[row["date"]]:return False
        days=[date.fromisoformat(day) for day in list(dates)+[d for d,_ in production["dates"]]]
        return bool(days) and (max(days)-min(days)).days<=45
    except (KeyError,TypeError,ValueError):
        return False
