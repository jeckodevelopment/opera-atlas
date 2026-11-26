"use strict";
(()=>{
 const $=id=>document.getElementById(id),E=globalThis.OperaPlusExplore,D=globalThis.OperaPlusExploreData,A=globalThis.OperaPlusExploreAnalysis,X=globalThis.OperaPlusExploreExport,P=globalThis.OperaPlusExplorePdf;
 const fmt=new Intl.NumberFormat("it-IT");
 const metrics={productions:"Produzioni",performances:"Recite rilevate",works:"Opere",composers:"Compositori",venues:"Teatri e sedi",cities:"Città",regions:"Regioni",festivals:"Festival"};
 const pageSize=30;
 let rows=[],selected=[],rawById=new Map(),workById=new Map(),page=0,sortKey="first",descending=false,appliedQuery={},appliedPreset="custom",reportGroups=[],reportMonths=[],reportRegions=[],reviewedOn="",appliedOn="";
 const chosen=Object.fromEntries(D.dimensions.map(key=>[key,new Set()]));
 const controls=new Map();
 const node=(tag,value,cls)=>{const e=document.createElement(tag);if(value!=null)e.textContent=value;if(cls)e.className=cls;return e};
 const date=s=>s?s.split("-").reverse().join("/"):"—";
 const clock=s=>s&&/^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(s)?s.slice(11,16):"Orario da confermare";
 const normalize=s=>s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it");
 function refreshOptions(key){
  const control=controls.get(key),opts=D.options(rows,key,[...chosen.region]);
  const allowed=new Set(opts.map(o=>o.id));
  for(const id of chosen[key])if(!allowed.has(id))chosen[key].delete(id);
  control.options=opts;
  drawOptions(key);
 }
 function drawOptions(key){
  const c=controls.get(key),query=normalize(c.search.value.trim());
  c.list.replaceChildren();
  for(const o of c.options){
   if(query&&!normalize(o.label).includes(query))continue;
   const label=node("label"),input=node("input");input.type="checkbox";input.checked=chosen[key].has(o.id);
   input.addEventListener("change",()=>{
    if(input.checked)chosen[key].add(o.id);else chosen[key].delete(o.id);
    updateSummary(key);
    if(key==="region"){refreshOptions("city");refreshOptions("venue")}
   });
   label.append(input,node("span",o.label));c.list.append(label);
  }
  if(!c.list.childElementCount)c.list.append(node("p","Nessun valore disponibile"));
  updateSummary(key);
 }
 function updateSummary(key){
  const c=controls.get(key),active=c.options.filter(o=>chosen[key].has(o.id));
  c.summary.textContent=D.labels[key]+": "+(active.length===0?"Tutti":active.length===1?active[0].label:active.length+" selezionati");
 }
 function initFilters(){
  for(const key of D.dimensions){
   const field=node("div",null,"explore-field"),details=node("details"),summary=node("summary");
   const panel=node("div",null,"explore-options"),search=node("input"),list=node("div",null,"explore-choices");
   search.type="search";search.placeholder="Cerca…";search.setAttribute("aria-label","Cerca "+D.labels[key].toLowerCase());
   list.setAttribute("role","group");list.setAttribute("aria-label",D.labels[key]);
   search.addEventListener("input",()=>drawOptions(key));
   details.addEventListener("toggle",()=>{if(details.open)for(const [other,c] of controls)if(other!==key)c.details.open=false});
   panel.append(search,list);details.append(summary,panel);field.append(details);$("dimensions").append(field);
   controls.set(key,{details,summary,search,list,options:[]});refreshOptions(key);
  }
  const year=D.today().slice(0,4);
  if(controls.get("year").options.some(o=>o.id===year)){chosen.year.add(year);drawOptions("year")}
 }
 function readQuery(){
  const q=Object.fromEntries(D.dimensions.map(k=>[k,[...chosen[k]]]));
  for(const k of ["from","to","type","temporal"])q[k]=$("query").elements.namedItem(k).value;
  return q;
 }
 function context(q){
  const result=[];
  for(const k of D.dimensions){
   if(q[k].length){const labels=new Map(controls.get(k).options.map(o=>[o.id,o.label]));result.push(D.labels[k]+": "+q[k].map(id=>labels.get(id)||id).join(", "))}
  }
  if(q.from||q.to)result.push("Periodo: "+(q.from?date(q.from):"inizio")+" – "+(q.to?date(q.to):"fine"));
  if(q.type!=="all")result.push(q.type==="festival"?"Festival":"Non associate a festival");
  if(q.temporal!=="all")result.push(q.temporal==="past"?"Date trascorse":"Da oggi in poi");
  return result.join(" · ")||"Tutto il catalogo disponibile";
 }
 function query(){
  const q=readQuery();
  try{
   const filtered=E.select(rows,q,D.today());
   const preset=$("preset").value;
   const next=A.scope(filtered,preset);
   $("filter-error").textContent="";
   selected=next;appliedQuery=q;appliedPreset=preset;appliedOn=D.today();page=0;sortKey=$("view").value==="productions"?"first":"date";descending=false;
   for(const c of controls.values())c.details.open=false;
   $("query-context").textContent=context(q)+(preset==="rare"?" · Opere con 1–3 recite nel campione filtrato":"");
   const counts=E.summary(selected);
   $("metrics").replaceChildren(...Object.entries(metrics).map(([key,label])=>{
    const item=node("article");item.append(node("strong",fmt.format(counts[key])),node("p",label));return item;
   }));
   drawTable();drawAnalysis();syncUrl();
  }catch(err){$("filter-error").textContent=err.message}
 }
 function link(label,url){
  if(!url)return node("span",label);
  const a=node("a",label);a.href=url;return a;
 }
 function workLinks(container,works){
  if(!works.length)return;
  const line=node("small");
  for(const w of works){
   const canonical=workById.get(w.id);
   const slug=canonical?.route_slug||canonical?.slug;
   line.append(link(w.title+(w.composer?" · "+w.composer:""),D.atlasRoute(slug?"/opere/"+slug+"/":null)));
  }
  container.append(line);
 }
 function sources(container,r){
  const event=rawById.get(r.id);
  const urls=[...new Set((Array.isArray(event?.sources)?event.sources:[]).map(D.sourceUrl).filter(Boolean))];
  if(urls.length){
   const line=node("small");urls.forEach((url,i)=>{const a=link("Fonte "+(i+1),url);a.target="_blank";a.rel="noopener noreferrer";line.append(a)});container.append(line);
  }
 }
 function productions(){
  const map=new Map();
  for(const r of selected){
   if(!map.has(r.stagingId))map.set(r.stagingId,new Map());
   for(const w of r.works)map.get(r.stagingId).set(w.id,w);
  }
  return E.productions(selected).map(p=>({...p,works:[...map.get(p.id).values()]}));
 }
 const productionColumns=[["title","Opera o programma"],["venue","Teatro o sede"],["city","Città"],["region","Regione"],["season","Stagione"],["first","Prima recita nel periodo"],["last","Ultima recita nel periodo"],["performances","Recite"]];
 const performanceColumns=[["date","Data"],["startsAt","Ora"],["title","Opera o programma"],["venue","Teatro o sede"],["city","Città"],["region","Regione"],["season","Stagione"],["festivals","Festival"]];
 function drawTable(){
  const prod=$("view").value==="productions",columns=prod?productionColumns:performanceColumns;
  const records=prod?productions():selected.map(r=>({...r,festivals:r.festivals.map(f=>f.name).join(" · ")}));
  const ordered=D.sortRows(records,sortKey,descending),pages=Math.max(1,Math.ceil(ordered.length/pageSize));
  page=Math.min(page,pages-1);
  const tr=node("tr");
  for(const [key,label] of columns){
   const th=node("th"),b=node("button",label+(sortKey===key?(descending?" ↓":" ↑"):""));b.type="button";th.scope="col";
   if(sortKey===key)th.setAttribute("aria-sort",descending?"descending":"ascending");
   b.addEventListener("click",()=>{descending=sortKey===key?!descending:false;sortKey=key;page=0;drawTable();$("table-head").querySelectorAll("button")[columns.findIndex(c=>c[0]===key)].focus()});
   th.append(b);tr.append(th);
  }
  $("table-head").replaceChildren(tr);
  const body=$("table-body");body.replaceChildren();
  for(const record of ordered.slice(page*pageSize,(page+1)*pageSize)){
   const row=node("tr");
   for(const [key] of columns){
    const td=node("td");
    if(key==="title"){
     td.append(link(record.title,D.atlasRoute(record.url)));workLinks(td,record.works);
     if(!prod)sources(td,record);
    }else if(["date","first","last"].includes(key))td.textContent=date(record[key]);
    else if(key==="startsAt")td.textContent=clock(record[key]);
    else if(key==="performances")td.textContent=fmt.format(record[key]);
    else td.textContent=record[key]||"—";
    row.append(td);
   }
   body.append(row);
  }
  if(!ordered.length){const r=node("tr"),td=node("td","Nessun risultato per i filtri selezionati. Prova a modificare la ricerca.");td.colSpan=columns.length;r.append(td);body.append(r)}
  $("table-count").textContent=ordered.length?fmt.format(page*pageSize+1)+"–"+fmt.format(Math.min((page+1)*pageSize,ordered.length))+" di "+fmt.format(ordered.length):"0 risultati";
  $("previous").disabled=page===0;$("next").disabled=page>=pages-1;
 }
 function setOptions(id,items,initial){
  const el=$(id);el.replaceChildren();
  for(const [key,label] of items){const o=node("option",label);o.value=key;el.append(o)}
  el.value=initial;
 }
 function configurePreset(){
  const key=$("preset").value,preset=A.presets[key];
  $("preset-description").textContent=preset.description;
  if(preset.group){
   $("group-by").value=preset.group;
   $("group-metric").value=key==="theatres"?"works":"performances";
   $("group-order").value=key==="rare"?"asc":"auto";
   $("compare-productions").checked=key!=="theatres";
  }
 }
 function initAnalysis(){
  setOptions("preset",Object.entries(A.presets).map(([id,p])=>[id,p.label]),"custom");
  setOptions("group-by",Object.entries(E.fields),"work");
  setOptions("group-metric",Object.entries(A.metrics),"performances");
  configurePreset();
  $("preset").addEventListener("change",()=>{configurePreset();query()});
  for(const id of ["group-by","group-metric","group-order","compare-productions"]){
   $(id).addEventListener("change",()=>{drawAnalysis();syncUrl()});
  }
 }
 function chart(id,groups,keys,emptyMessage){
  const root=$(id);root.replaceChildren();
  if(!groups.length){root.append(node("p",emptyMessage||"Nessun dato nel campione selezionato."));return}
  for(const item of A.barScale(groups,keys)){
   const row=node("div",null,"explore-chart-row"),series=node("div",null,"explore-chart-series");
   row.setAttribute("role","listitem");
   row.append(node("span",item.label,"explore-chart-label"));
   for(const [i,bar] of item.bars.entries()){
    const line=node("div",null,"explore-bar-line"),track=node("div",null,"explore-bar-track");
    const fill=node("div",null,"explore-bar-fill"+(i?" secondary":""));
    track.setAttribute("aria-hidden","true");fill.style.width=bar.percent+"%";track.append(fill);
    const count=node("strong",fmt.format(bar.value),"explore-bar-number");
    count.setAttribute("aria-label",A.metrics[bar.key]+": "+fmt.format(bar.value));
    line.append(track,count);series.append(line);
   }
   row.append(series);root.append(row);
  }
 }
 function limitNote(subset,base){
  return base+(subset.total>subset.items.length?" Grafico: primi "+subset.items.length+" di "+subset.total+" gruppi; tabella completa disponibile.":"");
 }
 function drawAnalysis(){
  const group=$("group-by").value,metric=$("group-metric").value,order=$("group-order").value;
  const secondary=$("compare-productions");secondary.disabled=metric==="productions";
  const keys=secondary.checked&&!secondary.disabled?[metric,"productions"]:[metric];
  const monthly=A.monthly(selected,appliedQuery);
  const months=A.chartSubset(monthly,"month","auto",24);
  chart("monthly-chart",months.items,["performances"]);
  $("monthly-note").textContent="Zero indica nessuna recita rilevata con questi filtri, non assenza di attività."+
   (months.total>months.items.length?" Mostrati i primi 24 di "+months.total+" mesi; usa il raggruppamento Mese per il dettaglio.":"");
  const region=A.chartSubset(A.compare(selected,"region"),"region","auto",20);
  chart("region-chart",region.items,["performances"]);
  $("region-note").textContent="Solo regioni con recite rilevate nel campione filtrato."+
   (region.total>region.items.length?" Mostrate "+region.items.length+" di "+region.total+".":"");
  const groups=group==="month"&&order==="auto"?monthly:A.compare(selected,group,metric,order);
  // For month, use the same explicit zero buckets regardless of ordering.
  const monthGroups=group==="month"&&order!=="auto"?[...monthly].sort((a,b)=>
   order==="label"?a.label.localeCompare(b.label,"it")||a.id.localeCompare(b.id):
    (order==="asc"?a[metric]-b[metric]:b[metric]-a[metric])||a.id.localeCompare(b.id)):groups;
  reportGroups=monthGroups;reportMonths=monthly;reportRegions=A.compare(selected,"region");
  const subset=A.chartSubset(monthGroups,group,order,12);
  const legend=$("comparison-legend");legend.replaceChildren();
  for(const [i,key] of keys.entries()){
   const label=node("span"),swatch=node("i",null,i?"secondary":"");swatch.setAttribute("aria-hidden","true");
   label.append(swatch,node("span",A.metrics[key]));legend.append(label);
  }
  chart("comparison-chart",subset.items,keys);
  $("comparison-note").textContent=limitNote(subset,"Conteggi distinti per gruppo. Le barre condividono la stessa scala.");
  const columns=[["label",E.fields[group]],...Object.entries(A.metrics)];
  const head=node("tr");for(const [,label] of columns){const th=node("th",label);th.scope="col";head.append(th)}
  $("group-head").replaceChildren(head);
  const body=$("group-body");body.replaceChildren();
  for(const item of monthGroups){
   const tr=node("tr");
   for(const [key] of columns)tr.append(node("td",key==="label"?item.label:fmt.format(item[key])));
   body.append(tr);
  }
  if(!monthGroups.length){const tr=node("tr"),td=node("td","Nessun gruppo nel campione selezionato.");td.colSpan=columns.length;tr.append(td);body.append(tr)}
 }
 function state(){
  return {preset:appliedPreset,group:$("group-by").value,metric:$("group-metric").value,order:$("group-order").value,secondary:$("compare-productions").checked,view:$("view").value};
 }
 function sharedUrl(){const u=new URL(location.href);u.search=X.encode(appliedQuery,state());u.hash="";return u.href}
 function syncUrl(){
  if(!appliedOn)return;
  const u=sharedUrl();history.replaceState(null,"",u);$("share-url").value=u;
 }
 function restoreUrl(){
  const saved=X.decode(location.search);if(!saved)return;
  const {q,state:st}=saved;
  // Validate before altering controls. A disappeared identity must never broaden a shared query.
  for(const key of D.dimensions){
   const known=new Set(D.options(rows,key,key==="city"||key==="venue"?q.region:[]).map(o=>o.id));
   if(q[key].some(id=>!known.has(id)))throw Error("Il collegamento contiene filtri non più disponibili: "+D.labels[key]);
  }
  E.select(rows,q,D.today());
  for(const key of D.dimensions){chosen[key].clear();q[key].forEach(id=>chosen[key].add(id))}
  for(const key of D.dimensions)refreshOptions(key);
  for(const k of ["from","to","type","temporal"])$("query").elements.namedItem(k).value=q[k];
  $("preset").value=st.preset;configurePreset();
  $("group-by").value=st.group;$("group-metric").value=st.metric;$("group-order").value=st.order;
  $("compare-productions").checked=st.secondary;$("view").value=st.view;
 }
 function download(blob,name){
  const url=URL.createObjectURL(blob),a=node("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
 }
 function csvDownload(columns,records,name){
  download(new Blob([X.csv(columns,records)],{type:"text/csv;charset=utf-8"}),name);
 }
 function initExports(){
  $("export-summary").addEventListener("click",()=>csvDownload(X.summaryColumns,reportGroups,"opera-plus-esplora-sintesi.csv"));
  $("export-detail").addEventListener("click",()=>{
   const prod=$("view").value==="productions";
   const sourceMap=new Map([...rawById].map(([id,r])=>[id,(r.sources||[]).map(D.sourceUrl).filter(Boolean)]));
   csvDownload(prod?X.productionColumns:X.performanceColumns,prod?X.productionRecords(selected,D.atlasRoute):X.performanceRecords(selected,sourceMap,D.atlasRoute),prod?"opera-plus-esplora-produzioni.csv":"opera-plus-esplora-recite.csv");
  });
  $("export-pdf").addEventListener("click",()=>{
   try{
    const st=state();
    const blob=P.create({reviewedOn,generatedOn:appliedOn,context:$("query-context").textContent,
     groupLabel:E.fields[st.group],metricLabel:A.metrics[st.metric],metric:st.metric,counts:E.summary(selected),labels:metrics,
     groups:reportGroups,months:reportMonths,regions:reportRegions,secondary:st.secondary,view:st.view,
     productions:X.productionRecords(selected,D.atlasRoute),performances:X.performanceRecords(selected)});
    download(blob,"opera-plus-esplora-report.pdf");$("export-status").textContent="";
   }catch(error){$("export-status").textContent="Impossibile generare il PDF: "+error.message}
  });
  $("share-query").addEventListener("click",async()=>{
   const url=sharedUrl(),input=$("share-url");input.value=url;
   try{await navigator.clipboard.writeText(url);$("export-status").textContent="Collegamento copiato."}
   catch{input.hidden=false;input.focus();input.select();$("export-status").textContent="Copia il collegamento dal campo sottostante."}
  });
 }
 async function main(){
  try{
   const result=await D.load(globalThis.OperaAtlasCatalog);
   rows=E.normalize(result.data.performances,result.festivals);
   rawById=new Map(result.data.performances.map(r=>[r.id,r]));
   workById=new Map(result.data.works.map(w=>[w.id,w]));
   reviewedOn=result.data.reviewed_on;
   initFilters();initAnalysis();initExports();
   restoreUrl();
   $("query").addEventListener("submit",e=>{e.preventDefault();query()});
   $("reset").addEventListener("click",()=>{
    for(const key of D.dimensions){chosen[key].clear();controls.get(key).search.value=""}
    $("query").reset();for(const key of D.dimensions)refreshOptions(key);
    $("preset").value="custom";$("group-by").value="work";$("group-metric").value="performances";$("group-order").value="auto";$("compare-productions").checked=true;configurePreset();query();
   });
   $("view").addEventListener("change",()=>{page=0;sortKey=$("view").value==="productions"?"first":"date";descending=false;drawTable();syncUrl()});
   $("previous").addEventListener("click",()=>{page--;drawTable()});$("next").addEventListener("click",()=>{page++;drawTable()});
   $("updated").textContent="Versione del catalogo: "+date(result.data.reviewed_on)+". Copertura temporale delle date rilevate: "+(rows.length?date(rows[0].date)+" – "+date(rows.at(-1).date):"non disponibile")+".";
   $("status").textContent=result.mirror?"Indici complementari caricati dal canale alternativo.":"";
   if(result.data.warning)$("status").textContent+=($("status").textContent?" ":"")+result.data.warning;
   $("explore-content").hidden=false;query();
  }catch(error){
   $("explore-content").hidden=true;
   $("status").textContent="Dati temporaneamente non disponibili. "+error.message+". Nessuna stima viene mostrata.";
  }
 }
 main();
})();
