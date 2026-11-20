"""Conservative Teatro Regio production-page extraction (offline HTML input).

The official season listing mixes opera and ballet. Only individual detail
pages with explicit full date, local time and Europe/Rome timezone are accepted.
A date interval in a listing is never expanded into guessed performances.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

REGIO_HOST = "www.teatroregio.torino.it"
DATE_RE = re.compile(
    r"(?<!\\d)(20\\d{2}-\\d{2}-\\d{2})[ T](\\d{2}:\\d{2}:\\d{2})"
    r"\\s*(?:Europe/Rome)(?![\\w/])"
)
TIMEZONE = ZoneInfo("Europe/Rome")
NON_OPERA = re.compile(r"\\b(ballet|balletto|danza|concert[oi])\\b", re.I)


@dataclass(frozen=True)
class PerformanceFact:
    title: str
    composer: str
    starts_at: datetime
    source_url: str
    external_id: str


class _PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.heading: list[str] = []
        self.in_h1 = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif tag == "h1":
            self.in_h1 += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
        elif tag == "h1" and self.in_h1:
            self.in_h1 -= 1
            self.heading.append(" ".join(self.parts[-8:]))

    def handle_data(self, data):
        if not self.skip:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


def parse_regio_detail(
    html: str, *, source_url: str, expected_title: str,
    expected_composer: str,
) -> list[PerformanceFact]:
    """Extract only individually timestamped recite with verified work facts.

    Work title and composer must come from a curated verified mapping, not be
    inferred from the shared Opera e Balletto category heading.
    """
    uri = urlsplit(source_url)
    if uri.scheme != "https" or uri.hostname not in (REGIO_HOST, "teatroregio.torino.it"):
        raise ValueError("not an official HTTPS Teatro Regio page")
    if "/calendario" in uri.path or "/calendar/" in uri.path:
        raise ValueError("listing pages cannot yield individual recite")
    if not expected_title.strip() or not expected_composer.strip():
        raise ValueError("verified work title and composer required")
    parser = _PageText()
    parser.feed(html)
    text = " ".join(parser.parts)
    if not text.strip():
        return []
    if NON_OPERA.search(expected_title):
        return []
    # Keep evidence minimal. We do not store descriptions or cast excerpts.
    if expected_title.casefold() not in text.casefold():
        raise ValueError("curated title not present in page")
    if expected_composer.casefold() not in text.casefold():
        raise ValueError("curated composer not present in page")
    matches = DATE_RE.findall(text)
    parsed: dict[str, PerformanceFact] = {}
    for day, clock in matches:
        naive = datetime.fromisoformat(day + "T" + clock)
        start = naive.replace(tzinfo=TIMEZONE)
        # Detect ambiguous/nonexistent wall times instead of inventing offset.
        utc = start.astimezone(ZoneInfo("UTC"))
        if utc.astimezone(TIMEZONE).replace(tzinfo=None) != naive:
            raise ValueError("nonexistent local time")
        alternate = naive.replace(tzinfo=TIMEZONE, fold=1)
        if alternate.utcoffset() != start.utcoffset():
            raise ValueError("ambiguous local time")
        key = start.isoformat(timespec="seconds")
        parsed[key] = PerformanceFact(
            expected_title.strip(), expected_composer.strip(), start,
            source_url, f"{uri.path}:{key}",
        )
    return list(parsed.values())
