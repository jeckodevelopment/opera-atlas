"""Future Teatro Verdi Salerno productions, independent of 2026 work allowlist.

Important: the municipal source labels some *ballets* as Opera, including
La vie en rose / Bolero. The card taxonomy is not authoritative; a dated
production enters Atlas only when the first-party event's own synopsis
explicitly identifies an opera/operetta and credits its composer.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

from opera_atlas.national_detail_parser import MONTHS, clean
from opera_atlas.salerno_opera_parser import WEEKDAYS, VENUE

HOST = "cultura.comune.salerno.it"
INDEX = f"https://{HOST}/teatro-verdi/la-stagione/"
EVENT = re.compile(r"/eventi/([a-z0-9-]+)-(20\d{2})/?")
RECITE = re.compile(
    r"(?i)\b(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre),?\s+ore\s+"
    r"(2[0-3]|1\d|0?\d)[:.]([0-5]\d)\b"
)
DECLARED = re.compile(
    r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
    r"venerd[iì]|sabato|domenica)\s+\d{1,2}\s+"
    r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\b"
)
OPERA = re.compile(r"(?i)\b(?:opera|operetta|melodramma|dramma lirico)\b")
NONOPERA = re.compile(
    r"(?i)\b(?:balletto|coreograf[iaie]|danza|musical|concerto|"
    r"pop|crossover|musica d.artista)\b"
)
CANCEL = re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")


class FutureSalernoSeasonNotYetVerified(ValueError):
    """Exact official season year is earlier than all eligible rolling dates."""



def eligible_detail(url: str) -> bool:
    p = urlsplit(url)
    m = EVENT.fullmatch(p.path)
    return bool(p.scheme == "https" and p.hostname == HOST and m
                and 2027 <= int(m[2]) <= 2099
                and not p.query and not p.fragment
                and not p.username and not p.password and p.port is None)


class _OfficialLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.links = []
        self.href = None
        self.parts = []
        self.headings = []
        self.h3 = None

    def handle_starttag(self, tag, attrs):
        if tag in ("nav", "footer", "script", "style"):
            self.hidden += 1
        if self.hidden:
            return
        if tag == "h3":
            self.h3 = []
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.hidden:
            return
        if self.href is not None:
            self.parts.append(data)
        if self.h3 is not None:
            self.h3.append(data)

    def handle_endtag(self, tag):
        if tag == "h3" and self.h3 is not None:
            title = " ".join(" ".join(self.h3).split())
            if title:
                self.headings.append(title)
            self.h3 = None
        if tag == "a" and self.href:
            label = " ".join(" ".join(self.parts).split())
            if label:
                self.links.append((self.href, label))
            self.href = None
        if tag in ("nav", "footer", "script", "style"):
            self.hidden = max(0, self.hidden - 1)


def extract_index(html: str, *, url: str, min_links: int) -> list[str]:
    if url != INDEX:
        raise ValueError("unapproved municipal Salerno season index")
    visible = _OfficialLinks()
    visible.feed(html)
    # Page must have the municipal theatre's season identity. A generic
    # listing or an archived navigation link is not enough.
    text = clean(html)
    if not re.search(r"(?i)\bTeatro Verdi\s*[\u2013-]\s*Stagione Lirica e di Balletto\s+20\d{2}\b", text):
        raise ValueError("official Teatro Verdi opera season identity missing")
    out = set()
    for href, label in visible.links:
        target = urljoin(url, href)
        if not eligible_detail(target):
            continue
        year = int(EVENT.fullmatch(urlsplit(target).path)[2])
        # Historic mixed cards are *not* promoted as future; even if the
        # municipality erroneously tags a ballet as Opera, the detail
        # authority check remains mandatory.
        if re.search(rf"(?<!\d){year}(?!\d)", label):
            out.add(target)
    if len(out) < min_links:
        # The official page can legitimately still advertise the preceding
        # edition. Distinguish this from malformed HTML, unapproved URLs and
        # a genuine source parser failure, without inferring a 2027 program.
        year_match = re.search(
            r"(?i)\\bTeatro Verdi\\s*[\\u2013-]\\s*Stagione Lirica e di Balletto\\s+(20\\d{2})\\b",
            text)
        if year_match and int(year_match[1]) < 2027 and not out:
            raise FutureSalernoSeasonNotYetVerified(
                "future_salerno_season_not_yet_verified")
        raise ValueError("no future Salerno opera-season production candidates")
    return sorted(out)


def parse_detail(html: str, *, url: str):
    if not eligible_detail(url):
        raise ValueError("unapproved future Salerno event")
    year = int(EVENT.fullmatch(urlsplit(url).path)[2])
    heading = re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>", html)
    if not heading:
        raise ValueError("official Salerno title missing")
    heading_text = clean(heading[1])
    match = re.fullmatch(r"(.+?)\s*[|\u2013-]\s*(20\d{2})", heading_text)
    if not match or int(match[2]) != year:
        raise ValueError("Salerno event heading/year mismatch")
    title = match[1].strip()
    if not title or len(title) > 160 or NONOPERA.search(title):
        raise ValueError("Salerno event not a credible opera title")

    text = clean(html)
    source = re.search(
        r"(?is)\bDescrizione breve\b(.*?)\b(?:Evento|Organizzatore|Descrizione completa)\b",
        text)
    if not source:
        raise ValueError("missing bounded official Salerno opera description")
    description = source[1].strip()
    if not OPERA.search(description[:180]) or NONOPERA.search(description[:180]):
        raise ValueError("Salerno event synopsis does not confirm an opera")
    # First-party type + credited composer, not a cast name, soundtrack,
    # generic footer 'OPERA' price table, or related-show link.
    composer_match = re.search(
        r"(?i)\b(?:opera|operetta|melodramma|dramma lirico)\b.{0,150}?"
        r"\bdi\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'.\u2019-]*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'.\u2019-]*){1,3})"
        r"(?=\s+(?:Libretto|Prima|Direttore|Regia|lasciata|incompiuta)\b|[.;]|$)",
        description,
    )
    if not composer_match:
        raise ValueError("first-party Salerno opera composer not uniquely credited")
    composer = composer_match[1].strip()
    # Reject placeholders and multi-author credits rather than treating a
    # generic phrase as a composer's personal name.
    tokens = composer.casefold().split()
    if (any(word in {"un","uno","una","artista","ignoto","ignota",
                     "sconosciuto","sconosciuta","identificato","identificata",
                     "non","vari","diversi","anonimo","anonima","e"} for word in tokens)
            or len(tokens)>4):
        raise ValueError("ambiguous or uncredited future Salerno composer")
    if VENUE.casefold() not in text[:text.find("APPUNTAMENTI")].casefold():
        raise ValueError("Teatro Municipale Verdi source venue absent")
    section = re.search(
        r"(?is)\bAPPUNTAMENTI\b(.*?)(?:\bLuoghi collegati\b|\bData inizio\b)",
        text)
    if not section:
        raise ValueError("missing bounded future Salerno showtimes")
    block = section[1]
    if CANCEL.search(block):
        raise ValueError("cancelled or postponed future Salerno production")
    matches = list(RECITE.finditer(block))
    if not matches or len(matches) != len(DECLARED.findall(block)) or len(matches) > 24:
        raise ValueError("Salerno future official recite dates incomplete")
    rows = []
    for row in matches:
        weekday, day, month, hour, minute = row.groups()
        observed = date(year, MONTHS[month.casefold()], int(day))
        if observed.weekday() != WEEKDAYS[weekday.casefold()]:
            raise ValueError("Salerno weekday and year disagree")
        rows.append((observed.isoformat(), f"{int(hour):02d}:{minute}"))
    if len(rows) != len(set(rows)):
        raise ValueError("duplicate Salerno future recite")
    return title, composer, VENUE, sorted(rows)
