"""Pre-render crawlable, identity-specific HTML at existing Atlas canonical URLs.

These are presentation snapshots of the *published* catalog. The same client
scripts still load the live feed. No crawler, new IDs or editorial inference.
Only owned /atlas/ routes are emitted, never user-supplied paths.
"""
from __future__ import annotations

from collections import defaultdict
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

ROOT_URL = "https://opera.plus/atlas/"
DEFAULT_IMAGE = ROOT_URL + "og-atlas.png"
ROUTE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GROUP = re.compile(r"^oa-g-[a-z0-9-]+$")
PROGRAM = re.compile(r"^oa-p-[a-f0-9]{16}$")
ALLOWED_ART = {
    "archival_work_image", "official_production_image", "official_coproduction_poster",
    "official_original_work_artwork", "official_civic_production_image",
    "verified_historical_theatre_poster"
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validated_route(route: str) -> str:
    """Route relative to /atlas/, no query, separators or hidden/parent segments."""
    parts = route.strip("/").split("/")
    if not 2 <= len(parts) <= 3 or any(not ROUTE.fullmatch(p) for p in parts):
        raise ValueError("Unsafe SEO route: " + repr(route))
    if route != "/" + "/".join(parts) + "/":
        raise ValueError("Non-canonical SEO route: " + repr(route))
    return "/".join(parts) + "/"


def safe_image(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 2000:
        return False
    url = urlsplit(value)
    return url.scheme == "https" and bool(url.netloc) and not url.username and not url.password


def field(text: str, attr: str) -> str:
    return escape(str(text or ""), quote=attr == "attribute")


def truncate(s: str, limit: int = 165) -> str:
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def render(template: str, *, route: str, title: str, description: str,
           heading: str, subtitle: str, image: str, alt: str,
           entity_type: str, summary: str, events: list[dict] | None = None) -> str:
    canonical = ROOT_URL + route
    safe_title = field(title + " | Opera+ Atlas", "content")
    safe_desc = field(truncate(description), "content")
    safe_image_url = field(image, "attribute")
    # Strip the generic template metadata and supply full static HTML for bots.
    text = template
    text = re.sub(r"<title>[^<]*</title>", "<title>" + escape(title + " | Opera+ Atlas") + "</title>", text, count=1)
    text = re.sub(r'<meta name="description"[^>]*>', '', text)
    text = re.sub(r'<meta property="og:(?:title|description|url|image|image:alt|image:width|image:height|image:type|type)"[^>]*>', '', text)
    text = re.sub(r'<meta name="twitter:(?:title|description|image)"[^>]*>', '', text)
    text = re.sub(r'<link rel="canonical"[^>]*>', '', text)
    tags = "\n".join([
        '<meta name="description" content="' + safe_desc + '">',
        '<link rel="canonical" href="' + field(canonical, "attribute") + '">',
        '<meta property="og:url" content="' + field(canonical, "attribute") + '">',
        '<meta property="og:type" content="article">',
        '<meta property="og:title" content="' + safe_title + '">',
        '<meta property="og:description" content="' + safe_desc + '">',
        '<meta property="og:image" content="' + safe_image_url + '">',
        '<meta property="og:image:alt" content="' + field(alt,"attribute") + '">',
        '<meta name="twitter:title" content="' + safe_title + '">',
        '<meta name="twitter:description" content="' + safe_desc + '">',
        '<meta name="twitter:image" content="' + safe_image_url + '">'
    ])
    text = text.replace("</head>", tags + "\n</head>", 1)
    text = text.replace('<h1 id="detail-title">Caricamento…</h1>',
                        '<h1 id="detail-title">' + escape(heading) + '</h1>', 1)
    text = text.replace('<p class="lede" id="detail-subtitle"></p>',
                        '<p class="lede" id="detail-subtitle">' + escape(subtitle) + '</p>', 1)
    text = text.replace('<p class="eyebrow" id="kind">Scheda</p>',
                        '<p class="eyebrow" id="kind">' + escape(entity_type) + '</p>', 1)
    # Real body content for no-JS indexing. Client removes this paragraph once
    # its canonical live data has loaded; no duplicate content in live UX.
    body = '<section class="seo-prerender" id="atlas-prerender"><h2>Informazioni</h2><p>' + escape(summary) + '</p>'
    if events:
        body += '<h2>Date delle rappresentazioni</h2><ul>'
        for event in sorted(events, key=lambda e: (e["local_date"], e.get("starts_at") or ""))[:20]:
            clock = (event["starts_at"][11:16] if event.get("time_known") and
                     isinstance(event.get("starts_at"), str) else "orario da confermare")
            body += "<li>" + escape(event["local_date"] + " · " + clock + " · " + str(event.get("venue", ""))) + "</li>"
        body += "</ul>"
    body += "</section>"
    text = text.replace('<section id="detail-content" aria-label="Informazioni sull’opera"></section>',
                        '<section id="detail-content" aria-label="Informazioni sull’opera">' + body + '</section>', 1)
    return text


def generate(destination: Path, catalog: Path) -> list[str]:
    manifest = load_json(catalog / "manifest.json")
    def records(key):
        ref = manifest["files"][key]["path"]
        if not re.fullmatch(r"data/" + key + r"\.[a-f0-9]{16}\.json", ref):
            raise ValueError("Unsafe versioned catalog filename")
        return load_json(catalog / ref)[key]
    works, venues, stagings, performances = (records(k) for k in ("works","venues","stagings","performances"))
    directory = load_json(catalog.parent / "venue-directory.json")["venues"]
    poster_registry = load_json(catalog.parent / "work-posters.json")
    posters = poster_registry["works"] if poster_registry.get("schema_version") == 2 else {}
    groups = load_json(catalog / "production-groups.json").get("groups", [])
    programs = load_json(catalog.parent / "programs.json").get("programs", [])
    template = (destination / "detail.html").read_text(encoding="utf-8")
    work_by_id = {w["id"]: w for w in works}
    venue_by_id = {v["id"]: v for v in venues}
    stage_by_id = {s["id"]: s for s in stagings}
    events_by_stage = defaultdict(list)
    for event in performances:
        if event.get("staging_id") in stage_by_id:
            events_by_stage[event["staging_id"]].append(event)
    items: dict[str,dict] = {}
    def art(work_id):
        choice = posters.get(work_id) or {}
        if (choice.get("work_id") == work_id and choice.get("kind") in ALLOWED_ART
            and safe_image(choice.get("image_url")) and safe_image(choice.get("source_url"))):
            return choice["image_url"], choice.get("alt") or "Documento iconografico dell’opera"
        return DEFAULT_IMAGE, "Opera+ Atlas — repertorio lirico italiano"
    def add(route, **kwargs):
        path = validated_route(route)
        if path in items:
            raise ValueError("Duplicate canonical public route " + path)
        items[path] = kwargs
    for work in works:
        slug = work.get("route_slug") or work.get("slug")
        if not isinstance(slug,str) or not ROUTE.fullmatch(slug):
            continue
        title,composer = work["title"], work["composer"]
        image,alt = art(work["id"])
        add("/opere/"+slug+"/", title=title, heading=title,
            description=title+" di "+composer+": produzioni e recite nei teatri italiani su Opera+ Atlas.",
            subtitle=composer, summary=title+" è un'opera di "+composer+". Consulta produzioni, teatri e recite nel catalogo nazionale.",
            image=image,alt=alt,entity_type="Opera del repertorio")
    for v in directory:
        city,slug = v.get("city_slug"),v.get("slug")
        if not all(isinstance(s,str) and ROUTE.fullmatch(s) for s in (city,slug)):
            continue
        title = v["name"]
        description = v.get("description") or "Scopri il teatro "+title+" a "+v["city"]+" e le opere in programma su Opera+ Atlas."
        image,alt = DEFAULT_IMAGE,"Opera+ Atlas — teatri italiani"
        if (isinstance(v.get("photo_file"),str) and safe_image(v.get("photo_source_url"))
            and "commons.wikimedia.org" == urlsplit(v["photo_source_url"]).hostname):
            image = "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + quote(v["photo_file"].replace(" ","_")) + "?width=1200"
            alt = "Fotografia del teatro " + title + " a " + v["city"]
        elif safe_image(v.get("photo_url")) and safe_image(v.get("photo_source_url")) and v.get("photo_credit"):
            image,alt=v["photo_url"],"Fotografia del teatro "+title
        if v.get("id") == "oa-v-000072":
            image,alt=ROOT_URL+"sanbapolis-platea.jpg","Platea del Teatro Sanbàpolis a Trento"
        add("/"+city+"/"+slug+"/", title=title+" — "+v["city"], heading=title,
            description=description, subtitle=v["city"]+" · "+v.get("region",""),
            summary=description, image=image,alt=alt,entity_type="Teatro")
    for s in stagings:
        w=work_by_id.get(s.get("work_id"))
        v=venue_by_id.get(s.get("venue_id"))
        if not w or not v: continue
        route=s.get("url")
        if not isinstance(route,str): continue
        title=w["title"]
        image,alt=art(w["id"])
        events=[dict(event,venue=v.get("display_name") or v["name"])
                for event in events_by_stage.get(s["id"],[])]
        add(route, title=title+" — "+(v.get("display_name") or v["name"]),
            heading=title, description=title+" di "+w["composer"]+" al "+
            (v.get("display_name") or v["name"])+" di "+v["city"]+": date e recite su Opera+ Atlas.",
            subtitle=(v.get("display_name") or v["name"])+" · "+v["city"],
            summary=title+" al "+(v.get("display_name") or v["name"])+" a "+v["city"]+
            ", stagione "+str(s.get("season",""))+".",
            image=image,alt=alt,entity_type="Produzione",events=events)
    for group in groups:
        group_id=group.get("id","")
        if not isinstance(group_id,str) or not GROUP.fullmatch(group_id):continue
        stages=[stage_by_id[x] for x in group.get("staging_ids",[]) if x in stage_by_id]
        w=work_by_id.get(group.get("work_id"))
        if not w or not stages:continue
        images=art(w["id"])
        events=[]
        for stage in stages:
            venue=venue_by_id.get(stage["venue_id"])
            for e in events_by_stage.get(stage["id"],[]):
                events.append(dict(e,venue=(venue or {}).get("display_name") or (venue or {}).get("name","")))
        title=group.get("name") or w["title"]
        add("/produzioni/"+group_id+"/",title=title,heading=title,
            description=title+" — teatri e date delle rappresentazioni su Opera+ Atlas.",
            subtitle=w["composer"],summary=title+" — produzione condivisa presente nel catalogo nazionale.",
            image=images[0],alt=images[1],entity_type="Produzione",events=events)
    for program in programs:
        pid=program.get("id","")
        if not isinstance(pid,str) or not PROGRAM.fullmatch(pid) or not program.get("performances"):continue
        title=program["title"]
        venue,city=program["venue"],program["municipality"]
        events=[dict(e,venue=venue) for e in program["performances"]]
        artwork=program.get("artwork") or {}
        image,alt=DEFAULT_IMAGE,"Opera+ Atlas — programma lirico"
        if (artwork.get("kind")=="official_program_image" and artwork.get("credit")
            and artwork.get("source_url")==program.get("source_url")
            and safe_image(artwork.get("image_url")) and safe_image(artwork.get("source_url"))):
            image,alt=artwork["image_url"],artwork.get("alt") or title
        else:
            for component in program["components"]:
                if not component.get("work_id"):continue
                candidate,caption=art(component["work_id"])
                if candidate!=DEFAULT_IMAGE:
                    image,alt=candidate,"Immagine di una delle opere del programma: "+caption
                    break
        add("/programmi/"+pid+"/",title=title+" — "+venue,heading=title,
            description=title+" al "+venue+" di "+city+": date e programma su Opera+ Atlas.",
            subtitle=venue+" · "+city,summary=title+" è un programma di più opere presso "+venue+" a "+city+".",
            image=image,alt=alt,
            entity_type="Programma composto",events=events)
    result=[]
    for route,kwargs in sorted(items.items()):
        out=destination/route/"index.html"
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(render(template,route=route,**kwargs),encoding="utf-8")
        result.append(route+"index.html")
    (destination/"seo-routes.json").write_text(
        json.dumps({"schema_version":1,"files":result},ensure_ascii=False,separators=(",",":"))+"\n",
        encoding="utf-8")
    return result
