"use strict";

/* Static deep-route details: an opera lists every staging in Italy, a theatre
   lists its stagings, and one staging owns all of its date/time replicas.
   No client-supplied path is used as a remote URL. */
const root = new URL(document.baseURI).pathname;
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
async function appendTheatreProfile(event,venueRecord=null){
  let stored=null;
  // Editorial updates live in GitHub; the SFTP snapshot is only a fallback.
  for(const url of [
    "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/theatre-profiles.json",
    "./theatre-profiles.json"
  ]){
    try{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)continue;
      const doc=await response.json();
      if(doc.schema_version!==1 || !doc.venues)continue;
      const lookup=event.municipality+"|"+
        (event.municipality==="Torino" && event.venue==="Teatro Regio di Torino"?"Teatro Regio":event.venue);
      stored=doc.venues[lookup]||null;
      if(stored)break;
    }catch(error){console.warn("Theatre historical profile unavailable",url,error);}
  }
  // The independently catalogued national venues have a factual, sourced
  // short profile even without a legacy history or any registered performance.
  const profile=stored || (venueRecord ? {
    description:venueRecord.description,
    website:venueRecord.website||venueRecord.source_url,
    source:venueRecord.source_url
  } : null);
  if(!profile)return null;
  const section=node("section","theatre-introduction");
  if(profile.description)section.append(node("p","theatre-description",profile.description));
  if(typeof profile.history==="string" && profile.history.trim()){
    const history=node("section","theatre-history");
    history.append(node("h2",null,"La storia del teatro"),
      node("p","theatre-history-text",profile.history));
    section.append(history);
  }
  if(typeof profile.address==="string" && profile.address.trim()){
    const place=node("div","theatre-location");
    place.append(node("h2",null,"Dove si trova"));
    place.append(node("p",null,profile.address+" · "+event.municipality));
    // Google Maps search links work without an API key and preserve the verified full address.
    const direction=link("Come arrivare", "https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(profile.address+", "+event.municipality+", Italia"));
    direction.setAttribute("aria-label","Apri Google Maps per "+event.venue+" a "+event.municipality);
    direction.target="_blank";direction.rel="noopener noreferrer";
    place.append(direction);
    section.append(place);
  }
  content.append(section);
  return profile;
}
function link(text, url, css="detail-link") {
  const a=node("a",css,text);
  a.href=url;
  return a;
}

// Search metadata for canonical entities is generated from validated catalog data.
// A generic OG preview remains in detail.html for bots that cannot execute JS.
function setDetailSEO(selected,first) {
  const text = String(title.textContent||"").trim();
  const description = selected.kind==="work"
    ? text+" di "+(first.composer||"autore non indicato")+": scopri produzioni e recite nei teatri italiani su Opera+ Atlas."
    : selected.kind==="venue"
      ? text+" a "+first.municipality+": repertorio e rappresentazioni operistiche su Opera+ Atlas."
      : text+" al "+first.venue+" di "+first.municipality+": programma e date delle recite su Opera+ Atlas.";
  const urls=window.OperaAtlasCatalog.urls(first);
  const pathname=selected.kind==="work"?urls.work:selected.kind==="venue"?urls.venue:
    selected.kind==="group"?urls.production:urls.staging;
  const canonical=new URL(pathname,location.origin).href;
  function meta(key,value,property=false){
    let element=document.head.querySelector('meta['+(property?'property':'name')+'="'+key+'"]');
    if(!element){element=document.createElement("meta");element.setAttribute(property?"property":"name",key);document.head.append(element);}
    element.content=value;
  }
  meta("description",description);
  meta("og:title",document.title,true);
  meta("og:description",description,true);
  meta("og:url",canonical,true);
  meta("twitter:title",document.title);
  meta("twitter:description",description);
  let link=document.head.querySelector('link[rel="canonical"]');
  if(!link){link=document.createElement("link");link.rel="canonical";document.head.append(link);}
  link.href=canonical;
  // Only semantic facts actually present in the catalog; no invented venue
  // street addresses, tickets, prices, times or performer credits.
  let structured;
  if(selected.kind==="work"){
    structured={"@context":"https://schema.org","@type":"MusicComposition","name":first.title,
      "composer":first.composer?{"@type":"Person","name":first.composer}:undefined,"url":canonical};
  }else if(selected.kind==="venue"){
    structured={"@context":"https://schema.org","@type":"PerformingArtsTheater","name":first.venue,
      "address":{"@type":"PostalAddress","addressLocality":first.municipality,"addressCountry":"IT"},
      "url":canonical};
  }else{
    const recite=selected.events.filter(e=>e.starts_at && e.time_known &&
      e.status!=="cancelled" && e.status!=="canceled").slice(0,60);
    structured={"@context":"https://schema.org","@graph":recite.map(e=>({
      "@type":"Event","name":e.title,"startDate":e.starts_at,
      "location":{"@type":"Place","name":e.venue,
        "address":{"@type":"PostalAddress","addressLocality":e.municipality,"addressCountry":"IT"}},
      "url":canonical
    }))};
  }
  let block=document.getElementById("atlas-structured-data");
  if(!block){block=document.createElement("script");block.id="atlas-structured-data";block.type="application/ld+json";document.head.append(block);}
  block.textContent=JSON.stringify(structured);
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
      "./work-synopses.json",
      "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/work-synopses.json"
    ]){
      try{
        const response=await fetch(url,{cache:"no-store"});
        if(!response.ok)continue;
        const candidate=await response.json();
        if(candidate.schema_version!==1)continue;
        doc=Array.isArray(candidate.works)
          ? {synopses:Object.fromEntries(candidate.works.flatMap(w=>[[w.work_id,w.synopsis],[w.slug,w.synopsis]]))}
          : candidate;
        if(doc.synopses)break;
      }catch{/* Try the last deployed static fallback. */}
    }
    if(!doc||!doc.synopses)return;
    const slug=event.work_slug||window.OperaAtlasCatalog.urls(event).work.split("/").filter(Boolean).pop();
    const text=doc.synopses[event.work_id] ||
      (doc.synopses_by_id?.[event.work_id]) ||
      (event.work_slug==="la-boheme"?null:doc.synopses[slug]);
    if(typeof text!=="string"||!text.trim())return;
    const section=node("section","brief-synopsis");
    section.append(node("h2",null,"La trama"),node("p",null,text));
    content.prepend(section);
  }catch{/* Optional editorial synopsis must never block performance dates. */}
}
async function appendHistory(event) {
  const slug=event.work_slug||window.OperaAtlasCatalog.urls(event).work.split("/").filter(Boolean).pop();
  for(const url of ["https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/work-editorial.json",
    "./work-history.json",
    "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/work-history.json"]){
    try{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)continue;
      const doc=await response.json();
      if(doc.schema_version!==1||!doc.works||typeof doc.works!=="object")continue;
      const history=Array.isArray(doc.works)
        ? doc.works.find(w=>event.work_id?w.work_id===event.work_id:
          (w.slug===slug && slug!=="la-boheme"))?.history
        : doc.works_by_id?.[event.work_id] ||
          (event.work_slug==="la-boheme"?null:doc.works[slug]);
      if(!history)return;
      const historyParts=[];
      const librettists=String(history.librettist||"").trim().replace(/;\s*/g," e ");
      const composed=Number.isInteger(history.composition_year)?history.composition_year:null;
      const premiered=Number.isInteger(history.premiere_year)?history.premiere_year:null;
      const date=typeof history.premiere_date==="string" && /^\d{4}-\d{2}-\d{2}$/.test(history.premiere_date)
        && Number.isInteger(premiered) && history.premiere_date.startsWith(String(premiered)+"-")
        && !Number.isNaN(Date.parse(history.premiere_date+"T12:00:00Z"))
        ? dateLabel(history.premiere_date):null;
      const theatre=String(history.premiere_venue||"").trim();
      const city=String(history.premiere_city||"").trim();
      const place=[theatre,city].filter(Boolean).join(" di ");
      const when=date?"il "+date:premiered?"nel "+premiered:"";
      // An announced world premiere is not a historical event yet. Compare
      // against the calendar date in Italy, rather than the visitor's timezone.
      const today=new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",
        year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
      const part=type=>today.find(item=>item.type===type)?.value||"";
      const todayISO=part("year")+"-"+part("month")+"-"+part("day");
      const futurePremiere=Boolean(
        (history.premiere_date && /^\d{4}-\d{2}-\d{2}$/.test(history.premiere_date) &&
         history.premiere_date>todayISO) ||
        (!history.premiere_date && premiered>Number(part("year"))));
      const beginning=futurePremiere?"La prima assoluta è prevista ":"La prima rappresentazione ebbe luogo ";
      if(when && place){
        historyParts.push(beginning+when+" al "+place+
          (librettists?" su libretto di "+librettists:"")+".");
      }else if(when){
        historyParts.push(beginning+when+
          (librettists?" su libretto di "+librettists:"")+".");
      }else if(place){
        historyParts.push(beginning+"al "+place+
          (librettists?" su libretto di "+librettists:"")+".");
      }else if(librettists){
        historyParts.push("Il libretto dell’opera è di "+librettists+".");
      }
      if(composed)historyParts.push("L’opera fu composta nel "+composed+".");
      if(!historyParts.length)return;
      const section=node("section","work-history work-history-narrative");
      section.append(node("h2",null,"La storia dell’opera"),
        node("p","work-history-story",historyParts.join(" ")));
      content.append(section);
      // Historical references are kept at the very end of the opera detail.
      const source=Array.isArray(history.sources)?history.sources.map(safeSource).find(Boolean):null;
      if(source){
        const references=node("section","official-links work-references");
        references.append(node("h2",null,"Per approfondire"));
        const anchor=link("Consulta la scheda archivistica dell’opera",source);
        anchor.target="_blank";anchor.rel="noopener noreferrer";
        references.append(anchor);
        results.after(references);
      }
      return;
    }catch(error){console.warn("Opera history data unavailable",error);}
  }
}
// Related homonyms are discovered from canonical work IDs, never from title-only URLs.
// The list is informational: each target resolves to its own permanent work identity.
function appendHomonymousWorks(current, allEvents) {
  const byId=new Map();
  for(const candidate of allEvents){
    if(!candidate.work_id || candidate.work_id===current.work_id)continue;
    if(normalize(candidate.title)!==normalize(current.title))continue;
    if(!byId.has(candidate.work_id))byId.set(candidate.work_id,candidate);
  }
  if(!byId.size)return;
  const section=node("section","work-homonyms");
  section.append(node("h2",null,"Altre opere con lo stesso titolo"));
  const list=node("ul","official-link-list");
  for(const candidate of [...byId.values()].sort((a,b)=>a.composer.localeCompare(b.composer,"it"))){
    const item=node("li");
    item.append(link(candidate.title+" — "+candidate.composer,
      window.OperaAtlasCatalog.urls(candidate).work));
    list.append(item);
  }
  section.append(list);
  content.append(section);
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
  const imageInfo=window.OperaAtlasImages?.work?.(event);
  if(imageInfo?.sourceUrl){
    const caption=node("figcaption","work-image-credit");
    const anchor=node("a",null,
      imageInfo.kind==="archival_work_image"
        ?"Immagine storica · fonte e licenza"
        :"Immagine della produzione · fonte ufficiale");
    anchor.href=imageInfo.sourceUrl;
    anchor.target="_blank";
    anchor.rel="noopener noreferrer";
    caption.append(anchor);
    figure.append(caption);
  }
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
  section.append(link("Scopri la produzione",window.OperaAtlasCatalog.urls(first).production,"detail-link staging-action"));
  results.append(section);
}
function todayInItaly(){
  const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const get=key=>parts.find(x=>x.type===key).value;
  return get("year")+"-"+get("month")+"-"+get("day");
}
function resolve(events,venues=[],works=[]) {
  const pathname=decodeURI(window.location.pathname);
  const path=pathname.startsWith(root) ? pathname.slice(root.length) : "";
  const pieces=path.split("/").filter(Boolean);
  if(pieces.length && pieces.every(part=>/^[a-z0-9-]+$/.test(part))) {
    if(pieces.length===2 && pieces[0]==="produzioni")
      return {kind:"group",events:events.filter(e=>e.production_group_id===pieces[1])};
    if(pieces.length===2 && pieces[0]==="programmi")
      return {kind:"program",events:events.filter(e=>e.program_id===pieces[1])};
    if(pieces.length===2 && pieces[0]==="opere") {
      const work=works.find(w=>(w.route_slug||w.slug)===pieces[1])||null;
      return {kind:"work",work,events:events.filter(e=>
        (work && e.work_id===work.id) ||
        window.OperaAtlasCatalog.urls(e).work===root+pieces.join("/")+"/" ||
        (e.program_components||[]).some(c=>c.work_route_slug===pieces[1]))};
    }
    if(pieces.length===2){
      const url=root+pieces.join("/")+"/";
      const venue=venues.find(v=>v.city_slug===pieces[0] && v.slug===pieces[1])||null;
      return {kind:"venue",venue,events:events.filter(e=>
        window.OperaAtlasCatalog.urls(e).venue===url)};
    }
    if(pieces.length===3)
      return {kind:"staging",events:events.filter(e=>
        window.OperaAtlasCatalog.urls(e).staging===root+pieces.join("/")+"/")};
  }
  // Backward-compatible query-string URLs from older catalog editions.
  const args=new URLSearchParams(window.location.search);
  const type=args.get("type"),key=args.get("key");
  if(!key || key.length>512)return {kind:null,events:[]};
  if(type==="work")return {kind:"work",events:events.filter(e=>
    (key.startsWith("oa-w-")?e.work_id===key ||
      (e.program_work_ids||[]).includes(key):
      normalize(e.title)+"|"+normalize(e.composer)===key))};
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
    await window.OperaAtlasImages?.load?.();

    if(data.warning)status.textContent="Alcuni aggiornamenti non sono momentaneamente disponibili.";
    const events=data.performances.filter(validEvent);
    const venues=await window.OperaAtlasCatalog.venues();
    const selected=resolve(events,venues,data.works||[]);
    if(!selected.kind || (!selected.events.length && !(selected.kind==="venue" && selected.venue) && !(selected.kind==="work" && selected.work))) {
      missing("Questo indirizzo non corrisponde a una scheda pubblicata.");
      return;
    }
    // The HTML response already contains a crawler-readable editorial snapshot.
    // Once live client data is validated, remove it before rendering the full
    // interactive detail, so visitors do not see duplicate summaries.
    document.getElementById("atlas-prerender")?.remove();
    const first=selected.kind==="work" && selected.work ? {
      title:selected.work.title,composer:selected.work.composer,
      work_id:selected.work.id,work_slug:selected.work.slug,
      work_route_slug:selected.work.route_slug||selected.work.slug
    } : selected.events[0] || (selected.kind==="venue" && selected.venue ? {
      venue:selected.venue.name,
      municipality:selected.venue.city,
      region:selected.venue.region,
      venue_slug:selected.venue.slug,
      city_slug:selected.venue.city_slug
    } : null);
    const future=selected.events.filter(e=>e.local_date>=todayInItaly());
    let theatreProfile=null;
    if(selected.kind==="work") {
      kind.textContent="Opera del repertorio";
      title.textContent=first.title;
      subtitle.textContent=first.composer||"Compositore non verificato";
      document.querySelector(".detail-related h2").textContent="Dove vedere "+first.title;
      await appendSynopsis(first);
      await appendHistory(first);
      appendHomonymousWorks(first,events);
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
      // Even without recite, show a contextual calendar status on the detail
      // page only. The theatre directory never displays acquisition notices.
      document.querySelector(".detail-related").hidden=false;
      theatreProfile=selected.venue
        ? await appendTheatreProfile(first,selected.venue)
        : await appendTheatreProfile(first);
      if(selected.events.length)content.append(node("p","staging-summary",
        grouping(selected.events).length+" messe in scena · "+
        selected.events.length+" repliche"));

      for(const group of grouping(future))stagingGroup(group,"venue");
      if(!future.length){
        const acquired=selected.events.length>0 ||
          selected.venue?.calendar_status==="acquired";
        if(acquired){
          results.append(node("p","empty","Non risultano prossimi spettacoli in programma."));
        }else{
          const notice=node("p","empty","Calendario non ancora acquisito · consulta il ");
          const official=theatreProfile?.website || selected.venue?.website;
          if(safeSource(official)){
            const website=link("sito del teatro",official,"");
            website.rel="noopener noreferrer";website.target="_blank";
            notice.append(website);
          }else{
            notice.append(document.createTextNode("sito del teatro"));
          }
          results.append(notice);
        }
      }
    }else if(selected.kind==="program"){
      kind.textContent="Programma composto";
      title.textContent=first.title;
      subtitle.textContent=first.venue+" · "+first.municipality;
      document.querySelector(".detail-related h2").textContent="Date dello spettacolo";
      content.append(node("p","staging-summary",
        "Un unico spettacolo con "+first.program_components.length+
        " composizioni e "+selected.events.length+" rappresentazioni verificate."));
      const components=node("ul","program-components");
      for(const component of first.program_components){
        const li=node("li","program-component");
        if(component.work_route_slug)
          li.append(link(component.title,root+"opere/"+component.work_route_slug+"/",""));
        else li.append(node("strong",null,component.title));
        li.append(document.createTextNode(" — "+component.composer));
        components.append(li);
      }
      content.append(components);
      content.append(link("Scopri il teatro",window.OperaAtlasCatalog.urls(first).venue));
      if(future.length)results.append(dateSelector(future));
      else results.append(node("p","empty","Non risultano rappresentazioni future verificate."));
    }else if(selected.kind==="group"){
      kind.textContent="Produzione condivisa";
      title.textContent=first.title;
      const venues=[...new Set(selected.events.map(e=>e.venue+" · "+e.municipality))];
      subtitle.textContent=venues.length+" teatri · "+(first.composer||"");
      document.querySelector(".detail-related h2").textContent="Dove e quando vedere questa produzione";
      await appendSynopsis(first);
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
      await appendSynopsis(first);
      content.append(node("p","staging-summary",
        "Una messa in scena, "+selected.events.length+" repliche in calendario."));
      content.append(link("Scopri l’opera",window.OperaAtlasCatalog.urls(first).work));
      content.append(node("span",null," · "));
      content.append(link("Scopri il teatro",window.OperaAtlasCatalog.urls(first).venue));
      if(future.length)results.append(dateSelector(future));
      if(!future.length)results.append(node("p","empty","Questa produzione non ha date future censite."));
    }
    if(selected.kind==="work")arrangeWorkOverview(first);
    else if(selected.kind==="staging" || selected.kind==="group" || selected.kind==="program"){
      const figure=node("figure","production-cover-figure");
      const imageKind=selected.kind==="program"?"program":"work";
      const poster=editorialImage(imageKind,first);
      poster.className="production-cover-image";
      figure.append(poster);
      if(imageKind==="program"){
        const info=window.OperaAtlasImages?.program?.(first);
        if(info?.sourceUrl && safeSource(info.sourceUrl)){
          const caption=node("figcaption","work-image-credit");
          const credit=node("a",null,(info.kind==="program_component_image"?"Immagine di una delle opere · ":"")+ (info.credit||"Fonte ufficiale"));
          credit.href=info.sourceUrl;credit.target="_blank";credit.rel="noopener noreferrer";
          caption.append(credit);figure.append(caption);
          if(info.fallbackArtwork)poster.addEventListener("error",()=>{
            const fallback=info.fallbackArtwork;
            credit.textContent="Immagine di una delle opere · "+(fallback.credit||"Fonte");
            credit.href=fallback.sourceUrl;
          },{once:true});
        }
      }
      content.prepend(figure);
      content.classList.add("production-detail");
    }
    else {
      const venueImageEvent={
        ...first,
        photo_file:selected.venue?.photo_file || theatreProfile?.photo_file,
        photo_url:selected.venue?.photo_url || theatreProfile?.photo_url,
        photo_credit:selected.venue?.photo_credit || theatreProfile?.photo_credit,
        photo_license:selected.venue?.photo_license || theatreProfile?.photo_license,
        photo_source_url:selected.venue?.photo_source_url || theatreProfile?.photo_source_url,
        no_city_fallback:!!selected.venue
      };
      const figure=node("figure","theatre-cover-figure");
      const venuePicture=editorialImage("venue",venueImageEvent);
      figure.append(venuePicture);
      const photoSource=venueImageEvent.photo_url && venuePicture?.src===venueImageEvent.photo_url
        ? venueImageEvent.photo_source_url : null;
      if(photoSource && safeSource(photoSource)){
        const caption=node("figcaption","work-image-credit");
        const attribution=link(venueImageEvent.photo_credit || "Fotografia del teatro · autore e licenza",photoSource,"");
        attribution.target="_blank";attribution.rel="noopener noreferrer";
        caption.append(attribution);figure.append(caption);
        venuePicture.addEventListener("error",()=>{caption.remove();},{once:true});
      }
      content.prepend(figure);
    }
    if(selected.events.length)sourceLinks(selected.events,selected.kind,theatreProfile);
    else sourceLinks([first],selected.kind,theatreProfile);
    document.title=title.textContent+" — Opera+ Atlas";
    setDetailSEO(selected,first);
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
