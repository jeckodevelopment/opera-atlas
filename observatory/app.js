"use strict";
(() => {
const ROOT="https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/";
const FALLBACK="https://cdn.jsdelivr.net/gh/jeckodevelopment/opera-atlas@main/public/catalog/v2/";
const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat("it-IT");
let catalogue, rows=[];
const count=arr=>new Set(arr).size;
const key=(obj,id)=>obj.get(id);
const text=(node,value)=>{node.textContent=String(value)};
async function load(base){
 const manifest=await fetch(base+"manifest.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Manifest: "+r.status);return r.json()});
 if(manifest.schema_version!==2)throw Error("Versione catalogo non riconosciuta");
 const result={manifest};
 await Promise.all(["works","venues","stagings","performances"].map(async type=>{
   const meta=manifest.files[type];
   if(!meta || !/^data\/[a-z-]+\.[a-f0-9]{16}\.json$/.test(meta.path))throw Error("Manifest non valido: "+type);
   const response=await fetch(base+meta.path,{cache:"no-store"});
   if(!response.ok)throw Error("Dati "+type+": "+response.status);
   const bytes=await response.arrayBuffer();
   if(!globalThis.crypto?.subtle)throw Error("Verifica di integrità non disponibile");
   const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))).map(b=>b.toString(16).padStart(2,"0")).join("");
   if(digest!==meta.sha256)throw Error("Integrità catalogo: "+type);
   const data=JSON.parse(new TextDecoder().decode(bytes));
   if(data.schema_version!==2||!Array.isArray(data[type])||data[type].length!==meta.count)throw Error("Catalogo incompleto: "+type);
   result[type]=data[type];
 }));
 return result;
}
function mapRows(cat){
 const work=new Map(cat.works.map(x=>[x.id,x]));
 const venue=new Map(cat.venues.map(x=>[x.id,x]));
 const staging=new Map(cat.stagings.map(x=>[x.id,x]));
 const out=[],seen=new Set();
 for(const p of cat.performances){
   if(!p || seen.has(p.id))continue;
   seen.add(p.id);
   if(["cancelled","canceled","postponed"].includes(p.status))continue;
   const s=staging.get(p.staging_id);if(!s)continue;
   const w=work.get(s.work_id),v=venue.get(s.venue_id);
   if(!w||!v||!/^\d{4}-\d{2}-\d{2}$/.test(p.local_date||""))continue;
   out.push({id:p.id,date:p.local_date,year:p.local_date.slice(0,4),season:s.season||"Non indicata",region:v.region||"Non indicata",workId:w.id,work:w.title,composer:w.composer||"Non indicato",venueId:v.id,stagingId:s.id});
 }
 return out;
}
function populate(){
 const years=[...new Set(rows.map(x=>x.year))].sort().reverse(), seasons=[...new Set(rows.map(x=>x.season))].sort().reverse(), regions=[...new Set(rows.map(x=>x.region))].sort((a,b)=>a.localeCompare(b,"it"));
 for(const [id,values] of [["year",years],["season",seasons],["region",regions]]){
  for(const v of values){let o=document.createElement("option");o.value=v;o.textContent=v;$(id).append(o)}
 }
 // Default to the current calendar year in Italy, rather than guessing a season.
 const todayParts=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Rome",year:"numeric"}).formatToParts(new Date());
 const currentYear=todayParts.find(x=>x.type==="year")?.value;
 if(years.includes(currentYear))$("year").value=currentYear;
}
function frequencies(values){const m=new Map();for(const value of values)m.set(value,(m.get(value)||0)+1);return [...m].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0]),"it"))}
function bars(id,items,limit=10){
 const root=$(id);root.replaceChildren();if(!items.length){root.textContent="Nessun dato nel periodo selezionato";return}
 const max=Math.max(1,...items.map(x=>x[1]));
 for(const [name,n] of items.slice(0,limit)){
  const line=document.createElement("div");line.className="barrow";
  const label=document.createElement("span");label.textContent=name;label.title=name;
  const track=document.createElement("div");track.className="track";
  const fill=document.createElement("div");fill.className="fill";fill.style.width=(100*n/max)+"%";track.append(fill);
  const value=document.createElement("b");value.textContent=fmt.format(n);
  line.append(label,track,value);root.append(line);
 }
}
function list(id,items){const el=$(id);el.replaceChildren();for(const [name,n] of items.slice(0,5)){const li=document.createElement("li");const title=document.createElement("span");title.textContent=name;const number=document.createElement("span");number.textContent=fmt.format(n)+" recite";li.append(title,number);el.append(li)}if(!items.length)el.textContent="Nessun dato";}
function render(){
 const year=$("year").value, season=$("season").value, region=$("region").value;
 const selected=rows.filter(r=>(year==="all"||r.year===year)&&(season==="all"||r.season===season)&&(region==="all"||r.region===region));
 const countUnique=f=>count(selected.map(f));
 for(const [id,n] of [["k-perfs",selected.length],["k-venues",countUnique(x=>x.venueId)],["k-works",countUnique(x=>x.workId)],["k-stagings",countUnique(x=>x.stagingId)]])text($(id),fmt.format(n));
 const works=frequencies(selected.map(r=>r.work));
 bars("regions",frequencies(selected.map(r=>r.region)),20);
 bars("seasons",frequencies(selected.map(r=>r.season)).sort((a,b)=>a[0].localeCompare(b[0])),20);
 // Bars normalize to the largest chronological row to preserve meaningful proportions.
 bars("composers",frequencies(selected.map(r=>r.composer)).filter(x=>x[0]!=="Non indicato"),8);
 list("works",works);
 const rare=works.filter(x=>x[1]<=3).sort((a,b)=>a[1]-b[1]||a[0].localeCompare(b[0],"it"));
 const rareEl=$("rare-list");rareEl.replaceChildren();
 for(const [name,n] of rare.slice(0,30)){const span=document.createElement("span");span.className="pill";span.textContent=name+" · "+n;rareEl.append(span)}
 if(!rare.length)rareEl.textContent="Nessuna opera nel campione selezionato.";
 const hi=$("highlights");hi.replaceChildren();
 for(const [title,value,detail] of [["Recite osservate",fmt.format(selected.length),"Solo recite pubblicate nel catalogo"],["Repertorio",fmt.format(countUnique(x=>x.workId))+" opere","Titoli canonici distinti"],["Titoli rari",fmt.format(rare.length),"Da una a tre recite nel campione"]]){
  const div=document.createElement("div");div.className="highlight";const s=document.createElement("strong");s.textContent=title+" · "+value;const p=document.createElement("span");p.textContent=detail;div.append(s,p);hi.append(div);
 }
 const an=$("analysis");an.replaceChildren();const p=document.createElement("p");p.textContent="Compositori distinti nel campione: "+fmt.format(countUnique(x=>x.composer))+". La distribuzione per secolo sarà disponibile quando Atlas pubblicherà date di composizione affidabili.";an.append(p);
 $("download").onclick=()=>{
  const columns=["id","date","year","season","region","work","composer","venueId","stagingId"];
  const csv=[columns.join(";"),...selected.map(r=>columns.map(k=>'"'+String(r[k]??"").replace(/"/g,'""')+'"').join(";"))].join("\r\n");
  const blob=new Blob(["\ufeff",csv],{type:"text/csv;charset=utf-8"});const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download="osservatorio-opera-plus.csv";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
}
async function main(){
 try{
  try{catalogue=await load(ROOT)}catch(err){catalogue=await load(FALLBACK)}
  rows=mapRows(catalogue);populate();$("year").addEventListener("change",render);$("season").addEventListener("change",render);$("region").addEventListener("change",render);
  render();$("content").hidden=false;
  text($("status"),"");text($("updated"),"Versione dati: "+(catalogue.manifest.reviewed_on||"data non indicata")+". Recite annullate e rinviate escluse.");
 }catch(error){text($("status"),"Dati temporaneamente non disponibili. Nessuna statistica mostrata: "+error.message)}
}
main();
})();