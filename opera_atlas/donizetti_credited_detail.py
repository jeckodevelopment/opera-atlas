"""Unambiguous first-party Donizetti Opera work credits and performance times.

The official opera page may list a work absent from Atlas's canonical graph.
Only the page's h1, explicitly labelled composer, actual venue and dated
performance rows can create source evidence. Never infer identity from URL.
"""
from __future__ import annotations
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from opera_atlas.italian_detail_parser import parse_detail
from scripts.publish_catalog_v2 import normalized,slugify

class BlockLines(HTMLParser):
    BLOCKS=frozenset({"h1","h2","h3","h4","p","div","li","section"})
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines=[]
        self.current=[]
    def _flush(self):
        value=" ".join("".join(self.current).split())
        if value:self.lines.append(value)
        self.current=[]
    def handle_starttag(self,tag,attrs):
        if tag in self.BLOCKS:self._flush()
    def handle_endtag(self,tag):
        if tag in self.BLOCKS:self._flush()
    def handle_data(self,data):
        self.current.append(data)
    def close(self):
        super().close()
        self._flush()


def parse_credited_detail(html:str,*,url:str):
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="www.donizettiopera.org"
        or parsed.port is not None or parsed.username or parsed.password
        or parsed.query or parsed.fragment
        or not re.fullmatch(r"/it/evento/[a-z0-9-]+/(?:20[0-9]{2}-[0-9]{2}-[0-9]{2}/)?",
                            parsed.path)):
        raise ValueError("untrusted Donizetti opera event URL")

    from scripts.collect_candidate_details import FirstHeading
    h=FirstHeading()
    h.feed(html)
    title=h.first
    if not isinstance(title,str) or not 4<=len(title)<=160:
        raise ValueError("missing official Donizetti opera heading")
    event_slug=parsed.path.rstrip("/").split("/")[-1]
    if re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}",event_slug):
        event_slug=parsed.path.rstrip("/").split("/")[-2]
    if slugify(title)!=event_slug:
        raise ValueError("official Donizetti heading contradicts event URL")

    blocks=BlockLines()
    blocks.feed(html)
    blocks.close()
    lines=blocks.lines
    title_pos=next((i for i,x in enumerate(lines)
                    if normalized(x)==normalized(title)),None)
    if title_pos is None:
        raise ValueError("opera h1 not present in first-party content")
    # Trust a standalone official label in the pre-cast production credits,
    # never a name from the orchestra, conductor, plot or footer.
    end=next((i for i,x in enumerate(lines[title_pos+1:],title_pos+1)
              if x.strip().casefold() in ("cast","trama","info")),len(lines))
    intro=lines[title_pos+1:end]
    names=[]
    for i,line in enumerate(intro):
        match=re.fullmatch(r"Musica\s+di\s+(.{4,100})",line,re.I)
        if match:names.append(match[1].strip())
        elif re.fullmatch(r"Musica\s+di",line,re.I) and i+1<len(intro):
            names.append(intro[i+1].strip())
    if len(names)!=1:
        raise ValueError("missing or conflicting labelled Donizetti composer")
    composer=names[0]
    if (not 4<=len(composer)<=100
        or not re.fullmatch(r"[A-Za-zÀ-ÿ'’.\-]+(?:\s+[A-Za-zÀ-ÿ'’.\-]+){1,4}",
                            composer)
        or composer.split()[0].casefold() in
           ("direttore","compositore","maestro","da","ignoto")):
        raise ValueError("invalid or generic first-party composer credit")
    venue,recite=parse_detail(html,source_key="donizetti-opera-2026",
                              url=url,title=title,composer=composer)
    from opera_atlas.national_detail_parser import clean
    visible=clean(html)
    info=re.search(r"\bInfo\b",visible,re.I)
    if not info:
        raise ValueError("missing official festival calendar section")
    tail=visible[info.end():]
    end=re.search(r"\bLuogo\b",tail,re.I)
    if not end:
        raise ValueError("missing official festival venue")
    calendar=tail[:end.start()]
    # All explicitly listed dates must have validated individual hours.
    months="gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
    listed=re.findall(r"\b[0-3]?\d\s+(?:"+months+r")\s+20\d{2}\s*\|",calendar,re.I)
    if len(listed)!=len(recite):
        raise ValueError("incomplete official festival showtime evidence")
    return title,composer,venue,recite
