"use strict";
(() => {
const ROOT="https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/";
const FALLBACK="https://cdn.jsdelivr.net/gh/jeckodevelopment/opera-atlas@main/public/catalog/v2/";
const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat("it-IT");
let catalogue, rows=[], editorials=null;
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
   out.push({id:p.id,date:p.local_date,year:p.local_date.slice(0,4),season:s.season||"Non indicata",region:v.region||"Non indicata",city:v.city||"Non indicata",workId:w.id,work:w.title,composer:w.composer||"Non indicato",venueId:v.id,venue:v.display_name||v.name||"Sede non indicata",stagingId:s.id});
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
const MONTHS=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"];
function drawMonths(selected,year){
 const counts=Array(12).fill(0);
 for(const row of selected)counts[Number(row.date.slice(5,7))-1]++;
 const max=Math.max(1,...counts),root=$("months");root.replaceChildren();
 for(let month=0;month<12;month++){
  const entry=document.createElement("div");entry.className="month-column";
  const number=document.createElement("span");number.className="month-value";number.textContent=fmt.format(counts[month]);
  const track=document.createElement("div");track.className="month-track";
  const bar=document.createElement("div");bar.className="month-bar";bar.style.height=(100*counts[month]/max)+"%";track.append(bar);
  const label=document.createElement("span");label.className="month-label";label.textContent=MONTHS[month];
  entry.append(number,track,label);root.append(entry);
 }
 root.setAttribute("aria-label",MONTHS.map((m,i)=>m+": "+counts[i]+" recite").join("; "));
 const caption=year==="all"?"Tutti gli anni presenti nel catalogo (sommati per mese)":"Anno solare "+year;
 text($("months-caption"),caption+" · Solo recite rilevate: zero non equivale ad assenza di attività.");
}

const WEEKDAYS=["Lun","Mar","Mer","Gio","Ven","Sab","Dom"];
function groupedCounts(records,keyFn){
 const groups=new Map();
 for(const row of records){const [key,label]=keyFn(row);if(!key)continue;
  const prev=groups.get(key);if(prev)prev.count++;else groups.set(key,{name:label,count:1});
 }
 return [...groups.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,"it")).map(item=>[item.name,item.count]);
}
function ranked(id,records,limit=10){
 const root=$(id);root.replaceChildren();
 for(const [name,n] of records.slice(0,limit)){
  const item=document.createElement("li"),label=document.createElement("span"),count=document.createElement("span");
  label.textContent=name;count.textContent=fmt.format(n)+" recite";
  item.append(label,count);root.append(item);
 }
 if(records.length===0){const empty=document.createElement("li");empty.className="rank-empty";empty.textContent="Nessun dato nel campione selezionato.";root.append(empty)}
}
function renderInsights(selected){
 const weekdays=Array(7).fill(0);
 for(const r of selected){
  const [y,m,d]=r.date.split("-").map(Number);
  const index=(new Date(Date.UTC(y,m-1,d)).getUTCDay()+6)%7;
  weekdays[index]++;
 }
 const weekCounts=WEEKDAYS.map((name,index)=>[name,weekdays[index]]);
 // bars normalizes against the maximum even when the input is chronological.
 bars("weekday-chart",weekCounts,7);
 ranked("venue-ranking",groupedCounts(selected,r=>[r.venueId,r.venue]));
 const diversity=new Map();
 for(const row of selected){
  if(!diversity.has(row.region))diversity.set(row.region,new Set());
  diversity.get(row.region).add(row.workId);
 }
 const diverse=[...diversity].map(([region,ids])=>[region,ids.size])
  .sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],"it"));
 bars("diversity-chart",diverse,20);
 ranked("regional-works",groupedCounts(selected,r=>[JSON.stringify([r.region,r.workId]),r.work+" · "+r.region]));
 ranked("regional-composers",groupedCounts(selected,r=>r.composer==="Non indicato"?[null,null]:[JSON.stringify([r.region,r.composer]),r.composer+" · "+r.region]));
 ranked("staging-ranking",groupedCounts(selected,r=>[r.stagingId,r.work+" · "+r.venue+" · "+r.season]));
}


function circulation(selected){
 const groups=new Map();
 for(const r of selected){
  if(!groups.has(r.workId))groups.set(r.workId,{
   work:r.work,composer:r.composer,venues:new Set(),cities:new Set(),regions:new Set()
  });
  const g=groups.get(r.workId);
  g.venues.add(r.venueId);
  if(r.city!=="Non indicata")g.cities.add(JSON.stringify([r.region,r.city]));
  if(r.region!=="Non indicata")g.regions.add(r.region);
 }
 const ordered=[...groups.values()].sort((a,b)=>
  b.venues.size-a.venues.size||b.cities.size-a.cities.size||
  b.regions.size-a.regions.size||a.work.localeCompare(b.work,"it"));
 const root=$("circulation-rows");root.replaceChildren();
 if(!ordered.length){
  const tr=document.createElement("tr"),td=document.createElement("td");
  td.colSpan=4;td.textContent="Nessuna opera nel campione selezionato.";
  tr.append(td);root.append(tr);return;
 }
 for(const item of ordered.slice(0,8)){
  const tr=document.createElement("tr");
  const name=document.createElement("td"),title=document.createElement("strong");
  title.textContent=item.work;const composer=document.createElement("small");
  composer.textContent=item.composer;
  name.append(title,composer);tr.append(name);
  for(const value of [item.venues.size,item.cities.size,item.regions.size]){
   const cell=document.createElement("td");
   cell.textContent=fmt.format(value);tr.append(cell);
  }
  root.append(tr);
 }
}
async function loadEditorial(base){
 const response=await fetch(base.replace("/v2/","/")+"work-editorial.json",{cache:"no-store"});
 if(!response.ok)throw Error("Schede editoriali non disponibili: "+response.status);
 const result=await response.json();
 if(result.schema_version!==1||!Array.isArray(result.works))throw Error("Formato schede editoriali non valido");
 const validIds=new Set(catalogue.works.map(w=>w.id));
 const entries=new Map();
 for(const w of result.works){
  if(!validIds.has(w.work_id)||entries.has(w.work_id))continue;
  const h=w.history;
  if(!h||!Number.isInteger(h.premiere_year)||h.premiere_year<1600||h.premiere_year>2100)continue;
  if(!Array.isArray(h.sources)||h.sources.length===0)continue;
  entries.set(w.work_id,{work:w,history:h});
 }
 return entries;
}
function localToday(){
 return new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
}
function premieres(selected,year){
 const root=$("premiere-items");root.replaceChildren();
 if(!editorials){
  text($("premiere-total"),"—");
  text($("premiere-summary-label"),"Schede editoriali temporaneamente non disponibili");
  text($("premiere-context"),"Nessun numero viene mostrato senza le fonti verificate.");
  return;
 }
 const workIds=new Set(selected.map(r=>r.workId));
 const applicable=[...editorials.entries()].filter(([id,e])=>workIds.has(id)&&(year==="all"||String(e.history.premiere_year)===year))
 .map(([,e])=>e).sort((a,b)=>b.history.premiere_year-a.history.premiere_year||a.work.title.localeCompare(b.work.title,"it"));
 text($("premiere-total"),fmt.format(applicable.length));
 text($("premiere-summary-label"),year==="all"?"Opere censite con anno di prima assoluta verificato":"Opere censite con prima assoluta attribuita al "+year);
 const today=localToday();
 const exact=applicable.filter(e=>typeof e.history.premiere_date==="string"&&/^\\d{4}-\\d{2}-\\d{2}$/.test(e.history.premiere_date));
 const past=exact.filter(e=>e.history.premiere_date<=today);
 const upcoming=exact.filter(e=>e.history.premiere_date>today);
 const yearOnly=applicable.length-exact.length;
 const details=[];
 if(past.length)details.push(past.length+" con data già trascorsa");
 if(upcoming.length)details.push(upcoming.length+" con data futura");
 if(yearOnly)details.push(yearOnly+" con solo anno verificato");
 text($("premiere-context"),(details.join(" · ")||"Nessuna prima assoluta registrata nel campione.")+
  ". Il conteggio non equivale a prime già avvenute quando manca la data esatta.");
 if(!applicable.length){
  const p=document.createElement("p");p.textContent="Nessuna opera con prima assoluta documentata nei filtri scelti.";root.append(p);return;
 }
 for(const e of applicable.slice(0,6)){
  const h=e.history,entry=document.createElement("div");entry.className="premiere-entry";
  const name=document.createElement("strong");name.textContent=e.work.title;
  const detail=document.createElement("span");
  const date=typeof h.premiere_date==="string"&&/^\\d{4}-\\d{2}-\\d{2}$/.test(h.premiere_date)
    ?h.premiere_date:h.premiere_year;
  const place=[h.premiere_city,h.premiere_venue].filter(Boolean).join(" · ");
  detail.textContent=e.work.composer+" · "+date+(place?" · "+place:"");
  entry.append(name,detail);root.append(entry);
 }
}

function render(){
 const year=$("year").value, season=$("season").value, region=$("region").value;
 const selected=rows.filter(r=>(year==="all"||r.year===year)&&(season==="all"||r.season===season)&&(region==="all"||r.region===region));
 const countUnique=f=>count(selected.map(f));
 for(const [id,n] of [["k-perfs",selected.length],["k-venues",countUnique(x=>x.venueId)],["k-works",countUnique(x=>x.workId)],["k-stagings",countUnique(x=>x.stagingId)]])text($(id),fmt.format(n));
 drawMonths(selected,year);
 renderInsights(selected);
 circulation(selected);
 premieres(selected,year);
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
  rows=mapRows(catalogue);
  try{editorials=await loadEditorial(ROOT)}catch(_err){try{editorials=await loadEditorial(FALLBACK)}catch(_fallback){editorials=null}}
  populate();$("year").addEventListener("change",render);$("season").addEventListener("change",render);$("region").addEventListener("change",render);
  render();$("content").hidden=false;
  text($("status"),"");text($("updated"),"Versione dati: "+(catalogue.manifest.reviewed_on||"data non indicata")+". Recite annullate e rinviate escluse.");
 }catch(error){text($("status"),"Dati temporaneamente non disponibili. Nessuna statistica mostrata: "+error.message)}
}
main();
})();