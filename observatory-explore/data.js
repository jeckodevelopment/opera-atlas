"use strict";
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 else root.OperaPlusExploreData=api;
})(globalThis,()=>{
 const BASES=[
  "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/",
  "https://cdn.jsdelivr.net/gh/jeckodevelopment/opera-atlas@main/public/catalog/"
 ];
 async function json(url,fetcher){
  const response=await fetcher(url,{cache:"no-store"});
  if(!response.ok)throw Error("HTTP "+response.status);
  return response.json();
 }
 function validateCompanions(data,programs,festivals){
  if(programs?.schema_version!==1||!Array.isArray(programs.programs)||
     festivals?.schema_version!==1||!Array.isArray(festivals.festivals))throw Error("Indici complementari non validi");
  const expected=new Map();
  for(const p of programs.programs){
   if(!p.id||!Array.isArray(p.performances)||!Array.isArray(p.components))throw Error("Programma non valido");
   for(const r of p.performances){
    if(!r.id||expected.has(r.id))throw Error("Recita composta duplicata");
    expected.set(r.id,[p.id,r.local_date]);
   }
  }
  const actual=data.performances.filter(r=>r.program_id);
  if(actual.length!==expected.size||actual.some(r=>{
   const match=expected.get(r.id);
   return !match||match[0]!==r.program_id||match[1]!==r.local_date;
  }))throw Error("Indice programmi non allineato");
  const stages=new Set(data.performances.map(r=>r.staging_id)),ids=new Set();
  for(const f of festivals.festivals){
   if(!f?.id||ids.has(f.id)||!f.name||!Array.isArray(f.staging_ids)||
      f.staging_ids.some(id=>!stages.has(id)))throw Error("Indice festival non allineato");
   ids.add(f.id);
  }
  return festivals.festivals;
 }
 async function load(client,fetcher=globalThis.fetch){
  if(!client||typeof client.load!=="function")throw Error("Client Atlas non disponibile");
  const data=await client.load();
  // The Atlas client validates the v2 manifest and SHA-256 channels.
  // Its local snapshot is intentionally not accepted for statistics.
  if(data?.source!=="github"||!Array.isArray(data.performances)||!Array.isArray(data.works)||
     !/^\d{4}-\d{2}-\d{2}$/.test(data.reviewed_on||""))throw Error("Catalogo remoto verificato non disponibile");
  for(const base of BASES){
   try{
    const [programs,festivals]=await Promise.all([
     json(base+"programs.json",fetcher),json(base+"v2/festival-directory.json",fetcher)
    ]);
    return {data,festivals:validateCompanions(data,programs,festivals),mirror:base===BASES[1]};
   }catch(_error){/* Try another published endpoint, never a partial sample. */}
  }
  throw Error("Indici programmi o festival non disponibili o non allineati");
 }
 function today(now=new Date()){
  const parts=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(now);
  return ["year","month","day"].map(k=>parts.find(p=>p.type===k).value).join("-");
 }
 const dimensions=["work","composer","year","season","region","city","venue","festival"];
 const labels={work:"Opera",composer:"Compositore",year:"Anno solare",season:"Stagione",region:"Regione",city:"Città",venue:"Teatro o sede",festival:"Festival"};
 function options(rows,key,regions=[]){
  const m=new Map();
  const add=(id,label)=>{if(id&&label)m.set(id,label)};
  for(const r of rows){
   if((key==="city"||key==="venue")&&regions.length&&!regions.includes(r.region))continue;
   if(key==="work")r.works.forEach(w=>add(w.id,w.title+(w.composer?" · "+w.composer:"")));
   else if(key==="composer")r.works.forEach(w=>add(w.composer,w.composer));
   else if(key==="festival")r.festivals.forEach(f=>add(f.id,f.name));
   else if(key==="city"){if(r.city&&r.region)add(JSON.stringify([r.region,r.city]),r.city+" · "+r.region)}
   else if(key==="venue")add(r.venueId,r.venue+((r.organizerCity||r.city)?" · "+(r.organizerCity||r.city):""));
   else add(r[key],r[key]);
  }
  return [...m].map(([id,label])=>({id,label})).sort((a,b)=>
   ["year","season"].includes(key)?b.label.localeCompare(a.label,"it"):a.label.localeCompare(b.label,"it")||a.id.localeCompare(b.id));
 }
 function atlasRoute(path){
  return typeof path==="string"&&/^\/(?:[a-z0-9-]+\/)+$/.test(path)?"https://opera.plus/atlas"+path:null;
 }
 function sourceUrl(value){
  try{const url=new URL(value);return url.protocol==="https:"||url.protocol==="http:"?url.href:null}catch{return null}
 }
 function sortRows(rows,key,descending=false){
  return [...rows].sort((a,b)=>{
   const x=a[key],y=b[key];
   const order=typeof x==="number"&&typeof y==="number"?x-y:String(x??"").localeCompare(String(y??""),"it");
   return (descending?-order:order)||String(a.id).localeCompare(String(b.id));
  });
 }
 return Object.freeze({load,validateCompanions,today,options,dimensions,labels,atlasRoute,sourceUrl,sortRows});
});
