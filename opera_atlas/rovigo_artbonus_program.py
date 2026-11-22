"""Bounded Comune di Rovigo season-programme identity from its Art Bonus entry.

This primary issuer-authored text verifies programme titles and composers, not
individual dates or clocks. Never promote a recita using this source alone.
"""
from __future__ import annotations
import re
from urllib.parse import urlsplit

from opera_atlas.national_detail_parser import clean

URL="https://artbonus.gov.it/1319-comune-di-rovigo.html"
EXPECTED=(
    ("Pagliacci","Ruggero Leoncavallo"),
    ("Pimpinone","Tomaso Albinoni"),
    ("The Telephone","Gian Carlo Menotti"),
    ("Trouble in Tahiti","Leonard Bernstein"),
    ("La traviata","Giuseppe Verdi"),
    ("Aida","Giuseppe Verdi"),
    ("La Cenerentola","Gioachino Rossini"),
)
EXCLUDED=(("Die Fledermaus","operetta"),)

def verified_programmes(html:str,*,url:str)->dict:
    parsed=urlsplit(url)
    if (url!=URL or parsed.scheme!="https" or parsed.hostname!="artbonus.gov.it"
            or parsed.query or parsed.fragment or parsed.port is not None
            or parsed.username or parsed.password):
        raise ValueError("unapproved municipal Art Bonus URL")
    text=clean(html)
    # This page includes many seasons: scan ONLY the 2026/27 entry and
    # cut before the next Art Bonus project. Do not conflate 2025/26 titles.
    start=re.search(r"(?i)Stagione\s+lirica\s+2026\s*[/–-]\s*2027\s*-\s*"
                    r"Eventi\s+promozionali\s+e\s+titoli\s+specifici",text)
    if start is None:
        raise ValueError("municipal 2026/27 season programme not identified")
    following=text[start.end():]
    end=re.search(r"(?i)TeatroRagazzi\s+2026|Sostituzione delle balaustre",following)
    if end is None or not 100<=end.start()<=6000:
        raise ValueError("municipal current-season block not safely bounded")
    body=following[:end.start()]
    if not re.search(r"(?i)\bTeatro Sociale\b",body):
        raise ValueError("official theatre not established")
    # This registry confirms a bounded WORK LIST, not the calendar. The
    # author-edited descriptions use abbreviated credits and typos; retain
    # canonical form only for fixed, explicit pairings below.
    hints={
        "Pagliacci":r"Pagliacci\s+di\s+R\.?\s*Leoncavallo",
        "Pimpinone":r"Pimpinone\s+di\s+T\.?\s*Albinoni",
        "The Telephone":r"The\s+Telephone\s+di\s+(?:G\.?\s*)?Menotti",
        "Trouble in Tahiti":r"Trouble\s+in\s+Tha?iti\s+di\s+(?:L\.?\s*)?Bernstein",
        "La traviata":r"(?:La\s+)?Traviata\s*\W*di\s*G\.?\s*Verdi",
        "Aida":r"Aida\s*\W*di\s*G\.?\s*Verdi",
        "La Cenerentola":r"(?:La\s+)?Cenerentola\s*\W*di\s*G\.?\s*Rossini",
    }
    # For full-year descriptions, text may have punctuation between artists
    # and titles, but must never infer unsupported composers from work title.
    observed=[]
    for title,composer in EXPECTED:
        if re.search(hints[title],body,re.I):
            observed.append({"title":title,"composer":composer})
    if len(observed)!=len(EXPECTED):
        raise ValueError("incomplete municipal lyric-opera lineup")
    if not re.search(r"(?i)operetta\s+Die\s+Fledermaus",body):
        raise ValueError("operetta genre separation not corroborated")
    if not re.search(r"(?i)dittico\s+The\s+Telephone",body):
        raise ValueError("composite event identity not established")
    return {
        "issuer":"Comune di Rovigo",
        "season":"2026/27",
        "venue":"Teatro Sociale di Rovigo",
        "works":observed,
        "excluded":[{"title":"Die Fledermaus","genre":"operetta"}],
        "composite":[["The Telephone","Trouble in Tahiti"]],
        "event_facts":[],
    }
