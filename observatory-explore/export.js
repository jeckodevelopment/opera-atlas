"use strict";
(function(root,factory){
 const api=factory(typeof module==="object"&&module.exports?require("./engine.js"):root.OperaPlusExplore,
 typeof module==="object"&&module.exports?require("./analysis.js"):root.OperaPlusExploreAnalysis);
 if(typeof module==="object"&&module.exports)module.exports=api;else root.OperaPlusExploreExport=api;
})(globalThis,(E,A)=>{
 const dims=["work","composer","year","season","region","city","venue","festival"];
 const defaults={preset:"custom",group:"work",metric:"performances",order:"auto",secondary:true,view:"productions"};
 const valid=(value,allowed,def)=>allowed.includes(value)?value:def;
 function encode(q,state){
  const p=new URLSearchParams();p.set("v","1");
  for(const k of dims)for(const value of [...new Set(q[k]||[])].sort())p.append(k,value);
  for(const k of ["from","to","type","temporal"])if(q[k]&&q[k]!=="all")p.set(k,q[k]);
  for(const k of ["preset","group","metric","order","view"])p.set(k,state[k]||defaults[k]);
  p.set("secondary",state.secondary===false?"0":"1");return p.toString();
 }
 function decode(search){
  const p=new URLSearchParams(search);if(!p.has("v"))return null;
  if(p.get("v")!=="1")throw Error("Versione del collegamento non supportata");
  const q=Object.fromEntries(dims.map(k=>[k,[...new Set(p.getAll(k))]]));
  for(const k of ["from","to"]){q[k]=p.get(k)||"";if(q[k]&&!/^\d{4}-\d{2}-\d{2}$/.test(q[k]))throw Error("Data nel collegamento non valida")}
  for(const [k,allowed] of [["type",["all","festival","nonfestival"]],["temporal",["all","past","future"]]]){
   q[k]=p.get(k)||"all";if(!allowed.includes(q[k]))throw Error("Filtro nel collegamento non valido");
  }
  const state={};
  for(const [k,allowed] of [["preset",Object.keys(A.presets)],["group",Object.keys(E.fields)],["metric",Object.keys(A.metrics)],["order",["auto","asc","desc","label"]],["view",["productions","performances"]]]){
   state[k]=p.get(k)||defaults[k];if(!allowed.includes(state[k]))throw Error("Impostazione del collegamento non valida: "+k);
  }
  state.secondary=p.get("secondary")!=="0";
  return {q,state};
 }
 function cell(value){
  let s=String(value??"");
  // Protect text cells against spreadsheet formula injection, including leading whitespace.
  if(typeof value!=="number"&&/^[\s\uFEFF]*[=+\-@]/.test(s))s="'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
 }
 function csv(columns,records){
  return "\uFEFF"+[columns.map(c=>cell(c[1])).join(";"),...records.map(r=>columns.map(([k])=>cell(r[k])).join(";"))].join("\r\n")+"\r\n";
 }
 const summaryColumns=[["id","ID gruppo"],["label","Gruppo"],...Object.entries(A.metrics)];
 const performanceColumns=[["id","ID recita"],["stagingId","ID produzione"],["date","Data"],["startsAt","Data e ora locale"],["title","Opera o programma"],["workIds","ID opere corrispondenti"],["works","Opere corrispondenti"],["venue","Teatro o sede"],["city","Città"],["region","Regione"],["season","Stagione"],["festivals","Festival"],["url","Scheda Atlas"],["sources","Fonti"]];
 const productionColumns=[["id","ID produzione"],["title","Opera o programma"],["works","Opere corrispondenti"],["venue","Teatro o sede"],["city","Città"],["region","Regione"],["season","Stagione"],["first","Prima recita nel periodo"],["last","Ultima recita nel periodo"],["performances","Recite"],["url","Scheda Atlas"]];
 const workText=works=>works.map(w=>w.title+(w.composer?" · "+w.composer:"")).join(" | ");
 function performanceRecords(rows,sourceById=new Map(),route=x=>x){
  return rows.map(r=>({...r,workIds:r.works.map(w=>w.id).join(" | "),works:workText(r.works),festivals:r.festivals.map(f=>f.name).join(" | "),url:route(r.url)||"",sources:(sourceById.get(r.id)||[]).join(" | ")}));
 }
 function productionRecords(rows,route=x=>x){
  const works=new Map();for(const r of rows){if(!works.has(r.stagingId))works.set(r.stagingId,new Map());for(const w of r.works)works.get(r.stagingId).set(w.id,w)}
  return E.productions(rows).map(p=>({...p,works:workText([...works.get(p.id).values()]),url:route(p.url)||""}));
 }
 return Object.freeze({encode,decode,csv,summaryColumns,performanceColumns,productionColumns,performanceRecords,productionRecords});
});
