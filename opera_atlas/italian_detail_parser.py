"""Strict official detail-page dates for Carlo Felice and Donizetti Opera.

Only explicitly dated and timed events are extracted. No season-range inference,
no venue substitution and no automatic publication without a canonical work.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import clean
from scripts.publish_catalog_v2 import normalized

MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
CUES=re.compile(r"(?i)\\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\\b")

def parse_detail(html:str,*,source_key:str,url:str,title:str,composer:str):
    parsed=urlsplit(url)
    hosts={"carlo-felice-season-2026-27":"www.carlofelice.it",
           "donizetti-opera-2026":"www.donizettiopera.org"}
    if (source_key not in hosts or parsed.scheme!="https"
        or parsed.hostname!=hosts[source_key] or parsed.port is not None
        or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("untrusted opera detail origin")
    if source_key=="carlo-felice-season-2026-27":
        if not re.fullmatch(r"/spettacolo/[a-z0-9-]+/",parsed.path):
            raise ValueError("untrusted Carlo Felice detail path")
    elif not re.fullmatch(r"/it/evento/[a-z0-9-]+/",parsed.path):
        raise ValueError("untrusted Donizetti detail path")
    text=clean(html)
    if not text or normalized(composer) not in normalized(text):
        raise ValueError("composer absent from official detail")
    # Verify the actual heading, rather than a title occurring in a footer.
    from scripts.collect_candidate_details import FirstHeading
    heading=FirstHeading()
    heading.feed(html)
    if normalized(heading.first or "")!=normalized(title):
        raise ValueError("official detail heading mismatches work")
    if source_key=="carlo-felice-season-2026-27":
        cutoff=re.search(r"(?i)\\bDove\\s*:",text)
        if not cutoff:raise ValueError("missing Carlo Felice venue boundary")
        schedule=text[:cutoff.start()]
        venue_section=text[cutoff.end():cutoff.end()+90]
        if not re.match(r"\\s*Teatro Carlo Felice\\b",venue_section,re.I):
            raise ValueError("unknown Carlo Felice venue")
        venue="Teatro Carlo Felice"
        rx=re.compile(r"(?i)\\b(?:LU|MA|ME|GI|VE|SA|DO)\\s+(\\d{1,2})/(\\d{1,2})/(20\\d{2})"
                      r"\\s+.{0,45}?\\bOre\\s+([01]?\\d|2[0-3]):([0-5]\\d)\\b")
    else:
        section=re.search(r"(?i)\\bInfo\\b",text)
        venue_marker=re.search(r"(?i)\\bLuogo\\b",text[section.end():] if section else "")
        if not section or not venue_marker:
            raise ValueError("missing Donizetti schedule section")
        schedule=text[section.end():section.end()+venue_marker.start()]
        venue_text=text[section.end()+venue_marker.end():]
        venue_match=re.match(r"\\s*(Teatro Donizetti|Teatro Sociale)\\b",venue_text,re.I)
        if not venue_match:raise ValueError("unknown Donizetti venue")
        venue=venue_match.group(1)
        rx=re.compile(r"(?i)\\b(\\d{1,2})\\s+("+ "|".join(MONTHS) +
                      r")\\s+(20\\d{2})\\s*\\|\\s*([01]?\\d|2[0-3]):([0-5]\\d)\\b")
    found={}
    for match in rx.finditer(schedule):
        if source_key=="carlo-felice-season-2026-27":
            day,month,year,hour,minute=map(int,match.groups())
        else:
            day=int(match[1]);month=MONTHS[match[2].casefold()]
            year=int(match[3]);hour=int(match[4]);minute=int(match[5])
        key=date(year,month,day).isoformat()
        if CUES.search(schedule[max(0,match.start()-50):match.end()+60]):
            raise ValueError("changed or cancelled showtime needs review")
        if key in found:
            raise ValueError("same-day duplicate or conflicting recite")
        found[key]=f"{hour:02d}:{minute:02d}"
    if not found:raise ValueError("no explicit official performance dates")
    return venue,sorted(found.items())
