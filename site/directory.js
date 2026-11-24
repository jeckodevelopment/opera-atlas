"use strict";
const params=new URLSearchParams(location.search);
const section=["opere","teatri","festival"].includes(params.get("section"))?params.get("section"):"opere";
const config={opere:["Le opere","Scopri le storie che prendono vita nei teatri italiani."],teatri:["I teatri","I luoghi dove l’opera prende vita, città dopo città."],festival:["I festival","L’opera nei grandi festival italiani: stagioni, città e spettacoli."]};
document.getElementById("directory-title").textContent=config[section][0];
document.getElementById("directory-desc").textContent=config[section][1];
document.title=config[section][0]+" — Opera+ Atlas";

function directorySEO(name,description,canonical) {
  document.title=name+" — Opera+ Atlas";
  const fields=[["name","description",description],["property","og:title",document.title],
    ["property","og:description",description],["property","og:url",canonical],
    ["name","twitter:title",document.title],["name","twitter:description",description]];
  for(const [kind,key,value] of fields){
    let tag=document.head.querySelector('meta['+kind+'="'+key+'"]');
    if(!tag){tag=document.createElement("meta");tag.setAttribute(kind,key);document.head.append(tag);}
    tag.content=value;
  }
  let link=document.head.querySelector('link[rel="canonical"]');
  if(!link){link=document.createElement("link");link.rel="canonical";document.head.append(link);}
  link.href=canonical;
}
directorySEO(config[section][0],config[section][1],
  new URL("./directory.html?section="+section,document.baseURI).href);

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
      : ["https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/"+name,"./"+name];
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
      ? {city:item.city,municipality:item.city,venue:item.title,
         photo_file:item.photo_file,photo_url:item.photo_url,photo_credit:item.photo_credit,photo_license:item.photo_license,photo_source_url:item.photo_source_url,
         no_city_fallback:item.independentVenue===true}
      : {city:item.city,name:item.title,
         photo_file:item.photo_file,photo_source_url:item.photo_source_url,
         photo_credit:item.photo_credit,photo_alt:item.photo_alt};
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
    grid.append(node("p","empty",section==="festival"?(params.get("id")?"Nessuna opera attualmente in programma.":"Nessun festival corrispondente alla ricerca."):"Nessun risultato corrispondente alla ricerca."));
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
        const found=festivalListings.find(x=>x.item.id===focus || x.item.editions.some(e=>e.id===focus));
        if(!found){status.textContent="Festival non disponibile.";return;}
        const x=found.item;
        if(focus!==x.id){
          const canonical=new URL(location.href);canonical.searchParams.set("id",x.id);
          location.replace(canonical.href);return;
        }
        directorySEO(x.name,
          x.description||("Festival "+x.name+" a "+x.city),
          new URL("./directory.html?section=festival&id="+encodeURIComponent(x.id),document.baseURI).href);
        document.getElementById("directory-title").textContent=x.name;
        document.getElementById("directory-desc").textContent=x.description||x.city+" · "+x.region;
        search.hidden=true;
        if(x.photo_file && x.photo_source_url){
          const cover=node("figure","festival-cover-figure theatre-cover-figure");
          const photo=imageFor({title:x.name,city:x.city,imageKind:"festival",
            photo_file:x.photo_file,photo_source_url:x.photo_source_url,
            photo_credit:x.photo_credit,photo_alt:x.photo_alt});
          photo.className="detail-image";
          cover.append(photo);
          const caption=node("figcaption");
          const attribution=node("a",null,x.photo_credit||"Fotografia della sede · Wikimedia Commons");
          attribution.href=x.photo_source_url;
          attribution.target="_blank";attribution.rel="noopener noreferrer";
          caption.append(attribution);cover.append(caption);
          grid.before(cover);
        }
        const official=node("a","detail-link","Visita il sito del festival");
        official.href=x.official_url;official.target="_blank";official.rel="noopener noreferrer";
        official.id="festival-official";
        const stages=new Map();
        // Historical recitals remain in the catalog, not in the public programme.
        for(const event of found.future){
          if(!stages.has(event.staging_id))stages.set(event.staging_id,event);
        }
        for(const event of stages.values()){
          const url=window.OperaAtlasCatalog.urls(event).staging;
          const next=found.future.filter(e=>e.staging_id===event.staging_id)
            .sort((a,b)=>a.local_date.localeCompare(b.local_date))[0];
          const label="Prossima recita "+dateLabel(next.local_date);
          entries.push({url,title:event.title,subtitle:event.venue+" · "+event.municipality+" · "+label,city:event.municipality,imageKind:"work",work_slug:event.work_slug,work_id:event.work_id,composer:event.composer});
        }
        const footer=node("section","official-links");footer.append(node("h2",null,"Informazioni e biglietti"),official);grid.after(footer);
        if(!entries.length)status.textContent="Nessuna opera attualmente in programma.";
      }else{
        for(const found of festivalListings){
          const x=found.item;
          entries.push({url:"./directory.html?section=festival&id="+encodeURIComponent(x.id),
            title:x.name,city:x.city,description:x.description||"",
            photo_file:x.photo_file,photo_source_url:x.photo_source_url,
            photo_credit:x.photo_credit,photo_alt:x.photo_alt,
            subtitle:x.city+" · "+x.region+" · "+(found.future.length?found.future.length+" recite future":"Scopri il festival")});
        }
      }
      render();return;
    }
    const grouped=new Map();
    if(section==="teatri"){
      const knownVenues=new Set(data.performances.map(e=>window.OperaAtlasCatalog.urls(e).venue));
      const national=await window.OperaAtlasCatalog.venues();
      for(const venue of national){
        // Reuse the canonical production route for an already-known venue.
        const published=data.performances.find(e=>e.municipality===venue.city && e.venue===venue.name);
        const url=published ? window.OperaAtlasCatalog.urls(published).venue :
          window.OperaAtlasCatalog.urls({
            city_slug:venue.city_slug,venue_slug:venue.slug,municipality:venue.city,venue:venue.name
          }).venue;
        grouped.set(url,{
          url,title:venue.name,city:venue.city,
          subtitle:venue.city+" · "+venue.region,
          description:venue.description,
          photo_file:venue.photo_file,
          photo_url:venue.photo_url,
          photo_credit:venue.photo_credit,
          photo_license:venue.photo_license,
          photo_source_url:venue.photo_source_url,
          imageKind:"venue",
          hasPerformances:knownVenues.has(url),
          independentVenue:true,
        });
      }
    }
    for(const e of data.performances){
      // A program is a performance, not a new canonical opera.
      if(section==="opere"&&e.program_id)continue;
      if(typeof e.title!=="string"||typeof e.venue!=="string"||!e.local_date)continue;
      const urls=window.OperaAtlasCatalog.urls(e);
      const url=section==="opere"?urls.work:urls.venue;
      if(!grouped.has(url)){
        const profile=editorial.venues[e.municipality+"|"+(e.municipality==="Torino" && e.venue==="Teatro Regio di Torino"?"Teatro Regio":e.venue)];
        grouped.set(url,{url,title:section==="opere"?e.title:e.venue,work_slug:section==="opere"?e.work_slug:undefined,
          work_id:section==="opere"?e.work_id:undefined,
          composer:section==="opere"?e.composer:undefined,
          subtitle:section==="opere"?e.composer||"":e.municipality+" · "+(e.region||"Italia"),city:e.municipality,
          description:section==="opere"?editorial.synopses[e.work_id] || (e.work_slug==="la-boheme"?"":editorial.synopses[e.work_slug]||""):profile?.description||"",
          // Performance-derived venues are not necessarily in the independently
          // reviewed national directory. Carry their sourced editorial photo.
          ...(section==="teatri" && profile ? {
            photo_file:profile.photo_file,
            photo_url:profile.photo_url,
            photo_credit:profile.photo_credit,
            photo_license:profile.photo_license,
            photo_source_url:profile.photo_source_url,
            imageKind:"venue",
            independentVenue:true
          } : {})});
      }
    }
    // Canonical works can be published from verified program components
    // without inventing a solo staging or a future performance.
    if(section==="opere" && Array.isArray(data.works)){
      for(const work of data.works){
        if(!work || typeof work.id!=="string" || typeof work.title!=="string"
           || !/^[a-z0-9-]+$/.test(work.route_slug||work.slug||""))continue;
        const url=new URL("./opere/"+(work.route_slug||work.slug)+"/",document.baseURI).pathname;
        if(grouped.has(url))continue;
        grouped.set(url,{url,title:work.title,subtitle:work.composer||"",
          work_id:work.id,work_slug:work.slug,composer:work.composer,
          description:editorial.synopses[work.id]||""});
      }
    }
    entries.push(...[...grouped.values()].sort((a,b)=>a.title.localeCompare(b.title,"it")));
    if(data.warning)status.textContent=data.warning;
    render();
  }catch(error){console.error("Atlas directory initialization failed",error);status.textContent="Il catalogo non è momentaneamente consultabile. Riprova tra poco.";}
}
search.addEventListener("input",render);
initialize();