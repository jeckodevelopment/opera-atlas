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
function sourceLinks(events,kind,profile) {
  // Opera overview links to productions inside Atlas; it is not a source directory.
  if(kind==="work")return;
  const first=events[0];
  const urls=new Map();
  if(kind==="venue" && profile && safeSource(profile.website)){
    urls.set(profile.website,"Sito del "+first.venue);
  }else{
    for(const event of events){
      const href=(event.sources||[]).map(safeSource).find(Boolean);
      if(!href || urls.has(href))continue;
      let label;
      if(kind==="group"){
        label=event.venue+" · "+event.municipality+" — programma e biglietti";
      }else{
        label=first.title+" al "+first.venue+" — programma e biglietti";
      }
      urls.set(href,label);
    }
  }
  if(!urls.size)return;
  const panel=node("section","official-links");
  panel.append(node("h2",null,kind==="venue"?"Il sito del teatro":"Programma e biglietti"));
  const list=node("ul","official-link-list");
  for(const [href,label] of urls){
    const li=node("li"),a=node("a",null,label);
    a.href=href;a.rel="noopener noreferrer";a.target="_blank";
    li.append(a);list.append(li);
  }
  panel.append(list);
  results.after(panel);
}
function editorialImage(kind,event){
  const images=window.OperaAtlasImages;
  if(images && typeof images.element==="function"){
    try{return images.element(images[kind](event),"detail-image");}
    catch(error){console.warn("Atlas image fallback",error);}
  }
  const fallback=node("div","detail-image image-placeholder");
  fallback.setAttribute("role","img");
  fallback.setAttribute("aria-label","Fotografia non disponibile");
  return fallback;
}
async function appendTheatreProfile(event){
  try{
    const response=await fetch("./theatre-profiles.json");
    if(!response.ok) return null;
    const doc=await response.json();
    if(doc.schema_version!==1||!doc.venues)return null;
    const profile=doc.venues[event.municipality+"|"+event.venue];
    if(!profile)return null;
    const section=node("section","theatre-introduction");
    section.append(node("p","theatre-description",profile.description));
    const place=node("div","theatre-location");
    place.append(node("h2",null,"Dove si trova"));
    place.append(node("p",null,profile.address+" · "+event.municipality));
    const direction=link("Come arrivare", "https://www.openstreetmap.org/search?query="+encodeURIComponent(profile.address+", "+event.municipality+", Italia"));
    direction.target="_blank";direction.rel="noopener noreferrer";
    place.append(direction);
    section.append(place);
    content.append(section);
    return profile;
  }catch(error){console.warn("Theatre profile unavailable",error);return null;}
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
    let doc=null;
    for(const url of [
      "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/work-editorial.json",
      "./work-synopses.json"
    ]){
      try{
        const response=await fetch(url,{cache:"no-store"});
        if(!response.ok)continue;
        const candidate=await response.json();
        if(candidate.schema_version!==1)continue;
        doc=Array.isArray(candidate.works)
          ? {synopses:Object.fromEntries(candidate.works.map(w=>[w.slug,w.synopsis]))}
          : candidate;
        if(doc.synopses)break;
      }catch{/* Try the last deployed static fallback. */}
    }
    if(!doc||!doc.synopses)return;
    const slug=event.work_slug||window.OperaAtlasCatalog.urls(event).work.split("/").filter(Boolean).pop();
    const text=doc.synopses[slug];
    if(typeof text!=="string"||!text.trim())return;
    const section=node("section","brief-synopsis");
    section.append(node("h2",null,"In breve"),node("p",null,text));
    content.prepend(section);
  }catch{/* Optional editorial synopsis must never block performance dates. */}
}
function arrangeWorkOverview(event) {
  // The copy and cover belong to one editorial composition; listings stay below.
  const layout=node("div","work-overview");
  const copy=node("div","work-overview-copy");
  while(content.firstChild)copy.append(content.firstChild);
  const figure=node("figure","work-overview-figure");
  const poster=editorialImage("work",event);
  poster.className="work-cover-image";
  poster.loading="eager";
  figure.append(poster);
  layout.append(copy,figure);
  content.append(layout);
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
function miniDateParts(day) {
  const date=new Date(day+"T12:00:00Z");
  return {
    month:new Intl.DateTimeFormat("it-IT",{month:"short",timeZone:"UTC"}).format(date).replace(".","").toUpperCase(),
    day:String(date.getUTCDate()),
    weekday:new Intl.DateTimeFormat("it-IT",{weekday:"short",timeZone:"UTC"}).format(date).replace(".",""),
    long:dateLabel(day)
  };
}
function dateSelector(events) {
  const sorted=[...events].sort((a,b)=>a.local_date.localeCompare(b.local_date)||
    (a.starts_at||"").localeCompare(b.starts_at||""));
  const section=node("div","date-picker-section");
  const grid=node("div","mini-calendar-list");
  grid.setAttribute("role","group");
  grid.setAttribute("aria-label","Scegli una data della rappresentazione");
  const panel=node("div","selected-replica");
  panel.setAttribute("role","status");
  panel.setAttribute("aria-live","polite");
  const buttons=[];
  function show(event,index) {
    buttons.forEach((button,i)=>{
      const active=i===index;
      button.classList.toggle("is-selected",active);
      button.setAttribute("aria-pressed",active?"true":"false");
    });
    panel.replaceChildren();
    panel.append(node("strong","selected-replica-date",dateLabel(event.local_date)));
    panel.append(node("span","selected-replica-time",
      event.time_known?"Inizio alle ore "+event.starts_at.slice(11,16):"Orario da confermare"));
    panel.append(node("span","selected-replica-venue",event.venue+" · "+event.municipality));
  }
  sorted.forEach((event,i)=>{
    const p=miniDateParts(event.local_date);
    const button=node("button","mini-calendar");
    button.type="button";
    button.setAttribute("aria-label",p.long+", "+event.venue+" a "+event.municipality);
    button.setAttribute("aria-pressed","false");
    button.append(node("span","mini-calendar-month",p.month));
    const middle=node("span","mini-calendar-day",p.day);
    button.append(middle,node("span","mini-calendar-weekday",p.weekday));
    button.addEventListener("click",()=>show(event,i));
    buttons.push(button);grid.append(button);
  });
  section.append(grid,panel);
  if(sorted.length)show(sorted[0],0);
  return section;
}
function stagingGroup(events,owner) {
  const first=events[0];
  const section=node("section","staging-group"+(owner==="venue"?" theatre-production":""));
  const heading=node("h3");
  heading.append(link(owner==="work"
    ? first.venue+" · "+first.municipality
    : first.title,window.OperaAtlasCatalog.urls(first).staging,""));
  section.append(heading);
  if(owner==="venue" && first.composer)section.append(node("p","staging-composer",first.composer));
  section.append(dateSelector(events));
  section.append(link("Scopri la produzione",window.OperaAtlasCatalog.urls(first).production));
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
    if(pieces.length===2 && pieces[0]==="produzioni")
      return {kind:"group",events:events.filter(e=>e.production_group_id===pieces[1])};
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
    if(data.warning)status.textContent="Alcuni aggiornamenti non sono momentaneamente disponibili.";
    const events=data.performances.filter(validEvent);
    const selected=resolve(events);
    if(!selected.kind || !selected.events.length) {
      missing("Questo indirizzo non corrisponde a una scheda pubblicata.");
      return;
    }
    const first=selected.events[0];
    const future=selected.events.filter(e=>e.local_date>=todayInItaly());
    let theatreProfile=null;
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
        "Le prossime rappresentazioni nei teatri italiani."));
      for(const group of grouping(future))stagingGroup(group,"work");
      if(!future.length)results.append(node("p","empty","Non risultano prossime rappresentazioni verificate di questa opera nel catalogo Atlas."));
    }else if(selected.kind==="venue") {
      kind.textContent="Teatro";
      document.querySelector(".detail-related h2").textContent="Spettacoli in programma";
      title.textContent=first.venue;
      subtitle.textContent=[first.municipality,first.region].filter(Boolean).join(" · ");
      theatreProfile=await appendTheatreProfile(first);
      content.append(node("p","staging-summary",
        grouping(selected.events).length+" messe in scena · "+
        selected.events.length+" repliche"));
      for(const group of grouping(future))stagingGroup(group,"venue");
      if(!future.length)results.append(node("p","empty","Nessun prossimo spettacolo verificato presso questo teatro nel catalogo Atlas."));
    }else if(selected.kind==="group"){
      kind.textContent="Produzione condivisa";
      title.textContent=first.title;
      const venues=[...new Set(selected.events.map(e=>e.venue+" · "+e.municipality))];
      subtitle.textContent=venues.length+" teatri · "+(first.composer||"");
      document.querySelector(".detail-related h2").textContent="Dove e quando vedere questa produzione";
      content.append(node("p","staging-summary","Una produzione condivisa, "+venues.length+" sedi e "+selected.events.length+" rappresentazioni censite."));
      content.append(link("Scopri l'opera",window.OperaAtlasCatalog.urls(first).work));
      for(const group of grouping(future))stagingGroup(group,"work");
      if(!future.length)results.append(node("p","empty","Non risultano rappresentazioni future verificate di questa produzione."));
    }else{
      kind.textContent="Produzione";
      document.querySelector(".detail-related h2").textContent="Scegli la data della rappresentazione";
      title.textContent=first.title;
      subtitle.textContent=first.venue+" · "+first.municipality+
        (first.season ? " · Stagione "+first.season : "");
      content.append(node("p","staging-summary",
        "Una messa in scena, "+selected.events.length+" repliche in calendario."));
      content.append(link("Scopri l’opera",window.OperaAtlasCatalog.urls(first).work));
      content.append(node("span",null," · "));
      content.append(link("Scopri il teatro",window.OperaAtlasCatalog.urls(first).venue));
      if(future.length)results.append(dateSelector(future));
      if(!future.length)results.append(node("p","empty","Questa produzione non ha date future censite."));
    }
    if(selected.kind==="work")arrangeWorkOverview(first);
    else if(selected.kind==="staging" || selected.kind==="group"){
      const figure=node("figure","production-cover-figure");
      const poster=editorialImage("work",first);
      poster.className="production-cover-image";
      figure.append(poster);
      content.prepend(figure);
      content.classList.add("production-detail");
    }
    else content.prepend(editorialImage("venue",first));
    sourceLinks(selected.events,selected.kind,theatreProfile);
    document.title=title.textContent+" — Opera+ Atlas";
    // Canonicalize old query-based links after resolution; never change identity.
    if(pathnameIsLegacy()) {
      const canonical=selected.kind==="work"
        ? window.OperaAtlasCatalog.urls(first).work
        : selected.kind==="venue"
          ? window.OperaAtlasCatalog.urls(first).venue
          : selected.kind==="group"
            ? window.OperaAtlasCatalog.urls(first).production
            : window.OperaAtlasCatalog.urls(first).staging;
      window.history.replaceState(null,"",canonical);
    }
  }catch(error) {
    console.error("Atlas detail page error",error);
    missing("Non è stato possibile aprire questa scheda.");
  }
}
function pathnameIsLegacy() {
  return window.location.pathname.endsWith("/detail.html");
}
initialize();
