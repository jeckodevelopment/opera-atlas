"""Official Province of Lecce: Teatro Apollo 2026 single contemporary opera.

The shared provincial lyric season also contains three *different* operas
at the Politeama Greco. Only the explicitly named Teatro Apollo Pinocchio
event is eligible here; never publish another event from this article.
"""
from __future__ import annotations
from urllib.parse import urlsplit
import re

from opera_atlas.national_detail_parser import clean

HOST="www.provincia.le.it"
PATH="/al-via-la-51-stagione-lirica-della-provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini"
TITLE="Le avventure di Pinocchio"
COMPOSER="Antonio Cericola"
VENUE="Teatro Apollo"
DAY="2026-12-30"
HOUR="20:45"

def parse_detail(html:str,*,url:str):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.path.rstrip("/")!=PATH
        or u.query or u.fragment or u.username or u.password
        or u.port is not None):
        raise ValueError("unapproved Province of Lecce official article")
    text=clean(re.sub(r"(?i)</h[1-6]>", " </h3> ",html)).replace("’","'")
    if not re.search(r"(?i)\b51\s*[ª^a]?\s*stagione\s+lirica\b",text):
        raise ValueError("official 2026 lyrical season not identified")
    # A specific editorial section explicitly distinguishes this contemporary
    # opera from the Politeama's three separately ticketed productions.
    begin=re.search(r"(?i)\bLA CHICCA FUORI ABBONAMENTO:\s*"
                    r"LE AVVENTURE DI PINOCCHIO\b",text)
    if begin is None:
        raise ValueError("distinct Teatro Apollo production section missing")
    section=text[begin.end():begin.end()+2200]
    if not (re.search(r"(?i)\bLe avventure di Pinocchio\s+di\s+Antonio Cericola\b",section)
            or re.search(r"(?i)\bLe avventure di Pinocchio\b.{0,260}?\bopera omonima composta da Antonio Cericola\b",section)):
        raise ValueError("Apollo title and composer not verified together")
    pattern=(r"(?i)\b(?:mercoled[iì]\s+)?30\s+dicembre\s*,?\s*"
             r"ore\s+20[.:]45\s*,?\s*presso\s+il\s+Teatro Apollo\s+di\s+Lecce\b")
    if len(re.findall(pattern,section))!=1:
        raise ValueError("one precise Apollo date and time not confirmed")
    if re.search(r"(?i)\b(?:annullat[oaie]|rinviat[oaie]|cancellat[oaie])\b",section):
        raise ValueError("opera cancellation requires review")
    return TITLE,COMPOSER,VENUE,[(DAY,HOUR)]
