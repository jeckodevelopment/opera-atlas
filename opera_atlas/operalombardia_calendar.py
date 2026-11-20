"""Conservative multi-production OperaLombardia season calendar parser.

The 2026/27 calendar gives precise dates and theatres, but no start times.
Decode only semantic HTML table rows, not text fragments or page body
matches. An unknown opera, ambiguous date, malformed venue or cancellation
makes the entire scan inconclusive. Never infer a midnight performance.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

MONTHS = {
    "SETTEMBRE": 9, "OTTOBRE": 10, "NOVEMBRE": 11,
    "DICEMBRE": 12, "GENNAIO": 1, "FEBBRAIO": 2,
    "MARZO": 3, "APRILE": 4, "MAGGIO": 5, "GIUGNO": 6,
    "LUGLIO": 7, "AGOSTO": 8,
}
OPERA_TITLES = {
    "TURANDOT": ("Turandot",),
    "DEATH IN VENICE": ("Death in Venice",),
    "CAVALLERIA RUSTICANA / PAGLIACCI": ("Cavalleria rusticana", "Pagliacci"),
    "L’ITALIANA IN ALGERI": ("L’italiana in Algeri",),
    "L'ITALIANA IN ALGERI": ("L’italiana in Algeri",),
    "UN BALLO IN MASCHERA": ("Un ballo in maschera",),
}
IGNORED = {"WORLD OPERA DAY 2026"}


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
        self.table_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table_depth += 1
        if self.table_depth <= 0:
            return
        if tag == "tr" and self.row is None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None and self.cell is None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
            self.cell = None
        elif tag == "table" and self.table_depth > 0:
            self.table_depth -= 1


def parse_calendar(html: str, *, allow_unknown_for_review: bool = False) -> list[tuple[str,str,str,str,None]]:
    if not isinstance(html, str) or not html:
        raise ValueError("missing official season HTML")
    parser = _Table()
    parser.feed(html)
    month = year = None
    found = []
    seen = set()
    for cells in parser.rows:
        if not cells:
            continue
        heading = " ".join(cells).upper().replace("’", "'")
        full = re.fullmatch(
            r"\s*(" + "|".join(MONTHS) + r")\s+(20\d\d)\s*", heading
        )
        if full:
            month = MONTHS[full.group(1)]
            year = int(full.group(2))
            if year not in (2026,2027):
                raise ValueError("unsupported OperaLombardia season")
            continue
        if not cells[0].strip().isdigit():
            continue
        if len(cells) < 3 or month is None or year is None:
            raise ValueError("calendar recita missing month/title/theatre")
        day = int(cells[0].strip())
        if day < 1 or day > 31:
            raise ValueError("invalid calendar day")
        from datetime import date
        local_day = date(year,month,day).isoformat()
        title = cells[1].strip().upper().replace("’","'")
        if "ANNULLAT" in " ".join(cells).upper() or "RINVIAT" in " ".join(cells).upper():
            raise ValueError("cancelled/moved performance requires review")
        if title in IGNORED:
            continue
        recognized = {
            key.upper().replace("’","'"): value
            for key,value in OPERA_TITLES.items()
        }.get(title)
        if recognized is None:
            if not allow_unknown_for_review:
                raise ValueError("unrecognized production: " + title[:100])
            # Unknown titles are ONLY factual review candidates, never
            # validated operatic works or public events.
            if len(title) > 120 or not re.fullmatch(r"[A-ZÀ-ÖØ-Ý0-9 '’.,:;!?()/-]+", title):
                raise ValueError("invalid unknown calendar title")
            recognized = (cells[1].strip(),)
        if len(cells) != 3:
            raise ValueError("ambiguous venue columns")
        venue_parts = [p.strip() for p in cells[2].split(",", 1)]
        if len(venue_parts) != 2 or not all(venue_parts):
            raise ValueError("unknown theatre for calendar row")
        city, venue = venue_parts
        for name in recognized:
            key = (name.casefold(),city.casefold(),venue.casefold(),local_day)
            if key in seen:
                raise ValueError("duplicate calendar opera/venue/date")
            seen.add(key)
            found.append((name,venue,city,local_day,None))
    if len(found) < 30:
        # Rejection prevents a partially fetched or restructured index from
        # deleting/adding arbitrary observations.
        raise ValueError("incomplete OperaLombardia 2026/27 calendar")
    return found
