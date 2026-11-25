"""2026 national venue × month coverage matrix, diagnostics only.

An observed performance is not a complete season. Only individually
attributable source-credited recite qualify as observations; generic index
events and non-opera screening never count toward a venue's opera denominator.
Never mutate published catalog, registry, official sources or editorial data.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VENUES = ROOT / "data/venue-directory.json"
REGISTRY = ROOT / "data/identity-registry.json"
MANIFEST = ROOT / "data/verified-launch-catalog.json"
PROGRAMS = ROOT / "public/catalog/programs.json"
HISTORICAL = ROOT / "data/historical-2026-official-evidence.json"
H1 = ROOT / "public/diagnostics/atlas-2026-jan-jun-official-archive.json"
H1_RECONCILIATION = ROOT / "public/diagnostics/atlas-2026-jan-jun-reconciliation.json"
H2 = ROOT / "public/diagnostics/atlas-2026-retrospective-reconciliation.json"
SEEDS = ROOT / "data/official-2026-retrospective-season-seeds.json"
SEED_SCAN = ROOT / "public/diagnostics/atlas-2026-jan-jun-official-archive.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-venue-month-coverage.json"
OFFICIAL_ZERO_VENUE_LEADS = ROOT / "data/official-2026-zero-venue-opera-leads.json"


def canonical(text):
    text = unicodedata.normalize("NFKD", str(text or "").casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(
        c for c in text if not unicodedata.combining(c))).strip()


def url_identity(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return None
        return parsed.hostname.lower().removeprefix("www."), parsed.path.rstrip("/")
    except ValueError:
        return None


def source_slot(entry):
    day = entry.get("date")
    hour = entry.get("time")
    if not isinstance(day, str) or not re.fullmatch(r"2026-\d{2}-\d{2}", day):
        return None
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    if not isinstance(hour, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", hour):
        return None
    return day, hour


def validated_venue_leads(document, venues):
    """Freeze primary opera showtimes without treating them as published."""
    from urllib.parse import urlsplit
    if (document.get("schema_version") != 1 or document.get("year") != 2026
            or not isinstance(document.get("records"),list)):
        raise ValueError("invalid 2026 zero-venue official lead evidence")
    by_id={v["id"]:v for v in venues}
    approved={
        "oa-v-000002": ("Como", "Teatro Sociale", "teatrosocialecomo.it"),
        "oa-v-000007": ("Verona", "Arena di Verona", "www.arena.it"),
        "oa-vd-000036": ("Macerata", "Arena Sferisterio", "www.sferisterio.it"),
        "oa-vd-000019": ("Verona", "Teatro Filarmonico", "www.arena.it"),
        "oa-vd-000034": ("Torre del Lago Puccini", "Gran Teatro Giacomo Puccini", "www.puccinifestival.it"),
        "oa-vd-000047": ("Messina", "Teatro Vittorio Emanuele", "www.teatrovittorioemanuele.it"),
        "oa-vd-000049": ("Cagliari", "Teatro Lirico di Cagliari", "www.liricocagliari.it"),
        "oa-v-000005": ("Cremona", "Teatro Ponchielli", "www.comune.cremona.it"),
        "oa-v-000011": ("Novara", "Teatro Coccia", "www.fondazioneteatrococcia.it"),
        "oa-vd-000031": ("Lucca", "Teatro del Giglio Giacomo Puccini", "www.teatrodelgigliogiacomopuccini.it"),
        "oa-vd-000057": ("Mantova", "Teatro Sociale di Mantova", "www.teatrosocialemantova.it"),
        "oa-v-000014": ("Ravenna", "Teatro Dante Alighieri", "artbonus.gov.it"),
        "oa-vd-000060": ("Sabbioneta", "Teatro all'Antica", "www.comune.sabbioneta.mn.it"),
        "oa-vd-000022": ("Rovigo", "Teatro Sociale", "www.comune.rovigo.it"),
        "oa-vd-000056": ("Roma", "Teatro Nazionale", "www.operaroma.it"),
        "oa-vd-000053": ("Bologna", "Teatro Auditorium Manzoni", "www.tcbo.it"),
        "oa-vd-000015": ("Asti", "Teatro Alfieri", "www.comune.asti.it"),
    }
    # Exact institutional schedule supplements, scoped to the reviewed venue.
    supplemental={
        "oa-vd-000034":"https://www.comune.viareggio.lu.it/eventi/CLT-Puccini-Festival-2031.html",
        "oa-v-000014":"https://www.turismo.ra.it/eventi/teatro-opera-danza/stagione-opera-e-danza/",
    }
    result=defaultdict(list)
    seen=set()
    for record in document["records"]:
        vid=record.get("venue_id")
        if vid not in approved:
            raise ValueError("unreviewed venue for 2026 opera evidence")
        city,venue,host=approved[vid]
        entity=by_id.get(vid)
        if (entity is None or record.get("city")!=city
                or record.get("venue")!=venue or entity["city"]!=city
                or entity["name"]!=venue):
            raise ValueError("2026 venue identity mismatch")
        url=record.get("official_url")
        parsed=urlsplit(url) if isinstance(url,str) else None
        if (not parsed or parsed.scheme!="https" or (parsed.hostname!=host and url!=supplemental.get(vid))
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError("2026 venue lead requires exact primary hostname")
        if (not isinstance(record.get("title"),str) or not record["title"]
                or not isinstance(record.get("composer"),str) or not record["composer"]
                or not isinstance(record.get("dates"),list) or not record["dates"]):
            raise ValueError("unverified lead work or dates")
        for day,clock in record["dates"]:
            if (not isinstance(day,str) or date.fromisoformat(day).isoformat()!=day
                    or not day.startswith("2026-") or
                    (clock is not None and source_slot({"date":day,"time":clock}) is None)):
                raise ValueError("unverified official venue lead date or clock")
            key=(vid,canonical(record["title"]),day,clock)
            if key in seen:raise ValueError("duplicate verified 2026 venue lead")
            seen.add(key)
            result[vid].append({"date":day,"time":clock,
                "title":record["title"],"composer":record["composer"],
                "official_url":url,"publication_review_required":True,
                "official_source_verified":True,
                "complete_month_verified":False})
    return result


def reconcile_lead(lead, vid, candidates):
    """Conservative identity-aware comparison; never infer an unknown clock."""
    title, composer = canonical(lead['title']), canonical(lead['composer'])
    same_day = [c for c in candidates if c['date'] == lead['date']]
    same_work = [c for c in same_day if title and composer and
                 canonical(c['title']) == title and canonical(c['composer']) == composer]
    local = [c for c in same_work if c['venue_id'] == vid]
    exact = [c for c in local if lead['time'] is not None and c['time'] == lead['time']]
    if exact:
        return 'exact_match'
    if local:
        return 'clock_review'
    if same_work:
        return 'venue_review'
    if any(c['venue_id'] == vid and (canonical(c['title']) == title or
           lead['time'] is None or c['time'] == lead['time']) for c in same_day):
        return 'identity_review'
    return 'publication_candidate' if lead['time'] is not None else 'clock_review'


def build_matrix(venues, registry, manifest, programs, historical, h1, h2,
                 seeds, seed_scan, venue_leads=None):
    venue_rows = venues.get("venues", [])
    if venue_leads is None:
        venue_leads={"schema_version":1,"year":2026,"records":[]}
    verified_leads=validated_venue_leads(venue_leads,venue_rows)

    if len(venue_rows) != 72 or len({v["id"] for v in venue_rows}) != len(venue_rows):
        raise ValueError("expected 72 distinct reviewed venue IDs")
    by_id = {v["id"]: v for v in venue_rows}
    registry_venues = registry["venues"]
    registry_to_directory = {}
    unlinked_registry = []
    for rv in registry_venues.values():
        target = next((v for v in venue_rows
                       if v["id"] == rv["id"] or v.get("canonical_venue_id") == rv["id"]), None)
        if target is None:
            matches = [v for v in venue_rows if
                       canonical(v["city"]) == canonical(rv["city"]) and
                       canonical(v["name"]) == canonical(rv["name"])]
            if len(matches) == 1:
                target = matches[0]
        if target is not None:
            registry_to_directory[rv["id"]] = target["id"]
        else:
            unlinked_registry.append({"venue_id": rv["id"], "name": rv["name"],
                                      "city": rv["city"]})
    # A physical venue and its exact local calendar slot are the primary
    # units; multiple sources/works can share a single double-bill performance.
    published = defaultdict(lambda: defaultdict(set))
    published_sources = defaultdict(set)
    unresolved_published = []
    from scripts.build_verified_catalog import TIME_EVIDENCE, validate_time_evidence
    verified_times = validate_time_evidence(manifest,json.loads(TIME_EVIDENCE.read_text(encoding="utf-8")))
    reconciliation_candidates = []
    for production in manifest.get("productions", []):
        staging = registry["stagings"].get(production.get("key"))
        vid = (registry_to_directory.get(staging["venue_id"])
               if isinstance(staging, dict) else None)
        if vid is None:
            unresolved_published.append({
                "source_url": production.get("source_url"),
                "title": production.get("title"), "venue": production.get("venue"),
                "city": production.get("municipality")})
            continue
        for item in production.get("dates", []):
            if not isinstance(item, list) or len(item) != 2:
                continue
            from scripts.build_verified_catalog import replica_registry_key
            rk = replica_registry_key(production,item[0],item[1])
            slot = source_slot({"date": item[0], "time": verified_times.get(rk,{}).get("time",item[1])})
            if slot:
                published[vid][slot[0][:7]].add(slot)
                published_sources[(vid, slot)].add(url_identity(production["source_url"]))
                reconciliation_candidates.append(dict(venue_id=vid,date=slot[0],time=slot[1],
                    title=production.get("title"),composer=production.get("composer")))
    # Programmes: no double counting with standard productions.
    unlinked_programs = []
    for p in programs.get("programs", []):
        matches = [v for v in venue_rows if
                   canonical(v["city"]) == canonical(p.get("municipality")) and
                   canonical(v["name"]) == canonical(p.get("venue"))]
        if len(matches) != 1:
            unlinked_programs.append({"venue": p.get("venue"),
                                      "city": p.get("municipality")})
            continue
        vid = matches[0]["id"]
        for item in p.get("performances", []):
            stamp = item.get("starts_at")
            day = item.get("local_date")
            hour = stamp[11:16] if isinstance(stamp, str) and stamp.startswith(str(day)+"T") else None
            slot = source_slot({"date": day, "time": hour})
            if slot:
                published[vid][day[:7]].add(slot)
                published_sources[(vid, slot)].add(url_identity(p.get("source_url")))
                for component in p.get("components", []):
                    reconciliation_candidates.append(dict(venue_id=vid,date=slot[0],time=slot[1],
                        title=component.get("title"),composer=component.get("composer")))
                components=p.get("components", [])
                if components:
                    reconciliation_candidates.append(dict(venue_id=vid,date=slot[0],time=slot[1],
                        title=" / ".join(str(c.get("title") or "") for c in components),
                        composer=" / ".join(str(c.get("composer") or "") for c in components)))
    historic = defaultdict(lambda: defaultdict(set))
    for record in historical.get("records", []):
        vid = record.get("venue_id")
        if vid not in by_id or record.get("audience") != "general_public":
            continue
        for item in record.get("dates", []):
            slot = source_slot(item)
            if slot:
                historic[vid][slot[0][:7]].add(slot)

    # H1 has explicit source-credited opera/composer/venue and clocks.
    # The historical audit's old 'unpublished' classification becomes stale
    # when later catalogue PRs merge; always compare CURRENT canonical slots.
    observed = defaultdict(lambda: defaultdict(set))
    observation_details = defaultdict(dict)
    ambiguous_source_facts = []
    review_formats = {"il piccolo principe",
                      "piccolo orso e la montagna di ghiaccio"}
    for fact in h1.get("observations", []):
        candidate_vid = fact.get("venue_id_candidate")
        # The source-index belongs to the Fenice institution, but individual
        # performance pages may explicitly identify Teatro Malibran, a
        # separate canonical physical venue. The original matrix wrongly
        # counted those as Fenice performances.
        explicit = [v for v in venue_rows
                    if canonical(v.get("name")) == canonical(fact.get("venue"))
                    and candidate_vid in by_id
                    and canonical(v.get("city")) == canonical(by_id[candidate_vid]["city"])]
        vid = explicit[0]["id"] if len(explicit)==1 else candidate_vid
        slot = source_slot({"date": fact.get("date"),
                            "time": (fact.get("starts_at") or "")[11:16]})
        if vid not in by_id or not slot or slot[0] >= "2026-07-01":
            continue
        if canonical(fact.get("event_title")) in review_formats:
            ambiguous_source_facts.append({"venue_id": vid, "date": slot[0],
                                           "title": fact.get("event_title"),
                                           "reason": "family_or_school_scope_review"})
            continue
        month = slot[0][:7]
        observed[vid][month].add(slot)
        observation_details[(vid,slot)] = {
            "source_url": fact.get("official_url"),
            "title": fact.get("event_title"),
            "composer": fact.get("composer"),
        }
    for vid, month_slots in historic.items():
        for month, slots in month_slots.items():
            observed[vid][month].update(slots)
    # The broader Jul-Dec scan is a mixture of concerts and other genres:
    # DO NOT add 64 scanned observations to an opera denominator.
    # Report them by state in a separate, explicitly unverified summary.
    h2_counts = dict(Counter(x.get("status", "unknown")
                             for x in h2.get("observations", [])))
    sources_by_venue = defaultdict(list)
    scan_rows = {r["key"]:r for r in seed_scan.get("seed_results", [])}
    for seed in seeds.get("seeds", []):
        vid = seed.get("venue_id")
        if vid not in by_id:
            continue
        scan = scan_rows.get(seed.get("key"), {})
        sources_by_venue[vid].append({
            "source_key": seed["key"], "season": seed["season"],
            "official_url": seed["url"],
            "fetch_status": scan.get("status", "not_attempted"),
            "failure": scan.get("failure"),
            "detail_links_discovered": len(scan.get("links", [])),
            "scope": ("historical_2025_26" if seed["season"]=="2025/26"
                      else "2026_calendar"),
            "source_exhaustiveness_verified": False,
        })
    # Exact source leads are NOT included in observed/published denominators.
    # With no officially supported start time, a calendar date is still
    # useful evidence but never becomes a fabricated time-specific recita.
    lead_counts=Counter()
    unpublished_leads=defaultdict(list)
    reconciliation=[]
    reconciliation_counts=Counter()
    for vid, entries in verified_leads.items():
        for lead in entries:
            state=reconcile_lead(lead,vid,reconciliation_candidates)
            row=dict(lead,venue_id=vid,reconciliation_status=state,
                     publication_review_required=state!="exact_match")
            reconciliation.append(row)
            reconciliation_counts[state]+=1
            if state!="exact_match":
                unpublished_leads[vid].append(row)
                lead_counts[vid]+=1
    rows = []
    counts = Counter()
    for v in venue_rows:
        vid = v["id"]
        for m in range(1, 13):
            month = f"2026-{m:02d}"
            pub = published[vid][month]
            obs = observed[vid][month]
            missing = sorted(obs - pub)
            # 'no observations' can mean access denied, historical pages
            # removed, no opera on that month, or simply a missing parser.
            if missing:
                status = "official_observations_require_reconciliation"
            elif pub:
                status = "published_dates_not_exhaustively_verified"
            elif obs:
                status = "source_dates_without_publication"
            else:
                status = "coverage_not_established"
            counts[status] += 1
            rows.append({
                "venue_id":vid, "venue":v["name"],"city":v["city"],
                "region":v.get("region"),"month":month,
                "published_showtimes":len(pub),
                "source_observed_opera_showtimes":len(obs),
                "observed_already_published":len(obs & pub),
                "observed_not_in_publication":len(missing),
                "observed_unpublished_dates":[{"date":d,"time":h}
                                              for d,h in missing],
                "official_unpublished_opera_leads":[x for x in unpublished_leads[vid]
                                                 if x["date"][:7]==month],
                "official_unpublished_opera_lead_count":sum(
                    x["date"][:7]==month for x in unpublished_leads[vid]),
                "historical_sources_checked":sources_by_venue[vid] if m<=6 else [],
                "source_exhaustiveness_verified":False,
                "complete_month_verified":False,
                "status":status,
            })
    # Audit priorities are evidence statuses, not declarations of missing recite.
    # In particular, 'acquired' refers to catalogue acquisition status, not
    # independent historical exhaustiveness of any monthly calendar.
    venue_priorities = []
    venue_status_counts = Counter()
    for v in venue_rows:
        vid = v["id"]
        venue_months = [r for r in rows if r["venue_id"] == v["id"]]
        total = sum(r["published_showtimes"] for r in venue_months)
        status = v.get("calendar_status", "unknown")
        if total == 0:
            venue_status_counts[status] += 1
        venue_priorities.append({
            "venue_id": v["id"], "venue": v["name"],
            "city": v["city"], "region": v.get("region"),
            "calendar_status": status,
            "monitoring_status": v.get("monitoring_status"),
            "published_2026_showtimes": total,
            "published_months": sum(bool(r["published_showtimes"]) for r in venue_months),
            "official_verified_opera_lead_count":len(verified_leads[vid]),
            "official_unpublished_opera_lead_count":lead_counts[vid],
            "official_opera_lead_review_required":lead_counts[vid]>0,
            "historical_source_seed_count": len(sources_by_venue[v["id"]]),
            "official_historical_sources": [x["official_url"] for x in sources_by_venue[v["id"]]],
            "audit_priority": ("zero_published_with_official_opera_leads" if total == 0 and lead_counts[vid]>0
                               else "zero_published_acquired_calendar" if total == 0 and status == "acquired"
                               else "zero_published_calendar_not_acquired" if total == 0
                               else "published_not_exhaustively_verified"),
            "missing_recite_certified": False,
        })
    venue_priorities.sort(key=lambda v: (v["published_2026_showtimes"] != 0,
                                         v["calendar_status"] != "acquired",
                                         v["city"], v["venue"]))
    return {
        "schema_version":1, "year":2026,
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,
        "venue_count":len(venue_rows),"months_per_venue":12,
        "cell_count":len(rows),
        "complete_venue_months":0,"complete_annual_venues":0,
        "status_counts":dict(sorted(counts.items())),
        "zero_published_venue_count":sum(venue_status_counts.values()),
        "zero_published_by_calendar_status":dict(sorted(venue_status_counts.items())),
        "venue_audit_priorities":venue_priorities,
        "official_2026_opera_lead_venue_count":sum(
            bool(verified_leads[v["id"]]) for v in venue_rows),
        "official_2026_opera_lead_count":sum(map(len,verified_leads.values())),
        "official_unpublished_opera_lead_count":sum(lead_counts.values()),
        "official_lead_reconciliation_counts":dict(sorted(reconciliation_counts.items())),
        "official_lead_reconciliation":reconciliation,
        "official_lead_venues_with_zero_published":sum(
            bool(verified_leads[v["id"]]) and
            not any(r["published_showtimes"] for r in rows if r["venue_id"]==v["id"])
            for v in venue_rows),
        "published_2026_showtimes":sum(x["published_showtimes"] for x in rows),
        "observed_2026_opera_showtimes":sum(x["source_observed_opera_showtimes"] for x in rows),
        "unmatched_source_showtimes":sum(x["observed_not_in_publication"] for x in rows),
        "h1_scope_review":ambiguous_source_facts,
        "h2_mixed_genre_observation_counts":h2_counts,
        "unlinked_registry_venues":unlinked_registry,
        "unlinked_published_productions":unresolved_published,
        "unlinked_programs":unlinked_programs,
        "rows":rows,
        "warning":"Counts are source-observed and published showtimes, never exhaustive official calendars. Zero does not imply no scheduled performances. Only an independently validated complete season can certify a venue-month.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args=ap.parse_args()
    def load(path): return json.loads(path.read_text(encoding="utf-8"))
    report=build_matrix(*(load(p) for p in (
        VENUES,REGISTRY,MANIFEST,PROGRAMS,HISTORICAL,H1,H2,SEEDS,SEED_SCAN)),
        load(OFFICIAL_ZERO_VENUE_LEADS))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({
        "venue_count":report["venue_count"],"cell_count":report["cell_count"],
        "published":report["published_2026_showtimes"],
        "observed":report["observed_2026_opera_showtimes"],
        "unmatched":report["unmatched_source_showtimes"],
        "states":report["status_counts"]},ensure_ascii=False))


if __name__=="__main__":
    main()
