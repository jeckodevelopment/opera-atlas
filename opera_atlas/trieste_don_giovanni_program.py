"""Source-bound Teatro Verdi Trieste official January 2027 Don Giovanni calendar.

The season brochure and the official press article both identify Mozart's
opera and the six ticketed dates. This is not inferred from event URL slugs.
"""
from __future__ import annotations

from datetime import date
import re
from scripts.build_verified_catalog import official_local_time

KEY="verdi-trieste-season-2026-27"
URL="https://www.teatroverdi-trieste.com/it/spettacoli/don-giovanni-2/"
SCHEDULE_URL=("https://www.teatroverdi-trieste.com/wp-content/uploads/2026/11/"
              "Programma_STAGIONE_LIRICA_2026_27_WEB.pdf")
CREDITS_URL=("https://www.teatroverdi-trieste.com/it/news/"
             "presentata-la-stagione-lirica-e-di-balletto-2026-27/")
VENUE="Teatro Lirico Giuseppe Verdi"
ROWS=(
    ("2027-01-15","20:00"),("2027-01-16","18:00"),
    ("2027-01-17","16:00"),("2027-01-21","20:00"),
    ("2027-01-23","16:00"),("2027-01-24","16:00"),
)


def verified_calendar(*,source_key:str,source_url:str)->list[dict]:
    """Return only the six individually documented public performances."""
    if source_key!=KEY or source_url!=URL:
        raise ValueError("not the verified 2027 Trieste Don Giovanni production")
    if len(ROWS)!=6 or len({day for day,_ in ROWS})!=6:
        raise ValueError("incomplete official Trieste calendar")
    for day,clock in ROWS:
        date.fromisoformat(day)
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",clock):
            raise ValueError("invalid Trieste official clock")
    return [{"event_title":"Don Giovanni",
             "composer":"Wolfgang Amadeus Mozart",
             "venue":VENUE,"date":day,
             "starts_at":official_local_time(day,clock)}
            for day,clock in ROWS]
