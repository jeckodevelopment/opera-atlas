"use strict";

/* The only external input is a generated, operator-reviewed JSON export.
   Render via DOM text nodes, not innerHTML; never invent missing times. */
/* Data are loaded from the canonical GitHub feed, not the SFTP copy. */
const PAGE_SIZE = 12;
let viewMode = "staging";
const controls = {
  query: document.getElementById("search"),
  location: document.getElementById("location"),
  radius: document.getElementById("radius"),
  period: document.getElementById("period"),
  sort: document.getElementById("sort"),
  city: document.getElementById("city"),
  region: document.getElementById("region"),
  from: document.getElementById("from"),
  to: document.getElementById("to"),
  time: document.getElementById("time-filter"),
};
const list = document.getElementById("events");
const message = document.getElementById("message");
const count = document.getElementById("count");
const pageLabel = document.getElementById("page-label");
const pager = document.querySelector(".pagination");
const prev = document.getElementById("previous");
const next = document.getElementById("next");
let catalog = [];
let page = 0;
let monthOffset = 0;

function safeSource(uri) {
  try {
    const parsed = new URL(uri);
    return parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function validEvent(event) {
  return event && typeof event.title === "string" && event.title.trim()
    && typeof event.venue === "string" && event.venue.trim()
    && typeof event.municipality === "string" && event.municipality.trim()
    && typeof event.local_date === "string"
    && /^\d{4}-\d{2}-\d{2}$/.test(event.local_date)
    && typeof event.time_known === "boolean"
    && (event.time_known
      ? typeof event.starts_at === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(event.starts_at)
      : event.starts_at === null)
    && Array.isArray(event.sources)
    && event.sources.some(safeSource);
}

function normalized(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("it").trim();
}

// Approximate municipal centers, not theatre geocodes. Values used solely for
// indicative straight-line city distance and the diagram map.
const CITY_CENTERS = Object.freeze({
  "torino":[45.0703,7.6869],"milano":[45.4642,9.1900],"como":[45.8081,9.0852],
  "pavia":[45.1847,9.1582],"brescia":[45.5416,10.2118],"cremona":[45.1332,10.0227],
  "verona":[45.4384,10.9916],"venezia":[45.4408,12.3155],
  "palermo":[38.1157,13.3615],"parma":[44.8015,10.3279],
  "novara":[45.445,8.622],"bergamo":[45.695,9.670],
  "reggio emilia":[44.698,10.631],"ravenna":[44.418,12.204]
});
function haversine(a,b) {
  const rad = Math.PI/180;
  const dLat=(b[0]-a[0])*rad, dLon=(b[1]-a[1])*rad;
  const h=Math.sin(dLat/2)**2+Math.cos(a[0]*rad)*Math.cos(b[0]*rad)*Math.sin(dLon/2)**2;
  return 6371*2*Math.atan2(Math.sqrt(h),Math.sqrt(1-h));
}
function distanceFor(event) {
  const start=CITY_CENTERS[normalized(controls.location.value)];
  const end=CITY_CENTERS[normalized(event.municipality)];
  return start && end ? Math.round(haversine(start,end)) : null;
}
function matches(event) {
  const phrase=normalized(controls.query.value);
  if (phrase && !normalized([event.title,event.composer,event.venue,event.municipality,event.region].join(" ")).includes(phrase)) return false;
  if (controls.city.value && event.municipality !== controls.city.value) return false;
  if (controls.region.value && (event.region||"") !== controls.region.value) return false;
  if (controls.from.value && event.local_date < controls.from.value) return false;
  if (controls.to.value && event.local_date > controls.to.value) return false;
  if (controls.time.value==="known" && !event.time_known) return false;
  if (controls.time.value==="unknown" && event.time_known) return false;
  if (controls.radius.value!=="all" && controls.location.value!=="") {
    const distance=distanceFor(event);
    if (distance===null || distance>Number(controls.radius.value)) return false;
  }
  return true;
}

function node(tag, cls, text) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (text !== undefined) element.textContent = text;
  return element;
}

function dateLabel(iso) {
  const d = new Date(iso + "T12:00:00Z");
  return new Intl.DateTimeFormat("it-IT", {day:"numeric",month:"long",year:"numeric",timeZone:"UTC"}).format(d);
}

function editorialImage(type,event,cls) {
  // Photographic assets are optional: they must never prevent catalog rendering.
  const images=window.OperaAtlasImages;
  if(images && typeof images.element==="function" && typeof images[type]==="function") {
    try{return images.element(images[type](event),cls);}catch(error){console.warn("Atlas image fallback",error);}
  }
  const placeholder=node("div",cls+" image-placeholder");
  placeholder.setAttribute("role","img");
  placeholder.setAttribute("aria-label","Illustrazione non disponibile");
  return placeholder;
}

function createCard(event) {
  const article = node("article","event");
  article.append(editorialImage("work",event,"event-image"));
  const main = node("div","event-main");
  main.append(node("div","event-meta","Opera lirica · "+event.municipality));
  const heading = node("h3");
  const title = node("a",null,event.title);
  title.href = window.OperaAtlasCatalog.urls(event).work;
  heading.append(title);
  main.append(heading);
  if (event.composer) main.append(node("p","composer",event.composer));
  const details = node("div","event-details");
  const venue = node("div","venue");
  const venueLink = node("a",null,event.venue);
  venueLink.href = window.OperaAtlasCatalog.urls(event).venue;
  venue.append(venueLink);
  details.append(venue);
  details.append(node("div","city",[event.municipality,event.region].filter(Boolean).join(" · ")));
  details.append(node("div","time"+(event.time_known?"":" unknown"),
    event.time_known ? "Ore "+event.starts_at.slice(11,16) : "Orario da confermare"));
  main.append(details);
  const detail = node("a","detail-link","Dettagli e date");
  detail.href = window.OperaAtlasCatalog.urls(event).staging;
  main.append(detail);
  article.append(main);
  const side = node("div","event-side");
  const calendar = node("div","calendar");
  const parts = event.local_date.split("-");
  const month = new Intl.DateTimeFormat("it-IT",{month:"short",timeZone:"UTC"})
    .format(new Date(event.local_date+"T12:00:00Z"));
  calendar.append(node("span","calendar-month",month));
  calendar.append(node("span","calendar-day",String(Number(parts[2]))));
  calendar.append(node("span","calendar-year",parts[0]));
  side.append(calendar);
  article.append(side);
  return article;
}

function fillOptions(select, values) {
  for (const value of [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b,"it"))) {
    const option = node("option",null,value);
    option.value = value;
    select.append(option);
  }
}

function compactDate(event) {
  const date=new Date(event.local_date+"T12:00:00Z");
  const tile=node("span","home-calendar");
  const month=new Intl.DateTimeFormat("it-IT",{month:"short",timeZone:"UTC"}).format(date).replace(".","").toUpperCase();
  const day=new Intl.DateTimeFormat("it-IT",{weekday:"short",timeZone:"UTC"}).format(date).replace(".","");
  tile.append(node("span","home-calendar-month",month));
  tile.append(node("span","home-calendar-day",String(date.getUTCDate())));
  tile.append(node("span","home-calendar-weekday",day));
  return tile;
}
function createStagingCard(events) {
  const first = events[0];
  const article = node("article","event");
  article.append(editorialImage("work",first,"event-image"));
  const main = node("div","event-main");
  main.append(node("div","event-meta",first.municipality+" · "+events.length+" repliche"));
  const heading = node("h3");
  const title = node("a",null,first.title);
  title.href = window.OperaAtlasCatalog.urls(first).production;
  heading.append(title);
  main.append(heading);
  if (first.composer) main.append(node("p","composer",first.composer));
  const uniqueVenues=[...new Set(events.map(e=>e.venue+" · "+e.municipality))];
  const theatre=node("p","composer",uniqueVenues.length===1?uniqueVenues[0]:uniqueVenues.length+" teatri · "+uniqueVenues.slice(0,2).join(" · ")+(uniqueVenues.length>2?" e altre sedi":""));
  main.append(theatre);
  const km=distanceFor(first);
  if(km!==null && controls.location.value)main.append(node("p","distance-label","A circa "+km+" km da "+controls.location.value));
  const dates=node("div","home-calendar-list");
  dates.setAttribute("aria-label","Prossime date delle rappresentazioni");
  for(const recita of events.slice(0,3)){
    const dateLink=node("a","home-calendar-link");
    dateLink.href=window.OperaAtlasCatalog.urls(recita).production;
    dateLink.setAttribute("aria-label","Vai alle date: "+dateLabel(recita.local_date));
    dateLink.append(compactDate(recita));
    dates.append(dateLink);
  }
  if(events.length>3)dates.append(node("span","home-calendar-more","+"+(events.length-3)+" altre"));
  main.append(dates);
  const link = node("a","detail-link","Dettagli e rappresentazioni");
  link.href = window.OperaAtlasCatalog.urls(first).production;
  main.append(link);
  article.append(main);
  return article;
}

function groupByStaging(events) {
  const groups = new Map();
  for (const e of events) {
    const key = e.production_group_id || e.staging_id || window.OperaAtlasCatalog.urls(e).staging;
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(e);
  }
  return [...groups.values()].map(group=>group.sort((a,b)=>a.local_date.localeCompare(b.local_date))).sort((a,b)=>a[0].local_date.localeCompare(b[0].local_date));
}

let workDescriptions={};
async function loadWorkDescriptions(){
  const sources=["./work-synopses.json","https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/work-synopses.json"];
  for(const uri of sources){
    try{
      const response=await fetch(uri,{cache:"no-store"});
      if(!response.ok)continue;
      const data=await response.json();
      if(data.schema_version===1 && data.synopses && Object.keys(data.synopses).length>=20){
        workDescriptions=data.synopses;return;
      }
    }catch(error){console.warn("Opera summaries unavailable from",uri,error);}
  }
}
function imageTile(url,title,subtitle,image,description=""){
  const a=node("a","discovery-card");
  a.href=url;
  a.append(image);
  const inside=node("span","discovery-card-body");
  inside.append(node("strong",null,title));
  if(subtitle)inside.append(node("small",null,subtitle));
  if(description)inside.append(node("span","discovery-description",description));
  a.append(inside);
  return a;
}
function renderDiscoveries() {
  const works=new Map(),venues=new Map();
  for(const event of catalog){
    const urls=window.OperaAtlasCatalog.urls(event);
    if(!works.has(urls.work))works.set(urls.work,event);
    if(!venues.has(urls.venue))venues.set(urls.venue,event);
  }
  const workBox=document.getElementById("discover-works");
  const venueBox=document.getElementById("discover-venues");
  workBox.replaceChildren();
  venueBox.replaceChildren();
  for(const [url,event] of [...works].sort((a,b)=>a[1].title.localeCompare(b[1].title,"it")).slice(0,6)){
    workBox.append(imageTile(url,event.title,event.composer,editorialImage("work",event,"discovery-image"),workDescriptions[event.work_slug]||""));
  }
  for(const [url,event] of [...venues].sort((a,b)=>{
    const priority=x=>x.municipality==="Torino" && x.venue==="Teatro Regio" ? 0 : 1;
    return priority(a[1])-priority(b[1]) || a[1].venue.localeCompare(b[1].venue,"it");
  }).slice(0,6)){
    venueBox.append(imageTile(url,event.venue,event.municipality,editorialImage("venue",event,"discovery-image")));
  }
}
async function renderFestivals(){
  const target=document.getElementById("discover-festivals");
  if(!target)return;
  target.replaceChildren(node("p",null,"Verifica dei programmi festivalieri…"));
  try{
    const festivals=await window.OperaAtlasFestivals.load();
    target.replaceChildren();
    let count=0;
    for(const festival of festivals){
      const future=catalog.filter(e=>festival.staging_ids.includes(e.staging_id)&&e.local_date>=todayInItaly());
      if(!future.length)continue;
      const url="./directory.html?section=festival&id="+encodeURIComponent(festival.id);
      target.append(imageTile(url,festival.name,festival.city+(festival.edition?" · "+festival.edition:""),editorialImage("festival",festival,"discovery-image")));count++;
    }
    if(!count)target.append(node("p",null,"Il prossimo festival da scoprire arriverà presto."));
    const all=node("a","detail-link","Esplora i festival");all.href="./directory.html?section=festival";target.append(all);
  }catch{
    target.replaceChildren(node("p",null,"I festival torneranno presto disponibili."));
  }
}
function todayInItaly() {
  const parts = new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const part = key => parts.find(p=>p.type===key).value;
  return part("year")+"-"+part("month")+"-"+part("day");
}
function defaultPeriod() {
  const today = todayInItaly();
  const end = new Date(today+"T12:00:00Z");
  end.setUTCDate(end.getUTCDate()+29);
  controls.from.value = today;
  controls.to.value = end.toISOString().slice(0,10);
}
function orderedEvents() {
  const filtered=catalog.filter(matches);
  if(controls.sort.value==="title") filtered.sort((a,b)=>a.title.localeCompare(b.title,"it")||a.local_date.localeCompare(b.local_date));
  else if(controls.sort.value==="distance")filtered.sort((a,b)=>(distanceFor(a)??Infinity)-(distanceFor(b)??Infinity)||a.local_date.localeCompare(b.local_date));
  return filtered;
}
function calendarMonth(events) {
  const panel=document.getElementById("calendar-view");
  panel.replaceChildren();
  const current=new Date(todayInItaly()+"T12:00:00Z");
  const month=new Date(Date.UTC(current.getUTCFullYear(),current.getUTCMonth()+monthOffset,1,12));
  const year=month.getUTCFullYear(),m=month.getUTCMonth();
  const header=node("div","month-header");
  const back=node("button",null,"‹ Mese precedente"), nextMonth=node("button",null,"Mese successivo ›");
  back.type=nextMonth.type="button";
  back.addEventListener("click",()=>{monthOffset--;calendarMonth(events);});
  nextMonth.addEventListener("click",()=>{monthOffset++;calendarMonth(events);});
  header.append(back,node("h3",null,new Intl.DateTimeFormat("it-IT",{month:"long",year:"numeric",timeZone:"UTC"}).format(month)),nextMonth);
  panel.append(header);
  const grid=node("div","calendar-grid");
  for(const name of ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"])grid.append(node("div","weekday",name));
  const first=(month.getUTCDay()+6)%7;
  for(let i=0;i<first;i++)grid.append(node("div","calendar-blank"));
  const total=new Date(Date.UTC(year,m+1,0)).getUTCDate();
  for(let day=1;day<=total;day++){
    const iso=year+"-"+String(m+1).padStart(2,"0")+"-"+String(day).padStart(2,"0");
    const cell=node("div","calendar-cell");
    cell.append(node("strong",null,String(day)));
    for(const e of events.filter(x=>x.local_date===iso)){
      const link=node("a","calendar-event",e.title+" · "+e.municipality+(e.time_known?" · "+e.starts_at.slice(11,16):""));
      link.href=window.OperaAtlasCatalog.urls(e).production;
      cell.append(link);
    }
    grid.append(cell);
  }
  panel.append(grid);
}
function renderMap(events) {
  const holder=document.getElementById("atlas-map");
  const venueLinks=document.getElementById("map-venues");
  holder.replaceChildren();venueLinks.replaceChildren();
  const byVenue=new Map();
  for(const event of events) {
    const url=window.OperaAtlasCatalog.urls(event).venue;
    if(!byVenue.has(url))byVenue.set(url,{event,count:0});
    byVenue.get(url).count++;
  }
  const locations=[...byVenue.values()].map(({event,count})=>({
    event,count,coord:CITY_CENTERS[normalized(event.municipality)]
  })).filter(item=>Array.isArray(item.coord));
  if(!locations.length){
    const empty=node("p","map-empty");
    empty.append(node("strong",null,events.length
      ?"Non sono disponibili coordinate per le sedi filtrate."
      :"Nessun teatro corrisponde ai filtri attuali."));
    empty.append(node("span",null,
      " Per esplorare altre sedi, amplia il periodo oppure seleziona «Tutta Italia» nei filtri."));
    holder.append(empty);
    return;
  }
  const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
  svg.setAttribute("role","group");
  svg.setAttribute("aria-label","Posizione indicativa dei teatri nei risultati. Seleziona un punto o un collegamento sotto la mappa.");
  const addSvg=(tag,attrs,parent=svg)=>{
    const n=document.createElementNS("http://www.w3.org/2000/svg",tag);
    for(const [key,value] of Object.entries(attrs))n.setAttribute(key,String(value));
    parent.append(n);return n;
  };
  const projected=locations.map(item=>({
    ...item,
    x:(item.coord[1]-6)*51+65,
    y:(47-item.coord[0])*54+35
  }));
  const minX=Math.min(...projected.map(v=>v.x)),maxX=Math.max(...projected.map(v=>v.x));
  const minY=Math.min(...projected.map(v=>v.y)),maxY=Math.max(...projected.map(v=>v.y));
  // Zoom to *visible* venues, avoiding a near-empty Italy-wide plate for one city.
  // Wide enough for readable labels and marker hit areas, including one location.
  const width=Math.max(300,maxX-minX+160),height=Math.max(185,maxY-minY+110);
  const midX=(minX+maxX)/2,midY=(minY+maxY)/2;
  svg.setAttribute("viewBox",[midX-width/2,midY-height/2,width,height].join(" "));
  svg.setAttribute("preserveAspectRatio","xMidYMid meet");
  // Light geographical reference grid; schematic, not navigational cartography.
  const left=midX-width/2,top=midY-height/2;
  for(let i=0;i<Math.ceil(width/85)+1;i++){
    const x=Math.floor(left/85)*85+i*85;
    addSvg("line",{x1:x,y1:top,x2:x,y2:top+height,stroke:"#e7e2d8","stroke-width":1});
  }
  for(let i=0;i<Math.ceil(height/85)+1;i++){
    const y=Math.floor(top/85)*85+i*85;
    addSvg("line",{x1:left,y1:y,x2:left+width,y2:y,stroke:"#e7e2d8","stroke-width":1});
  }
  const collisions=new Map();
  for(const place of projected){
    const url=window.OperaAtlasCatalog.urls(place.event).venue;
    const key=place.coord.join(",");
    const ordinal=collisions.get(key)||0;
    collisions.set(key,ordinal+1);
    const x=place.x+ordinal*18,y=place.y+ordinal*20;
    const anchor=addSvg("a",{href:url,"aria-label":place.event.venue+" a "+place.event.municipality+
      ", "+place.count+" rappresentazioni; apri la scheda del teatro"});
    addSvg("circle",{cx:x,cy:y,r:15,fill:"#b58b24",stroke:"#fff","stroke-width":3},anchor);
    addSvg("circle",{cx:x,cy:y,r:6,fill:"#262018"},anchor);
    addSvg("text",{x:x+21,y:y+5,"font-size":13,fill:"#24292b","font-weight":600},anchor)
      .textContent=place.event.municipality;
    addSvg("title",{},anchor).textContent=place.event.venue+" · "+place.count+" rappresentazioni";
    const link=node("a","discovery-link",place.event.venue+" · "+
      place.event.municipality+" ("+place.count+" recite)");
    link.href=url;venueLinks.append(link);
  }
  holder.append(svg);
  const caption=node("p","map-caption",locations.length+" "+
    (locations.length===1?"teatro localizzato":"teatri localizzati")+
    " nei risultati filtrati. Posizioni indicative per città; seleziona un punto o un teatro per i dettagli.");
  holder.append(caption);
}

function render() {
  const filtered=orderedEvents();
  const entries=viewMode==="staging"?groupByStaging(filtered):filtered;
  const pages=Math.ceil(entries.length/PAGE_SIZE);
  page=Math.max(0,Math.min(page,Math.max(0,pages-1)));
  list.replaceChildren();
  const isCalendar=viewMode==="calendar",isMap=viewMode==="map";
  list.hidden=isCalendar||isMap;
  document.getElementById("calendar-view").hidden=!isCalendar;
  document.getElementById("map-view").hidden=!isMap;
  pager.hidden=isCalendar||isMap||pages<=1;
  if(isCalendar)calendarMonth(filtered);
  else if(isMap)renderMap(filtered);
  else{
    const visible=entries.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);
    if(viewMode==="staging")visible.forEach(group=>list.append(createStagingCard(group)));
    else visible.forEach(event=>list.append(createCard(event)));
    if(!filtered.length){
      const empty=node("div","empty");
      empty.append(node("strong",null,catalog.length?"Nessuno spettacolo per questa ricerca.":"Nessuna recita pubblicata."));
      empty.append(node("p",null,"Prova ad ampliare distanza o periodo oppure seleziona «Tutta Italia»."));
      list.append(empty);
    }
  }
  const productionCount=groupByStaging(filtered).length;
  const resultTitle=document.getElementById("results-title");
  resultTitle.textContent=productionCount+" "+(productionCount===1?"opera":"opere")+" in scena vicino a te";
  count.textContent=(viewMode==="staging"?productionCount+" produzioni · ":"")+filtered.length+" rappresentazioni";
  prev.disabled=page===0;next.disabled=page>=pages-1;
  pageLabel.textContent=pages?"Pagina "+(page+1)+" di "+pages:"";
}
function syncPeriod(){
  const today=todayInItaly();
  controls.from.value=today;
  if(controls.period.value==="all")controls.to.value="";
  else{
    const end=new Date(today+"T12:00:00Z");
    end.setUTCDate(end.getUTCDate()+Number(controls.period.value)-1);
    controls.to.value=end.toISOString().slice(0,10);
  }
}
function populateLocations(){
  const cities=[...new Set(catalog.map(x=>x.municipality))].sort((a,b)=>a.localeCompare(b,"it"));
  controls.location.replaceChildren(node("option",null,"Tutta Italia"));
  controls.location.firstChild.value="";
  for(const city of cities){const opt=node("option",null,city);opt.value=city;controls.location.append(opt);}
  controls.location.value=cities.includes("Torino")?"Torino":"";
}

async function initialize() {
  try {
    const documentData = await window.OperaAtlasCatalog.load();
    if (documentData.warning) message.textContent = documentData.warning;

    if (!documentData || documentData.schema_version !== 1 || !Array.isArray(documentData.performances)) {
      throw new Error("schema non supportato");
    }
    const raw = documentData.performances;
    catalog = raw.filter(validEvent).sort((a,b)=>a.local_date.localeCompare(b.local_date) ||
      (a.starts_at || "").localeCompare(b.starts_at || ""));
    if (raw.length !== catalog.length) {
      message.textContent = "Alcuni spettacoli non sono disponibili.";
    }

    fillOptions(controls.city,catalog.map(x=>x.municipality));
    populateLocations();
    renderDiscoveries();
    loadWorkDescriptions().then(renderDiscoveries).catch(error=>console.warn("Opera descriptions unavailable",error));
    renderFestivals();
    fillOptions(controls.region,catalog.map(x=>x.region));
    render();
  } catch (error) {
    console.error("Opera Atlas catalog initialization failed",error);
    count.textContent = "Dati non disponibili";
    list.replaceChildren(node("p","empty","Non è stato possibile caricare il catalogo verificato. Riprova più tardi."));
    pager.hidden = true;
  }
}

document.getElementById("filters").addEventListener("submit",event=>{event.preventDefault();page=0;render();document.getElementById("results-title").scrollIntoView({behavior:"smooth"});});
document.querySelectorAll("[data-catalog-view]").forEach(button=>{
  button.addEventListener("click",()=>{
    viewMode=button.dataset.catalogView;
    document.querySelectorAll("[data-catalog-view]").forEach(item=>{
      const active=item===button;item.classList.toggle("active",active);
      item.setAttribute("aria-pressed",active?"true":"false");
    });
    page=0;render();
  });
});
for(const [name,control] of Object.entries(controls)){
  control.addEventListener("change",()=>{
    if(name==="period")syncPeriod();
    page=0;render();
  });
  if(name==="query")control.addEventListener("input",()=>{page=0;render();});
}
document.getElementById("locate-me").addEventListener("click",()=>{
  if(!navigator.geolocation){message.textContent="Posizione non disponibile in questo browser.";return;}
  navigator.geolocation.getCurrentPosition(position=>{
    const coords=[position.coords.latitude,position.coords.longitude];
    const candidates=[...controls.location.options].filter(option=>option.value&&CITY_CENTERS[normalized(option.value)])
      .map(option=>({city:option.value,distance:Math.round(haversine(coords,CITY_CENTERS[normalized(option.value)]))}))
      .sort((a,b)=>a.distance-b.distance);
    if(!candidates.length||candidates[0].distance>80){
      message.textContent="Nessuna città censita sufficientemente vicina. Scegli una località manualmente.";
      return;
    }
    controls.location.value=candidates[0].city;page=0;render();
    message.textContent="Località impostata sulla città censita più vicina ("+candidates[0].city+"). La posizione esatta non viene conservata.";
  },()=>{message.textContent="Localizzazione non autorizzata o non disponibile. Puoi scegliere una città manualmente.";},
  {enableHighAccuracy:false,timeout:9000,maximumAge:0});
});
document.getElementById("reset").addEventListener("click",()=>{
  controls.query.value=controls.city.value=controls.region.value=controls.time.value="";
  controls.location.value="Torino";controls.radius.value="100";controls.period.value="30";controls.sort.value="date";
  syncPeriod();page=0;render();
});
prev.addEventListener("click",()=>{page--;render();});
next.addEventListener("click",()=>{page++;render();});
syncPeriod();
initialize();