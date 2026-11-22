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
    OUTPUT, PUBLIC, classify, excluded_nonopera, reviewed_source_urls,
)
from scripts.publish_catalog_v2 import ROOT

HEALTH=ROOT/"data"/"candidate-reconciliation-health.json"
AUTO_STATES=frozenset({"needs_review","already_catalogued","excluded_nonopera",
                       "not_in_official_season"})

def verified_pisa_recital_urls(manifest:dict, detail:dict)->set[str]:
    """Recognize calendar event URLs already represented by a Pisa staging.

    Pisa publishes one official URL per recita alongside a different staging
    URL. Match a first-party captured observation to exactly one reviewed
    Pisa performance by canonical title, date, and local clock time.
    """
    import re
    from html import unescape
    from scripts.publish_catalog_v2 import normalized
    from opera_atlas.pisa_future_calendar import eligible_detail

    scheduled={}
    for production in manifest.get("productions",[]):
        if (production.get("municipality")!="Pisa"
                or production.get("venue")!="Teatro Verdi"
                or not str(production.get("source_url","")).startswith(
                    "https://teatrodipisa.it/spettacolo/")):
            continue
        for day,hour in production.get("dates",[]):
            scheduled.setdefault((day,hour),[]).append(normalized(production["title"]).replace("’", "'"))

    matched=set()
    for row in detail.get("evidence",[]):
        if not isinstance(row,dict) or row.get("source_key")!="pisa-future-calendar":
            continue
        url=row.get("source_url")
        digest=row.get("content_sha256")
        if (not isinstance(url,str) or not eligible_detail(url)
                or not isinstance(digest,str)
                or not re.fullmatch(r"[0-9a-f]{64}",digest)):
            continue
        facts=row.get("event_facts")
        if not isinstance(facts,list) or len(facts)!=1 or not isinstance(facts[0],dict):
            continue
        fact=facts[0]
        title=normalized(unescape(str(fact.get("event_title","")))).replace("’", "'").strip()
        instant=fact.get("starts_at")
        day=fact.get("date")
        if (not isinstance(instant,str) or not isinstance(day,str)
                or not instant.startswith(day+"T") or len(instant)<16):
            continue
        clock=instant[11:16]
        possible=scheduled.get((day,clock),[])
        if len(possible)!=1:
            continue
        canonical=possible[0]
        # A bounded "ossia" subtitle is legitimate; arbitrary prefixes aren't.
        if title==canonical or title.startswith(canonical+" ossia "):
            matched.add(url)
    return matched


def verified_livorno_recital_urls(manifest:dict, detail:dict)->set[str]:
    """Match the Goldoni's individual ticket URLs to an existing staging.

    The rolling collector observes one independently dated page per recita,
    while the 2026/27 opera season collector published a single staging URL.
    Match only a unique work+composer+venue+local showtime to a production
    verified from that exact season announcement; no title-only retirement.
    """
    import re
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from scripts.publish_catalog_v2 import normalized
    from opera_atlas.livorno_future_parser import eligible_detail

    official_season="https://www.goldoniteatro.it/notizie/la-stagione-lirica/"
    festival_sources={
        "https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana/",
        "https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana-2/",
    }
    rome=ZoneInfo("Europe/Rome")
    performances={}
    festival_performances={}
    for production in manifest.get("productions",[]):
        if production.get("municipality")!="Livorno":
            continue
        is_season=(production.get("venue")=="Teatro Goldoni"
                   and production.get("source_url")==official_season)
        is_festival=(production.get("venue")=="Piazza Goldoni"
                     and production.get("source_url") in festival_sources
                     and production.get("title")=="Cavalleria rusticana"
                     and production.get("composer")=="Pietro Mascagni")
        if not (is_season or is_festival):
            continue
        title=normalized(production.get("title","")).replace("’","'")
        composer=normalized(production.get("composer","")).replace("’","'")
        for day,clock in production.get("dates",[]):
            key=(title,composer,day,clock)
            if is_season:
                performances[key]=performances.get(key,0)+1
            if is_festival and day in {"2026-08-19","2026-08-20"} and clock=="21:30":
                festival_performances[key]=festival_performances.get(key,0)+1

    verified=set()
    for row in detail.get("evidence",[]):
        if (not isinstance(row,dict)
            or row.get("source_key")!="goldoni-livorno-rolling-lirica"):
            continue
        url=row.get("source_url")
        facts=row.get("event_facts")
        if (not isinstance(url,str) or not eligible_detail(url)
            or not re.fullmatch(r"[0-9a-f]{64}",
                                str(row.get("content_sha256","")))
            or row.get("status")!="needs_editorial_review"
            or not isinstance(facts,list) or len(facts)!=1
            or not isinstance(facts[0],dict)):
            continue
        fact=facts[0]
        venue=fact.get("venue")
        if venue not in ("Teatro Goldoni","Piazza Goldoni"):
            continue
        is_festival=(venue=="Piazza Goldoni"
                     and url in festival_sources
                     and fact.get("event_title")=="Cavalleria rusticana"
                     and fact.get("composer")=="Pietro Mascagni")
        if venue=="Piazza Goldoni" and not is_festival:
            continue
        try:
            day=fact["date"]
            moment=datetime.fromisoformat(fact["starts_at"])
            if moment.tzinfo is None or moment.utcoffset() is None:
                continue
            local=moment.astimezone(rome)
            if local.date().isoformat()!=day:
                continue
            clock=local.strftime("%H:%M")
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
        key=(normalized(str(fact.get("event_title",""))).replace("’","'"),
             normalized(str(fact.get("composer",""))).replace("’","'"),
             day,clock)
        if (festival_performances.get(key)==1 if is_festival
            else performances.get(key)==1):
            verified.add(url)
    return verified


def verified_haydn_cronaca_urls(manifest:dict,detail:dict)->set[str]:
    """Both ticket pages can reference one verified Trento production.

    Do not close a candidate from title alone. Require original first-party
    observation with checksum, exact opera/composer/venue and matched Italian
    date/time in exactly one canonical staging.
    """
    import re
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from scripts.publish_catalog_v2 import normalized
    from opera_atlas.haydn_rolling_opera import eligible_detail

    pages={
        "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini",
        "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini-2",
    }
    target="cronaca di un amore. callas e pasolini"
    allowed={"2027-01-29":"20:00","2027-01-31":"16:00"}
    productions=[p for p in manifest.get("productions",[])
                 if p.get("source_url") in pages
                 and p.get("municipality")=="Trento"
                 and p.get("venue")=="Teatro Sociale"
                 and normalized(p.get("title",""))==target
                 and normalized(p.get("composer",""))=="davide tramontano"
                 and all(allowed.get(d)==h for d,h in p.get("dates",[]))]
    if len(productions)!=1:return set()
    performance_dates=dict(productions[0]["dates"])
    matches=set()
    for row in detail.get("evidence",[]):
        if not isinstance(row,dict) or row.get("source_key")!="haydn-rolling-opera":
            continue
        url=row.get("source_url")
        facts=row.get("event_facts")
        if (url not in pages or not eligible_detail(url)
            or row.get("status")!="needs_editorial_review"
            or not re.fullmatch(r"[0-9a-f]{64}",str(row.get("content_sha256","")))
            or not isinstance(facts,list) or len(facts)!=1
            or not isinstance(facts[0],dict)):
            continue
        fact=facts[0]
        if (normalized(str(fact.get("event_title","")))!=target
            or normalized(str(fact.get("composer","")))!="davide tramontano"
            or fact.get("venue")!="Teatro Sociale"):
            continue
        try:
            day=fact["date"]
            instant=datetime.fromisoformat(fact["starts_at"])
            if instant.tzinfo is None or instant.utcoffset() is None:
                continue
            local=instant.astimezone(ZoneInfo("Europe/Rome"))
            if local.date().isoformat()!=day:continue
            clock=local.strftime("%H:%M")
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
        if performance_dates.get(day)==clock and allowed.get(day)==clock:
            matches.add(url)
    return matches


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
                     and re.fullmatch(r"https://www\.fondazionepetruzzelli\.it/eventi/[a-z0-9-]+/",url)
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


def verified_shared_page_identities(candidates:dict, detail:dict,
                                    manifest:dict, programs:dict)->tuple[set[str],set[tuple[str,str]]]:
    """Resolve candidates sharing one official season URL by identity, not URL.

    A production is verified only if each dated official observation belongs
    to an actually published solo staging. Programs require the identical
    source_key as well as all credited components and recite dates.
    """
    from scripts.publish_catalog_v2 import normalized
    from collections import Counter
    rows=candidates.get("candidates",[])
    url_counts=Counter(x.get("official_url") for x in rows)
    ambiguous={url for url,n in url_counts.items() if n>1}
    # A single source URL can document *several* independently ticketed
    # operas even if discovery has only one candidate for that page.
    # Never mark the page resolved merely because one of its works is live.
    ambiguous.update(x.get("official_url") for x in rows
                     if x.get("source_key")=="treviso-del-monaco-opera-2026-27")
    published=set()
    by_source={(x.get("source_key"),x.get("source_url")):x
               for x in detail.get("evidence",[]) if isinstance(x,dict)}
    by_url={}
    for product in manifest.get("productions",[]):
        by_url.setdefault(product.get("source_url"),[]).append(product)
    by_program={(p.get("source_key"),p.get("source_url")):p
                for p in programs.get("programs",[]) if isinstance(p,dict)}
    # Two approved collectors may discover the identical individual event:
    # the year-specific source and its year-independent successor. This is
    # provenance duplication, NOT a season page containing multiple operas.
    # Only exact known source-key pairs with one published production qualify.
    source_aliases=(
        frozenset({"filarmonico-verona-opera-2027",
                   "filarmonico-verona-rolling-opera"}),
        frozenset({"coccia-novara-opera-2027",
                   "coccia-novara-rolling-opera"}),
        frozenset({"macerata-festival-2027",
                   "macerata-festival-rolling"}),
        frozenset({"sassari-de-carolis-opera-2026",
                   "sassari-de-carolis-rolling-opera"}),
        frozenset({"ravenna-alighieri-cherubini-2027",
                   "ravenna-cherubini-rolling-opera"}),
    )
    grouped={}
    for row in rows:
        grouped.setdefault(row.get("official_url"),[]).append(row)
    for url,discovered in grouped.items():
        if (url not in ambiguous or len(discovered)!=2
                or frozenset(x.get("source_key") for x in discovered)
                   not in source_aliases
                or len(by_url.get(url,[]))!=1):
            continue
        production=by_url[url][0]
        # The staging must be real and dated; a mere identity-registry entry
        # is not sufficient to retire a discovery candidate.
        if not production.get("dates"):
            continue
        # Official pages can use a typographic apostrophe whereas event
        # evidence uses the ASCII equivalent. This is a spelling variant,
        # not a different work identity.
        def same_name(left,right):
            return normalized(left or "").replace("’","'")==normalized(right or "").replace("’","'")
        valid=True
        for item in discovered:
            observed=by_source.get((item["source_key"],url))
            if not observed or not observed.get("event_facts"):
                continue
            for fact in observed["event_facts"]:
                if (not isinstance(fact,dict)
                    or not same_name(fact.get("event_title"),
                                     production.get("title"))
                    or not same_name(fact.get("composer"),
                                     production.get("composer"))
                    or fact.get("date") not in
                       {d[0] for d in production["dates"]}):
                    valid=False
                    break
        if valid:
            published.update((item["source_key"],url) for item in discovered)
    for row in rows:
        key,url=row.get("source_key"),row.get("official_url")
        if url not in ambiguous:
            continue
        observed=by_source.get((key,url))
        if not observed:
            continue
        facts=observed.get("event_facts") or []
        if not isinstance(facts,list) or not facts:
            continue
        solo=by_url.get(url,[])
        def match_solo(fact):
            title=normalized(fact.get("event_title",""))
            composer=normalized(fact.get("composer",""))
            date=fact.get("date")
            return any(normalized(p.get("title",""))==title
                       and normalized(p.get("composer",""))==composer
                       and date in {x[0] for x in p.get("dates",[])}
                       for p in solo)
        if all(isinstance(fact,dict) and match_solo(fact) for fact in facts):
            published.add((key,url))
            continue
        program=by_program.get((key,url))
        if not program:
            continue
        components={(normalized(p["title"]),normalized(p["composer"]))
                    for p in program.get("components",[])}
        dates={r.get("local_date") for r in program.get("performances",[])}
        if all(isinstance(fact,dict)
               and (normalized(fact.get("event_title","")),
                    normalized(fact.get("composer",""))) in components
               and fact.get("date") in dates for fact in facts):
            published.add((key,url))
    return ambiguous,published


def reconcile(candidates:dict,verified_urls:set[str],*,
              other_season_urls:set[tuple[str,str]]|None=None,
              cagliari_season_urls:set[str]|None=None,
              ambiguous_urls:set[str]|None=None,
              identity_verified:set[tuple[str,str]]|None=None)->tuple[dict,dict]:
    if candidates.get("schema_version")!=1 or not isinstance(candidates.get("candidates"),list):
        raise ValueError("invalid season index candidate registry")
    updated={"schema_version":1,"candidates":[]}
    changes=[]
    for row in candidates["candidates"]:
        entry=row.copy()
        if entry.get("status") in AUTO_STATES:
            key=(entry["source_key"],entry["official_url"])
            if excluded_nonopera(entry["source_key"],entry["official_url"]):
                now="excluded_nonopera"
            elif (key in (other_season_urls or set())
                  and entry["official_url"] not in verified_urls):
                # Exact official dated proof that this source event belongs to
                # a different season takes priority over duplicate discovery
                # records of the same URL (e.g. two Petruzzelli indexes).
                now="not_in_official_season"
            elif entry["official_url"] in (ambiguous_urls or set()):
                # A season page may list several independent compositions.
                # A published Nabucco must not mark Don Pasquale or a new
                # commission at the same URL as already catalogued.
                # Identity-level proof is sufficient even if a separately
                # generated URL index has not yet caught up in this refresh.
                now=("already_catalogued" if key in (identity_verified or set())
                     else "needs_review")
            elif entry["official_url"] in verified_urls:
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
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    published.update(verified_pisa_recital_urls(manifest,detail))
    published.update(verified_livorno_recital_urls(manifest,detail))
    published.update(verified_haydn_cronaca_urls(manifest,detail))
    cagliari_2027=verified_cagliari_2027_brochure_urls()
    programs_path=ROOT/"public"/"catalog"/"programs.json"
    programs=json.loads(programs_path.read_text(encoding="utf-8")) if programs_path.exists() else {"programs":[]}
    ambiguous,identity_verified=verified_shared_page_identities(
        original,detail,manifest,programs)
    updated,report=reconcile(original,published,
                             other_season_urls=official_older,
                             cagliari_season_urls=cagliari_2027,
                             ambiguous_urls=ambiguous,
                             identity_verified=identity_verified)
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
