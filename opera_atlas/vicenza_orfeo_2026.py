"""Two-source first-party confirmation of the 2026 L'Orfeo at Villa Pisani.

The exact event page provides artist/title/composer and place/time; the
independent official festival press release confirms it is opera, the full
calendar year, and the correct physical venue. This is a narrowly bounded
historic fallback, not a rule for deducing future productions.
"""
from __future__ import annotations
import re
from opera_atlas.vicenza_olimpico_opera import KEY, Page

URL = "https://www.vicenzainlirica.it/lorfeo-monteverdi/"
PRESS_URL = (
    "https://www.vicenzainlirica.it/"
    "lorfeo-di-monteverdi-chiude-la-xiv-edizione-di-vicenza-in-lirica-"
    "domenica-a-villa-pisani-bonetti-lultimo-appuntamento-del-festival/"
)
VENUE = "Villa Pisani Bonetti"
CITY = "Lonigo"
DAY = "2026-09-20"
CLOCK = "17:00"


def verified_calendar(detail_html: str, press_html: str, *,
                      source_key: str, source_url: str) -> list[dict]:
    if source_key != KEY or source_url != URL:
        raise ValueError("unapproved Vicenza Orfeo source")
    article, release = Page(), Page()
    article.feed(detail_html)
    release.feed(press_html)
    heading = " ".join(article.h1)
    # Exact composition identity; an artist biography mentioning Monteverdi
    # cannot authorize this candidate.
    if not re.fullmatch(r"L[’']Orfeo\\s*[–-]\\s*Monteverdi", heading, re.I):
        raise ValueError("Vicenza Orfeo work title missing")
    official = " ".join(article.parts)
    news = " ".join(release.parts)
    required_detail = (
        r"Domenica\\s+20\\s+settembre\\s*[|,–-]?\\s*ore\\s*17[.,:]00",
        r"Villa\\s+Pisani\\s+Bonetti\\s+di\\s+Bagnolo\\s+di\\s+Lonigo",
        r"L[’']ORFEO\\s+di\\s+C\\.?\\s*MONTEVERDI",
    )
    if not all(re.search(pattern, official, re.I) for pattern in required_detail):
        raise ValueError("Vicenza Orfeo original article venue/clock/identity missing")
    # The independent 2026 festival announcement explicitly calls this work
    # an opera, not a gala/concert, and confirms the date and different venue.
    press_checks = (
        r"L[’']Orfeo\\s+di\\s+Claudio\\s+Monteverdi",
        r"\\bopera\\b",
        r"20\\s+settembre\\s+alle\\s+ore\\s+17[.,:]00\\s+a\\s+Villa\\s+Pisani\\s+Bonetti",
        r"Bagnolo\\s+di\\s+Lonigo",
        r"\\b2026\\b",
    )
    if not all(re.search(pattern, news, re.I) for pattern in press_checks):
        raise ValueError("Vicenza Orfeo festival press corroboration missing")
    from scripts.build_verified_catalog import official_local_time
    return [{"event_title": "L'Orfeo", "composer": "Claudio Monteverdi",
             "venue": VENUE, "date": DAY,
             "starts_at": official_local_time(DAY, CLOCK)}]
