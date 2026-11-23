"use strict";
(() => {
  const el=id=>document.getElementById(id);
  const dateInput=el("day-input"),region=el("today-region"),city=el("today-city"),time=el("today-time"),query=el("today-query");
  const cards=el("today-cards"),empty=el("today-empty"),count=el("today-count"),message=el("today-message");
  let performances=[];
  function italianToday(){
    // Calendar date in Italy, independent of visitor timezone.
    const parts=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
    const get=t=>parts.find(x=>x.type===t).value;
    return get("year")+"-"+get("month")+"-"+get("day");
  }
  function dateFromISO(value){return new Date(value+"T12:00:00Z");}
  function dayShift(value,days){const d=dateFromISO(value);d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10);}
  function labelDate(value){return new Intl.DateTimeFormat("it-IT",{timeZone:"UTC",weekday:"long",day:"numeric",month:"long",year:"numeric"}).format(dateFromISO(value));}
  function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
  function options(select,values,placeholder){
    const old=select.value;select.replaceChildren(node("option",null,placeholder));
    for(const v of [...new Set(values.filter(x=>typeof x==="string"&&x.trim()))].sort((a,b)=>a.localeCompare(b,"it"))){
      const opt=node("option",null,v);opt.value=v;select.append(opt);
    }
    select.value=[...select.options].some(o=>o.value===old)?old:"";
  }
  function filtered(){
    return performances.filter(p=>{
      if(p.local_date!==dateInput.value || p.status==="cancelled" || p.status==="canceled")return false;
      if(region.value && p.region!==region.value)return false;
      if(city.value && p.municipality!==city.value)return false;
      const term=query.value.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it").trim();
      if(term && ![p.title,p.composer,p.venue,p.municipality,p.region].some(v=>String(v||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it").includes(term)))return false;
      if(!time.value)return true;
      if(time.value==="unknown")return !p.time_known;
      if(!p.time_known || typeof p.starts_at!=="string")return false;
      const hour=Number(p.starts_at.slice(11,13));
      return time.value==="morning"?hour<13:time.value==="afternoon"?hour>=13&&hour<19:hour>=19;
    }).sort((a,b)=>(a.time_known?0:1)-(b.time_known?0:1) ||
      (a.starts_at||"").localeCompare(b.starts_at||"") ||
      a.municipality.localeCompare(b.municipality,"it")||a.title.localeCompare(b.title,"it"));
  }
  function card(p){
    const article=node("article","today-card");
    const imageHost=node("div","today-image");
    try{
      const images=window.OperaAtlasImages;
      if(!p.program_id && p.work_id && images?.element && images?.work){
        const artwork=images.work(p);
        // Canonical identity + explicit source: title-only legacy matches are
        // not reliable when different composers share a title.
        if(artwork?.src && artwork?.sourceUrl && artwork.kind!=="unavailable")
          imageHost.append(images.element(artwork,"today-photo"));
        else imageHost.append(node("span","today-no-image","Opera+ Atlas"));
      } else imageHost.append(node("span","today-no-image","Opera+ Atlas"));
    }catch(e){console.warn("Immagine non disponibile",e);}
    article.append(imageHost);
    const body=node("div","today-card-body");
    body.append(node("p","eyebrow",p.municipality));
    const heading=node("h3"),a=node("a",null,p.title);
    a.href=window.OperaAtlasCatalog.urls(p).production;heading.append(a);body.append(heading);
    if(p.composer)body.append(node("p","today-composer",p.composer));
    body.append(node("p","today-venue",p.venue));
    if(p.local_date!==dateInput.value)body.append(node("p","today-future-date",labelDate(p.local_date)));
    body.append(node("p","today-hour",p.time_known && typeof p.starts_at==="string" ? "Ore "+p.starts_at.slice(11,16) : "Orario da confermare"));
    const detail=node("a","detail-link","Dettagli e rappresentazioni");detail.href=window.OperaAtlasCatalog.urls(p).production;body.append(detail);
    article.append(body);return article;
  }
  function render(){
    el("selected-day").textContent=labelDate(dateInput.value);
    renderQuickDays();
    const scoped=performances.filter(p=>p.local_date===dateInput.value && p.status!=="cancelled" && p.status!=="canceled");
    options(region,scoped.map(p=>p.region),"Tutte le regioni");
    options(city,scoped.filter(p=>!region.value||p.region===region.value).map(p=>p.municipality),"Tutte le città");
    const found=filtered();
    cards.replaceChildren(...found.map(card));
    count.textContent=found.length+" "+(found.length===1?"rappresentazione":"rappresentazioni")+" in programma";
    empty.hidden=found.length>0;
    const suggestions=el("today-suggestions"),future=el("today-future-cards");
    const next=found.length===0 && !region.value && !city.value && !time.value && !query.value
      ? performances.filter(p=>p.local_date>dateInput.value && p.status!=="cancelled" && p.status!=="canceled")
        .sort((a,b)=>a.local_date.localeCompare(b.local_date)||(a.starts_at||"").localeCompare(b.starts_at||"")).slice(0,3)
      : [];
    suggestions.hidden=next.length===0;
    future.replaceChildren(...next.map(card));
    const params=new URLSearchParams(window.location.search);params.set("data",dateInput.value);
    history.replaceState(null,"",window.location.pathname+"?"+params.toString());
  }
  function renderQuickDays(){
    const strip=el("today-quick-days");
    strip.replaceChildren();
    const current=italianToday();
    for(let offset=-2;offset<=2;offset++){
      const day=dayShift(dateInput.value,offset);
      const button=node("button","today-day"+(offset===0?" selected":""),null);
      button.type="button";
      button.setAttribute("aria-pressed",offset===0?"true":"false");
      const weekday=new Intl.DateTimeFormat("it-IT",{weekday:"short",timeZone:"UTC"}).format(dateFromISO(day));
      const date=new Intl.DateTimeFormat("it-IT",{day:"numeric",month:"short",timeZone:"UTC"}).format(dateFromISO(day));
      button.append(node("span","today-day-weekday",day===current?"Oggi":weekday),node("strong",null,date));
      button.addEventListener("click",()=>changeDate(day));
      strip.append(button);
    }
  }
  function changeDate(value){dateInput.value=value;region.value="";city.value="";time.value="";render();}
  el("day-prev").addEventListener("click",()=>changeDate(dayShift(dateInput.value,-1)));
  el("day-next").addEventListener("click",()=>changeDate(dayShift(dateInput.value,1)));
  el("day-today").addEventListener("click",()=>changeDate(italianToday()));
  dateInput.addEventListener("change",()=>{if(/^\d{4}-\d{2}-\d{2}$/.test(dateInput.value))changeDate(dateInput.value);});
  region.addEventListener("change",()=>{city.value="";render();});
  city.addEventListener("change",render);time.addEventListener("change",render);query.addEventListener("input",render);
  el("today-upcoming").addEventListener("click",()=>{
    const next=performances.filter(p=>p.local_date>dateInput.value && p.status!=="cancelled" && p.status!=="canceled").map(p=>p.local_date).sort()[0];
    if(next)changeDate(next);else window.location.href="./#spettacoli";
  });
  const requested=new URLSearchParams(location.search).get("data");
  dateInput.value=requested && /^\d{4}-\d{2}-\d{2}$/.test(requested) && !Number.isNaN(dateFromISO(requested).getTime())?requested:italianToday();
  el("selected-day").textContent=labelDate(dateInput.value);
  Promise.all([window.OperaAtlasCatalog.load(),window.OperaAtlasImages?.load?.()||Promise.resolve()]).then(([data])=>{
    performances=(data.performances||[]).filter(p=>p&&typeof p.id==="string"&&typeof p.title==="string"&&
      typeof p.municipality==="string"&&typeof p.venue==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(p.local_date||""));
    if(data.warning)message.textContent=data.warning;
    render();
  }).catch(()=>{count.textContent="Cartellone non disponibile";message.textContent="Impossibile caricare il calendario. Riprova più tardi.";});
})();