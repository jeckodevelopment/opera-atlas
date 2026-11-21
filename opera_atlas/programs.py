"""Source-neutral, fail-closed identity and schedule for multi-work programs.

A program is one ticketed event per local date; component works keep their own
attributions and optional canonical IDs. It is *not* a new single opera.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from scripts.publish_catalog_v2 import normalized, slugify

CREDITS=re.compile(r"^\s*(.{2,160}?)\s+di\s+(.{3,100}?)\s*$",re.I)
IT=ZoneInfo("Europe/Rome")

def credited_components(heading: str) -> list[dict]:
    """Extract an unambiguous first-party composite heading, no URL guesses."""
    if not isinstance(heading,str) or len(heading)>700:
        raise ValueError("invalid official program heading")
    segments=[x.strip() for x in heading.split("|")]
    # Last segment may be the season date range, never a composition.
    if segments and re.search(r"\b(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
                              r"luglio|agosto|settembre|ottobre|novembre|dicembre)\b",
                              segments[-1],re.I):
        segments.pop()
    if not 2<=len(segments)<=12:raise ValueError("not a multi-work program")
    parts=[]
    seen=set()
    for segment in segments:
        match=CREDITS.fullmatch(segment)
        if not match:raise ValueError("missing independent title/composer credit")
        title,composer=(x.strip() for x in match.groups())
        identity=(normalized(title),normalized(composer))
        if identity in seen:raise ValueError("duplicate program component")
        seen.add(identity)
        parts.append({"title":title,"composer":composer})
    return parts

def program_from_evidence(*,heading:str,source_key:str,source_url:str,
                          candidate:dict,detail:dict,registry:dict,venue:str,
                          city:str,region:str) -> dict:
    """Require consistent official source, real calendar and a unique ticket."""
    from urllib.parse import urlsplit
    from scripts.discover_season_indexes import eligible
    if (not isinstance(source_url,str) or not eligible(source_key,source_url)
        or urlsplit(source_url).scheme!="https"
        or candidate.get("source_key")!=source_key
        or candidate.get("official_url")!=source_url
        or detail.get("source_key")!=source_key
        or detail.get("source_url")!=source_url
        or detail.get("status") not in ("needs_program_review","needs_editorial_review")):
        raise ValueError("untrusted composite source")
    parts=credited_components(heading)
    works=list(registry.get("works",{}).values())
    for part in parts:
        found=[w for w in works if normalized(w.get("title",""))==normalized(part["title"])
               and normalized(w.get("composer",""))==normalized(part["composer"])]
        if len(found)>1:raise ValueError("ambiguous canonical component")
        part["work_id"]=found[0]["id"] if found else None
    rows=detail.get("event_facts")
    if not isinstance(rows,list) or not rows:raise ValueError("missing program showtimes")
    seen=set()
    dates=[]
    for row in rows:
        if not isinstance(row,dict) or row.get("venue")!=venue:
            raise ValueError("different program venues")
        try:
            day=date.fromisoformat(row["date"])
            stamp=datetime.fromisoformat(row["starts_at"])
            if not stamp.tzinfo or stamp.utcoffset() is None or stamp.astimezone(IT).date()!=day:
                raise ValueError("program time not verified in Italy")
            local=stamp.astimezone(IT)
        except (ValueError,TypeError,KeyError) as exc:
            raise ValueError("invalid program schedule") from exc
        if day in seen:raise ValueError("one ticketed program per calendar date")
        seen.add(day)
        dates.append({"local_date":day.isoformat(),"starts_at":local.isoformat()})
    identity=hashlib.sha256((source_key+"|"+source_url).encode()).hexdigest()[:16]
    pid="oa-p-"+identity
    return {
        "id":pid,"title":" / ".join(part["title"] for part in parts),
        "components":parts,"source_key":source_key,"source_url":source_url,
        "venue":venue,"municipality":city,"region":region,
        "route_slug":slugify(" ".join(part["title"] for part in parts)),
        "performances":[{
            "id":"oa-pr-"+hashlib.sha256((pid+"|"+d["local_date"]).encode()).hexdigest()[:16],
            "program_id":pid,**d} for d in sorted(dates,key=lambda x:x["local_date"])]
    }
