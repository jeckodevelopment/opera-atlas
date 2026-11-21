"""Conservative official 2026 opera programme readers for Jesi and Ancona.

Both foundations publish a bounded season article. Extract real showtimes in
the block immediately preceding each individual bill, not calendar widgets,
footers, rehearsals, school previews, past seasons or productions elsewhere.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit
from opera_atlas.national_detail_parser import MONTHS,clean

JESI_URL="https://www.fondazionepergolesispontini.com/lirica/programma-stagione-lirica-2026/"
ANCONA_URL="https://www.fondazionemuse.org/stagione-lirica-2026/"
JESI="Teatro Giovan Battista Pergolesi"
ANCONA="Teatro delle Muse"
# One source key per bill, even where the season article URL is shared.
PRODUCTIONS={
 "jesi-trittico-opera-2026":(JESI_URL,JESI,"IL TABARRO","Giacomo Puccini",3,
   (("Il tabarro","Giacomo Puccini"),("Suor Angelica","Giacomo Puccini"),("Gianni Schicchi","Giacomo Puccini"))),
 "jesi-don-pasquale-opera-2026":(JESI_URL,JESI,"DON PASQUALE","Gaetano Donizetti",3,None),
 "jesi-esecuzione-opera-2026":(JESI_URL,JESI,"L'ESECUZIONE","Salvatore Passantino",3,None),
 "jesi-nabucco-opera-2026":(JESI_URL,JESI,"NABUCCO","Giuseppe Verdi",3,None),
 "ancona-elisir-opera-2026":(ANCONA_URL,ANCONA,"L’ELISIR D’AMORE","Gaetano Donizetti",3,None),
 "ancona-cavalleria-program-2026":(ANCONA_URL,ANCONA,
   "A GIACOMO LEOPARDI / CAVALLERIA RUSTICANA","Pietro Mascagni",3,
   (("A Giacomo Leopardi","Pietro Mascagni"),("Cavalleria rusticana","Pietro Mascagni"))),
}
WEEKDAYS={"lunedì":0,"martedì":1,"mercoledì":2,"giovedì":3,"venerdì":4,"sabato":5,"domenica":6,
          "lunedi":0,"martedi":1,"mercoledi":2,"giovedi":3,"venerdi":4}
DAY=r"(luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
MONTH=r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
# For Ancona the institution publishes year in the season heading, weekday
# and day/month beside each date. Year is accepted only if weekday validates.
DATES=re.compile(rf"(?i)\b{DAY}\s+(\d{{1,2}})\s+{MONTH}(?:\s+(2026))?\s*,?\s*ore\s*([01]\d|2[0-3]|[0-9])(?:[.:]([0-5]\d))?")
WHITESPACE=re.compile(r"\s+")
def canon(s:str)->str:
    return WHITESPACE.sub(" ",s.replace("’","'")).casefold().strip()


def read_program(html:str,*,source_key:str,url:str):
    meta=PRODUCTIONS.get(source_key)
    if meta is None:raise ValueError("unknown official Marche programme")
    expected,venue,title,composer,slots,components=meta
    target=urlsplit(expected)
    actual=urlsplit(url)
    if (actual.scheme!="https" or actual.hostname!=target.hostname or
        actual.path.rstrip("/")!=target.path.rstrip("/") or
        actual.username or actual.password or actual.port is not None or
        actual.query or actual.fragment):
        raise ValueError("Marche source is not first-party approved season")
    text=clean(html)
    if source_key.startswith("jesi-"):
        start=text.find("59^ STAGIONE LIRICA DI TRADIZIONE")
        stop=text.find("Progetti speciali",start)
        if start<0 or stop<=start:raise ValueError("missing bounded Jesi 2026 opera season")
        season=text[start:stop]
        venue_label="JESI, TEATRO PERGOLESI"
    else:
        if not re.search(r"(?i)\bstagione\s+lirica\s+2026\b",html):
            raise ValueError("missing Ancona 2026 season identity")
        stop=re.search(r"(?i)\*?\s*spettacoli riservati agli studenti",text)
        season=text[:stop.start()] if stop else text[:7000]
        venue_label="ANCONA TEATRO DELLE MUSE"
        if canon(venue_label) not in canon(season[:400]):
            raise ValueError("Ancona stage venue not corroborated")
    # Only the first single-season occurrence of the exact production heading.
    target_title=canon(title)
    norm=canon(season)
    matches=list(re.finditer(r"(?<!\w)"+re.escape(target_title)+r"(?!\w)",norm))
    if not matches:raise ValueError("work not listed in the approved season")
    # Position after whitespace normalization; use one normalized coordinate system.
    idx=matches[0].start()
    if source_key.startswith("jesi-"):
        prefix=norm[:idx]
        venue_idx=prefix.rfind(canon(venue_label))
        if venue_idx<0 or idx-venue_idx>140:
            raise ValueError("Jesi work is not at Teatro Pergolesi")
        before=norm[max(0,venue_idx-320):venue_idx]
    else:
        before=norm[max(0,idx-240):idx]
    found=list(DATES.finditer(before))
    # A related educational preview or a previous "Guida all'opera"
    # appointment may occur before the current bill's three schedule rows.
    # Only the last three, immediately adjacent to this title, are eligible.
    if len(found)<slots:
        raise ValueError("incomplete exact season dates before programme")
    found=found[-slots:]
    shown=[]
    for i,m in enumerate(found):
        weekday,day,month,printed_year,hour,minute=m.groups()
        after=before[m.end():found[i+1].start() if i+1<len(found) else len(before)]
        if printed_year and int(printed_year)!=2026:
            raise ValueError("unexpected year in 2026 season")
        observed=date(2026,MONTHS[month],int(day))
        if observed.weekday()!=WEEKDAYS[weekday]:
            raise ValueError("weekday cannot corroborate 2026 date")
        if "anteprima giovani" in after or "riservat" in after:
            continue
        shown.append((observed.isoformat(),f"{int(hour):02d}:{minute or '00'}"))
    if len(shown)!=2 or len(set(day for day,_ in shown))!=2:
        raise ValueError("programme missing two ordinary ticketed performances")
    # Work specific body, not credits for a later production or related events.
    later=norm[idx:idx+4800]
    if source_key=="jesi-trittico-opera-2026":
        for work,_ in components:
            if later.count(canon(work))<1:
                raise ValueError("a Puccini Trittico component is missing")
        if later.count(canon("musica di Giacomo Puccini"))<3:
            raise ValueError("Trittico work credits not independently verified")
    elif source_key=="ancona-cavalleria-program-2026":
        if ("a giacomo leopardi" not in later or "cavalleria rusticana" not in later
            or canon("musica di Pietro Mascagni") not in later[:220]):
            raise ValueError("Mascagni mixed programme credits incomplete")
    elif canon("musica di "+composer) not in later[:650]:
        raise ValueError("missing official composer credit after target work")
    if re.search(r"\b(?:annullata|annullato|rinviata|rinviato|cancellata|cancellato)\b",
                 later[:600],re.I):
        raise ValueError("cancelled or postponed performance")
    return title,composer,venue,sorted(shown),components
