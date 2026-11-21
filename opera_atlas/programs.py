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

def heading_from_html(html:str)->str|None:
    """Find a complete independently credited multi-work primary heading.

    Never treat a slash in an URL or a title alone as a verified component.
    """
    from html.parser import HTMLParser
    class Heading(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active=False
            self.found=None
            self.parts=[]
        def handle_starttag(self,tag,attrs):
            if tag.lower()=="h1" and self.found is None:self.active=True
        def handle_data(self,data):
            if self.active:self.parts.append(data)
        def handle_endtag(self,tag):
            if tag.lower()=="h1" and self.active:
                self.found=" ".join("".join(self.parts).split())
                self.active=False
    h=Heading()
    h.feed(html[:250000])
    if not h.found:return None
    try:credited_components(h.found)
    except ValueError:return None
    return h.found


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
    # Source adapters may record separately verified component credits.
    # This supports different official heading formats without venue-specific
    # handling inside the central program model.
    credited=detail.get("program_components")
    if credited is not None:
        if (not isinstance(credited,list) or not 2<=len(credited)<=12
            or any(not isinstance(p,dict) or set(p)!={"title","composer"}
                   or not all(isinstance(p[k],str) and p[k].strip()
                              for k in ("title","composer")) for p in credited)):
            raise ValueError("invalid credited components")
        parts=[dict(p) for p in credited]
        names=[(normalized(p["title"]),normalized(p["composer"])) for p in parts]
        if len(set(names))!=len(names) or heading!=detail.get("program_heading"):
            raise ValueError("ambiguous credited program")
    else:
        parts=credited_components(heading)
    works=list(registry.get("works",{}).values())
    for part in parts:
        found=[w for w in works if normalized(w.get("title",""))==normalized(part["title"])
               and normalized(w.get("composer",""))==normalized(part["composer"])]
        if len(found)>1:raise ValueError("ambiguous canonical component")
        part["work_id"]=found[0]["id"] if found else None
    rows=detail.get("event_facts")
    if not isinstance(rows,list) or not rows:raise ValueError("missing program showtimes")
    member_identities={(normalized(part["title"]),normalized(part["composer"]))
                       for part in parts}
    if any((normalized(row.get("event_title","")),
            normalized(row.get("composer",""))) not in member_identities
           for row in rows if isinstance(row,dict)):
        raise ValueError("program schedule credited to unrelated composition")
    grouped={}
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
        group=grouped.setdefault(day.isoformat(),{})
        identity=(normalized(row["event_title"]),normalized(row["composer"]))
        if identity in group or (group and set(group.values())!={local.isoformat()}):
            raise ValueError("duplicate or contradictory program ticket")
        group[identity]=local.isoformat()
    observed={tuple(sorted(group)) for group in grouped.values()}
    if len(observed)!=1:raise ValueError("inconsistent program composition")
    identities=set(next(iter(grouped.values())))
    if identities!=member_identities and (
            len(identities)!=1 or detail.get("program_components") is not None):
        raise ValueError("incomplete independently credited program")
    for day,group in sorted(grouped.items()):
        dates.append({"local_date":day,"starts_at":next(iter(group.values()))})
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
