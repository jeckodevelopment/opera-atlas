"""Publish a standalone, reviewed, national opera venue directory.

Venues represent physical places, never festivals/circuits or inferred recite.
The mutable public feed can be refreshed without SFTP or any performances.
"""
from __future__ import annotations
import argparse
import copy
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data"/"venue-directory.json"
OUTPUT=ROOT/"public"/"catalog"/"venue-directory.json"
CANONICAL=ROOT/"data"/"identity-registry.json"
SLUG=re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def build(source:dict, registry:dict)->dict:
    if source.get("schema_version")!=1 or not isinstance(source.get("venues"),list):
        raise ValueError("invalid national venue registry")
    venues=copy.deepcopy(source["venues"])
    if not venues:raise ValueError("venue registry must not be empty")
    ids=set()
    routes=set()
    existing={v["id"]:v for v in registry["venues"].values()}
    for venue in venues:
        if not isinstance(venue,dict):raise ValueError("invalid venue")
        for key in ("id","name","city","region","city_slug","slug","source_url","description","monitoring_status"):
            if not isinstance(venue.get(key),str) or not venue[key].strip():
                raise ValueError("incomplete venue: "+str(venue.get("id"))+" "+key)
        if not SLUG.fullmatch(venue["city_slug"]) or not SLUG.fullmatch(venue["slug"]):
            raise ValueError("unsafe public venue route")
        # A public theatre card must be a complete editorial profile, not
        # an unverified placeholder dependent on performances.
        if not isinstance(venue.get("address"),str) or not venue["address"].strip():
            raise ValueError("missing theatre address: "+venue["id"])
        if not isinstance(venue.get("history"),str) or len(venue["history"].strip())<80:
            raise ValueError("missing theatre history: "+venue["id"])
        if venue.get("photo_file"):
            if not isinstance(venue.get("photo_source_url"),str) or not venue["photo_source_url"].startswith("https://commons.wikimedia.org/wiki/File:"):
                raise ValueError("theatre photo needs provenance: "+venue["id"])
        elif venue.get("status")!="sede_storica_cessata" and venue.get("photo_status")!="review_pending":
            raise ValueError("theatre photo missing: "+venue["id"])
        # An acquired calendar with no future recite differs from an
        # official calendar that has not yet been ingested.
        if venue.get("calendar_status") not in ("acquired","not_acquired"):
            raise ValueError("missing calendar acquisition state: "+venue["id"])
        if re.search(r"sede teatrale censita|le rappresentazioni saranno collegate|calendario non ancora acquisito",venue["description"],re.I):
            raise ValueError("generic theatre card: "+venue["id"])
        if not venue["source_url"].startswith("https://"):
            raise ValueError("source must be HTTPS")
        if venue.get("website") and not str(venue["website"]).startswith("https://"):
            raise ValueError("website must be HTTPS")
        route=venue["city_slug"]+"/"+venue["slug"]
        if venue["id"] in ids or route in routes:
            raise ValueError("duplicate national venue identity or route")
        ids.add(venue["id"])
        routes.add(route)
        if venue.get("canonical_venue_id"):
            authority=existing.get(venue["canonical_venue_id"])
            if not authority or venue["slug"]!=authority["slug"] or venue["city_slug"]!=authority["city_slug"] or (
                venue["id"]!=authority["id"] and not re.fullmatch(r"oa-vd-\\d{6}",venue["id"])
            ):
                raise ValueError("existing performance venue identity changed")
        elif not re.fullmatch(r"oa-vd-\d{6}",venue["id"]):
            raise ValueError("new venues require reserved directory-only IDs")
    # An approved production can autonomously promote a directory-only
    # venue into the canonical performance registry (e.g. Carlo Felice).
    # Match by the *already verified* city/venue route, not by display name;
    # keep the directory ID and public URL stable rather than duplicating it.
    by_route={v["city_slug"]+"/"+v["slug"]:v for v in venues}
    for authority in existing.values():
        route=authority["city_slug"]+"/"+authority["slug"]
        matched=by_route.get(route)
        if matched is None:
            # A brand new performance venue without an editorial profile
            # must not block publication of independently verified recite.
            # It will still be discoverable via the performance feed.
            continue
        if matched["id"]!=authority["id"]:
            if matched.get("canonical_venue_id") not in (None,authority["id"]):
                raise ValueError("conflicting canonical venue association")
            matched["canonical_venue_id"]=authority["id"]
        # A canonical venue is already evidenced by verified performances.
        matched["calendar_status"]="acquired"
    orgs=source.get("related_organizations",[])
    if not isinstance(orgs,list) or any(not isinstance(o,dict) or o.get("kind") not in ("festival","circuito","organizzatore") for o in orgs):
        raise ValueError("invalid non-venue organization")
    return {"schema_version":1,"reviewed_on":source["reviewed_on"],
            "venues":sorted(venues,key=lambda x:x["id"]),
            "related_organizations":orgs}


def publish(*, check:bool=False)->dict:
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    registry=json.loads(CANONICAL.read_text(encoding="utf-8"))
    result=build(source,registry)
    content=(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
    if check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes()!=content:
            raise ValueError("national venue directory requires regeneration")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_bytes(content)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=publish(check=args.check)
    print(json.dumps({"venues":len(result["venues"]),"organizations":len(result["related_organizations"])}))
