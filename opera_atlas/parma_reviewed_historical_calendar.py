"""Editorially reviewed first-party Parma 2026 public family calendar.

The exact theatre event URL publishes four audience-labelled ticket slots:
4 Dec 2026 09:00/11:00 Scuole (excluded),
5 Dec 2026 15:00/18:00 Famiglie (ordinary public ticketing).
The official historical dates are immutable source-bound evidence rather
than an inferred current-time or genre-based calendar.
"""
from __future__ import annotations
import re
from scripts.build_verified_catalog import official_local_time
from opera_atlas.national_detail_parser import clean
from scripts.collect_candidate_details import FirstHeading

SOURCE_KEY="parma-opera-2027"
URL="https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/"
TITLE="Piccolo Orso e la montagna di ghiaccio"
COMPOSER="Giovanni Sollima"
VENUE="Teatro Regio di Parma"
REVIEWED_PUBLIC=(("2026-12-05","15:00"),("2026-12-05","18:00"))
EXCLUDED_SCHOOLS=(("2026-12-04","09:00"),("2026-12-04","11:00"))

def verified_calendar(html:str,*,source_key:str,url:str)->list[dict]:
    """Read first-party production identity, then apply exact reviewed dates.

    The archived first-party showtime evidence was independently examined
    from this same theatre URL. The historical source may change its ticket
    widget; its event identity, author, venue and season must remain intact.
    """
    if source_key!=SOURCE_KEY or url!=URL:
        raise ValueError("unapproved historical Parma opera source")
    heading=FirstHeading()
    heading.feed(html)
    if heading.first!=TITLE:
        raise ValueError("Parma official production heading changed")
    text=clean(html)
    start=text.find(TITLE)
    if start<0:
        raise ValueError("Parma official production missing")
    body=text[start:start+12000]
    if (COMPOSER not in body or "Giancarlo De Cataldo" not in body
        or VENUE not in body
        or "4 dic 2026" not in body or "5 dic 2026" not in body):
        raise ValueError("Parma reviewed calendar identity or season changed")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",body):
        raise ValueError("Parma official cancellation requires review")
    return [{"event_title":TITLE,"composer":COMPOSER,"venue":VENUE,
             "date":day,"starts_at":official_local_time(day,hour)}
            for day,hour in REVIEWED_PUBLIC]
