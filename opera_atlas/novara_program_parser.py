"""Verified source-specific double bill at Teatro Coccia, Novara.

One ticket covers two independently credited operas. The HTML itself must
supply both credits, both dated showtimes, and the actual auditorium.
"""
from __future__ import annotations

from datetime import date
import re
from html import unescape

from opera_atlas.national_detail_parser import MONTHS, clean
from opera_atlas.novara_coccia_parser import WEEKDAYS
from opera_atlas.novara_future_parser import DATE, eligible_detail

URL="https://www.fondazioneteatrococcia.it/stagione-27-l-amor-mio.html"
URL_2026="https://www.fondazioneteatrococcia.it/stagione-26-dna-italia-azzardo-figlio-signor-bruschino.html"
COMPONENTS_2026=(("L’azzardo per un figlio","Claudio Scannavini"),("Il signor Bruschino","Gioachino Rossini"))
COMPONENTS=(
    ("L'amor mio","Cristian Carrara"),
    ("Il tabarro","Giacomo Puccini"),
)


def parse_program(html:str,*,url:str)->tuple[list[dict],str,list[tuple[str,str]]]:
    if url not in {URL,URL_2026} or not eligible_detail(url):
        raise ValueError("unapproved Novara mixed-program source")
    title=re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>",html)
    if not title:
        raise ValueError("missing official Novara composite heading")
    actual=unescape(clean(title[1])).replace("’","'").casefold()
    historic=url==URL_2026
    expected="l'azzardoperunfiglio/ilsignorbruschino" if historic else "l'amormio/iltabarro"
    if actual.replace(" ","")!=expected:
        raise ValueError("unexpected Novara programme title")
    text=unescape(clean(re.sub(r"(?i)</h[2-6]>"," </h3> ",html)))
    breadcrumb=(r"L['’]AZZARDO PER UN FIGLIO\s*/\s*IL SIGNOR BRUSCHINO" if historic else r"L['’]AMOR MIO\s*/\s*IL TABARRO")
    if not re.search(r"(?i)Spettacoli\s*/\s*Opera\s*/\s*"+breadcrumb,text):
        raise ValueError("official opera-category breadcrumb absent")
    before,separator,after=text.partition("informazioni sull'evento")
    if not separator:
        raise ValueError("official showtime section missing")
    # Require both independently named scores and their exact composers.
    # The premiere date of Il tabarro is never a performance date.
    credits=(r"(?is)\bL['’]AZZARDO PER UN FIGLIO\b.*?\bMusica di Claudio Scannavini\b.*?\bIL SIGNOR BRUSCHINO\b.*?\bMusica di Gioachino Rossini\b" if historic else r"(?is)\bL['’]AMOR MIO\b.*?\bMusica di Cristian Carrara\b.*?\bIL TABARRO\b.*?\bMusica di Giacomo Puccini\b")
    if not re.search(credits,before):
        raise ValueError("independent composer credits missing")
    m=re.search(r"(?is)(.*?)\bTEATRO\s+COCCIA\b",after)
    if not m:
        raise ValueError("official Novara venue missing")
    block=m[1]
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",block):
        raise ValueError("cancelled programme requires review")
    matches=list(DATE.finditer(block))
    dates=[]
    for item in matches:
        weekday,day,month,year,hour,minute=item.groups()
        if int(year)!=(2026 if historic else 2027):
            raise ValueError("mixed programme year mismatch")
        actual_day=date(int(year),MONTHS[month.casefold()],int(day))
        if actual_day.weekday()!=WEEKDAYS[weekday.casefold()]:
            raise ValueError("mixed programme weekday inconsistent")
        dates.append((actual_day.isoformat(),f"{int(hour):02d}:{minute}"))
    declared=re.findall(
        r"(?i)\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|"
        r"venerd[iì]|sabato|domenica)\s+\d{1,2}\s+"
        r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
        r"settembre|ottobre|novembre|dicembre)\s+20\d{2}",block)
    if not dates or len(dates)>24 or len(dates)!=len(declared) or len(set(dates))!=len(dates):
        raise ValueError("incomplete or duplicate Novara programme schedule")
    for i,item in enumerate(matches):
        following=block[item.end():matches[i+1].start() if i+1<len(matches) else len(block)]
        if re.search(r"(?i)\b(?:ore\s+)?\d{1,2}:[0-5]\d\b",following):
            raise ValueError("ambiguous additional Novara programme time")
    return ([{"title":title,"composer":composer} for title,composer in (COMPONENTS_2026 if historic else COMPONENTS)],
            "Teatro Coccia",sorted(dates))
