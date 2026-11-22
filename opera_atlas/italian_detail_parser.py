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
CUES=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie]|sospes[oaie])\b")

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
    else:
        from scripts.discover_season_indexes import eligible
        if not eligible("donizetti-opera-2026",url):
            raise ValueError("untrusted Donizetti detail path")
    # The Carlo Felice ticket widget uses inline elements for the date,
    # subscription turn and clock. The common visible-text helper does not
    # separate every inline tag: "16/10/2026Turno A|Ore 19:30" must never
    # be silently treated as an event without a verified showtime.
    if source_key=="carlo-felice-season-2026-27":
        visible_html=re.sub(r"(?i)</?(?:span|small|strong|b|em|time|label|button)\b[^>]*>",
                            " ",html)
    else:
        visible_html=html
    text=clean(visible_html)
    # The source may use a typographic apostrophe where the canonical composer
    # uses a straight one. Normalize only this glyph, never the actual credit.
    if not text or normalized(composer).replace("’","\u0027") not in normalized(text).replace("’","\u0027"):
        raise ValueError("composer absent from official detail")
    # Verify the actual heading, rather than a title occurring in a footer.
    from scripts.collect_candidate_details import FirstHeading
    heading=FirstHeading()
    heading.feed(html)
    if normalized(heading.first or "").replace("’","\u0027")!=normalized(title).replace("’","\u0027"):
        raise ValueError("official detail heading mismatches work")
    if source_key=="carlo-felice-season-2026-27":
        cutoff=re.search(r"(?i)\bDove\s*:",text)
        if not cutoff:raise ValueError("missing Carlo Felice venue boundary")
        schedule=text[:cutoff.start()]
        venue_section=text[cutoff.end():cutoff.end()+90]
        if not re.match(r"\s*Teatro Carlo Felice\b",venue_section,re.I):
            raise ValueError("unknown Carlo Felice venue")
        venue="Teatro Carlo Felice"
        # The first-party timetable always binds a fully dated ticket row
        # to an explicit clock. WordPress may change/remove its localized
        # weekday abbreviation, while keeping its dd/mm/yyyy and Turno label.
        # Only the block *before* the verified Dove: Teatro Carlo Felice
        # boundary is eligible; no repertoire/press dates from the body.
        rx=re.compile(r"(?i)\b(\d{1,2})/(\d{1,2})/(20\d{2})"
                      r"\s+(?:\([^)]{1,40}\)\s*)?(?:Turno\s+[A-Z0-9-]{1,8}\s*)?"
                      r"\|?\s*Ore\s*([01]?\d|2[0-3]):([0-5]\d)\b")
    else:
        section=re.search(r"(?i)\bInfo\b",text)
        venue_marker=re.search(r"(?i)\bLuogo\b",text[section.end():] if section else "")
        if not section or not venue_marker:
            raise ValueError("missing Donizetti schedule section")
        schedule=text[section.end():section.end()+venue_marker.start()]
        venue_text=text[section.end()+venue_marker.end():]
        venue_match=re.match(r"\s*(Teatro Donizetti|Teatro Sociale)\b",venue_text,re.I)
        if not venue_match:raise ValueError("unknown Donizetti venue")
        venue=venue_match.group(1)
        rx=re.compile(r"(?i)\b(\d{1,2})\s+("+ "|".join(MONTHS) +
                      r")\s+(20\d{2})\s*\|\s*([01]?\d|2[0-3]):([0-5]\d)\b")
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
    if not found and source_key=="carlo-felice-season-2026-27":
        # Some first-party ticket cards render additional subscription and
        # accessibility labels between the complete date and the clock.
        # A tightly bounded, date-specific fallback is allowed ONLY in the
        # verified theatre/venue section; do not borrow a clock from a
        # following date, cast paragraph or unrelated recommendation.
        dates_rx=re.compile(r"\\b\\d{1,2}/\\d{1,2}/20\\d{2}\\b")
        date_hits=list(dates_rx.finditer(schedule))
        for index,observed in enumerate(date_hits):
            boundary=(date_hits[index+1].start()
                      if index+1<len(date_hits) else len(schedule))
            block=schedule[observed.end():min(boundary,observed.end()+180)]
            clocks=re.findall(
                r"(?i)\\bOre\\s*([01]?\\d|2[0-3]):([0-5]\\d)\\b",block)
            if len(clocks)!=1 or CUES.search(block):
                raise ValueError("incomplete official Carlo Felice date/time evidence")
            day,month,year=map(int,observed.group().split("/"))
            key=date(year,month,day).isoformat()
            if key in found:
                raise ValueError("same-day duplicate or conflicting recite")
            found[key]=f"{int(clocks[0][0]):02d}:{clocks[0][1]}"
    if not found:raise ValueError("no explicit official performance dates")
    if source_key=="carlo-felice-season-2026-27":
        # Never silently omit a real official date if the page changes the
        # schedule markup. Each date-only row needs a single explicit hour.
        all_dates=re.findall(r"\b\d{1,2}/\d{1,2}/20\d{2}\b",schedule)
        if len(all_dates)!=len(found):
            raise ValueError("incomplete official Carlo Felice date/time evidence")
    return venue,sorted(found.items())

def extract_source_credited_carlo_felice(html:str,*,url:str):
    """Observe an unregistered work only with explicit official composer credit.

    This is source evidence, not an authority decision: the independent
    Wikidata identity check must still succeed before catalog promotion.
    """
    from scripts.collect_candidate_details import FirstHeading
    from scripts.publish_catalog_v2 import slugify
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="www.carlofelice.it"
        or parsed.port is not None or parsed.query or parsed.fragment
        or parsed.username or parsed.password
        or not re.fullmatch(r"/spettacolo/[a-z0-9-]+/",parsed.path)):
        raise ValueError("untrusted official composer source")
    heading=FirstHeading()
    heading.feed(html)
    title=heading.first
    path_slug=parsed.path.rstrip("/").rsplit("/",1)[-1]
    if (not isinstance(title,str) or not 3<=len(title)<=180
        or slugify(title)!=path_slug):
        raise ValueError("official heading does not match opera page")
    visible=clean(html)
    at=normalized(visible).find(normalized(title))
    if at<0:
        raise ValueError("official opera heading absent from visible text")
    window=visible[at+len(title):at+len(title)+1400]
    # Only a labelled work credit followed by the labelled conductor role,
    # not prose mentioning a musician, proves source attribution.
    credits=re.findall(
        r"(?i)\bMusica\s+di\s+"
        r"([A-ZÀ-Ž][\wÀ-ÿ'’.-]*(?:\s+[A-ZÀ-Ž][\wÀ-ÿ'’.-]*){1,5})"
        r"\s+Direttore\b",window)
    if len(credits)!=1:
        raise ValueError("missing or conflicting official composer credit")
    composer=credits[0].strip()
    venue,recite=parse_detail(html,source_key="carlo-felice-season-2026-27",
                               url=url,title=title,composer=composer)
    return title,composer,venue,recite
