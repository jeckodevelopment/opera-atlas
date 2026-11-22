"""Bounded first-party proof for the Trieste 2027 Jeanne double bill.

The official theatre brochure lists six public performances and attributes
two independent compositions. One ticket is published per date, never
one invented combined opera or duplicate component tickets.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from scripts.publish_catalog_v2 import ROOT

PROOF=ROOT/"data"/"trieste-jeanne-program-2027.json"
SOURCE_KEY="verdi-trieste-season-2026-27"
SOURCE_URL="https://www.teatroverdi-trieste.com/it/spettacoli/jeanne-darc-au-bucher-jeanne-dark/"
SCHEDULE_URL=("https://www.teatroverdi-trieste.com/wp-content/uploads/2026/11/"
              "Programma_STAGIONE_LIRICA_2026_27_WEB.pdf")
CREDITS_URL=("https://www.teatroverdi-trieste.com/it/news/"
             "presentata-la-stagione-lirica-e-di-balletto-2026-27/")
COMPONENTS=(
    ("Jeanne d’Arc au bûcher","Arthur Honegger"),
    ("Jeanne Dark","Fabio Vacchi"),
)
EXPECTED_DATES=(
    ("2027-04-09","20:00"),("2027-04-10","18:00"),
    ("2027-04-11","16:00"),("2027-04-16","20:00"),
    ("2027-04-17","16:00"),("2027-04-18","16:00"),
)
VENUE="Teatro Lirico Giuseppe Verdi"


def verified_program(*,source_key:str,source_url:str)->tuple[str,list[dict],list[dict]]:
    """Review exact source-bound season proof, then build two credited rows/date.

    A stale or tampered review document does not silently change recite.
    A newer season or different source URL must be checked independently.
    """
    if source_key!=SOURCE_KEY or source_url!=SOURCE_URL:
        raise ValueError("not the verified Trieste Jeanne programme")
    doc=json.loads(PROOF.read_text(encoding="utf-8"))
    if (doc.get("schema_version")!=1 or doc.get("source_key")!=SOURCE_KEY
            or doc.get("source_url")!=SOURCE_URL
            or doc.get("official_schedule_url")!=SCHEDULE_URL
            or doc.get("official_credits_url")!=CREDITS_URL
            or doc.get("venue")!=VENUE
            or [(part.get("title"),part.get("composer")) for part in doc.get("components",[])]
                !=list(COMPONENTS)
            or doc.get("dates")!=[list(row) for row in EXPECTED_DATES]):
        raise ValueError("unverified or inconsistent Trieste first-party season proof")
    # Check all dates are real calendar days and each clock has a legal HH:MM.
    for day,clock in EXPECTED_DATES:
        date.fromisoformat(day)
        if not re.fullmatch(r"(?:[01]\\d|2[0-3]):[0-5]\\d",clock):
            raise ValueError("invalid official Trieste clock")
    from scripts.build_verified_catalog import official_local_time
    parts=[{"title":title,"composer":composer} for title,composer in COMPONENTS]
    heading="/".join(x["title"] for x in parts)+" di "+"/".join(
        x["composer"] for x in parts)
    facts=[{"event_title":part["title"],"composer":part["composer"],
            "venue":VENUE,"date":day,"starts_at":official_local_time(day,clock)}
           for day,clock in EXPECTED_DATES for part in parts]
    return heading,parts,facts
