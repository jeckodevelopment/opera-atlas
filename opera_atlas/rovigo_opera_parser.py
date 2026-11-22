"""Conservative first-party Teatro Sociale Rovigo 2026/27 calendar evidence.

A season announcement alone is not performance-date evidence: return no
recite until the official Comune page contains title, composer, venue,
and fully explicit dated ticket rows in the same bounded work section.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlsplit
import re

from opera_atlas.national_detail_parser import MONTHS, clean

HOST="www.comune.rovigo.it"
PATH="/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-2026-2027"
VENUE="Teatro Sociale"
# Never infer a composite programme or composer from an homonymous title.
# Operettas such as Il pipistrello are outside the lyric-opera catalogue.
WORKS={
    "Pagliacci":"Ruggero Leoncavallo",
    "Pimpinone":"Tomaso Albinoni",
    "La traviata":"Giuseppe Verdi",
    "Aida":"Giuseppe Verdi",
    "La Cenerentola":"Gioachino Rossini",
    "Il telefono":"Gian Carlo Menotti",
    "Trouble in Tahiti":"Leonard Bernstein",
}
DATE=re.compile(
    r"(?i)\b(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)"
    r"\s+(2026|2027)\s+(?:ore|alle)\s+"
    r"([01]?\d|2[0-3])[.:]([0-5]\d)\b"
)
CANCEL=re.compile(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b")

def identify_season(html:str,*,url:str)->str:
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.path.rstrip("/")!=PATH
            or u.query or u.fragment or u.port is not None
            or u.username or u.password):
        raise ValueError("unapproved Rovigo municipal season URL")
    text=clean(re.sub(r"(?i)</h[1-6]>", " </h3> ",html))
    # Municipal season headings may separate the venue and city with "di",
    # a dash or punctuation; city and venue must still be explicit.
    if not re.search(r"(?i)\bTeatro Sociale\b.{0,45}\bRovigo\b",text):
        raise ValueError("Rovigo Teatro Sociale not identified")
    # Season 2026/27 and 2026/2027 appear in official programmes.
    # An unrelated date is never enough: require a season label nearby.
    if not re.search(
        r"(?i)\bstagione\s+(?:(?:teatrale|lirica|opera)\s+)?"
        r"2026\s*[/–-]\s*(?:2027|27)\b",text
    ):
        raise ValueError("official Rovigo season 2026/27 not established")
    if not any(re.search(r"(?i)\b"+re.escape(title)+r"\b",text)
               for title in WORKS):
        raise ValueError("no recognised season opera titles")
    return text

def parse_program(html:str,*,url:str)->list[tuple[str,str,str,str,str]]:
    text=identify_season(html,url=url)
    # One section starts at its explicit work heading and ends at the next
    # recognized work heading. Ambiguous mixed programmes are review-only.
    marks=sorted(
        [(m.start(),m.end(),title,composer)
         for title,composer in WORKS.items()
         for m in re.finditer(r"(?i)\b"+re.escape(title)+r"\b",text)]
        +[(m.start(),m.end(),None,None)
          for heading in ("Il pipistrello","Die Fledermaus","The Telephone")
          for m in re.finditer(r"(?i)\b"+re.escape(heading)+r"\b",text)]
    )
    # Combined Menotti/Bernstein billing is one ticketed programme.
    composite=re.compile(
        r"(?i)\b(?:Il telefono|The Telephone)\s*"
        r"(?:/|\+|&|e|[–-])\s*Trouble in Tahiti\b"
    )
    paired_spans=[m.span() for m in composite.finditer(text)]
    rows=[]
    for i,(start,end,title,composer) in enumerate(marks):
        if title is None:
            continue
        if title in ("Il telefono","Trouble in Tahiti") and any(
                left<=start<right for left,right in paired_spans):
            continue
        bound=marks[i+1][0] if i+1<len(marks) else len(text)
        section=text[end:bound]
        # Do not accept composer in unrelated cast/footers; require an
        # explicitly labelled composer in the same short work panel.
        credit=re.search(r"(?i)\b(?:musica|compositore)\s+di\s+"
                         +re.escape(composer)+r"\b",section[:220])
        if credit is None:continue
        # Date evidence must sit beside the title's primary booking panel,
        # not inside a general listing or a historic premiere paragraph.
        panel=section[credit.end():credit.end()+550]
        # A work-specific Ridotto announcement is not a performance in
        # the main Teatro Sociale auditorium. Preserve venue identity:
        # keep this production in review until the Ridotto has a separately
        # verified canonical venue mapping. Never silently relabel it.
        if re.search(r"(?i)\bRidotto\b",section[:550]):
            continue
        # A later concert or other genre heading must not leak its times
        # into the preceding opera, even on a one-page season programme.
        panel=re.split(r"(?i)\b(?:concerto(?: di Capodanno)?|\bconcertistica\b|\bprosa\b|\bballetto\b|\bdanza\b)\b",
                       panel,maxsplit=1)[0]
        if re.search(r"(?i)\b(?:prima rappresentazione|storia dell.opera)\b",panel):
            continue
        if CANCEL.search(panel):
            continue
        for m in DATE.finditer(panel):
            day,month,year,hour,minute=m.groups()
            stamp=date(int(year),MONTHS[month.casefold()],int(day))
            if stamp.year not in (2026,2027):
                continue
            rows.append((title,composer,VENUE,stamp.isoformat(),
                         f"{int(hour):02d}:{minute}"))
    # Separate headings on the same calendar day can also represent a
    # single double-bill ticket. Withhold those ambiguous component rows.
    telephone_days={r[3] for r in rows if r[0]=="Il telefono"}
    tahiti_days={r[3] for r in rows if r[0]=="Trouble in Tahiti"}
    paired_days=telephone_days&tahiti_days
    if paired_days:
        rows=[r for r in rows if not (
            r[0] in ("Il telefono","Trouble in Tahiti")
            and r[3] in paired_days)]
    if len(rows)!=len({(r[0],r[3],r[4]) for r in rows}):
        raise ValueError("duplicate ambiguous opera recite on official source")
    return sorted(rows,key=lambda r:(r[3],r[4],r[0]))
