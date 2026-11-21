"use strict";
const params=new URLSearchParams(location.search);
const section=["opere","teatri","festival"].includes(params.get("section"))?params.get("section"):"opere";
const config={opere:["Le opere","Scopri le storie che prendono vita nei teatri italiani."],teatri:["I teatri","I luoghi dove l’opera prende vita, città dopo città."],festival:["I festival","L’opera nei grandi festival italiani: stagioni, città e spettacoli."]};
document.getElementById("directory-title").textContent=config[section][0];
document.getElementById("directory-desc").textContent=config[section][1];
document.title=config[section][0]+" — Opera+ Atlas";
document.querySelectorAll(".primary-nav a, .mobile-nav a").forEach(link=>{
  if(link.getAttribute("href")==="./directory.html?section="+section)link.setAttribute("aria-current","page");
});
const grid=document.getElementById("directory-grid");
const search=document.getElementById("directory-search");
const status=document.getElementById("directory-status");
const entries=[];
let festivalListings=[];
let editorial={synopses:{},venues:{}};
async function loadEditorial(){
  async function load(name){
    const urls=name==="work-synopses.json"
      ? ["https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/work-editorial.json","./"+name]
      : ["./"+name,"https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/"+name];
    for(const url of urls){
      try{
        const response=await fetch(url,{cache:"no-store"});
        if(!response.ok)continue;
        const data=await response.json();
        if(data.schema_version===1){
          if(name==="work-synopses.json" && Array.isArray(data.works)){
            return {schema_version:1,synopses:Object.fromEntries(data.works.map(w=>[w.work_id,w.synopsis]))};
          }
          return data;
        }
      }catch(error){console.warn("Editorial data unavailable",url,error);}
    }
    return null;
  }
  const [works,theatres]=await Promise.all([load("work-synopses.json"),load("theatre-profiles.json")]);
  editorial.synopses={...(works?.synopses||{}),...(works?.synopses_by_id||{})};
  editorial.venues=theatres?.venues||{};
}
function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function todayItaly(){const p=new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());const v=k=>p.find(x=>x.type===k).value;return v("year")+"-"+v("month")+"-"+v("day");}
function dateLabel(d){return new Intl.DateTimeFormat("it-IT",{day:"numeric",month:"long",year:"numeric",timeZone:"UTC"}).format(new Date(d+"T12:00:00Z"));}
function imageFor(item){
  const images=window.OperaAtlasImages;
  const fallback=node("div","directory-image image-placeholder");
  fallback.setAttribute("role","img");fallback.setAttribute("aria-label","Fotografia non disponibile");
  if(!images || typeof images.element!=="function")return fallback;
  const type=item.imageKind|| (section==="opere"?"work":section==="teatri"?"venue":"festival");
  const identity=type==="work"
    ? {title:item.title,work_slug:item.work_slug,work_id:item.work_id,composer:item.composer}
    : type==="venue"
      ? {city:item.city,municipality:item.city,venue:item.title}
      : {city:item.city,name:item.title};
  try{return images.element(images[type](identity),"directory-image");}
  catch(error){console.warn("Atlas image fallback",error);return fallback;}
}
function normalize(s){return String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it");}
function render(){
  grid.replaceChildren();
  const q=normalize(search.value);
  const filtered=entries.filter(x=>normalize([x.title,x.subtitle,x.description].join(" ")).includes(q));
  for(const item of filtered){
    const card=node("article","directory-card");
    card.append(imageFor(item));
    const heading=node("h2"),link=node("a",null,item.title);link.href=item.url;heading.append(link);
    card.append(heading,node("p",null,item.subtitle));
    if(item.description)card.append(node("p","directory-description",item.description));
    const action=node("a","detail-link",section==="opere"?"Scopri l’opera":section==="festival"?"Esplora il festival":"Scopri il teatro");
    action.href=item.url;card.append(action);grid.append(card);
  }
  if(!filtered.length){
    grid.append(node("p","empty",section==="festival"?"Nessun festival in programma al momento.":"Nessun risultato corrispondente alla ricerca."));
  }
  status.textContent=filtered.length+" risultati";
}
async function initialize(){
  try {
    const data=await window.OperaAtlasCatalog.load();
    await window.OperaAtlasImages?.load?.();

    await loadEditorial();
    if(section==="festival"){
      const records=await window.OperaAtlasFestivals.load();
      const focus=params.get("id");
      festivalListings=records.map(item=>{
        const associated=data.performances.filter(e=>item.staging_ids.includes(e.staging_id));
        const future=associated.filter(e=>e.local_date>=todayItaly());
        return {item,associated,future};
      });
      if(focus){
        const found=festivalListings.find(x=>x.item.id===focus);
        if(!found){status.textContent="Festival non disponibile.";return;}
        const x=found.item;
        document.getElementById("directory-title").textContent=x.name+(x.edition?" · "+x.edition:"");
        document.getElementById("directory-desc").textContent=x.description||x.city+" · "+x.region;
        search.hidden=true;
        const official=node("a","detail-link","Visita il sito del festival");
        official.href=x.official_url;official.target="_blank";official.rel="noopener noreferrer";
        official.id="festival-official";
        const stages=new Map();
        for(const event of found.future){
          if(!stages.has(event.staging_id))stages.set(event.staging_id,event);
        }
        for(const event of stages.values()){
          const url=window.OperaAtlasCatalog.urls(event).staging;
          entries.push({url,title:event.title,subtitle:event.venue+" · "+event.municipality+" · dal "+dateLabel(event.local_date),city:event.municipality,imageKind:"work",work_slug:event.work_slug,work_id:event.work_id,composer:event.composer});
        }
        const footer=node("section","official-links");footer.append(node("h2",null,"Informazioni e biglietti"),official);grid.after(footer);
        if(!entries.length)status.textContent="Il programma sarà disponibile prossimamente.";
      }else{
        for(const found of festivalListings){
          const x=found.item;
          entries.push({url:"./directory.html?section=festival&id="+encodeURIComponent(x.id),
            title:x.name+(x.edition?" · "+x.edition:""),city:x.city,description:x.description||"",
            subtitle:x.city+" · "+x.region+" · "+(found.future.length?found.future.length+" date in programma":"Scopri il festival")});
        }
      }
      render();return;
    }
    const grouped=new Map();
    if(section==="teatri"){
      const knownVenues=new Set(data.performances.map(e=>window.OperaAtlasCatalog.urls(e).venue));
      const national=await window.OperaAtlasCatalog.venues();
      for(const venue of national){
        const url=window.OperaAtlasCatalog.urls({
          city_slug:venue.city_slug,venue_slug:venue.slug,municipality:venue.city,venue:venue.name
        }).venue;
        grouped.set(url,{
          url,title:venue.name,city:venue.city,
          subtitle:venue.city+" · "+venue.region,
          description:venue.description,
          imageKind:"venue",
          hasPerformances:knownVenues.has(url),
          independentVenue:true,
        });
      }
    }
    for(const e of data.performances){
      if(typeof e.title!=="string"||typeof e.venue!=="string"||!e.local_date)continue;
      const urls=window.OperaAtlasCatalog.urls(e);
      const url=section==="opere"?urls.work:urls.venue;
      if(!grouped.has(url)){
        const profile=editorial.venues[e.municipality+"|"+(e.municipality==="Torino" && e.venue==="Teatro Regio di Torino"?"Teatro Regio":e.venue)];
        grouped.set(url,{url,title:section==="opere"?e.title:e.venue,work_slug:section==="opere"?e.work_slug:undefined,
          work_id:section==="opere"?e.work_id:undefined,
          composer:section==="opere"?e.composer:undefined,
          subtitle:section==="opere"?e.composer||"":e.municipality+" · "+(e.region||"Italia"),city:e.municipality,
          description:section==="opere"?editorial.synopses[e.work_id] || (e.work_slug==="la-boheme"?"":editorial.synopses[e.work_slug]||""):profile?.description||""});
      }
    }
    entries.push(...[...grouped.values()].sort((a,b)=>a.title.localeCompare(b.title,"it")));
    if(data.warning)status.textContent=data.warning;
    render();
  }catch(error){console.error("Atlas directory initialization failed",error);status.textContent="Il catalogo non è momentaneamente consultabile. Riprova tra poco.";}
}
search.addEventListener("input",render);
initialize();