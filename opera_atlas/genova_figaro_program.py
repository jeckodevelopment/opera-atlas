"""Exact first-party 2026 Carlo Felice Figaro ticket calendar.

Both the performance webpage and the theatre's published 2026/27 brochure
list these six public performances; do not infer unlisted times.
"""
from __future__ import annotations
from datetime import date
import re
from scripts.build_verified_catalog import official_local_time

KEY="carlo-felice-season-2026-27"
URL="https://www.carlofelice.it/spettacolo/le-nozze-di-figaro/"
SCHEDULE_URL=("https://www.carlofelice.it/wp-content/uploads/2026/07/"
              "Stagione_26-27_Teatro_Carlo_Felice_v07.pdf")
ROWS=(
    ("2026-10-16","19:30"),("2026-10-17","15:00"),
    ("2026-10-18","15:00"),("2026-10-23","19:30"),
    ("2026-10-24","19:30"),("2026-10-25","15:00"),
)
def verified_calendar(*,source_key:str,source_url:str)->list[dict]:
    if source_key!=KEY or source_url!=URL:
        raise ValueError("not verified Genova Figaro source")
    if len(ROWS)!=6 or len({d for d,_ in ROWS})!=6:
        raise ValueError("incomplete Figaro official showtimes")
    for day,clock in ROWS:
        date.fromisoformat(day)
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",clock):
            raise ValueError("invalid official clock")
    return [{"event_title":"Le nozze di Figaro",
             "composer":"Wolfgang Amadeus Mozart",
             "venue":"Teatro Carlo Felice",
             "date":day,"starts_at":official_local_time(day,clock)}
            for day,clock in ROWS]
