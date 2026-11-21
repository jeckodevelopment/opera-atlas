"""Finalize candidate states in the same import transaction, before publication.

Only verified, generated canonical opera and program feeds can mark a candidate
as already catalogued. Preserve audit history and ensure subsequent refreshes
rebuild the same public feeds without a manual post-import reconciliation.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import (
    OUTPUT, PUBLIC, classify, reviewed_source_urls,
)
from scripts.publish_catalog_v2 import ROOT

HEALTH=ROOT/"data"/"candidate-reconciliation-health.json"
AUTO_STATES=frozenset({"needs_review","already_catalogued","excluded_nonopera",
                       "not_in_official_season"})

def verified_secondary_source_urls(manifest:dict, evidence:dict)->set[str]:
    """Recognize complete independently verified second-source theater dates.

    A source only matches an existing circuit production if every scheduled
    performance has independently validated time evidence from that same
    approved official venue URL. Partial or ambiguous observations stay open.
    """
    from scripts.build_verified_catalog import TIME_EVIDENCE_URLS,validate_time_evidence
    validate_time_evidence(manifest,evidence)
    matches=set()
    times=evidence["times"]
    for production in manifest["productions"]:
        days=[day for day,_ in production["dates"]]
        if not days:
            continue
        rows=[times.get(production["key"]+"|"+day) for day in days]
        if any(row is None for row in rows):
            continue
        urls={row["url"] for row in rows}
        if len(urls)!=1:
            continue
        url=next(iter(urls))
        if url in TIME_EVIDENCE_URLS.get(production["key"],set()):
            matches.add(url)
    return matches

def verified_other_season_evidence(evidence:dict)->set[tuple[str,str]]:
    """Only exact source-bound dated official season proof can retire a URL."""
    import re
    result=set()
    for row in evidence.get("evidence",[]):
        if not isinstance(row,dict) or row.get("status")!="out_of_monitored_season":
            continue
        key,url,season=row.get("source_key"),row.get("source_url"),row.get("official_season")
        rome=(key=="opera-roma-season-2026-27"
              and isinstance(url,str) and url.startswith("https://www.operaroma.it/spettacoli/")
              and re.fullmatch(r"20[0-9]{2}/20[0-9]{2}",season or "")
              and season!="2026/2027")
        petruzzelli=(key in ("petruzzelli-opera-2026","petruzzelli-opera-2027")
                     and isinstance(url,str)
                     and re.fullmatch(r"https://www\\.fondazionepetruzzelli\\.it/eventi/[a-z0-9-]+/",url)
                     and re.fullmatch(r"20[0-9]{2}",season or "")
                     and season!=key.rsplit("-",1)[-1])
        if (not (rome or petruzzelli)
                or not re.fullmatch(r"[a-f0-9]{64}",
                                    row.get("content_sha256",""))):
            continue
        result.add((row["source_key"],row["source_url"]))
    return result


def verified_cagliari_2027_brochure_urls()->set[str]:
    """Official 2027 brochure is the authoritative finite season boundary.

    Never use the site's generic all-years opera index to invent events in
    2027. This evidence is source-scoped, year-scoped and validated before
    retiring any legacy event link; a refreshed brochure automatically
    reopens a previously archived candidate if it adds that production.
    """
    import re
    from datetime import date
    from opera_atlas.cagliari_detail_parser import BROCHURE
    data=json.loads(BROCHURE.read_text(encoding="utf-8"))
    official=("https://www.liricocagliari.it/wp-content/uploads/2026/11/"
              "Pieghevole-Stagione-Opera-2027-21x15-4-ante.pdf")
    if (data.get("schema_version")!=1 or data.get("year")!=2027
            or data.get("official_schedule_url")!=official
            or not isinstance(data.get("works"),list)
            or len(data["works"])<3):
        raise ValueError("invalid official Cagliari season proof")
    urls=set()
    for item in data["works"]:
        slug=item.get("slug")
        if (not isinstance(slug,str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug)
            or not isinstance(item.get("title"),str) or not item["title"].strip()
            or not isinstance(item.get("composer"),str) or not item["composer"].strip()
            or not isinstance(item.get("dates"),list) or not item["dates"]):
            raise ValueError("incomplete individually verified Cagliari work")
        for row in item["dates"]:
            if (not isinstance(row,list) or len(row)!=2
                or not isinstance(row[0],str) or not row[0].startswith("2027-")
                or not isinstance(row[1],str)
                or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",row[1])):
                raise ValueError("invalid first-party Cagliari schedule entry")
            date.fromisoformat(row[0])
        url="https://www.liricocagliari.it/evento/"+slug+"/"
        if url in urls:
            raise ValueError("duplicate Cagliari season opera")
        urls.add(url)
    return urls


def reconcile(candidates:dict,verified_urls:set[str],*,
              other_season_urls:set[tuple[str,str]]|None=None,
              cagliari_season_urls:set[str]|None=None)->tuple[dict,dict]:
    if candidates.get("schema_version")!=1 or not isinstance(candidates.get("candidates"),list):
        raise ValueError("invalid season index candidate registry")
    updated={"schema_version":1,"candidates":[]}
    changes=[]
    for row in candidates["candidates"]:
        entry=row.copy()
        if entry.get("status") in AUTO_STATES:
            key=(entry["source_key"],entry["official_url"])
            if entry["official_url"] in verified_urls:
                now="already_catalogued"
            elif (entry["source_key"]=="lirico-cagliari-opera-2027"
                  and cagliari_season_urls is not None):
                # A candidate not in the verified 2027 programme is an
                # auditable historical/global-index listing, not 2027 opera.
                # When the programme adds it, restore review automatically.
                now=("needs_review" if entry["official_url"] in cagliari_season_urls
                     else "not_in_official_season")
            elif key in (other_season_urls or set()):
                now="not_in_official_season"
            elif entry["status"]=="not_in_official_season":
                now=entry["status"]  # Historical proof remains in the audit.
            else:
                now=classify(entry["source_key"],entry["official_url"],verified_urls)
            if now!=entry["status"]:
                changes.append({"candidate_id":entry["id"],"before":entry["status"],"after":now})
            entry["status"]=now
        # Preserve first_seen / last_seen, source and ID for accountability.
        updated["candidates"].append(entry)
    states={}
    for row in updated["candidates"]:
        states[row["status"]]=states.get(row["status"],0)+1
    return updated,{"total":len(updated["candidates"]),"states":states,
                    "changes":changes}

def run(*,check:bool=False):
    original=json.loads(OUTPUT.read_text(encoding="utf-8"))
    from scripts.build_verified_catalog import MANIFEST,TIME_EVIDENCE
    published=reviewed_source_urls()
    if TIME_EVIDENCE.exists():
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        times=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
        published.update(verified_secondary_source_urls(manifest,times))
    from scripts.collect_candidate_details import OUTPUT as DETAILS
    detail=json.loads(DETAILS.read_text(encoding="utf-8")) if DETAILS.exists() else {"evidence":[]}
    official_older=verified_other_season_evidence(detail)
    cagliari_2027=verified_cagliari_2027_brochure_urls()
    updated,report=reconcile(original,published,
                             other_season_urls=official_older,
                             cagliari_season_urls=cagliari_2027)
    if check:
        if updated!=original:
            raise ValueError("discovery queue out of sync with canonical catalog")
        if not PUBLIC.exists() or json.loads(PUBLIC.read_text(encoding="utf-8"))!=updated:
            raise ValueError("public discovery queue out of sync")
    else:
        _write_atomic(OUTPUT,updated)
        _write_atomic(PUBLIC,updated)
        _write_atomic(HEALTH,{"schema_version":1,
            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **report})
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    print(json.dumps(run(check=args.check),ensure_ascii=False))
if __name__=="__main__":
    main()
