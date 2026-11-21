"""Strict sourced premiere profile from an exact Wikidata opera QID.

A complete history is generated only when P87 (librettist), P1191
(premiere date), P4647 (premiere venue), and the venue's P131
(city/municipality) are unambiguous. Never fill gaps from guesses.
"""
from __future__ import annotations

import re

QID = re.compile(r"Q[1-9][0-9]*")
DATE = re.compile(r"\+?(1[6-9][0-9]{2}|20[0-9]{2})-[0-9]{2}-[0-9]{2}T")
def _values(entity: dict, prop: str) -> list:
    result = []
    for claim in entity.get("claims", {}).get(prop, []):
        if claim.get("rank") == "deprecated":
            continue
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if value is not None:
            result.append(value)
    return result


def _ids(entity: dict, prop: str) -> list[str]:
    ids = [v["id"] for v in _values(entity, prop)
           if isinstance(v, dict) and QID.fullmatch(str(v.get("id", "")))]
    return sorted(set(ids))


def _label(entity: dict) -> str | None:
    labels = entity.get("labels", {})
    value = labels.get("it", labels.get("en", {})).get("value")
    if not isinstance(value, str) or not 3 <= len(value.strip()) <= 150:
        return None
    return value.strip()


def wikidata_premiere(identity: dict, *, fetch=None) -> dict | None:
    """Extract historic facts from the *same QID* used to identify the work."""
    from scripts.auto_work_research import read_api, wikidata_url
    from scripts.publish_work_editorial import validate_history

    fetch = read_api if fetch is None else fetch
    qid = identity.get("wikidata_id")
    if not isinstance(qid, str) or not QID.fullmatch(qid):
        return None
    work = fetch(wikidata_url("wbgetentities", ids=qid, props="claims"))
    entity = work.get("entities", {}).get(qid)
    if not isinstance(entity, dict):
        return None
    librettists = _ids(entity, "P87")
    places = _ids(entity, "P4647")
    dates = _values(entity, "P1191")
    if not librettists or len(places) != 1 or len(dates) != 1:
        return None
    time = dates[0]
    if not isinstance(time, dict):
        return None
    match = DATE.match(str(time.get("time", "")))
    if not match:
        return None
    year = int(match.group(1))
    if not 1600 <= year <= 2100:
        return None
    ids = sorted(set(librettists + places))
    refs = fetch(wikidata_url("wbgetentities", ids="|".join(ids),
                             props="labels|claims", languages="it|en"))
    entities = refs.get("entities", {})
    names = [_label(entities.get(pid, {})) for pid in librettists]
    venue = _label(entities.get(places[0], {}))
    city_ids = _ids(entities.get(places[0], {}), "P131")
    if not venue or not all(names) or len(city_ids) != 1:
        return None
    city_entities = fetch(wikidata_url("wbgetentities", ids=city_ids[0],
                                      props="labels", languages="it|en"))
    city = _label(city_entities.get("entities", {}).get(city_ids[0], {}))
    if not city:
        return None
    result = {"librettist": "; ".join(names), "premiere_year": year,
              "premiere_venue": venue, "premiere_city": city,
              "sources": ["https://www.wikidata.org/wiki/" + qid]}
    return result if validate_history(result) else None
