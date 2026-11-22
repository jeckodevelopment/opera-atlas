"""Regione Veneto's official theatre-season document discovery (review only).

This verifies that the regional cultural portal explicitly identifies Teatro
Sociale di Rovigo, its 2026/27 season and its downloadable programme. It does
NOT treat the generic season date range as performance dates. PDF acquisition
and dated-work evidence are separate gated operations.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from opera_atlas.national_detail_parser import clean

URL="https://www.culturaveneto.it/spettacoli/musica/3563a671-d9b2-46bf-a10d-776af9ab17bc"
PDF_HOST="resc.deskline.net"
PDF_BASENAME="Programma_stagione_2026_27_da_scaricare.pdf"  # Historical fixture
PDF_NAME_RE=re.compile(r"Programma_stagione_(20\d{2})_(\d{2})_da_scaricare\.pdf",re.I)

class DocumentLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.documents=[]
        self.href=None
        self.label=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href")
            self.label=[]
    def handle_data(self,data):
        if self.href is not None:
            self.label.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.documents.append((self.href," ".join(self.label)))
            self.href=None
            self.label=[]

def approved_programme(html:str,*,url:str)->str:
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="www.culturaveneto.it"
            or parsed.path.rstrip("/")!=urlsplit(URL).path.rstrip("/")
            or parsed.query or parsed.fragment or parsed.username
            or parsed.password or parsed.port is not None):
        raise ValueError("unapproved Regione Veneto season index URL")
    page=clean(html)
    if not re.search(r"(?i)\bTeatro Sociale di Rovigo\b",page):
        raise ValueError("regional page does not identify Teatro Sociale di Rovigo")
    if not re.search(r"(?i)\bStagione Teatrale\b",page):
        raise ValueError("regional page does not establish the theatre season")
    parser=DocumentLinks()
    parser.feed(html)
    matches=set()
    for href,label in parser.documents:
        target=urljoin(url,href)
        parts=urlsplit(target)
        name=parts.path.rsplit("/",1)[-1]
        season=PDF_NAME_RE.fullmatch(name)
        if season is None:
            continue
        year=int(season.group(1))
        next_year=int("20"+season.group(2))
        if not (2026<=year<=2098 and next_year==year+1):
            continue
        # The programme year must also be present in the official page.
        # Never accept an unrelated or stale PDF link based on filename alone.
        if not (re.search(rf"(?<!\d){year}(?!\d)",page)
                and re.search(rf"(?<!\d){next_year}(?!\d)",page)):
            continue
        label_name=re.sub(r"\s+","_",label.strip())
        if (parts.scheme=="https" and parts.hostname==PDF_HOST
                and parts.path.endswith("/"+name)
                and not parts.username and not parts.password
                and parts.port is None and not parts.query
                and not parts.fragment
                and name[:-4].lower() in label_name.lower()):
            matches.add(target)
    if len(matches)!=1:
        raise ValueError("regional official downloadable programme missing or ambiguous")
    return next(iter(matches))
