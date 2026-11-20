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
function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function todayItaly(){const p=new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());const v=k=>p.find(x=>x.type===k).value;return v("year")+"-"+v("month")+"-"+v("day");}
function dateLabel(d){return new Intl.DateTimeFormat("it-IT",{day:"numeric",month:"long",year:"numeric",timeZone:"UTC"}).format(new Date(d+"T12:00:00Z"));}
function normalize(s){return String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it");}
function render(){
  grid.replaceChildren();
  const q=normalize(search.value);
  const filtered=entries.filter(x=>normalize([x.title,x.subtitle].join(" ")).includes(q));
  for(const item of filtered){
    const card=node("article","directory-card");
    const image=section==="opere"?window.OperaAtlasImages.work({title:item.title}):section==="teatri"?window.OperaAtlasImages.venue({municipality:item.city||item.subtitle}):window.OperaAtlasImages.festival({city:item.city});
    card.append(window.OperaAtlasImages.element(image,"directory-image"));
    const heading=node("h2"),link=node("a",null,item.title);link.href=item.url;heading.append(link);
    card.append(heading,node("p",null,item.subtitle));
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
        document.getElementById("directory-desc").textContent=x.city+" · "+x.region+" — "+x.note;
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
          entries.push({url,title:event.title,subtitle:event.venue+" · "+event.municipality+" · dal "+dateLabel(event.local_date),city:event.municipality});
        }
        const footer=node("section","official-links");footer.append(node("h2",null,"Informazioni e biglietti"),official);grid.after(footer);
        if(!entries.length)status.textContent="Il programma sarà disponibile prossimamente.";
      }else{
        for(const found of festivalListings){
          const x=found.item;
          entries.push({url:"./directory.html?section=festival&id="+encodeURIComponent(x.id),
            title:x.name+(x.edition?" · "+x.edition:""),city:x.city,
            subtitle:x.city+" · "+x.region+" · "+(found.future.length?found.future.length+" date in programma":"Scopri il festival")});
        }
      }
      render();return;
    }
    const grouped=new Map();
    for(const e of data.performances){
      if(typeof e.title!=="string"||typeof e.venue!=="string"||!e.local_date)continue;
      const urls=window.OperaAtlasCatalog.urls(e);
      const url=section==="opere"?urls.work:urls.venue;
      if(!grouped.has(url))grouped.set(url,{url,title:section==="opere"?e.title:e.venue,subtitle:section==="opere"?e.composer||"":e.municipality+" · "+(e.region||"Italia"),city:e.municipality});
    }
    entries.push(...[...grouped.values()].sort((a,b)=>a.title.localeCompare(b.title,"it")));
    if(data.warning)status.textContent=data.warning;
    render();
  }catch {status.textContent="Catalogo momentaneamente non disponibile.";}
}
search.addEventListener("input",render);
initialize();