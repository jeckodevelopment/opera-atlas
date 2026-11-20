"use strict";
const params=new URLSearchParams(location.search);
const section=["opere","teatri","festival"].includes(params.get("section"))?params.get("section"):"opere";
const config={opere:["Opere","Brevi presentazioni delle opere e tutte le produzioni recensite in Italia."],teatri:["Teatri","Sedi e prossimi spettacoli presenti nel catalogo Atlas."],festival:["Festival","Edizioni e programmi festivalieri verificati."]};
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
function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function normalize(s){return String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it");}
function render(){
  grid.replaceChildren();
  const q=normalize(search.value);
  const filtered=entries.filter(x=>normalize([x.title,x.subtitle].join(" ")).includes(q));
  for(const item of filtered){
    const card=node("article","directory-card");
    const heading=node("h2"),link=node("a",null,item.title);link.href=item.url;heading.append(link);
    card.append(heading,node("p",null,item.subtitle));
    const action=node("a","detail-link",section==="opere"?"Vedi dove è in scena":"Consulta il programma");
    action.href=item.url;card.append(action);grid.append(card);
  }
  if(!filtered.length){
    grid.append(node("p","empty",section==="festival"?"Nessun festival con edizione e programma verificati nel feed Atlas.":"Nessun risultato corrispondente alla ricerca."));
  }
  status.textContent=filtered.length+" risultati";
}
async function initialize(){
  try {
    const data=await window.OperaAtlasCatalog.load();
    if(section==="festival"){
      // Festival entities need edition/venue relationships; never infer them from venue names.
      render();return;
    }
    const grouped=new Map();
    for(const e of data.performances){
      if(typeof e.title!=="string"||typeof e.venue!=="string"||!e.local_date)continue;
      const urls=window.OperaAtlasCatalog.urls(e);
      const url=section==="opere"?urls.work:urls.venue;
      if(!grouped.has(url))grouped.set(url,{url,title:section==="opere"?e.title:e.venue,subtitle:section==="opere"?e.composer||"Compositore non disponibile":e.municipality+" · "+(e.region||"Italia")});
    }
    entries.push(...[...grouped.values()].sort((a,b)=>a.title.localeCompare(b.title,"it")));
    if(data.warning)status.textContent=data.warning;
    render();
  }catch {status.textContent="Catalogo momentaneamente non disponibile.";}
}
search.addEventListener("input",render);
initialize();