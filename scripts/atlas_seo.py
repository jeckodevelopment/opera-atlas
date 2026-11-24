"""Build-only SEO artifacts for the static Opera+ Atlas frontend.

Only reviewed canonical catalog identities enter the sitemap. The Open Graph
preview is original vector-inspired pixel artwork generated without external
services, fonts or images. It does not depict an actual opera production.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import struct
from xml.sax.saxutils import escape
import zlib

BASE = "https://opera.plus/atlas/"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FONT = {
"A":["01110","10001","10001","11111","10001","10001","10001"],
"B":["11110","10001","10001","11110","10001","10001","11110"],
"C":["01111","10000","10000","10000","10000","10000","01111"],
"D":["11110","10001","10001","10001","10001","10001","11110"],
"E":["11111","10000","10000","11110","10000","10000","11111"],
"F":["11111","10000","10000","11110","10000","10000","10000"],
"G":["01111","10000","10000","10111","10001","10001","01111"],
"H":["10001","10001","10001","11111","10001","10001","10001"],
"I":["11111","00100","00100","00100","00100","00100","11111"],
"L":["10000","10000","10000","10000","10000","10000","11111"],
"M":["10001","11011","10101","10101","10001","10001","10001"],
"N":["10001","11001","10101","10011","10001","10001","10001"],
"O":["01110","10001","10001","10001","10001","10001","01110"],
"P":["11110","10001","10001","11110","10000","10000","10000"],
"R":["11110","10001","10001","11110","10100","10010","10001"],
"S":["01111","10000","10000","01110","00001","00001","11110"],
"T":["11111","00100","00100","00100","00100","00100","00100"],
"U":["10001","10001","10001","10001","10001","10001","01110"],
"V":["10001","10001","10001","10001","10001","01010","00100"],
"Z":["11111","00001","00010","00100","01000","10000","11111"],
"+":["00000","00100","00100","11111","00100","00100","00000"],
"'":["00100","00100","00000","00000","00000","00000","00000"],
" ":["00000"]*7,
}

def png(path: Path) -> None:
    width, height = 1200, 630
    pixels = bytearray(width * height * 3)
    def point(x: int, y: int, rgb: tuple[int,int,int]):
        if 0 <= x < width and 0 <= y < height:
            at = (y*width + x)*3
            pixels[at:at+3] = bytes(rgb)
    for y in range(height):
        for x in range(width):
            glow = max(0, 1 - ((x-985)/730)**2 - ((y-190)/480)**2)
            shade = (int(16+28*glow), int(19+21*glow), int(23+13*glow))
            point(x,y,shade)
    gold = (205,165,90)
    cream = (247,239,218)
    # Original abstract proscenium arches and lights, not event photography.
    for y in range(84,557):
        for x in range(789,1120):
            outer = ((x-954)/169)**2 + ((y-306)/235)**2
            inner = ((x-954)/121)**2 + ((y-306)/189)**2
            if outer <= 1 and inner >= 1:
                point(x,y,(92,77,53))
            elif inner <= 1:
                point(x,y,(35,34,33))
    for x in range(810,1100):
        for y in range(492,500):
            point(x,y,gold)
    for y in range(84,555):
        for x in range(790,795):
            point(x,y,gold)
    for y in range(84,555):
        for x in range(1115,1120):
            point(x,y,gold)
    for y in range(84,91):
        for x in range(790,1120):
            point(x,y,gold)
    for x in range(100,725):
        for y in range(112,117):
            point(x,y,gold)
    for x in range(100,725):
        for y in range(508,511):
            point(x,y,gold)
    def write(text: str, start_x: int, start_y: int, scale: int, color: tuple[int,int,int]):
        x=start_x
        for letter in text.upper():
            bitmap=FONT.get(letter,FONT[" "])
            for row,bits in enumerate(bitmap):
                for col,bit in enumerate(bits):
                    if bit=="1":
                        for dy in range(scale):
                            for dx in range(scale):
                                point(x+col*scale+dx,start_y+row*scale+dy,color)
            x += 6*scale
    write("OPERA+ ATLAS",104,194,9,cream)
    write("IL TEATRO D'OPERA",105,352,4,gold)
    write("IN ITALIA",105,402,4,gold)
    # PNG RGB rows
    scan=b"".join(b"\x00"+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
    image=(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">2I5B",width,height,8,2,0,0,0))
           +chunk(b"IDAT",zlib.compress(scan,9))+chunk(b"IEND",b""))
    path.write_bytes(image)

def sitemap(path: Path, catalog: Path) -> None:
    manifest=json.loads((catalog/"manifest.json").read_text(encoding="utf-8"))
    def channel(name):
        spec=manifest["files"][name]
        rel=spec["path"]
        if not re.fullmatch(r"data/"+name+r"\.[0-9a-f]{16}\.json",rel):
            raise ValueError("Unsafe SEO catalog path")
        data=json.loads((catalog/rel).read_text(encoding="utf-8"))
        return data[name]
    works=channel("works")
    venues=channel("venues")
    stagings=channel("stagings")
    valid_works={w["id"] for w in works}
    valid_venues={v["id"] for v in venues}
    urls={BASE,BASE+"in-scena",BASE+"directory.html?section=opere",
          BASE+"directory.html?section=teatri",BASE+"directory.html?section=festival"}
    for work in works:
        slug=work.get("route_slug") or work.get("slug")
        if isinstance(slug,str) and SLUG.fullmatch(slug):
            urls.add(BASE+"opere/"+slug+"/")
    for venue in venues:
        city,slug=venue.get("city_slug"),venue.get("slug")
        if all(isinstance(v,str) and SLUG.fullmatch(v) for v in (city,slug)):
            urls.add(BASE+city+"/"+slug+"/")
    for staging in stagings:
        route=staging.get("url","")
        if staging.get("work_id") in valid_works and staging.get("venue_id") in valid_venues and (
            isinstance(route,str) and re.fullmatch(r"/[a-z0-9/-]+/",route)
            and ".." not in route and "//" not in route):
            urls.add(BASE+route.lstrip("/"))
    valid_stagings={s["id"] for s in stagings}
    # Add the shared production and multi-work program routes used by Atlas.
    groups_file=catalog/"production-groups.json"
    if groups_file.is_file():
        groups=json.loads(groups_file.read_text(encoding="utf-8"))
        for group in groups.get("groups",[]):
            gid=group.get("id","")
            if (re.fullmatch(r"oa-g-[a-z0-9-]+",gid)
                and group.get("work_id") in valid_works
                and any(s in valid_stagings for s in group.get("staging_ids",[]))):
                urls.add(BASE+"produzioni/"+gid+"/")
    programs_file=catalog.parent/"programs.json"
    if programs_file.is_file():
        programs=json.loads(programs_file.read_text(encoding="utf-8"))
        for program in programs.get("programs",[]):
            pid=program.get("id","")
            if (re.fullmatch(r"oa-p-[0-9a-f]{16}",pid)
                and program.get("performances")):
                urls.add(BASE+"programmi/"+pid+"/")
    festivals_file=catalog/"festival-directory.json"
    if festivals_file.is_file():
        festivals=json.loads(festivals_file.read_text(encoding="utf-8"))
        for festival in festivals.get("festivals",[]):
            fid=festival.get("id","")
            if re.fullmatch(r"[a-z0-9-]+",fid):
                urls.add(BASE+"directory.html?section=festival&id="+fid)
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sorted(urls):
        lines.append("  <url><loc>"+escape(url,{"\"":"&quot;"})+"</loc></url>")
    lines.append("</urlset>")
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def build(output: Path, catalog: Path) -> None:
    png(output/"og-atlas.png")
    sitemap(output/"sitemap.xml",catalog)
    # Scoped robots document, provided as informational companion.
    # Domain-level robots.txt must be managed at opera.plus/robots.txt.
