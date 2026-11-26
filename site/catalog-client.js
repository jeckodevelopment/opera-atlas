"use strict";
/* Public static client. No credentials, server or runtime dependencies.
   Reads the mutable v2 manifest, then immutable SHA-256-addressed channels.
   A failed/incomplete remote release falls back to the last SFTP snapshot
   with an explicit warning. The SFTP fallback is not a live data source. */
window.OperaAtlasCatalog = (() => {
  const BASE = "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/";
  const MIRROR = "https://cdn.jsdelivr.net/gh/jeckodevelopment/opera-atlas@main/public/catalog/v2/";
  const CHANNELS = ["works","venues","stagings","performances"];
  const VENUE_FEED = "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/venue-directory.json";

  const PREFIX = new URL(document.baseURI).pathname.replace(/\/$/, "");

  function slugify(text) {
    return String(text || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("it").replace(/æ/g,"ae").replace(/œ/g,"oe").replace(/^l['’]/, "")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function urls(event) {
    if(event.program_id){
      const route=PREFIX+"/programmi/"+event.program_id+"/";
      return {work:route,venue:PREFIX+"/"+(event.city_slug||slugify(event.municipality))+
        "/"+(event.venue_slug||slugify(event.venue))+"/",
        staging:route,production:route};
    }
    const city = event.city_slug || slugify(event.municipality);
    const theatre = event.venue_slug || slugify(event.venue);
    const work = event.work_route_slug || event.work_slug || slugify(event.title);
    const staging = event.staging_url || ("/" + city + "/" + theatre + "/" + work + "/");
    return {
      work: PREFIX + "/opere/" + work + "/",
      venue: PREFIX + "/" + city + "/" + theatre + "/",
      staging: PREFIX + staging,
      production: event.production_group_id ? PREFIX + "/produzioni/" + event.production_group_id + "/" : PREFIX + staging,
    };
  }


  async function jsonFrom(url, digest) {
    const response = await fetch(url, {cache:"no-store"});
    if (!response.ok) throw new Error("Catalog HTTP " + response.status);
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength > 12 * 1024 * 1024) throw new Error("Catalog part too large");
    if (digest) {
      if (!globalThis.crypto || !crypto.subtle) throw new Error("Secure digest unavailable");
      const actual = await crypto.subtle.digest("SHA-256", bytes);
      const hex = [...new Uint8Array(actual)].map(x => x.toString(16).padStart(2,"0")).join("");
      if (hex !== digest) throw new Error("Catalog digest mismatch");
    }
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  function validateChannel(key, manifest, part) {
    if (part.schema_version !== 2 || !Array.isArray(part[key])) throw new Error("Invalid feed channel");
    if (part[key].length !== manifest.files[key].count) throw new Error("Catalog count differs");
    return part[key];
  }

  async function productionGroupMap(byStaging,base) {
    const doc = await jsonFrom(base+"production-groups.json");
    if(doc.schema_version!==1||!Array.isArray(doc.groups)) throw Error("Invalid production groups");
    const map=new Map(), ids=new Set();
    for(const group of doc.groups){
      if(!group||typeof group.id!=="string"||!/^oa-g-[a-z0-9-]+$/.test(group.id)||
         ids.has(group.id)||!Array.isArray(group.staging_ids)||!group.staging_ids.length)
        throw Error("Invalid group identity");
      ids.add(group.id);
      for(const id of group.staging_ids){
        const staging=byStaging.get(id);
        if(!staging || staging.work_id!==group.work_id || map.has(id))
          throw Error("Conflicting production group");
        map.set(id,group.id);
      }
    }
    return map;
  }
  async function programPerformances(base,byWork,byVenue,existing){
    const endpoint=base.replace(/\/v2\/$/,"/")+"programs.json";
    // A companion channel permits stable repertoire IDs/manifest compatibility
    // while new source-independent composite programs are introduced.
    const response=await fetch(endpoint,{cache:"no-store"});
    if(response.status===404)return [];
    if(!response.ok)throw new Error("Program feed HTTP "+response.status);
    const doc=await response.json();
    if(doc.schema_version!==1||!Array.isArray(doc.programs))
      throw new Error("Invalid public program catalog");
    const ids=new Set(existing.map(x=>x.id));
    const byRoute=new Set(existing.map(x=>x.staging_url+"|"+x.local_date));
    const seenPrograms=new Set(),out=[];
    let nationalDirectory=null;
    for(const program of doc.programs){
      if(!program || !/^oa-p-[a-f0-9]{16}$/.test(program.id)
          || seenPrograms.has(program.id)
          || !Array.isArray(program.components) || program.components.length<2
          || !Array.isArray(program.performances) || program.performances.length<1)
        throw new Error("Invalid composite program identity");
      seenPrograms.add(program.id);
      let venue=[...byVenue.values()].find(v=>v.city===program.municipality &&
        (v.name===program.venue || v.display_name===program.venue));
      if(!venue){
        // A reviewed composite ticket can be the first opera at a verified
        // directory-only theatre (Jesi/Ancona), before a canonical solo work
        // has allocated a v2 venue ID. Never infer a theatre from free text.
        if(nationalDirectory===null){
          const directory=await jsonFrom(
            base.replace(/\/v2\/$/,"/")+"venue-directory.json");
          if(directory.schema_version!==1 || !Array.isArray(directory.venues))
            throw new Error("Invalid independent theatre directory");
          nationalDirectory=directory.venues;
        }
        const matches=nationalDirectory.filter(v=>
          v.city===program.municipality && v.name===program.venue &&
          v.region===program.region && typeof v.id==="string" &&
          /^oa-v(?:d)?-\d{6}$/.test(v.id) &&
          /^[a-z0-9-]+$/.test(v.city_slug||"") &&
          /^[a-z0-9-]+$/.test(v.slug||"") &&
          String(v.source_url||"").startsWith("https://"));
        if(matches.length!==1)throw new Error("Unknown program theatre");
        venue=matches[0];
      }
      const components=program.components.map(component=>{
        if(typeof component.title!=="string"||typeof component.composer!=="string")
          throw new Error("Invalid independently credited program component");
        const work=component.work_id ? byWork.get(component.work_id) : null;
        // A reviewed program component may have a permanent reserved ID
        // before a solo staging makes it eligible for the v2 works channel.
        // Never render that ID as a public work route until v2 confirms it.
        const pending=component.work_id && !work && /^oa-w-\d{6}$/.test(component.work_id)
          && component.editorial && typeof component.editorial.synopsis==="string"
          && component.editorial.synopsis.trim().length>=35
          && component.editorial.history
          && Array.isArray(component.editorial.history.sources)
          && component.editorial.history.sources.length>0
          && component.editorial.history.sources.every(s=>typeof s==="string"&&s.startsWith("https://"));
        if(component.work_id && !pending &&
           (!work || slugify(work.title)!==slugify(component.title) ||
             work.composer.normalize("NFKC").toLocaleLowerCase("it")!==
             component.composer.normalize("NFKC").toLocaleLowerCase("it")))
          throw new Error("Composite work identity mismatch");
        return {...component,work_route_slug:work?.route_slug||work?.slug||null};
      });
      const route="/programmi/"+program.id+"/";
      for(const recita of program.performances){
        if(!recita || !/^oa-pr-[a-f0-9]{16}$/.test(recita.id) ||
            recita.program_id!==program.id || ids.has(recita.id) ||
            !/^20\d\d-\d\d-\d\d$/.test(recita.local_date) ||
            typeof recita.starts_at!=="string" || !/^20\d\d-\d\d-\d\dT/.test(recita.starts_at) ||
            byRoute.has(route+"|"+recita.local_date))
          throw new Error("Invalid or duplicate program performance");
        ids.add(recita.id);byRoute.add(route+"|"+recita.local_date);
        out.push({id:recita.id,program_id:program.id,program_components:components,
          program_work_ids:components.filter(c=>c.work_id).map(c=>c.work_id),
          program_artwork:program.artwork?.source_url===program.source_url ? program.artwork : null,
          staging_id:program.id,staging_url:route,venue_id:venue.id,
          title:program.title,composer:components.map(c=>c.composer).join(" · "),
          venue:program.venue,municipality:program.municipality,region:program.region,
          venue_slug:venue.slug,city_slug:venue.city_slug,
          local_date:recita.local_date,starts_at:recita.starts_at,time_known:true,
          status:"announced",sources:[program.source_url]});
      }
    }
    return out;
  }
  async function remote(base) {
    const manifest = await jsonFrom(base + "manifest.json");
    if (manifest.schema_version !== 2 || !manifest.files || !/^\d{4}-\d{2}-\d{2}$/.test(manifest.reviewed_on)) {
      throw new Error("Unsupported manifest");
    }
    const parts = await Promise.all(CHANNELS.map(async channel => {
      const spec = manifest.files[channel];
      if (!spec || !new RegExp("^data/" + channel + "\.[a-f0-9]{16}\.json$").test(spec.path)
          || !/^[a-f0-9]{64}$/.test(spec.sha256) || !Number.isSafeInteger(spec.count)) {
        throw new Error("Unsafe catalog reference");
      }
      const doc = await jsonFrom(base + spec.path + "?v=" + spec.sha256.slice(0,16), spec.sha256);
      return validateChannel(channel,manifest,doc);
    }));
    const [works,venues,stagings,recite] = parts;
    const byWork = new Map(works.map(x=>[x.id,x]));
    const byVenue = new Map(venues.map(x=>[x.id,x]));
    const byStaging = new Map(stagings.map(x=>[x.id,x]));
    if (byWork.size !== works.length || byVenue.size !== venues.length
        || byStaging.size !== stagings.length) throw new Error("Duplicate canonical IDs");
    let groups=new Map(), groupWarning=null;
    try{groups=await productionGroupMap(byStaging,base);}catch{groupWarning="Alcune produzioni condivise potrebbero apparire separate per teatro.";}
    const ids = new Set();
    const performances = recite.map(item => {
      if (ids.has(item.id)) throw new Error("Duplicate performance ID");
      ids.add(item.id);
      const staging = byStaging.get(item.staging_id);
      const work = staging && byWork.get(staging.work_id);
      const venue = staging && byVenue.get(staging.venue_id);
      if (!work || !venue || !/^\d{4}-\d{2}-\d{2}$/.test(item.local_date)
          || (item.time_known ? typeof item.starts_at !== "string" : item.starts_at !== null)) {
        throw new Error("Invalid canonical relationship");
      }
      return {
        id:item.id, legacy_id:item.legacy_id, staging_id:staging.id,work_id:work.id,venue_id:venue.id,
        production_group_id:groups.get(staging.id)||null,
        ...(staging.project_name ? {project_name:staging.project_name,performance_format:staging.performance_format} : {}),
        ...(item.actual_location ? {actual_location:item.actual_location} : {}),
        staging_url:staging.url, season:staging.season, work_slug:work.slug,work_route_slug:work.route_slug||work.slug,
        venue_slug:venue.slug, city_slug:venue.city_slug,
        local_date:item.local_date,starts_at:item.starts_at,
        time_known:item.time_known, status:item.status,
        title:work.title, composer:work.composer,
        venue:venue.display_name||venue.name,municipality:venue.city,region:venue.region,
        sources:Array.isArray(item.sources) && item.sources.length ? item.sources : [staging.source_url],
      };
    });
    const programs=await programPerformances(base,byWork,byVenue,performances);
    return {schema_version:1,works,performances:[...performances,...programs],
      source:"github",reviewed_on:manifest.reviewed_on,warning:groupWarning};
  }

  // Theatre catalogue is independent of performance publication, including
  // venues with zero currently known recite and future national onboarding.
  async function venues() {
    try {
      const document=await jsonFrom(VENUE_FEED);
      if(document.schema_version!==1 || !Array.isArray(document.venues))
        throw Error("Invalid venue directory");
      const ids=new Set(),routes=new Set();
      for(const venue of document.venues){
        if(!venue || typeof venue.id!=="string" || typeof venue.name!=="string" ||
           !/^[a-z0-9-]+$/.test(venue.slug||"") ||
           !/^[a-z0-9-]+$/.test(venue.city_slug||"") ||
           !String(venue.source_url||"").startsWith("https://"))
          throw Error("Unsafe venue directory entry");
        const route=venue.city_slug+"/"+venue.slug;
        if(ids.has(venue.id)||routes.has(route))
          throw Error("Duplicate venue directory entry");
        ids.add(venue.id);routes.add(route);
      }
      return document.venues;
    }catch(error){
      console.warn("Atlas national venue directory unavailable",error);
      return [];
    }
  }

  async function load() {
    const failures=[];
    for(const base of [BASE,MIRROR]){
      try{
        const data=await remote(base);
        if(base===MIRROR)data.warning=data.warning||"Il catalogo è stato caricato dal canale alternativo.";
        return data;
      }catch(error){
        failures.push(error);
        console.warn("Opera Atlas feed endpoint failed",base,error);
      }
    }
    try{
      const snapshot=await jsonFrom("./performances.json");
      if(snapshot.schema_version!==1 || !Array.isArray(snapshot.performances))
        throw new Error("Invalid snapshot");
      // Keep historic registry keys and static URLs unchanged when rendering a label.
      const performances=snapshot.performances.map(event=>
        event.municipality==="Torino" && event.venue==="Teatro Regio"
          ? {...event,venue:"Teatro Regio di Torino",venue_slug:"teatro-regio",city_slug:"torino"} : event);
      return {...snapshot,performances,source:"fallback",warning:"Alcuni aggiornamenti del calendario potrebbero non essere ancora visibili."};
    }catch(error){
      console.error("Opera Atlas: all catalog endpoints failed",{failures,snapshot:error});
      throw new Error("Unable to load remote or local catalog");
    }
  }
  return Object.freeze({load, urls, slugify, venues});
})();
