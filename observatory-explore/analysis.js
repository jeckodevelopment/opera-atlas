"use strict";
(function(root,factory){
 const api=factory(typeof module==="object"&&module.exports?require("./engine.js"):root.OperaPlusExplore);
 if(typeof module==="object"&&module.exports)module.exports=api;
 else root.OperaPlusExploreAnalysis=api;
})(globalThis,E=>{
 const metrics=Object.freeze({performances:"Recite",productions:"Produzioni",venues:"Teatri e sedi",works:"Opere",composers:"Compositori",cities:"Città",regions:"Regioni",festivals:"Festival"});
 const presets=Object.freeze({
  custom:{label:"Ricerca personalizzata",group:null,description:"Scegli liberamente i filtri e il raggruppamento."},
  works:{label:"Le opere più rappresentate",group:"work",description:"Confronto delle opere per recite nel campione filtrato."},
  composers:{label:"I compositori più rappresentati",group:"composer",description:"Confronto dei compositori per recite nel campione filtrato."},
  regions:{label:"La lirica nelle regioni italiane",group:"region",description:"Confronto della programmazione per regione."},
  theatres:{label:"Il repertorio dei teatri",group:"venue",description:"Confronto delle sedi per numero di opere canoniche distinte."},
  evolution:{label:"Evoluzione del repertorio",group:"year",description:"Confronto per anno solare; seleziona più anni o tutti gli anni nei filtri."},
  rare:{label:"Le opere rare",group:"work",description:"Opere con 1–3 recite nel campione selezionato; non è una stima della rarità nazionale."}
 });
 const zero=()=>E.summary([]);
 const isChronological=key=>["month","year","season"].includes(key);
 const monthLabel=key=>{
  const [year,month]=key.split("-");
  const names=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"];
  return names[Number(month)-1]+" "+year;
 };
 function scope(rows,preset){
  if(!Object.hasOwn(presets,preset))throw Error("Ricerca predefinita non valida");
  if(preset!=="rare")return rows;
  const rare=new Set(E.group(rows,"work").filter(g=>g.performances>=1&&g.performances<=3).map(g=>g.id));
  return rows.flatMap(r=>{
   const works=r.works.filter(w=>rare.has(w.id));
   return works.length?[{...r,works}]:[];
  });
 }
 function compare(rows,key,metric="performances",order="auto"){
  if(!Object.hasOwn(metrics,metric))throw Error("Indicatore non valido");
  if(!["auto","asc","desc","label"].includes(order))throw Error("Ordinamento non valido");
  const groups=E.group(rows,key).map(g=>({...g,label:key==="month"?monthLabel(g.id):g.label}));
  const chronological=order==="auto"&&isChronological(key);
  return groups.sort((a,b)=>{
   if(chronological)return a.id.localeCompare(b.id);
   if(order==="label")return a.label.localeCompare(b.label,"it")||a.id.localeCompare(b.id);
   return (order==="asc"?a[metric]-b[metric]:b[metric]-a[metric])||a.label.localeCompare(b.label,"it")||a.id.localeCompare(b.id);
  });
 }
 function monthKeys(rows,q={}){
  // Draw zeros only for months inside the available data span or explicitly
  // chosen years/dates, never claim that an unobserved month had no activity.
  const actual=[...new Set(rows.map(r=>r.month))].sort();
  const years=Array.isArray(q.year)?q.year.filter(y=>/^\d{4}$/.test(y)):[];
  const min=q.from?.slice(0,7),max=q.to?.slice(0,7);
  if(years.length){
   return [...new Set(years)].sort().flatMap(y=>Array.from({length:12},(_,i)=>y+"-"+String(i+1).padStart(2,"0")))
    .filter(m=>(!min||m>=min)&&(!max||m<=max));
  }
  if(!actual.length)return [];
  const first=min||actual[0],last=max||actual.at(-1);
  const ordinal=s=>Number(s.slice(0,4))*12+Number(s.slice(5,7))-1;
  const start=ordinal(first),end=ordinal(last);
  // Bound expansion for unusually large user-selected date ranges.
  if(end<start||end-start>119)return actual;
  return Array.from({length:end-start+1},(_,i)=>{
   const n=start+i;return String(Math.floor(n/12)).padStart(4,"0")+"-"+String(n%12+1).padStart(2,"0");
  });
 }
 function monthly(rows,q={}){
  const groups=new Map(compare(rows,"month").map(g=>[g.id,g]));
  return monthKeys(rows,q).map(id=>groups.get(id)||{id,label:monthLabel(id),...zero()});
 }
 function chartSubset(groups,key,order="auto",limit=12){
  if(!Number.isSafeInteger(limit)||limit<1)throw Error("Limite non valido");
  return {items:groups.slice(0,limit),total:groups.length,chronological:order==="auto"&&isChronological(key)};
 }
 function barScale(items,keys){
  const max=Math.max(1,...items.flatMap(row=>keys.map(k=>row[k]||0)));
  return items.map(row=>({...row,bars:keys.map(k=>({key:k,value:row[k]||0,percent:100*(row[k]||0)/max}))}));
 }
 return Object.freeze({metrics,presets,scope,compare,monthly,chartSubset,barScale});
});
