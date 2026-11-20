"use strict";

/* Static deep-route details: an opera lists every staging in Italy, a theatre
   lists its stagings, and one staging owns all of its date/time replicas.
   No client-supplied path is used as a remote URL. */
const root = "/dev/opera-atlas/";
const title = document.getElementById("detail-title");
const subtitle = document.getElementById("detail-subtitle");
const kind = document.getElementById("kind");
const status = document.getElementById("detail-status");
const content = document.getElementById("detail-content");
const results = document.getElementById("detail-events");

function node(tag, cls, value) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (value !== undefined) element.textContent = value;
  return element;
}
function normalize(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("it").trim();
}
function dateLabel(day) {
  return new Intl.DateTimeFormat("it-IT", {
    day:"numeric",month:"long",year:"numeric",timeZone:"UTC",
  }).format(new Date(day+"T12:00:00Z"));
}
function safeSource(url) {
  try {
    const u=new URL(url);
    return u.protocol==="https:" ? u.href : null;
  } catch { return null; }
}
function sourceLinks(parent, events) {
  const list=node("ul","source-links");
  for (const url of new Set(events.flatMap(e=>e.sources||[]))) {
    const href=safeSource(url);
    if (!href) continue;
    const li=node("li");
    const a=node("a",null,"Fonte ufficiale");
    a.href=href;
    a.rel="noopener noreferrer";
    a.target="_blank";
    li.append(a);
    list.append(li);
  }
  parent.append(list);
}
function link(text, url, css="detail-link") {
  const a=node("a",css,text);
  a.href=url;
  return a;
}
function missing(message) {
  title.textContent="Scheda non disponibile";
  subtitle.textContent="";
  status.textContent=message;
}
async function appendSynopsis(event) {
  try {
    const response=await fetch("./work-synopses.json");
    if(!response.ok)return;
    const doc=await response.json();
    if(doc.schema_version!==1||!doc.synopses)return;
    const slug=event.work_slug||window.OperaAtlasCatalog.urls(event).work.split("/").filter(Boolean).pop();
    const text=doc.synopses[slug];
    if(typeof text!=="string"||!text.trim())return;
    const section=node("section","brief-synopsis");
    section.append(node("h2",null,"In breve"),node("p",null,text));
    content.prepend(section);
  }catch{/* Optional editorial synopsis must never block performance dates. */}
}
function validEvent(e) {
  return e && typeof e.id==="string" && typeof e.title==="string" && e.title
    && typeof e.venue==="string" && e.venue
    && typeof e.municipality==="string" && e.municipality
    && typeof e.local_date==="string" && /^\d{4}-\d{2}-\d{2}$/.test(e.local_date)
    && typeof e.time_known==="boolean"
    && (e.time_known ? typeof e.starts_at==="string" : e.starts_at===null)
    && Array.isArray(e.sources) && e.sources.some(safeSource);
}
function grouping(events) {
  const map=new Map();
  for (const e of events) {
    const key=e.staging_id || window.OperaAtlasCatalog.urls(e).staging;
    if (!map.has(key)) map.set(key,[]);
    map.get(key).push(e);
  }
  return [...map.values()].sort((a,b)=>a[0].local_date.localeCompare(b[0].local_date));
}
function replicaLine(e) {
  const row=node("div","replica-row");
  row.append(node("strong",null,dateLabel(e.local_date)));
  row.append(node("span","time"+(e.time_known?"":" unknown"),
    e.time_known ? "Ore "+e.starts_at.slice(11,16) : "Orario da confermare"));
  const sources=(e.sources||[]).map(safeSource).filter(Boolean);
  if(sources.length){const a=link("Programma e biglietti sul sito ufficiale",sources[0]);a.target="_blank";a.rel="noopener noreferrer";row.append(a);}
  return row;
}
function stagingGroup(events, owner) {
  const first=events[0];
  const section=node("section","staging-group");
  const heading=node("h3");
  heading.append(link(owner==="work"
    ? first.venue+" · "+first.municipality
    : first.title, window.OperaAtlasCatalog.urls(first).staging,""));
  section.append(heading);
  section.append(node("p",null,events.length+" repliche in catalogo"));
  const calendar=node("div","staging-repliche");
  for (const e of events.filter(x=>x.local_date>=todayInItaly()).slice(0,24)) {
    calendar.append(node("span","replica-chip",dateLabel(e.local_date)+
      (e.time_known ? " · "+e.starts_at.slice(11,16) : " · Orario da confermare")));
  }
  if(events.length>24)calendar.append(node("span","replica-chip","Consulta tutte le date nel dettaglio"));
  section.append(calendar);
  section.append(link("Apri la messa in scena",window.OperaAtlasCatalog.urls(first).staging));
  sourceLinks(section,events);
  results.append(section);
}
function todayInItaly(){
  const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const get=key=>parts.find(x=>x.type===key).value;
  return get("year")+"-"+get("month")+"-"+get("day");
}
function resolve(events) {
  const pathname=decodeURI(window.location.pathname);
  const path=pathname.startsWith(root) ? pathname.slice(root.length) : "";
  const pieces=path.split("/").filter(Boolean);
  if(pieces.length && pieces.every(part=>/^[a-z0-9-]+$/.test(part))) {
    if(pieces.length===2 && pieces[0]==="opere")
      return {kind:"work",events:events.filter(e=>
        window.OperaAtlasCatalog.urls(e).work===root+pieces.join("/")+"/")};
    if(pieces.length===2)
      return {kind:"venue",events:events.filter(e=>
        window.OperaAtlasCatalog.urls(e).venue===root+pieces.join("/")+"/")};
    if(pieces.length===3)
      return {kind:"staging",events:events.filter(e=>
        window.OperaAtlasCatalog.urls(e).staging===root+pieces.join("/")+"/")};
  }
  // Backward-compatible query-string URLs from older catalog editions.
  const args=new URLSearchParams(window.location.search);
  const type=args.get("type"),key=args.get("key");
  if(!key || key.length>512)return {kind:null,events:[]};
  if(type==="work")return {kind:"work",events:events.filter(e=>normalize(e.title)===key)};
  if(type==="venue")return {kind:"venue",events:events.filter(e=>
    normalize(e.venue)+"|"+normalize(e.municipality)===key)};
  if(type==="performance") {
    const hit=events.find(e=>String(e.id)===key || e.legacy_id===key);
    return hit ? {kind:"staging",events:events.filter(e=>
      window.OperaAtlasCatalog.urls(e).staging===window.OperaAtlasCatalog.urls(hit).staging)}
      : {kind:null,events:[]};
  }
  return {kind:null,events:[]};
}
async function initialize() {
  try {
    const data=await window.OperaAtlasCatalog.load();
    if(data.warning)status.textContent=data.warning;
    else if(data.reviewed_on)
      status.textContent="Dati verificati il "+data.reviewed_on.split("-").reverse().join("/");
    const events=data.performances.filter(validEvent);
    const selected=resolve(events);
    if(!selected.kind || !selected.events.length) {
      missing("Questo indirizzo non corrisponde a una scheda pubblicata.");
      return;
    }
    const first=selected.events[0];
    const future=selected.events.filter(e=>e.local_date>=todayInItaly());
    results.before(node("p","search-note","Le date future sono mostrate per prime. Gli eventi conclusi restano nello storico del catalogo."));
    if(selected.kind==="work") {
      kind.textContent="Opera del repertorio";
      title.textContent=first.title;
      subtitle.textContent=first.composer||"Compositore non verificato";
      document.querySelector(".detail-related h2").textContent="Dove vedere "+first.title;
      await appendSynopsis(first);
      content.append(node("p","staging-summary",
        grouping(selected.events).length+" messe in scena · "+
        selected.events.length+" repliche censite in Italia"));
      content.append(node("p",null,
        "Tutte le programmazioni di quest’opera presenti nel catalogo, raggruppate per teatro."));
      for(const group of grouping(future))stagingGroup(group,"work");
      if(!future.length)results.append(node("p","empty","Non risultano prossime rappresentazioni verificate di questa opera nel catalogo Atlas."));
    }else if(selected.kind==="venue") {
      kind.textContent="Teatro";
      document.querySelector(".detail-related h2").textContent="Spettacoli in programma";
      title.textContent=first.venue;
      subtitle.textContent=[first.municipality,first.region].filter(Boolean).join(" · ");
      content.append(node("p","staging-summary",
        grouping(selected.events).length+" messe in scena · "+
        selected.events.length+" repliche"));
      for(const group of grouping(future))stagingGroup(group,"venue");
      if(!future.length)results.append(node("p","empty","Nessun prossimo spettacolo verificato presso questo teatro nel catalogo Atlas."));
    }else{
      kind.textContent="Produzione";
      document.querySelector(".detail-related h2").textContent="Date e informazioni biglietti";
      title.textContent=first.title;
      subtitle.textContent=first.venue+" · "+first.municipality+
        (first.season ? " · Stagione "+first.season : "");
      content.append(node("p","staging-summary",
        "Una messa in scena, "+selected.events.length+" repliche in calendario."));
      content.append(link("Scopri l’opera",window.OperaAtlasCatalog.urls(first).work));
      content.append(node("span",null," · "));
      content.append(link("Scopri il teatro",window.OperaAtlasCatalog.urls(first).venue));
      for(const e of future.sort((a,b)=>a.local_date.localeCompare(b.local_date)))
        results.append(replicaLine(e));
      if(!future.length)results.append(node("p","empty","Questa produzione non ha date future censite."));
    }
    sourceLinks(content,selected.events);
    document.title=title.textContent+" — Opera+ Atlas";
    // Canonicalize old query-based links after resolution; never change identity.
    if(pathnameIsLegacy()) {
      const canonical=selected.kind==="work"
        ? window.OperaAtlasCatalog.urls(first).work
        : selected.kind==="venue"
          ? window.OperaAtlasCatalog.urls(first).venue
          : window.OperaAtlasCatalog.urls(first).staging;
      window.history.replaceState(null,"",canonical);
    }
  }catch {
    missing("Non è stato possibile caricare il catalogo.");
  }
}
function pathnameIsLegacy() {
  return window.location.pathname.endsWith("/detail.html");
}
initialize();
