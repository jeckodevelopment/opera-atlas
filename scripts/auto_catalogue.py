"""Autonomous publication of unambiguous, official, already-known opera recite.

No manual reconciliation. A candidate is accepted only if its official production
URL, canonical work+composer, venue, and explicit dates agree with the already
verified sources. New unknown works cannot be misidentified by title alone.
"""
from __future__ import annotations
import copy
import hashlib
import json
from datetime import date
from urllib.parse import urlsplit
from scripts.build_verified_catalog import MANIFEST
from scripts.daily_ingest import _next_replica_id, _write_atomic
from scripts.publish_catalog_v2 import REGISTRY, assemble, normalized, slugify
from scripts.discover_season_indexes import CONFIG, validate_config, eligible, OUTPUT as INDEX
from scripts.collect_candidate_details import OUTPUT as DETAILS
from pathlib import Path

ROOT=MANIFEST.parents[1]
SOURCE_ALLOWLIST=ROOT/"data"/"auto-source-urls.json"
HEALTH=ROOT/"data"/"autonomous-catalogue-health.json"
VENUE_BY_SOURCE={
    "martina-valle-itria-2026":("Martina Franca","Palazzo Ducale di Martina Franca"),
    "trapani-luglio-musicale-2026":("Trapani","Teatro Giuseppe Di Stefano"),
    "haydn-rolling-opera":("Bolzano","Teatro Comunale di Bolzano"),
    "asti-alfieri-rolling-opera":("Asti","Teatro Alfieri"),
    "savona-giocosa-rolling-opera":("Savona","Teatro Chiabrera"),
    "sassari-de-carolis-rolling-opera":("Sassari","Teatro Comunale di Sassari"),
    "lecce-apollo-pinocchio-2026":("Lecce","Teatro Apollo"),
    "lecce-provincia-politeama-2026":("Lecce","Teatro Politeama Greco"),
    "lecce-politeama-opera-2026":("Lecce","Teatro Politeama Greco"),
    "rovigo-sociale-opera-2026-27":("Rovigo","Teatro Sociale"),
    "padova-verdi-opera-2026":("Padova","Teatro Verdi"),
    "treviso-del-monaco-opera-2026-27":("Treviso","Teatro Comunale Mario del Monaco"),
    "scala-season-2026-27":("Milano","Teatro alla Scala"),
    "verdi-trieste-season-2026-27":("Trieste","Teatro Lirico Giuseppe Verdi"),
    "lirico-cagliari-opera-2027":("Cagliari","Teatro Lirico di Cagliari"),
    "bellini-catania-opera-2026-27":("Catania","Teatro Massimo Bellini"),
    "modena-teatro-opera-2026-27":("Modena","Teatro Comunale Pavarotti-Freni"),
    "puccini-torre-del-lago-2027":("Torre del Lago Puccini","Gran Teatro Giacomo Puccini"),
    "spoleto-tls-lirica-2026":("Spoleto","Teatro Nuovo Gian Carlo Menotti"),
    "chieti-marrucino-lirica-2026":("Chieti","Teatro Marrucino"),
    "modena-opera-2026-27":("Modena","Teatro Comunale Pavarotti-Freni"),
    "giglio-lucca-opera-2026-27":("Lucca","Teatro del Giglio Giacomo Puccini"),
    "piacenza-opera-2026-27":("Piacenza","Teatro Municipale"),
    "reggio-valli-opera-2026-27":("Reggio Emilia","Teatro Valli"),
    "jesi-trittico-opera-2026":("Jesi","Teatro Giovan Battista Pergolesi"),
    "jesi-don-pasquale-opera-2026":("Jesi","Teatro Giovan Battista Pergolesi"),
    "jesi-esecuzione-opera-2026":("Jesi","Teatro Giovan Battista Pergolesi"),
    "jesi-nabucco-opera-2026":("Jesi","Teatro Giovan Battista Pergolesi"),
    "ancona-elisir-opera-2026":("Ancona","Teatro delle Muse"),
    "ancona-cavalleria-program-2026":("Ancona","Teatro delle Muse"),
    "goldoni-livorno-rolling-lirica":("Livorno","Teatro Goldoni"),
    "goldoni-livorno-dido-2026-27":("Livorno","Teatro Goldoni"),
    "goldoni-livorno-otello-2026-27":("Livorno","Teatro Goldoni"),
    "goldoni-livorno-elisir-2026-27":("Livorno","Teatro Goldoni"),
    "ferrara-macbeth-opera-2026-27":("Ferrara","Teatro Comunale Claudio Abbado"),
    "ferrara-barbiere-opera-2026-27":("Ferrara","Teatro Comunale Claudio Abbado"),
    "ferrara-dido-opera-2026-27":("Ferrara","Teatro Comunale Claudio Abbado"),
    "ferrara-clemenza-opera-2026-27":("Ferrara","Teatro Comunale Claudio Abbado"),
    "ferrara-boccanegra-opera-2026-27":("Ferrara","Teatro Comunale Claudio Abbado"),
    "arena-festival-2027":("Verona","Arena di Verona"),
    # Independent physical venues already listed in the reviewed national
    # directory; they are not Arena di Verona or another city's Teatro Verdi.
    "filarmonico-verona-opera-2027":("Verona","Teatro Filarmonico"),
    "pisa-verdi-opera-2026-27":("Pisa","Teatro Verdi"),
    "salerno-verdi-opera-2026":("Salerno","Teatro Municipale Giuseppe Verdi"),
    "macerata-festival-2027":("Macerata","Arena Sferisterio"),
    "sassari-de-carolis-opera-2026":("Sassari","Teatro Comunale di Sassari"),
    "messina-vittorio-opera-2026-27":("Messina","Teatro Vittorio Emanuele"),
    # Newly approved detail adapters with already canonical physical venues.
    "coccia-novara-opera-2027":("Novara","Teatro Coccia"),
    "coccia-novara-rolling-opera":("Novara","Teatro Coccia"),
    "ravenna-alighieri-cherubini-2027":("Ravenna","Teatro Dante Alighieri"),
    "fenice-opera-2026-27":("Venezia","Teatro La Fenice"),
    "parma-opera-2027":("Parma","Teatro Regio di Parma"),
    "massimo-season-2026-27":("Palermo","Teatro Massimo"),
    "carlo-felice-season-2026-27":("Genova","Teatro Carlo Felice"),
    "donizetti-opera-2026":("Bergamo","Teatro Donizetti"),
    "teatro-grande-opera-2026":("Brescia","Teatro Grande"),
    "maggio-fiorentino-calendar-2027":("Firenze","Teatro del Maggio Musicale Fiorentino"),
    "opera-roma-season-2026-27":("Roma","Teatro dell\u0027Opera di Roma"),
    "petruzzelli-opera-2026":("Bari","Teatro Petruzzelli"),
    "petruzzelli-opera-2027":("Bari","Teatro Petruzzelli"),
    "bologna-comunale-opera-2026":("Bologna","Teatro Comunale di Bologna"),
    "bologna-comunale-opera-2027":("Bologna","Teatro Comunale di Bologna"),
}



def normalize_published_work_titles(facts:dict,registry:dict,seed_document:dict)->tuple[dict,dict,int]:
    """Normalize verified opera title AND composer display, preserving identity.

    Corrections require an exact official source URL, and the identical
    title/composer pair after Unicode casefolding. Every staging using that
    canonical work inherits the reviewed spelling. Never guess title case
    from the first production or rewrite immutable registry keys and IDs.
    """
    if seed_document.get("schema_version")!=1 or not isinstance(seed_document.get("works"),list):
        raise ValueError("invalid work authority seed registry")
    corrections={}
    for seed in seed_document["works"]:
        title,composer,url=(seed.get(k) for k in ("title","composer","source_url"))
        if not all(isinstance(x,str) and x.strip() for x in (title,composer,url)):
            continue
        matching=[p for p in facts.get("productions",[])
                  if p.get("source_url")==url
                  and normalized(p.get("title",""))==normalized(title)
                  and normalized(p.get("composer",""))==normalized(composer)]
        for product in matching:
            key=normalized(product["title"])+"|"+normalized(product["composer"])
            work=registry.get("works",{}).get(key)
            if (work is None or normalized(work.get("title",""))!=normalized(title)
                    or normalized(work.get("composer",""))!=normalized(composer)
                    or slugify(work["title"])!=slugify(title)):
                continue
            proposed=(title,composer)
            if key in corrections and corrections[key]!=proposed:
                raise ValueError("conflicting reviewed display credits for "+key)
            corrections[key]=proposed
    updated_facts=copy.deepcopy(facts)
    updated_registry=copy.deepcopy(registry)
    changed=0
    for key,(title,composer) in corrections.items():
        work=updated_registry["works"][key]
        if work["title"]!=title or work["composer"]!=composer:
            work["title"]=title
            work["composer"]=composer
            changed+=1
        for product in updated_facts["productions"]:
            if normalized(product["title"])+"|"+normalized(product["composer"])==key:
                product["title"]=title
                product["composer"]=composer
    return updated_facts,updated_registry,changed



def normalize_source_seed_trieste_genre(rows:list[dict],key:str,url:str,
                                        seed:dict|None)->list[dict]:
    """Repair an archived official genre suffix only with exact seed identity.

    Unlike canonicalize_cached_trieste_credit (existing published works),
    this form permits a *new* seeded composition, but only after the official
    URL has matched the source-backed and historically verified seed. It
    rewrites no date, time or venue.
    """
    # A previously checkpointed bilingual Modena title is the same Wagner
    # composition. Normalize only this exact first-party URL, verified
    # composer and historically reviewed canonical seed; never create
    # a separate work for the translated title.
    if (key=="modena-teatro-opera-2026-27"
        and url=="https://www.teatrocomunalemodena.it/spettacolo/richard-wagner-der-fliegender-hollander-lolandese-volante/"
        and isinstance(seed,dict) and seed.get("source_key")==key
        and seed.get("source_url")==url
        and seed.get("title")=="Der fliegende Holländer"
        and seed.get("composer")=="Richard Wagner"
        and isinstance(rows,list) and rows
        and all(isinstance(r,dict)
                and r.get("event_title") in (
                    "Der fliegende Holländer (L’olandese volante)",
                    "Der fliegende Holländer")
                and r.get("composer")=="Richard Wagner" for r in rows)):
        return [{**r,"event_title":"Der fliegende Holländer"} for r in rows]
    if (key!="verdi-trieste-season-2026-27" or not isinstance(seed,dict)
            or seed.get("source_key")!=key or seed.get("source_url")!=url
            or not isinstance(rows,list) or not rows
            or not all(isinstance(r,dict) for r in rows)):
        return rows
    title,composer=seed.get("title"),seed.get("composer")
    if not isinstance(title,str) or not isinstance(composer,str):
        return rows
    modified=[]
    for row in rows:
        if (normalized(row.get("event_title","")).replace("’","'")
                !=normalized(title).replace("’","'")):
            return rows
        old=row.get("composer")
        if (not isinstance(old,str)
                or old!=composer+" Melodramma"):
            return rows
        modified.append({**row,"event_title":title,"composer":composer})
    return modified


def official_identity_candidates(evidence:dict,candidates:dict,intelligence:dict)->dict:
    """Resolve new work identities from consistent, officially credited facts.

    Applies identical acceptance rules to every approved source. Adapter-specific
    normalization can prepare fields, but neither slug nor source identity is
    itself authority to create an opera. Independent Wikidata evidence remains
    preferable; this path is for first-party, independently credited details.
    """
    from scripts.publish_work_editorial import validate_history
    from datetime import datetime
    from zoneinfo import ZoneInfo

    seed_path=ROOT/"data"/"verified-work-authority-seeds.json"
    doc=json.loads(seed_path.read_text(encoding="utf-8"))
    if doc.get("schema_version")!=1 or not isinstance(doc.get("works"),list):
        raise ValueError("invalid official-source identity seed registry")
    sources={r["key"]:r for r in validate_config(
        json.loads(CONFIG.read_text(encoding="utf-8")))
        if r["access_status"]=="approved"}
    seeds={}
    for seed in doc["works"]:
        key,url=seed.get("source_key"),seed.get("source_url")
        if (key not in sources or not isinstance(url,str)
                or not eligible(key,url) or (key,url) in seeds
                or urlsplit(url).hostname!=urlsplit(sources[key]["official_url"]).hostname
                or not validate_history(seed.get("history"))
                or not isinstance(seed.get("synopsis"),str)
                or not 45<=len(seed["synopsis"].strip())<=300):
            raise ValueError("invalid or duplicate source-grounded work seed")
        seeds[(key,url)]=seed
    known={(entry.get("source_key"),entry.get("source_url"))
           for entry in intelligence.get("works",[])}
    candidates_by_id={x["id"]:x for x in candidates.get("candidates",[])
                      if x.get("status")=="needs_review"}
    results=copy.deepcopy(intelligence.get("works",[]))
    for record in evidence.get("evidence",[]):
        key=record.get("source_key")
        if key not in sources or record.get("status")!="needs_editorial_review":
            continue
        candidate=candidates_by_id.get(record.get("candidate_id"))
        url=record.get("source_url")
        if (not candidate or candidate.get("source_key")!=key
            or candidate.get("official_url")!=url or not isinstance(url,str)
            or not eligible(key,url)
            or urlsplit(url).hostname!=urlsplit(sources[key]["official_url"]).hostname
            or key not in VENUE_BY_SOURCE):
            continue
        rows=record.get("event_facts",[])
        rows=normalize_source_seed_trieste_genre(rows,key,url,seeds.get((key,url)))
        if key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
            from opera_atlas.bologna_detail_parser import normalize_event_fact
            rows=[normalize_event_fact(x) for x in rows]
        if not isinstance(rows,list) or not rows or any(
                not isinstance(x,dict) for x in rows):
            continue
        if any(not isinstance(x.get("event_title"),str)
                   or not isinstance(x.get("composer"),str)
                   or not isinstance(x.get("venue"),str)
                   or not x["venue"].strip() for x in rows):
            continue
        identities={(normalized(x["event_title"]),
                     normalized(x["composer"])) for x in rows}
        if len(identities)!=1 or any(not part for part in next(iter(identities))):
            continue
        title,composer=rows[0].get("event_title"),rows[0].get("composer")
        if (not isinstance(title,str) or not 3<=len(title)<=140
            or not isinstance(composer,str) or not 3<=len(composer)<=100
            or verified_venue(key,rows,{"venues":{}}) is None):
            continue
        dates=set()
        valid=True
        for x in rows:
            try:
                day=date.fromisoformat(x["date"])
                stamp=datetime.fromisoformat(x["starts_at"])
                if stamp.tzinfo is None or stamp.utcoffset() is None:
                    raise ValueError("timezone missing")
                if stamp.astimezone(ZoneInfo("Europe/Rome")).date()!=day:
                    raise ValueError("local date mismatch")
                if day in dates:raise ValueError("duplicate calendar date")
                dates.add(day)
            except (KeyError,TypeError,ValueError):
                valid=False
                break
        if not valid:continue
        seed=seeds.get((key,url))
        if seed and (normalized(seed["title"])!=normalized(title)
                     or normalized(seed["composer"])!=normalized(composer)):
            raise ValueError("official source contradicts verified opera identity seed")
        # The theater may publish SHOUTING UPPERCASE headings. Use the
        # source-bound reviewed work title for display only, retaining the
        # original official observations and the composer identity checks.
        if seed:
            title=seed["title"]
        # The remote research cache may already contain this candidate with
        # an incomplete editorial record. Reconcile its *exact official URL*
        # and credited identity before the publication transaction, instead
        # of skipping source-verified material merely because it was researched.
        if (key,url) in known:
            matching=[work for work in results
                      if work.get("source_key")==key and work.get("source_url")==url]
            if seed and len(matching)==1 and (
                    normalized(matching[0].get("title",""))==normalized(title)
                    and normalized(matching[0].get("composer",""))==normalized(composer)):
                matching[0]["synopsis"]=seed["synopsis"]
                matching[0]["history"]=seed["history"]
                matching[0]["official_authority_url"]=url
            continue
        summary=(seed["synopsis"] if seed else
                 f"«{title}» è un'opera di {composer}. "
                 "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
        results.append({"candidate_id":record["candidate_id"],
                        "source_key":key,"source_url":url,
                        "title":title,"composer":composer,"synopsis":summary,
                        "history":seed["history"] if seed else None,
                        "official_authority_url":url})
        known.add((key,url))
    return {"schema_version":1,"works":results}

def verified_venue(source_key:str,rows:list[dict],registry:dict):
    """Resolve exact official venue from evidence; never substitute a home theatre."""
    if source_key not in VENUE_BY_SOURCE or not rows:
        return None
    city,default_venue=VENUE_BY_SOURCE[source_key]
    named={x.get("venue") for x in rows if isinstance(x,dict)}
    if source_key=="haydn-rolling-opera" and len(named)==1:
        verified=next(iter(named))
        cities={"Teatro Comunale di Bolzano":"Bolzano",
                "Teatro Sociale":"Trento"}
        if verified not in cities:return None
        city=cities[verified]
    if len(named)!=1:return None
    venue=next(iter(named))
    if (source_key=="sassari-de-carolis-rolling-opera"
        and venue=="Forte della Maddalena"):
        city="Alghero"
        default_venue="Forte della Maddalena"
    permitted=({"Teatro Sangiorgi","Teatro Massimo Bellini"}
               if source_key=="bellini-catania-opera-2026-27" else
               {"Teatro Valli","Teatro Ariosto"}
               if source_key=="reggio-valli-opera-2026-27" else
               {"Teatro Donizetti","Teatro Sociale"}
               if source_key=="donizetti-opera-2026" else
               {"Teatro Comunale di Bologna","Teatro Auditorium Manzoni"}
               if source_key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027") else
               {"Teatro La Fenice","Teatro Malibran"}
               if source_key=="fenice-opera-2026-27" else
               {"Teatro dell'Opera di Roma","Teatro Valle Franca Valeri","Teatro Nazionale"}
               if source_key=="opera-roma-season-2026-27" else
               {"Teatro del Maggio Musicale Fiorentino","Teatro Goldoni"}
               if source_key=="maggio-fiorentino-calendar-2027" else
               {"Teatro Goldoni","Piazza Goldoni"}
               if source_key=="goldoni-livorno-rolling-lirica" else
               {"Teatro Coccia","Giardini di Palazzo Natta"}
               if source_key=="coccia-novara-rolling-opera" else
               {"Teatro Comunale di Bolzano","Teatro Sociale"}
               if source_key=="haydn-rolling-opera" else {default_venue})
    if source_key=="savona-giocosa-rolling-opera":
        # The official Opera Giocosa programme uses the short theatre name.
        # Preserve raw evidence while resolving one canonical physical venue.
        permitted={"Teatro Chiabrera","Teatro Gabriello Chiabrera"}
    if venue not in permitted:return None
    canonical_name=("Teatro Gabriello Chiabrera"
                    if source_key=="savona-giocosa-rolling-opera" else venue)
    found=[(key,value) for key,value in registry["venues"].items()
           if value["city"]==city and value["name"]==canonical_name
           and key==city+"|"+(default_venue if source_key=="savona-giocosa-rolling-opera" else canonical_name)]
    return (city,venue,found[0][1] if found else None) if len(found)<=1 else None

def ensure_venue(registry:dict,city:str,venue:str,existing:dict|None):
    """Allocate an immutable venue ID only together with a verified staging."""
    if existing is not None:return existing
    region={"Torre del Lago Puccini":"Toscana","Spoleto":"Umbria","Chieti":"Abruzzo","Lecce":"Puglia","Padova":"Veneto","Rovigo":"Veneto","Treviso":"Veneto","Jesi":"Marche","Ancona":"Marche","Livorno":"Toscana","Ferrara":"Emilia-Romagna","Reggio Emilia":"Emilia-Romagna","Pisa":"Toscana","Verona":"Veneto","Salerno":"Campania","Macerata":"Marche","Piacenza":"Emilia-Romagna","Lucca":"Toscana","Modena":"Emilia-Romagna","Catania":"Sicilia","Messina":"Sicilia","Cagliari":"Sardegna","Sassari":"Sardegna","Alghero":"Sardegna","Novara":"Piemonte","Trieste":"Friuli-Venezia Giulia","Genova":"Liguria","Savona":"Liguria","Asti":"Piemonte","Bolzano":"Trentino-Alto Adige","Trento":"Trentino-Alto Adige","Bergamo":"Lombardia","Firenze":"Toscana","Roma":"Lazio","Bari":"Puglia","Bologna":"Emilia-Romagna","Venezia":"Veneto"}.get(city)
    if region is None:
        raise ValueError("cannot provision venue without verified region")
    key=city+"|"+venue
    if key in registry["venues"]:
        raise ValueError("conflicting canonical venue registry")
    record={"id":next_id(registry["venues"],"oa-v-"),
            "slug":slugify(venue),"city_slug":slugify(city),
            "name":venue,"city":city,"region":region}
    registry["venues"][key]=record
    return record

def canonical_venue_id(venue:dict|None)->str|None:
    return venue["id"] if venue is not None else None

def season_from_source(source_key:str,url:str,days)->str:
    """Use the exact official season URL or observed dates, never 2026-27."""
    import re
    path=urlsplit(url).path
    if source_key=="scala-season-2026-27":
        match=re.search(r"/it/stagione/(20\d{2})-(20\d{2})/opera/",path)
        if match and int(match[2])==int(match[1])+1:
            return match[1]+"-"+match[2]
    if source_key in ("fenice-opera-2026-27","massimo-season-2026-27"):
        source=next((x for x in validate_config(json.loads(
            CONFIG.read_text(encoding="utf-8"))) if x["key"]==source_key),None)
        if source:
            start=re.search(r"(20\d{2})-(\d{2})",source["url"])
            if start and int(start[2])==(int(start[1])+1)%100:
                return str(int(start[1]))+"-"+str(int(start[1])+1)
    if days:
        y=int(min(days)[:4])
        return str(y)
    raise ValueError("cannot determine official source season")

def next_id(entries:dict,prefix:str)->str:
    numeric=[int(x["id"][len(prefix):]) for x in entries.values()
             if x["id"].startswith(prefix) and x["id"][len(prefix):].isdigit()]
    return prefix+f"{max(numeric,default=0)+1:06d}"

def canonicalize_cached_trieste_credit(rows:list[dict],registry:dict)->list[dict]:
    """Repair an older verified Trieste checkpoint only for known works.

    Old official text rendered the following genre as part of the author's
    name. Remove it ONLY where the exact title + corrected author already
    identify a unique canonical work. The official source is checked by the
    caller; individual clocks and venues are never rewritten.
    """
    if not isinstance(rows,list) or not rows or not all(isinstance(x,dict) for x in rows):
        return rows
    changed=[]
    for row in rows:
        title,composer=row.get("event_title"),row.get("composer")
        if not isinstance(title,str) or not isinstance(composer,str):
            return rows
        genre=next((g for g in (" Opera"," Tragedia"," Melodramma")
                    if composer.endswith(g)),None)
        if genre is None:return rows
        correct=composer[:-len(genre)]
        matches=[w for w in registry.get("works",{}).values()
                 if normalized(w["title"]).replace("’","'")==
                    normalized(title).replace("’","'")
                 and normalized(w["composer"])==normalized(correct)]
        if len(matches)!=1:return rows
        changed.append({**row,"event_title":matches[0]["title"],
                        "composer":matches[0]["composer"]})
    # Mixed or partially corrupted credit observations may never be repaired.
    if len(changed)!=len(rows) or len({(x["event_title"],x["composer"])
                                       for x in changed})!=1:
        return rows
    return changed


# These two official season notices explicitly enumerate independently
# ticketed operas. They are not composite bills: create one staging per
# canonical work, retaining the common official document as the evidence URL.
_MULTI_WORK_SEASONS={
    "lecce-provincia-politeama-2026": {
        ("Turandot","Giacomo Puccini"):2,
        ("L’elisir d’amore","Gaetano Donizetti"):2,
        ("Nabucco","Giuseppe Verdi"):2,
    },
    "padova-verdi-opera-2026": {
        ("Pagliacci","Ruggero Leoncavallo"):2,
        ("La traviata","Giuseppe Verdi"):3,
    },
    # The official Treviso 2026/27 season is one page for separately ticketed
    # operas. Each verified two-date work is independently publishable; later
    # missing works from the same page must reopen the candidate for review.
    "treviso-del-monaco-opera-2026-27": {
        ("La traviata","Giuseppe Verdi"):2,
        ("Pagliacci","Ruggero Leoncavallo"):2,
        ("Il cappello di paglia di Firenze","Nino Rota"):2,
    },

    "puccini-torre-del-lago-2027": {
        ("Turandot","Giacomo Puccini"):5,
        ("Tosca","Giacomo Puccini"):4,
        ("Madama Butterfly","Giacomo Puccini"):3,
        ("La bohème","Giacomo Puccini"):3,
    },
    "chieti-marrucino-lirica-2026": {
        ("Le avventure di Pinocchio","Antonio Cericola"):1,
        ("Turandot","Giacomo Puccini"):2,
        ("Le nozze di Figaro","Wolfgang Amadeus Mozart"):2,
        ("La traviata","Giuseppe Verdi"):2,
    },
}

def split_verified_season(item:dict)->list[dict]:
    """Split only complete, explicitly approved multi-work season schedules.

    Incomplete evidence must never silently publish the subset that happened
    to be parsable. All derived records retain the original source hash.
    """
    if item.get("source_key")=="savona-giocosa-rolling-opera":
        # Official evergreen homepage: independently ticketed, differently
        # credited works share one source URL. Split only fully bounded,
        # independently verified facts from the Chiabrera; unknown works
        # still follow the usual central authority/editorial gate.
        rows=item.get("event_facts")
        if not isinstance(rows,list) or not rows:
            return [item]
        groups={}
        for row in rows:
            if (not isinstance(row,dict)
                or row.get("venue")!="Teatro Chiabrera"
                or not all(isinstance(row.get(x),str) and row[x]
                           for x in ("event_title","composer","date","starts_at"))):
                return [item]
            identity=(row["event_title"],row["composer"])
            groups.setdefault(identity,[]).append(row)
        return [{**item,"event_facts":group}
                for _,group in sorted(groups.items())]
    expected=_MULTI_WORK_SEASONS.get(item.get("source_key"))
    if expected is None:
        return [item]
    rows=item.get("event_facts")
    if not isinstance(rows,list):
        return [item]
    groups={}
    for row in rows:
        if not isinstance(row,dict):
            return [item]
        identity=(row.get("event_title"),row.get("composer"))
        groups.setdefault(identity,[]).append(row)
    if item.get("source_key")=="treviso-del-monaco-opera-2026-27":
        # Three independently ticketed productions share this listing.
        # Only complete, title/composer-verified two-date groups may pass,
        # and no unknown credit is silently discarded.
        if (not groups or any(identity not in expected or
                              len(group)!=expected[identity]
                              for identity,group in groups.items())):
            return [item]
        return [{**item,"event_facts":group}
                for _,group in sorted(groups.items())]
    if {k:len(v) for k,v in groups.items()}!=expected:
        return [item]
    return [{**item,"event_facts":group} for _,group in sorted(groups.items())]

def promote(facts:dict, registry:dict, evidence:dict, candidates:dict,
            authorized_urls:list[str], *, today:date,
            intelligence:dict|None=None)->tuple[dict,dict,list[str],dict]:
    """Return all changes in memory; skip anomalies without publishing bad data."""
    from scripts.consolidate_goldoni_mascagni import consolidate
    facts,registry,consolidated_stagings=consolidate(facts,registry)
    next_facts=copy.deepcopy(facts)
    next_registry=copy.deepcopy(registry)
    approved=set(authorized_urls)
    indexes={x["id"]:x for x in candidates.get("candidates",[])
             if x.get("status")=="needs_review"}
    config={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
            if x["access_status"]=="approved"}
    issues=[]
    # Only a QID already associated with the canonical composition can
    # bridge a translated/alternative official title.
    resolved_by_candidate={entry.get("candidate_id"):entry
                           for entry in (intelligence or {}).get("works",[])
                           if isinstance(entry,dict)}
    from scripts.auto_work_research import validated_editorial_attributions
    attributed=validated_editorial_attributions()
    created_stagings=created_recite=0
    expanded=[row for item in evidence.get("evidence",[])
              for row in split_verified_season(item)]
    for item in sorted(expanded,key=lambda x:(x.get("candidate_id",""),
                      (x.get("event_facts") or [{}])[0].get("event_title",""))):
        cid=item.get("candidate_id")
        candidate=indexes.get(cid)
        if not candidate or item.get("status")!="needs_editorial_review":
            continue
        key=candidate["source_key"]
        source=config.get(key)
        url=candidate["official_url"]
        municipal_spoleto=False
        if key=="spoleto-tls-lirica-2026":
            from opera_atlas.spoleto_municipal_parser import URL as municipal
            municipal_spoleto=(url==municipal)
        if (source is None or key not in VENUE_BY_SOURCE or item.get("source_url")!=url
            or item.get("source_key")!=key or not eligible(key,url)
            or (urlsplit(url).hostname!=urlsplit(source["official_url"]).hostname
                and not municipal_spoleto)):
            issues.append({"candidate_id":cid,"reason":"unsupported_or_untrusted_source"})
            continue
        # Both the explicitly named work and composer must be present in the
        # evidence; an Event title alone never establishes a canonical opera.
        rows=item.get("event_facts",[])
        if key in ("bologna-comunale-opera-2026","bologna-comunale-opera-2027"):
            # Normalize previous source checkpoint data as well as fresh reads;
            # do not require refetching all already verified showtimes.
            from opera_atlas.bologna_detail_parser import normalize_event_fact
            rows=[normalize_event_fact(row) for row in rows]
        if key=="verdi-trieste-season-2026-27":
            rows=canonicalize_cached_trieste_credit(rows,next_registry)
        if not rows or not all(isinstance(x,dict) and
               isinstance(x.get("composer"),str) and isinstance(x.get("event_title"),str)
               and isinstance(x.get("date"),str) and isinstance(x.get("starts_at"),str)
               for x in rows):
            issues.append({"candidate_id":cid,"reason":"incomplete_work_or_clock"})
            continue
        names={(normalized(x["event_title"]),normalized(x["composer"])) for x in rows}
        if len(names)!=1:
            issues.append({"candidate_id":cid,"reason":"multiple_work_identities"})
            continue
        title,composer=next(iter(names))
        # Normalize only typographical apostrophe variation, not
        # different titles, spellings, translations or composers.
        # Macerata's first-party heading uses L'elisir d'amore whereas
        # the canonical work title uses Italian right apostrophes.
        title_credit=title.replace("’","'")
        matches=[w for w in next_registry["works"].values()
                 if normalized(w["title"]).replace("’","'")==title_credit
                 and normalized(w["composer"])==composer]
        # A verified program-only work already owns a permanent identity.
        # Promote that exact title/composer when a genuinely independent
        # performance has arrived, without allocating a second ID.
        reserved_matches=[w for w in next_registry.get("reserved_works",{}).values()
                          if normalized(w["title"])==title
                          and normalized(w["composer"])==composer]
        if not matches and len(reserved_matches)==1:
            matches=reserved_matches
        if len(matches)!=1:
            intel=resolved_by_candidate.get(cid)
            # Require the same official source, the same composer and an exact
            # independently resolved Wikidata QID. An alternative title on
            # its own is never sufficient to merge distinct compositions.
            if (intel and intel.get("source_key")==key
                    and intel.get("source_url")==url
                    and normalized(intel.get("composer",""))==composer):
                qid=intel.get("wikidata_id")
                matches=[w for w in next_registry["works"].values()
                         if normalized(w["composer"])==composer
                         and isinstance(qid,str)
                         and (w.get("wikidata_id") or
                              (attributed.get(w["slug"]) or {}).get("wikidata_id"))==qid]
        if len(matches)!=1:
            issues.append({"candidate_id":cid,"reason":"unknown_work_needs_authority_data"})
            continue
        work=matches[0]
        venue_match=verified_venue(key,rows,next_registry)
        if venue_match is None:
            issues.append({"candidate_id":cid,"reason":"unknown_or_conflicting_venue"})
            continue
        city,venue,canonical_venue=venue_match
        dates={}
        for row in rows:
            try:
                day=date.fromisoformat(row["date"]).isoformat()
                stamp=__import__("datetime").datetime.fromisoformat(row["starts_at"])
                if stamp.tzinfo is None or stamp.date().isoformat()!=day:
                    raise ValueError("missing timezone or conflicting day")
                from zoneinfo import ZoneInfo
                local=stamp.astimezone(ZoneInfo("Europe/Rome"))
                if local.date().isoformat()!=day:
                    raise ValueError("not Italian local day")
                hour=local.strftime("%H:%M")
                if day in dates and dates[day]!=hour:raise ValueError("ambiguous date")
                dates[day]=hour
            except (TypeError,ValueError):
                dates={}
                break
        if not dates:
            issues.append({"candidate_id":cid,"reason":"unreliable_event_dates"})
            continue
        # Production URL is an exact identity. A second staging of the same
        # opera at one theatre must not silently share an ambiguous route.
        colliding=[x for x in next_facts["productions"]
                   if x["municipality"]==city and x["venue"]==venue
                   and normalized(x["title"]).replace("’","'")==title_credit
                   and normalized(x["composer"])==composer]
        exact=[x for x in colliding if x["source_url"]==url]
        # The Mascagni Festival publishes one first-party ticket URL *per
        # recita*. Both pages explicitly identify the same 2026 production
        # in Piazza Goldoni. These two exact URLs form one staging, never
        # separate editions with misleading duplicate opera cards.
        mascagni_pages={
            "https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana/",
            "https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana-2/",
        }
        if (not exact and key=="goldoni-livorno-rolling-lirica"
            and url in mascagni_pages and city=="Livorno"
            and venue=="Piazza Goldoni" and title_credit=="cavalleria rusticana"
            and composer=="pietro mascagni"
            and all(day in {"2026-08-19","2026-08-20"} for day in dates)
            and all(hour=="21:30" for hour in dates.values())):
            shared=[p for p in colliding
                    if p["source_url"] in mascagni_pages
                    and p["title"]==work["title"]
                    and p["composer"]==work["composer"]
                    and all(day in {"2026-08-19","2026-08-20"} and hour=="21:30"
                            for day,hour in p["dates"])]
            if len(shared)==1 and all(
                day not in dict(shared[0]["dates"])
                or dict(shared[0]["dates"])[day]==hour
                for day,hour in dates.items()):
                exact=shared
        # Distinct official productions of the same opera in the same
        # theatre are legitimate (e.g. two different Aida stagings at
        # Verona). Preserve the original route and assign an edition URL
        # for the new staging, within the existing three-segment contract.
        edition_slug=None
        if colliding and not exact:
            overlaps=({day for p in colliding for day,hour in p["dates"] if hour is None} & set(dates)
                      if key=="teatro-grande-opera-2026" or any(
                          hour is None for p in colliding for _,hour in p["dates"])
                      else set())
            # Never publish the same canonical work at one venue on the same
            # day twice merely because a different official source lists it.
            # Separate editions are allowed only on non-overlapping dates.
            if overlaps:
                issues.append({"candidate_id":cid,
                               "reason":"same_recita_already_in_official_circuit",
                               "dates":sorted(overlaps)})
                continue
            from urllib.parse import unquote
            edition=slugify(unquote(urlsplit(url).path.rstrip("/").split("/")[-1]
                                       .removesuffix(".html")))
            edition_slug=(edition if edition.startswith(work["slug"]+"-")
                          else work["slug"]+"-"+edition)
            existing_routes={
                x.get("route_slug",x["slug"])
                for key2,x in next_registry["stagings"].items()
                if canonical_venue is not None and x["venue_id"]==canonical_venue["id"]}
            if edition_slug in existing_routes:
                issues.append({"candidate_id":cid,"reason":"venue_work_route_collision"})
                continue
        if len(exact)>1:
            issues.append({"candidate_id":cid,"reason":"ambiguous_existing_staging"})
            continue
        if exact:
            production=exact[0]
            if any(day in dict(production["dates"]) and dict(production["dates"])[day]!=hour
                   for day,hour in dates.items()):
                issues.append({"candidate_id":cid,"reason":"conflicting_existing_time"})
                continue
        else:
            # One season document can announce several separate works.
            # The immutable staging identity must therefore include the
            # verified work ID, not just the shared announcement URL.
            staging_identity=(key+"|"+url+"|"+work["id"]
                              if key in _MULTI_WORK_SEASONS or key=="savona-giocosa-rolling-opera"
                              else key+"|"+url)
            staging_key="auto-"+hashlib.sha256(staging_identity.encode()).hexdigest()[:16]
            if staging_key in next_registry["stagings"]:
                # The same official listing may identify performances at two
                # distinct approved theatres. Keep the old production ID and
                # derive a venue-qualified key only for the additional venue.
                staging_key="auto-"+hashlib.sha256(
                    (key+"|"+url+"|"+city+"|"+venue).encode()).hexdigest()[:16]
                if staging_key in next_registry["stagings"]:
                    issues.append({"candidate_id":cid,"reason":"identity_collision"})
                    continue
            # Transfer a reserved work to the staging-backed channel only
            # after all first-party date, venue and collision checks pass.
            reserved_key=next((name for name,value in
                next_registry.get("reserved_works",{}).items()
                if value["id"]==work["id"]),None)
            if reserved_key is not None:
                if reserved_key in next_registry["works"]:
                    raise ValueError("duplicate reserved work identity")
                promoted={key:value for key,value in work.items()
                          if key!="status"}
                next_registry["works"][reserved_key]=promoted
                del next_registry["reserved_works"][reserved_key]
                work=promoted
            canonical_venue=ensure_venue(next_registry,city,venue,canonical_venue)
            production={"key":staging_key,"title":work["title"],
                        "composer":work["composer"],"venue":venue,
                        "municipality":city,"region":canonical_venue["region"],
                        "source_url":url,"dates":[]}
            next_registry["stagings"][staging_key]={
                "id":next_id(next_registry["stagings"],"oa-s-"),
                "work_id":work["id"],"venue_id":canonical_venue["id"],
                "slug":work["slug"],"source_url":url,
                "season":season_from_source(key,url,dates),
                **({"route_slug":edition_slug} if edition_slug else {})}
            next_facts["productions"].append(production)
            created_stagings+=1
        for day,hour in sorted(dates.items()):
            if day in dict(production["dates"]):continue
            pk=production["key"]+"|"+day
            if pk in next_registry["performances"]:
                issues.append({"candidate_id":cid,"reason":"recita_id_collision"})
                continue
            next_registry["performances"][pk]={
                "id":f"oa-r-{_next_replica_id(next_registry):06d}",
                "staging_id":next_registry["stagings"][production["key"]]["id"],
                "original_date":day,"source_url":production["source_url"]}
            production["dates"].append([day,hour])
            created_recite+=1
        production["dates"].sort(key=lambda x:x[0])
        approved.add(url)
    if created_recite:
        next_facts["reviewed_on"]=today.isoformat()
    return (next_facts,next_registry,sorted(approved),
            {"new_stagings":created_stagings,"new_recite":created_recite,
             "consolidated_stagings":consolidated_stagings,
             "auto_skipped":issues})

def promote_calendar(facts:dict,registry:dict,health:dict,*,today:date):
    """Automatically onboard date-only OperaLombardia stagings of known operas.

    Never infer composer if the same title maps to multiple canonical works.
    The calendar's exact venue and city must already be verified in Atlas.
    """
    next_facts=copy.deepcopy(facts)
    next_registry=copy.deepcopy(registry)
    accepted=0
    created=0
    skipped=[]
    from scripts.daily_ingest import CONFIG as DAILY_CONFIG, validate_source_config
    sources={x["key"]:x for x in validate_source_config(json.loads(
        DAILY_CONFIG.read_text(encoding="utf-8")))}
    source=sources.get("opera-lombardia-calendar-2026-27")
    if source is None or source["access_status"]!="approved":
        return next_facts,next_registry,{"new_stagings":0,"new_recite":0,"auto_skipped":[]}
    for scan in health.get("sources",[]):
        if scan.get("key")!="opera-lombardia-calendar-2026-27" or scan.get("outcome")!="review_required":
            continue
        for row in scan.get("candidates",[]):
            title,city,venue,day=(row.get(k) for k in ("title","city","venue","date"))
            if not all(isinstance(v,str) and v.strip() for v in (title,city,venue,day)):
                continue
            if row.get("time") is not None:continue
            try:date.fromisoformat(day)
            except ValueError:continue
            # A calendar title alone is never evidence of the composer:
            # Rossini/Paisiello and Puccini/Leoncavallo must not be merged,
            # even if only one version is currently registered.
            composer=row.get("composer")
            works=[w for w in next_registry["works"].values()
                   if isinstance(composer,str) and composer.strip()
                   and normalized(w["title"])==normalized(title)
                   and normalized(w["composer"])==normalized(composer)]
            venue_key=city+"|"+venue
            canonical_venue=next_registry["venues"].get(venue_key)
            if len(works)!=1 or canonical_venue is None:
                skipped.append({"title":title,"city":city,"reason":"identity_requires_more_evidence"})
                continue
            work=works[0]
            collisions=[x for x in next_facts["productions"]
                        if x["municipality"]==city and x["venue"]==venue
                        and normalized(x["title"])==normalized(work["title"])
                        and normalized(x["composer"])==normalized(work["composer"])]
            exact=[x for x in collisions if x["source_url"]==source["url"]]
            if (len(exact)>1 or (collisions and not exact)):
                skipped.append({"title":title,"city":city,"reason":"venue_work_route_collision"})
                continue
            if exact:
                production=exact[0]
            else:
                key="auto-lombardia-"+hashlib.sha256(
                    (source["key"]+"|"+work["id"]+"|"+venue_key).encode()).hexdigest()[:16]
                if key in next_registry["stagings"]:continue
                production={"key":key,"title":work["title"],
                            "composer":work["composer"],"venue":venue,
                            "municipality":city,"region":canonical_venue["region"],
                            "source_url":source["url"],"dates":[]}
                next_registry["stagings"][key]={
                    "id":next_id(next_registry["stagings"],"oa-s-"),
                    "work_id":work["id"],"venue_id":canonical_venue["id"],
                    "slug":work["slug"],"source_url":source["url"],
                    "season":season_from_source(source["key"],source["url"],[day])}
                next_facts["productions"].append(production)
                created+=1
            if day in dict(production["dates"]):
                if dict(production["dates"])[day] is not None:
                    continue
                continue
            recita_key=production["key"]+"|"+day
            if recita_key in next_registry["performances"]:
                continue
            next_registry["performances"][recita_key]={
                "id":f"oa-r-{_next_replica_id(next_registry):06d}",
                "staging_id":next_registry["stagings"][production["key"]]["id"],
                "original_date":day,"source_url":source["url"]}
            production["dates"].append([day,None])
            production["dates"].sort(key=lambda x:x[0])
            accepted+=1
    if accepted:
        next_facts["reviewed_on"]=today.isoformat()
    return next_facts,next_registry,{"new_stagings":created,
                                     "new_recite":accepted,"auto_skipped":skipped}

def verified_candidate_image(detail:dict,*,title:str,url:str,composer:str|None=None)->dict|None:
    """Only first-party, title-matched, production-page poster metadata.

    Revalidate checkpoint JSON because it may have been produced by an older
    scanner; never trust an image URL merely because it exists in evidence.
    """
    # A user-reviewed TicketOne event artwork may be bound to the exact
    # official opera/composer/source. The URL remains externally hosted;
    # never copy the art or misidentify another production as a poster.
    if composer:
        from opera_atlas.verified_historical_theatre_posters import verified_theatre_poster
        historical_poster=verified_theatre_poster(
            source_url=url,title=title,composer=composer)
        if historical_poster is not None:
            return historical_poster
        from opera_atlas.verified_civic_work_images import verified_civic_image
        civic=verified_civic_image(source_url=url,title=title,composer=composer)
        if civic is not None:
            return civic
        from opera_atlas.verified_original_work_art import verified_original_art
        original=verified_original_art(
            source_url=url,title=title,composer=composer)
        if original is not None:
            return original
        from opera_atlas.verified_ticketing_art import verified_ticketing_image
        ticketing=verified_ticketing_image(
            source_url=url,title=title,composer=composer)
        if ticketing is not None:
            return ticketing
        from opera_atlas.verified_coproduction_posters import verified_coproduction_poster
        coproduced=verified_coproduction_poster(
            source_url=url,title=title,composer=composer)
        if coproduced is not None:
            return coproduced
    image=detail.get("poster_evidence")
    if not isinstance(image,dict) or image.get("kind")!="official_production_image":
        return None
    from scripts.publish_work_posters import allowed_image_url,image_matches_work
    raw=image.get("image_url","")
    artwork_source=image.get("source_url")
    # Source-specific work image is independently credited by the *same*
    # first-party issuer as the canonical season page. Never permit an
    # arbitrary alternate site or another opera on a shared programme.
    approved_alternate=(
        detail.get("source_key")=="jesi-esecuzione-opera-2026"
        and url=="https://www.fondazionepergolesispontini.com/lirica/programma-stagione-lirica-2026/"
        and artwork_source=="https://www.fondazionepergolesispontini.com/eventi/lesecuzione-sotto-lo-sguardo-di-tosca-2/"
        and composer=="Salvatore Passantino"
        and normalized(title)=="l'esecuzione")
    if ((artwork_source!=url and not approved_alternate) or
            not isinstance(raw,str) or allowed_image_url(raw,artwork_source if approved_alternate else url)!=raw or
            not image_matches_work(raw,title) or
            not isinstance(image.get("credit"),str) or
            not image.get("credit") or
            not isinstance(image.get("alt"),str) or not image.get("alt")):
        return None
    return {key:image[key] for key in
            ("image_url","source_url","credit","alt","kind")
            if key in image} | ({"license":image["license"]}
                            if isinstance(image.get("license"),str) else {})

def complete_cached_verified_work_cards(intelligence:dict,evidence:dict)->dict:
    """Finish an already identified composition using source-bound editorial art.

    This is an in-memory prepublication step, not a post-import reconciliation.
    Only a prior independently resolved Wikidata QID plus the exact official
    composer/title evidence may attach an original verified plot and history.
    """
    from scripts.auto_work_research import (
        preverified_work_material, validated_editorial_attributions)
    from scripts.publish_work_editorial import validate_history
    materials=preverified_work_material()
    approved=validated_editorial_attributions()
    observations={x.get("candidate_id"):x for x in evidence.get("evidence",[])
                  if x.get("status")=="needs_editorial_review"}
    updated=copy.deepcopy(intelligence)
    for work in updated.get("works",[]):
        if not isinstance(work,dict):continue
        try:
            slug=slugify(work.get("title",""))
        except (ValueError,TypeError):
            continue
        binding=approved.get(slug)
        card=materials.get(slug)
        detail=observations.get(work.get("candidate_id"))
        if (not binding or not card or not detail or
            binding.get("wikidata_id")!=work.get("wikidata_id") or
            normalized(binding.get("composer",""))!=normalized(work.get("composer","")) or
            detail.get("source_key")!=work.get("source_key") or
            detail.get("source_url")!=work.get("source_url")):
            continue
        rows=detail.get("event_facts",[])
        if (not isinstance(rows,list) or not rows or any(
             not isinstance(x,dict)
             or normalized(x.get("event_title",""))!=normalized(work.get("title",""))
             or normalized(x.get("composer",""))!=normalized(work.get("composer",""))
             for x in rows)):
            continue
        if not validate_history(card.get("history")):
            continue
        if not isinstance(card.get("synopsis"),str) or not 45<=len(card["synopsis"])<=300:
            continue
        # Identity-only boilerplate from an earlier lookup is not a plot.
        # The verified work-specific synopsis must replace that placeholder
        # before the new canonical card passes editorial publication.
        existing_summary=work.get("synopsis")
        if (existing_summary is None or
            (isinstance(existing_summary,str) and existing_summary.strip().endswith(
                "Consulta le rappresentazioni verificate in programma nei teatri italiani."))):
            work["synopsis"]=card["synopsis"]
        if not validate_history(work.get("history")):
            work["history"]=card["history"]
    return updated


def promote_new_works(facts:dict,registry:dict,evidence:dict,candidates:dict,
                      intelligence:dict,editorial:dict,approved_urls:list[str],*,
                      today:date, history:dict|None=None, require_image:bool=False):
    """One unattended all-or-nothing work+history+staging+recita transaction."""
    next_facts=copy.deepcopy(facts)
    next_registry=copy.deepcopy(registry)
    next_editorial=copy.deepcopy(editorial)
    next_history=copy.deepcopy(history) if history is not None else None
    allowed=set(approved_urls)
    sources={x["key"]:x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
             if x["access_status"]=="approved"}
    candidates_by_id={x["id"]:x for x in candidates.get("candidates",[])
                      if x.get("status")=="needs_review"}
    event_by_id={x["candidate_id"]:x for x in evidence.get("evidence",[])
                 if x.get("status")=="needs_editorial_review"}
    result={"new_works":0,"new_stagings":0,"new_recite":0,"auto_skipped":[]}
    if next_editorial.get("schema_version")!=1 or not isinstance(
            next_editorial.get("synopses"),dict):
        raise ValueError("invalid original editorial synopsis registry")
    for item in sorted(intelligence.get("works",[]),key=lambda x:x.get("candidate_id","")):
        cid=item.get("candidate_id")
        candidate=candidates_by_id.get(cid)
        detail=event_by_id.get(cid)
        if not candidate or not detail:continue
        source_key=item.get("source_key")
        url=item.get("source_url")
        source=sources.get(source_key)
        if (source_key not in VENUE_BY_SOURCE or source is None
            or not isinstance(url,str) or not eligible(source_key,url)
            or urlsplit(url).hostname!=urlsplit(source["official_url"]).hostname
            or candidate.get("official_url")!=url or candidate.get("source_key")!=source_key
            or detail.get("source_url")!=url or detail.get("source_key")!=source_key):
            continue
        title,composer,summary=(item.get(k) for k in ("title","composer","synopsis"))
        if not all(isinstance(x,str) and x.strip() for x in (title,composer,summary)):
            continue
        summary=summary.strip()
        if not 45<=len(summary)<=300:continue
        historical=item.get("history")
        # A title+composer identification is not a finished Atlas card.
        # Keep the candidate in the acquisition queue until both a short
        # real plot and source-backed premiere facts have been acquired.
        from scripts.publish_work_editorial import validate_history
        if require_image and (
                summary.endswith(
                    "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
                or not validate_history(historical)):
            result["auto_skipped"].append({
                "candidate_id":cid,"reason":"incomplete_work_editorial"})
            continue
        if next_history is not None and historical is not None:
            from scripts.publish_work_editorial import validate_history
            if not validate_history(historical):
                result["auto_skipped"].append({"candidate_id":cid,"reason":"invalid_historical_profile"})
                continue
        qid=item.get("wikidata_id")
        verified_wikidata=(isinstance(qid,str) and
                           __import__("re").fullmatch(r"Q[1-9][0-9]*",qid))
        # Identical evidence contract across all approved source adapters.
        verified_official=(item.get("official_authority_url")==url
                           and source_key in VENUE_BY_SOURCE
                           and detail.get("status")=="needs_editorial_review")
        if not (verified_wikidata or verified_official):continue
        work_key=normalized(title)+"|"+normalized(composer)
        slug=slugify(title)
        # Canonical dictionaries may retain historical, non-normalized keys.
        # Identity is the normalized title+composer pair, never just the map key.
        if (work_key in next_registry["works"] or any(
                normalized(w["title"])==normalized(title) and
                normalized(w["composer"])==normalized(composer)
                for w in next_registry["works"].values())):
            continue
        # Prefer historic, rights-documented Wikimedia artwork over a
        # potentially temporary theatre thumbnail. Require exact title and
        # composer identity; slug-keyed artwork cannot resolve homonyms.
        from scripts.publish_work_posters import load_archival_art
        legacy_homonyms=[w for w in next_registry["works"].values()
                         if w["slug"]==slug]
        archive=(load_archival_art({slug}).get(slug)
                 if not legacy_homonyms else None)
        if require_image and not (
                verified_candidate_image(detail,title=title,url=url,composer=composer) or archive):
            result["auto_skipped"].append({
                "candidate_id":cid,"reason":"verified_work_image_missing"})
            continue
        # A shared title is a legitimate new composition. Keep existing work
        # routes unchanged and allocate a composer-qualified route only to the
        # new work. Never overwrite older synopsis/history by title slug.
        homonyms=[w for w in next_registry["works"].values()
                  if w["slug"]==slug]
        route_slug=slug+"-"+slugify(composer) if homonyms else slug
        existing_routes={w.get("route_slug",w["slug"])
                         for w in next_registry["works"].values()}
        if route_slug in existing_routes:
            result["auto_skipped"].append({"candidate_id":cid,
                                            "reason":"homonym_route_collision"})
            continue
        rows=detail.get("event_facts",[])
        if verified_official:
            rows=normalize_source_seed_trieste_genre(
                rows,source_key,url,{"source_key":source_key,"source_url":url,
                                    "title":title,"composer":composer})
        if not isinstance(rows,list) or not rows:continue
        if verified_official:
            from opera_atlas.bologna_detail_parser import normalize_event_fact
            rows=[normalize_event_fact(x) for x in rows]
        venue_match=verified_venue(source_key,rows,next_registry)
        if venue_match is None:
            result["auto_skipped"].append({"candidate_id":cid,"reason":"unknown_or_conflicting_venue"})
            continue
        city,venue,canonical_venue=venue_match
        date_rows={}
        invalid=False
        for row in rows:
            if (not isinstance(row,dict) or normalized(row.get("event_title",""))!=normalized(title)
                or normalized(row.get("composer",""))!=normalized(composer)
                or row.get("venue")!=venue):invalid=True;break
            try:
                local_day=date.fromisoformat(row["date"]).isoformat()
                stamp=__import__("datetime").datetime.fromisoformat(row["starts_at"])
                from zoneinfo import ZoneInfo
                if stamp.tzinfo is None or stamp.utcoffset() is None:raise ValueError
                local=stamp.astimezone(ZoneInfo("Europe/Rome"))
                if local.date().isoformat()!=local_day:raise ValueError
                hour=local.strftime("%H:%M")
                if local_day in date_rows and date_rows[local_day]!=hour:raise ValueError
                date_rows[local_day]=hour
            except (KeyError,TypeError,ValueError):invalid=True;break
        if invalid or not date_rows:continue
        # The canonical work route must remain unique; no title-based
        # overwrites and no guessing which composer an old URL identifies.
        staging_key="auto-"+hashlib.sha256((source_key+"|"+url).encode()).hexdigest()[:16]
        if staging_key in next_registry["stagings"]:continue
        canonical_venue=ensure_venue(next_registry,city,venue,canonical_venue)
        # Reserved program-only identities hold immutable IDs even before
        # their first standalone staging; never allocate a colliding ID.
        occupied={**next_registry["works"],
                  **{"reserved:"+key:value for key,value in
                     next_registry.get("reserved_works",{}).items()}}
        reserved=next_registry.get("reserved_works",{}).get(work_key)
        if reserved and (reserved.get("slug")!=slug
                         or reserved.get("title")!=title
                         or reserved.get("composer")!=composer):
            raise ValueError("reserved canonical work identity mismatch")
        work_id=reserved["id"] if reserved else next_id(occupied,"oa-w-")
        stage_id=next_id(next_registry["stagings"],"oa-s-")
        next_registry["works"][work_key]={
            "id":work_id,"slug":slug,"title":title,"composer":composer,
            **({"wikidata_id":qid} if verified_wikidata else
               {"authority_url":url}),
            **({"route_slug":route_slug} if homonyms else {})}
        if reserved:
            del next_registry["reserved_works"][work_key]
        if homonyms:
            by_id=next_editorial.setdefault("synopses_by_id",{})
            for existing in homonyms:
                if existing["id"] not in by_id:
                    old_summary=next_editorial["synopses"].get(slug)
                    if not old_summary:
                        raise ValueError("missing existing homonym synopsis")
                    by_id[existing["id"]]=old_summary
            by_id[work_id]=summary
            if next_history is not None:
                history_by_id=next_history.setdefault("works_by_id",{})
                for existing in homonyms:
                    if existing["id"] not in history_by_id:
                        old_history=next_history["works"].get(slug)
                        if not old_history:
                            raise ValueError("missing existing homonym history")
                        history_by_id[existing["id"]]=old_history
                if historical is not None:history_by_id[work_id]=historical
        else:
            next_editorial["synopses"][slug]=summary
            if next_history is not None and historical is not None:next_history["works"][slug]=historical
        next_registry["stagings"][staging_key]={
            "id":stage_id,"work_id":work_id,"venue_id":canonical_venue["id"],
            "slug":slug,"source_url":url,
            **({"route_slug":route_slug} if homonyms else {}),
            "season":season_from_source(source_key,url,date_rows)}
        next_facts["productions"].append({
            "key":staging_key,"title":title,"composer":composer,"venue":venue,
            "municipality":city,"region":canonical_venue["region"],
            "source_url":url,
            "dates":[[day,hour] for day,hour in sorted(date_rows.items())]})
        for day in sorted(date_rows):
            next_registry["performances"][staging_key+"|"+day]={
                "id":f"oa-r-{_next_replica_id(next_registry):06d}",
                "staging_id":stage_id,"original_date":day,"source_url":url}
        allowed.add(url)
        result["new_works"]+=1
        result["new_stagings"]+=1
        result["new_recite"]+=len(date_rows)
    if result["new_recite"]:next_facts["reviewed_on"]=today.isoformat()
    if next_history is not None:
        return next_facts,next_registry,sorted(allowed),next_editorial,next_history,result
    return next_facts,next_registry,sorted(allowed),next_editorial,result


def enrich_existing_times(facts:dict,evidence:dict,candidates:dict,previous:dict):
    """Match an exact second official theatre page to an existing dated recita.

    Preserve the immutable performance/staging IDs and original circuit
    source, and store only the newly verified time and provenance.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from scripts.build_verified_catalog import TIME_EVIDENCE_URLS, validate_time_evidence
    updated=copy.deepcopy(previous)
    if updated.get("schema_version")!=1 or not isinstance(updated.get("times"),dict):
        raise ValueError("invalid existing time evidence")
    known={x["id"]:x for x in candidates.get("candidates",[])
           if x.get("status")=="needs_review"}
    count=0
    for record in evidence.get("evidence",[]):
        cid=record.get("candidate_id")
        cand=known.get(cid)
        if not cand or record.get("status")!="needs_editorial_review":
            continue
        key=cand.get("source_key")
        url=cand.get("official_url")
        if key!="teatro-grande-opera-2026" or not isinstance(url,str) or not eligible(key,url):
            continue
        if record.get("source_url")!=url or record.get("source_key")!=key:
            continue
        rows=record.get("event_facts")
        if not isinstance(rows,list) or not rows:continue
        # Candidate must describe exactly one already known opera in exactly
        # one location; a double bill is not a single work.
        names={(normalized(x.get("event_title","")).replace("’","'"),
                normalized(x.get("composer",""))) for x in rows
               if isinstance(x,dict)}
        if len(names)!=1:continue
        name,composer=next(iter(names))
        if any(x.get("venue")!="Teatro Grande" for x in rows):continue
        matches=[p for p in facts["productions"] if p["municipality"]=="Brescia"
                 and p["venue"]=="Teatro Grande"
                 and normalized(p["title"]).replace("’","'")==name
                 and normalized(p["composer"])==composer]
        if len(matches)!=1:continue
        product=matches[0]
        if url not in TIME_EVIDENCE_URLS.get(product["key"],set()):continue
        original=dict(product["dates"])
        proposed={}
        valid=True
        for row in rows:
            try:
                day=date.fromisoformat(row["date"]).isoformat()
                timestamp=datetime.fromisoformat(row["starts_at"])
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:raise ValueError
                local=timestamp.astimezone(ZoneInfo("Europe/Rome"))
                if local.date().isoformat()!=day or day not in original:raise ValueError
                hour=local.strftime("%H:%M")
                if original[day] is not None and original[day]!=hour:raise ValueError
                if day in proposed:raise ValueError
                proposed[day]=hour
            except (ValueError,TypeError,KeyError):
                valid=False;break
        if not valid or not proposed:continue
        # Never enrich only part of an already-known production from a
        # potentially truncated page; require all its documented dates.
        if set(proposed)!=set(original):continue
        fresh={}
        for day,hour in proposed.items():
            evidence_key=product["key"]+"|"+day
            candidate={"time":hour,"url":url}
            prior=updated["times"].get(evidence_key)
            if prior is not None and prior!=candidate:
                valid=False;break
            if prior is None:fresh[evidence_key]=candidate
        if not valid:continue
        updated["times"].update(fresh)
        count+=len(fresh)
    validate_time_evidence(facts,updated)
    return updated,count


def enrich_double_bill_times(facts:dict,evidence:dict,candidates:dict,previous:dict):
    """Legacy compatibility: a shared double bill is a PROGRAM, not two solo tickets.

    The official Brescia showtimes belong exclusively to the independently
    validated program feed. Never repopulate separate work-level recite or
    time evidence from the same two-ticket event.
    """
    return copy.deepcopy(previous),0


def merge_official_poster_cache(previous:dict|None,additions:dict)->dict|None:
    """Merge only newly verified official images; archival images need no cache write.

    For archival-only new works the poster generator resolves the independently
    verified Commons provenance from the stable archival registry.
    """
    if not additions:
        return None
    if (not isinstance(previous,dict)
            or previous.get("schema_version")!=2
            or not isinstance(previous.get("posters"),dict)):
        raise ValueError("invalid existing artwork evidence")
    merged=copy.deepcopy(previous)
    for work_id,proof in additions.items():
        if not isinstance(proof,dict) or proof.get("work_id")!=work_id:
            raise ValueError("inconsistent official poster work identity")
        merged["posters"][work_id]=proof
    return merged


def remove_retries_for_published_works(report:dict,candidates:dict,
                                      prior_facts:dict,next_facts:dict)->dict:
    """A newly published work is not an unresolved identity candidate.

    The earlier existing-work pass may mark an unknown work before the
    *same run* successfully publishes it through the new-work transaction.
    Correct this diagnostic only when a new canonical production exists,
    not for candidates merely enriched or still missing showtime evidence.
    """
    before={(x.get("source_url"),x.get("key")) for x in prior_facts.get("productions",[])}
    published_urls={row.get("source_url") for row in next_facts.get("productions",[])
                    if (row.get("source_url"),row.get("key")) not in before}
    by_candidate={row.get("id"):row.get("official_url")
                  for row in candidates.get("candidates",[])}
    amended=report.copy()
    amended["auto_skipped"]=[row for row in report.get("auto_skipped",[])
                             if not (row.get("reason")=="unknown_work_needs_authority_data"
                                     and by_candidate.get(row.get("candidate_id")) in published_urls)]
    return amended


def refine_new_work_skips(known_work_skips:list[dict],
                          verified_new_work_skips:list[dict])->list[dict]:
    """Report the final publication gate, not the earlier unknown-work stage.

    A source-validated new opera can be ready in every respect except its
    authentic image; don't mislead operators into researching its identity
    again. Never suppress unrelated errors or relax any publication gate.
    """
    image_blocked={entry.get("candidate_id") for entry in verified_new_work_skips
                   if entry.get("reason")=="verified_work_image_missing"}
    older=[entry for entry in known_work_skips
           if not (entry.get("candidate_id") in image_blocked
                   and entry.get("reason")=="unknown_work_needs_authority_data")]
    return older+verified_new_work_skips


def main():
    from datetime import date
    facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    # Correct previously published uppercase headings in the same validated
    # catalog transaction; never edit derived public JSON or IDs by hand.
    seeds=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text(encoding="utf-8"))
    facts,registry,corrected_titles=normalize_published_work_titles(facts,registry,seeds)
    evidence=json.loads(DETAILS.read_text(encoding="utf-8")) if DETAILS.exists() else {"evidence":[]}
    candidates=json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"candidates":[]}
    approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8")) if SOURCE_ALLOWLIST.exists() else {"schema_version":1,"urls":[]}
    from scripts.auto_work_research import OUT as RESEARCH
    intelligence=(json.loads(RESEARCH.read_text(encoding="utf-8"))
                  if RESEARCH.exists() else {"schema_version":1,"works":[]})
    next_facts,next_registry,urls,report=promote(
        facts,registry,evidence,candidates,approved["urls"],today=date.today(),
        intelligence=intelligence)
    from scripts.daily_ingest import HEALTH as DAILY_HEALTH
    health=json.loads(DAILY_HEALTH.read_text(encoding="utf-8")) if DAILY_HEALTH.exists() else {"sources":[]}
    next_facts,next_registry,calendar=promote_calendar(
        next_facts,next_registry,health,today=date.today())
    report["new_stagings"]+=calendar["new_stagings"]
    report["new_recite"]+=calendar["new_recite"]
    report["auto_skipped"]+=calendar["auto_skipped"]
    from scripts.publish_work_editorial import EDITORIAL, build_editorial
    intelligence=official_identity_candidates(evidence,candidates,intelligence)
    # Previously identified works should not wait for a second remote lookup
    # when their source-attributed synopsis, history and archival art exist.
    intelligence=complete_cached_verified_work_cards(intelligence,evidence)
    editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
    from scripts.publish_work_editorial import HISTORY, validate_history
    historical=json.loads(HISTORY.read_text(encoding="utf-8"))
    prior_to_new_work_publication=next_facts
    next_facts,next_registry,urls,next_editorial,next_history,newworks=promote_new_works(
        next_facts,next_registry,evidence,candidates,intelligence,editorial,urls,
        today=date.today(),history=historical,require_image=True)
    report=remove_retries_for_published_works(
        report,candidates,prior_to_new_work_publication,next_facts)
    report["auto_skipped"]=refine_new_work_skips(
        report["auto_skipped"],newworks["auto_skipped"])
    report["new_works"]=newworks["new_works"]
    report["new_stagings"]+=newworks["new_stagings"]
    report["new_recite"]+=newworks["new_recite"]
    # Only write after the full canonical graph validates against the expanded
    # source allowlist; rollback-like behavior by pre-validating in memory.
    from scripts.build_verified_catalog import validate_auto_sources,TIME_EVIDENCE,validate_time_evidence
    old_times=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
    next_times,enriched=enrich_existing_times(next_facts,evidence,candidates,old_times)
    next_times,double_enriched=enrich_double_bill_times(
        next_facts,evidence,candidates,next_times)
    enriched+=double_enriched
    validate_time_evidence(next_facts,next_times)
    report["enriched_recite_times"]=enriched
    report["normalized_work_titles"]=corrected_titles
    validate_auto_sources(urls)
    assemble(next_facts,next_registry,approved_extra=set(urls))
    build_editorial(next_facts,next_registry,next_editorial,approved_extra=set(urls),
                   history=next_history)
    # Every new opera must already have a real, correctly attributed image.
    # The public poster publisher independently loads archival artwork by
    # unique canonical slug, preferring Commons over temporary venue imagery.
    from scripts.publish_work_posters import load_archival_art
    # Reserved works already passed the same editorial/image identity gate
    # and have public, composer-bound archival artwork. Moving their ID to
    # the staging-backed channel is not a brand-new work/image identity.
    old_ids={w["id"] for collection in ("works","reserved_works")
             for w in registry.get(collection,{}).values()}
    new_ids={w["id"] for w in next_registry["works"].values()}-old_ids
    archival=load_archival_art({w["slug"] for w in next_registry["works"].values()})
    slug_counts={}
    for work in next_registry["works"].values():
        slug_counts[work["slug"]]=slug_counts.get(work["slug"],0)+1
    image_additions={}
    for work in next_registry["works"].values():
        if work["id"] not in new_ids:continue
        slug=work["slug"]
        if slug_counts[slug]==1 and slug in archival:
            continue  # archival file and license are checked by poster publisher
        matched=[p for p in next_facts["productions"]
                  if normalized(p["title"])==normalized(work["title"])
                  and normalized(p["composer"])==normalized(work["composer"])]
        proofs=[verified_candidate_image(e,title=work["title"],url=p["source_url"],composer=work["composer"])
                for p in matched for e in evidence.get("evidence",[])
                if e.get("source_url")==p["source_url"]]
        proofs=[proof for proof in proofs if proof is not None]
        if not proofs:
            raise ValueError("missing verified image for new canonical opera "+work["id"])
        image_additions[work["id"]]={"work_id":work["id"],**proofs[0]}
    # A verified archival Commons image can already be available for a new
    # work through the persistent archival bank. In that case there is no
    # newly-fetched official poster to append to the evidence cache.
    # The next poster publication reads the bank by canonical work identity.
    previous_images=None
    if image_additions:
        from scripts.publish_work_posters import EVIDENCE as POSTER_EVIDENCE
        previous_images=merge_official_poster_cache(
            json.loads(POSTER_EVIDENCE.read_text(encoding="utf-8")),image_additions)
    if report["new_recite"] or corrected_titles:
        _write_atomic(MANIFEST,next_facts)
        _write_atomic(REGISTRY,next_registry)
        _write_atomic(SOURCE_ALLOWLIST,{"schema_version":1,"urls":urls})
        if report["new_works"]:
            _write_atomic(EDITORIAL,next_editorial)
            _write_atomic(HISTORY,next_history)
            if previous_images is not None:
                from scripts.publish_work_posters import EVIDENCE as POSTER_EVIDENCE
                _write_atomic(POSTER_EVIDENCE,previous_images)
    if enriched:
        _write_atomic(TIME_EVIDENCE,next_times)
    _write_atomic(HEALTH,{"schema_version":1,**report})
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
