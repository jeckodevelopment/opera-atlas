"use strict";
// Standalone statistics engine. No DOM, network or changes to the overview.
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 else root.OperaPlusExplore=api;
})(globalThis,()=>{
 const excluded=new Set(["cancelled","canceled","postponed"]);
 const day=/^\d{4}-\d{2}-\d{2}$/;
 const unique=a=>[...new Set(a.filter(Boolean))];
 const cityKey=r=>r.city&&r.region?JSON.stringify([r.region,r.city]):"";
 const fields=Object.freeze({
  work:"Opera",composer:"Compositore",venue:"Teatro o sede",city:"Città",region:"Regione",
  festival:"Festival",month:"Mese",year:"Anno solare",season:"Stagione"
 });
 function normalize(events,festivals){
  if(!Array.isArray(events)||!Array.isArray(festivals))throw Error("Catalogo o indice festival non valido");
  const membership=new Map(),seen=new Set(),out=[];
  for(const f of festivals){
   if(!f.id||!f.name||!Array.isArray(f.staging_ids))throw Error("Festival non valido");
   for(const id of f.staging_ids){
    if(!membership.has(id))membership.set(id,new Map());
    membership.get(id).set(f.id,f.name);
   }
  }
  for(const e of events){
   if(!e||!e.id||seen.has(e.id))throw Error("Identità recita assente o duplicata");
   seen.add(e.id);
   if(excluded.has(e.status))continue;
   if(!e.staging_id||!e.venue_id||!day.test(e.local_date||""))throw Error("Recita senza riferimenti canonici");
   const source=Array.isArray(e.program_components)?e.program_components:[{work_id:e.work_id,title:e.title,composer:e.composer}];
   const works=new Map();
   for(const w of source){
    // Unresolved components remain part of the event, but are not counted as canonical works.
    if(w.work_id&&w.title)works.set(w.work_id,{id:w.work_id,title:w.title,composer:w.composer||""});
   }
   const festivalList=[...(membership.get(e.staging_id)||new Map())].map(([id,name])=>({id,name}));
   out.push({id:e.id,stagingId:e.staging_id,venueId:e.venue_id,title:e.title||"",venue:e.venue||"",
    city:e.municipality||"",region:e.region||"",date:e.local_date,year:e.local_date.slice(0,4),
    month:e.local_date.slice(0,7),season:e.season||"",status:e.status||"",url:e.staging_url||"",
    startsAt:e.starts_at||null,works:[...works.values()],festivals:festivalList,
    unresolvedComponents:source.filter(w=>!w.work_id).length});
  }
  return out.sort((a,b)=>a.date.localeCompare(b.date)||a.id.localeCompare(b.id));
 }
 const values=(q,k)=>Array.isArray(q[k])?q[k].filter(Boolean):[];
 const matches=(q,k,v)=>!values(q,k).length||values(q,k).includes(v);
 function select(rows,q={},today){
  if(q.from&&!day.test(q.from)||q.to&&!day.test(q.to)||q.from&&q.to&&q.from>q.to)throw Error("Intervallo non valido");
  if(q.temporal&&q.temporal!=="all"&&!day.test(today||""))throw Error("Data odierna non valida");
  return rows.flatMap(r=>{
   if(!matches(q,"year",r.year)||!matches(q,"season",r.season)||!matches(q,"region",r.region)||
     !matches(q,"city",cityKey(r))||!matches(q,"venue",r.venueId)||
     q.from&&r.date<q.from||q.to&&r.date>q.to||
     q.temporal==="past"&&r.date>=today||q.temporal==="future"&&r.date<today||
     q.type==="festival"&&!r.festivals.length||q.type==="nonfestival"&&r.festivals.length||
     values(q,"festival").length&&!r.festivals.some(f=>matches(q,"festival",f.id)))return [];
   const works=r.works.filter(w=>matches(q,"work",w.id)&&matches(q,"composer",w.composer));
   if((values(q,"work").length||values(q,"composer").length)&&!works.length)return [];
   return [{...r,works,festivals:r.festivals.filter(f=>matches(q,"festival",f.id))}];
  });
 }
 function summary(rows){
  return {performances:unique(rows.map(r=>r.id)).length,productions:unique(rows.map(r=>r.stagingId)).length,
   works:unique(rows.flatMap(r=>r.works.map(w=>w.id))).length,
   composers:unique(rows.flatMap(r=>r.works.map(w=>w.composer))).length,
   venues:unique(rows.map(r=>r.venueId)).length,cities:unique(rows.map(cityKey)).length,
   regions:unique(rows.map(r=>r.region)).length,festivals:unique(rows.flatMap(r=>r.festivals.map(f=>f.id))).length};
 }
 function dimensions(r,key){
  switch(key){
   case "work":return r.works.map(w=>[w.id,w.title+(w.composer?" · "+w.composer:""),{...r,works:[w]}]);
   case "composer":return unique(r.works.map(w=>w.composer)).map(c=>[c,c,{...r,works:r.works.filter(w=>w.composer===c)}]);
   case "festival":return r.festivals.map(f=>[f.id,f.name,{...r,festivals:[f]}]);
   case "venue":return [[r.venueId,r.venue,r]];
   case "city":return [[cityKey(r),r.city+(r.region?" · "+r.region:""),r]];
   case "region":case "month":case "year":case "season":return [[r[key],r[key],r]];
   default:throw Error("Raggruppamento non valido");
  }
 }
 function group(rows,key){
  if(!Object.hasOwn(fields,key))throw Error("Raggruppamento non valido");
  const groups=new Map();
  for(const r of rows)for(const [id,label,entry] of dimensions(r,key)){
   if(!id)continue;
   if(!groups.has(id))groups.set(id,{id,label,rows:[]});
   groups.get(id).rows.push(entry);
  }
  return [...groups.values()].map(g=>({id:g.id,label:g.label,...summary(g.rows)}))
   .sort((a,b)=>["year","month","season"].includes(key)?a.id.localeCompare(b.id):
    b.performances-a.performances||a.label.localeCompare(b.label,"it")||a.id.localeCompare(b.id));
 }
 function productions(rows){
  const m=new Map();
  for(const r of rows){
   if(!m.has(r.stagingId))m.set(r.stagingId,{id:r.stagingId,title:r.title,venue:r.venue,region:r.region,city:r.city,season:r.season,url:r.url,dates:[],ids:new Set()});
   const p=m.get(r.stagingId);
   if(!p.ids.has(r.id)){p.ids.add(r.id);p.dates.push(r.date);}
  }
  return [...m.values()].map(({ids,dates,...p})=>({...p,performances:ids.size,first:dates.sort()[0],last:dates.at(-1)}))
   .sort((a,b)=>a.first.localeCompare(b.first)||a.id.localeCompare(b.id));
 }
 return Object.freeze({normalize,select,summary,group,productions,fields});
});
