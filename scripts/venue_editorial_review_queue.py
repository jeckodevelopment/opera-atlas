"""Report canonical venues awaiting researched editorial profiles.

A verified production is not withheld while its theatre history or photo
is being researched. This report contains only identity and source provenance;
it does not fabricate street addresses, history or image rights.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"data/identity-registry.json"
FACTS=ROOT/"data/verified-launch-catalog.json"
PROFILES=ROOT/"site/theatre-profiles.json"
OUTPUT=ROOT/"data/venue-editorial-review-queue.json"


def build(registry:dict,facts:dict,profiles:dict)->dict:
    if not isinstance(registry.get("venues"),dict) or not isinstance(
            facts.get("productions"),list) or not isinstance(
            profiles.get("venues"),dict):
        raise ValueError("invalid venue editorial inputs")
    sources={}
    for production in facts["productions"]:
        if not production.get("dates"):
            continue
        url=production.get("source_url")
        if not isinstance(url,str) or not url.startswith("https://"):
            continue
        key=production["municipality"]+"|"+production["venue"]
        sources.setdefault(key,set()).add(url)
    queue=[]
    for key,venue in registry["venues"].items():
        displayed=venue.get("city","")+"|"+venue.get("name","")
        # Historical source keys can use a short theatre name, while the
        # canonical display uses its full official name (e.g. Savona).
        # Accept this only when the full official display profile exists.
        if key!=displayed and displayed not in profiles["venues"]:
            raise ValueError("inconsistent canonical venue identity")
        if key in profiles["venues"] or displayed in profiles["venues"]:
            continue
        if key not in sources:
            raise ValueError("unprofiled venue without verified staging evidence: "+key)
        queue.append({
            "venue_id":venue["id"],"city":venue["city"],"name":venue["name"],
            "route_slug":venue["city_slug"]+"/"+venue["slug"],
            "source_urls":sorted(sources[key]),
            "missing":["editorial_profile","verified_address","venue_history",
                       "licensed_photo"],
            "status":"editorial_review_pending",
        })
    queue.sort(key=lambda x:(x["city"].casefold(),x["name"].casefold(),x["venue_id"]))
    return {"schema_version":1,"purpose":"nonblocking_verified_venue_editorial",
            "count":len(queue),"venues":queue}


def run(*,check:bool=False)->dict:
    data=build(json.loads(REGISTRY.read_text(encoding="utf-8")),
               json.loads(FACTS.read_text(encoding="utf-8")),
               json.loads(PROFILES.read_text(encoding="utf-8")))
    content=(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    if check:
        if not OUTPUT.exists() or OUTPUT.read_bytes()!=content:
            raise ValueError("venue editorial review queue is stale")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_bytes(content)
    return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    print(json.dumps({"pending":run(check=args.check)["count"]}))


if __name__=="__main__":
    main()
