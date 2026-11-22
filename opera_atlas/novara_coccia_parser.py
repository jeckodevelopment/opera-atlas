"""Exact official 2027 Teatro Coccia opera dates, without archive inference."""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urlsplit

from opera_atlas.national_detail_parser import MONTHS, clean

HOST = "www.fondazioneteatrococcia.it"
VENUE = "Teatro Coccia"
WORKS = {
    "stagione-27-rigoletto.html": ("Rigoletto", "Giuseppe Verdi", 4),
    "stagione-27-il-barbiere-di-siviglia.html": (
        "Il barbiere di Siviglia", "Gioachino Rossini", 4),
    "stagione-27-le-nozze-di-figaro.html": (
        "Le nozze di Figaro", "Wolfgang Amadeus Mozart", 3),
}
WEEKDAYS = {
    "lunedì": 0, "lunedi": 0, "martedì": 1, "martedi": 1,
    "mercoledì": 2, "mercoledi": 2, "giovedì": 3, "giovedi": 3,
    "venerdì": 4, "venerdi": 4, "sabato": 5, "domenica": 6,
}
DATE = re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\s+2027\s+"
    r"ore\s+([01]?\d|2[0-3]):([0-5]\d)\b"
)

def parse_detail(html: str, *, url: str):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != HOST
            or parsed.port is not None or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError("unapproved Novara source origin")
    slug = parsed.path.removeprefix("/")
    if parsed.path != "/" + slug or slug not in WORKS:
        raise ValueError("unapproved Novara opera page")
    title, composer, expected = WORKS[slug]
    # Distinguish the composer credited to the production from cast,
    # directors and historical notes about other productions.
    text = clean(re.sub(r"(?i)</h[2-6]>", " </h3> ", html))
    if not re.search(r"(?i)\bMusica di\s+" + re.escape(composer) + r"\b", text):
        raise ValueError("missing first-party composer attribution")
    if not re.search(r"(?i)\b" + re.escape(title) + r"\b", text):
        raise ValueError("missing official work title")
    area = re.search(
        r"(?i)\binformazioni sull.evento\b(.*?)\bTEATRO COCCIA\b", text, re.S)
    if not area:
        raise ValueError("unbounded official booking dates")
    block = area.group(1)
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b", block):
        raise ValueError("cancellation requires editorial review")
    rows = []
    for match in DATE.finditer(block):
        weekday, day, month, hour, minute = match.groups()
        value = date(2027, MONTHS[month.casefold()], int(day))
        if value.weekday() != WEEKDAYS[weekday.casefold()]:
            raise ValueError("official weekday and date conflict")
        rows.append((value.isoformat(), f"{int(hour):02d}:{minute}"))
    if len(rows) != expected or len(set(rows)) != expected:
        raise ValueError("incomplete or ambiguous official performance dates")
    return title, composer, VENUE, sorted(rows)
