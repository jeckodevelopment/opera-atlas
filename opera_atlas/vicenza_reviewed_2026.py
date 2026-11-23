"""Source-bound archival ticket-office evidence for two 2026 Olimpico operas.

The dated listing was independently checked on the official festival ticket
office at https://www.vicenzainlirica.it/biglietteria/ (2026-11-23).
These are *historic reviewed facts*, not a synthetic future season and not a
replacement for the evergreen first-party discovery/parser. Every candidate's
live article still must confirm title, composer, venue and *each* showtime.
"""
from __future__ import annotations

from scripts.build_verified_catalog import official_local_time
from opera_atlas.vicenza_olimpico_opera import (
    KEY, TICKETING, parse_detail,
)

REVIEWED = {
    "https://www.vicenzainlirica.it/il-barbiere-di-siviglia-rossini/": {
        "title": "Il barbiere di Siviglia",
        "composer": "Gioachino Rossini",
        "dates": (("2026-09-10", "20:30"), ("2026-09-12", "20:30"),
                  ("2026-09-13", "19:00")),
        "ticket_excerpt": (
            "10/09/2026 Il barbiere di Siviglia – Rossini "
            "(anteprima-prova generale), ore 20,30. "
            "12 e 13/09/2026 Il barbiere di Siviglia – Rossini "
            "(prima e seconda recita), ore 20,30/19,00."),
    },
    "https://www.vicenzainlirica.it/il-filosofo-di-campagna-galuppi/": {
        "title": "Il filosofo di campagna",
        "composer": "Baldassare Galuppi",
        "dates": (("2026-09-14", "20:30"),),
        "ticket_excerpt": (
            "14/09/2026 Il filosofo di campagna – Galuppi, ore 20,30."),
    },
}


def verified_calendar(html: str, *, source_key: str,
                      source_url: str) -> list[dict]:
    if source_key != KEY or source_url not in REVIEWED:
        raise ValueError("Vicenza archival calendar source not reviewed")
    record = REVIEWED[source_url]
    # The frozen excerpt originates from the exact official ticket office,
    # but cannot override any contradiction in the separately fetched article.
    title, composer, venue, dates = parse_detail(
        html, url=source_url,
        ticketing_html="<article>" + record["ticket_excerpt"] + "</article>")
    if (title != record["title"] or composer != record["composer"]
            or venue != "Teatro Olimpico"
            or tuple(dates) != record["dates"]):
        raise ValueError("Vicenza reviewed showtimes contradict official article")
    return [{"event_title": title, "composer": composer,
             "venue": venue, "date": day,
             "starts_at": official_local_time(day, clock)}
            for day, clock in dates]
