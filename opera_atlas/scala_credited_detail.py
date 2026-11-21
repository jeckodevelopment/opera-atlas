"""Official Scala 2026–27 work credit and individually timed recite extraction.

No URL-slug-to-title guesses. The visible official Opera heading, following
composer credit and ticket dates are all independently required.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit
from html.parser import HTMLParser

from opera_atlas.national_detail_parser import clean
from opera_atlas.scala_arena_parser import parse_showtimes
from scripts.publish_catalog_v2 import normalized

class FirstH1(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=False
        self.parts=[]
        self.value=None
    def handle_starttag(self,tag,attrs):
        if tag=="h1" and self.value is None:
            self.active=True
    def handle_data(self,data):
        if self.active:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h1" and self.active:
            self.value=" ".join("".join(self.parts).split())
            self.active=False

def extract_scala_official_credit(html:str,*,url:str)->tuple[str,str]:
    """Read an explicit title and composer from the page's own header region."""
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="www.teatroallascala.org"
        or parsed.port is not None or parsed.username or parsed.password
        or parsed.query or parsed.fragment
        or not re.fullmatch(r"/it/stagione/2026-2027/opera/[a-z0-9-]+\.html",parsed.path)):
        raise ValueError("untrusted Scala 2026–27 opera detail URL")
    heading=FirstH1()
    heading.feed(html)
    title=heading.value
    if not isinstance(title,str) or not 3<=len(title)<=140:
        raise ValueError("missing first-party opera title")
    visible=clean(html)
    # The theatre explicitly prints 'Opera / [h1 title] / [composer] /
    # Dal [date range]' in the page's own production header. The composer's
    # name must be captured *between* the title and dated production summary.
    match=re.search(r"\bOpera\s+"+re.escape(title)+
                    r"\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+){1,4})"
                    r"\s+Dal\s+\d{1,2}\s+",visible)
    if not match:raise ValueError("official Scala title/composer header absent")
    composer=match.group(1).strip()
    if normalized(title)==normalized(composer):
        raise ValueError("contradictory official Scala credit")
    return title,composer

def parse_scala_credited_opera(html:str,*,url:str)->tuple[str,str,list[tuple[str,str]]]:
    title,composer=extract_scala_official_credit(html,url=url)
    dates=parse_showtimes(html,url=url,title=title,composer=composer,adapter="scala")
    return title,composer,dates
