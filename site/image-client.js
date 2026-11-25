"use strict";
/* Photo selections are historical/illustrative, never photos of the current production.
   Commons file pages and license/attribution sources are listed in credits.html.
   Venue photos and opera artwork are selected independently; historical cover documents are preferred. Missing archival items remain visibly editorial, never represented as historical posters. */
window.OperaAtlasImages=Object.freeze((()=>{
  const FILES={
    "torino":"Teatro Regio - foto aerea.jpg",
    "como":"Teatro Sociale di Como.jpg",
    "pavia":"Teatro Fraschini - Pavia.jpg",
    "brescia":"Teatro Grande (Sala).jpg",
    "cremona":"Teatro Ponchielli in Cremona (1).jpg",
    "milano":"Teatro alla Scala interior Milan.jpg",
    "verona":"Arena di Verona esterno.jpg",
    "venezia":"Teatro-la-fenice-sala.jpg",
    "palermo":"Interior of Teatro Massimo (Palermo) SAM 0420.JPG",
    "parma":"Interior of Teatro Regio, Parma, Italy.JPG",
    "novara":"Teatro Coccia Novara.jpg",
    "bergamo":"Teatro Donizetti Bergamo - Esterno.jpg",
    "reggio emilia":"Teatro Valli Reggio Emilia.JPG",
    "ravenna":"Teatro Dante Alighieri Ravenna.jpg",
    "pesaro":"TeatroRossiniPesaro.jpg"
  };
  // Legacy homepage cards without a venue-directory record: exact identities only.
  const VENUE_NAMES={
    "torino":["Teatro Regio"],"como":["Teatro Sociale"],"pavia":["Teatro Fraschini"],
    "brescia":["Teatro Grande"],"cremona":["Teatro Ponchielli"],
    "milano":["Teatro alla Scala"],"verona":["Arena di Verona"],
    "venezia":["Teatro La Fenice"],"palermo":["Teatro Massimo"],
    "parma":["Teatro Regio di Parma"],"novara":["Teatro Coccia"],
    "bergamo":["Teatro Donizetti"],"reggio emilia":["Teatro Valli"],
    "ravenna":["Teatro Dante Alighieri"],"pesaro":["Teatro Rossini"]
  };
  const WORKS={
    "la-traviata":"Traviata.jpg",
    "carmen":"1875 Carmen poster.jpg",
    "tosca":"Puccini Tosca.jpg",
    "rigoletto":"Rigoletto premiere poster.jpg",
    "aida":"Giuseppe Verdi - Hippodrome Opera Company - Aida poster.jpg",
    "la-boheme":"La Boheme poster by Hohenstein.PNG",
    "turandot":"Poster Turandot.jpg",
    "salome":"Max Tilke- Poster-of-opera-salome-richard-strauss.jpg",
    "nabucco":"Nabucco - 1852 cover.jpg",
    "otello":"Poster Otello by Giuseppe Verdi.jpg",
    "madama-butterfly":"Hohenstein Madama Butterfly.jpg",
    "don-giovanni":"Theatre Poster for Don Giovanni.jpg",
    "iris":"Iris, opera by Pietro Mascagni, poster by Adolf Hohenstein.jpg",
    "cavalleria-rusticana":"Cavalleria rusticana poster.jpg",
    "pagliacci":"Pagliacci Original Score Cover.jpg",
    "italiana-in-algeri":"1930-Italiana-in-Algeri.jpg",
    "jenufa":"Jenufa.jpg",
    "evgenij-onegin":"\"Eugene Onegin\" opera poster,1937, Yerevan Opera Theatre.jpg",
    "un-ballo-in-maschera":"Giuseppe Verdi, Un Ballo in maschera, Vocal score frontispiece - restoration.jpg",
    "macbeth":"Locandina macbeth a firenze, 1847.jpg",
    "samson-et-dalila":"Samson et Dalila. Opéra de C. Saint-Saens affiche, Georges Antoine Rochegrosse.jpg",
    "lucia-di-lammermoor":"Mdlle. Jenny Lind, as 'Lucia di Lammermoor,' at Her Majesty's Theatre. (BM 1901,1022.1647).jpg",
    "edgar":"Romilda Pantaleoni as Tigrana in Puccini's Edgar - Milan 1889.png",
    "fedora":"Ida Aalberg i titelrollen i operan Fedora av Umberto Giordano - 1900 SLSA 1270 34 foto 29.jpg",
    "death-in-venice":"Pears death in venice.jpg",
    "nixon-in-china":"Dortmund Kampstr Nixon in China IMG 20230315 1145.jpg"
  };
  // Identity-pinned historical works: never allow a cached older feed to
  // restore temporary staging photos of these six operas. ID + composer is
  // mandatory, so homonymous compositions cannot share a poster.
  const HISTORIC_POSTER_PINS=Object.freeze({
    "oa-w-000001":{composer:"Giuseppe Verdi",file:"Traviata.jpg"},
    "oa-w-000002":{composer:"Gioachino Rossini",file:"1930-Italiana-in-Algeri.jpg"},
    "oa-w-000006":{composer:"Ruggero Leoncavallo",file:"Pagliacci Original Score Cover.jpg"},
    "oa-w-000010":{composer:"Pëtr Il'ič Čajkovskij",file:'"Eugene Onegin" opera poster,1937, Yerevan Opera Theatre.jpg'},
    "oa-w-000011":{composer:"Giacomo Puccini",file:"Poster Turandot.jpg"},
    "oa-w-000025":{composer:"Giuseppe Verdi",file:"Nabucco - 1852 cover.jpg"}
  });
  // Published by the catalog workflow, not by an FTPS site rebuild.
  // A static site update is needed once to enable this feed; subsequent
  // newly catalogued operas automatically gain an image reference.
  const POSTER_FEED="https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/work-posters.json";
  let posters={};
  let posterSchema=0;
  let pending=null;
  function load(){
    if(pending)return pending;
    pending=(async()=>{
      try{
        const response=await fetch(POSTER_FEED,{cache:"no-store"});
        if(!response.ok)throw new Error("poster registry unavailable");
        const body=await response.json();
        if(![1,2].includes(body.schema_version) || !body.works ||
           Array.isArray(body.works))
          throw new Error("invalid poster registry");
        posterSchema=body.schema_version;
        posters=body.works;
      }catch(error){
        // The original generated cover remains available even when the
        // feed or a third-party image provider is inaccessible.
        console.warn("Atlas poster registry unavailable",error);
      }
    })();
    return pending;
  }
  const normalize=value=>String(value||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"")
    .replace(/^l['’]/i,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
  const commune=value=>String(value||"").toLowerCase().trim();
  const esc=value=>String(value||"").replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  function commons(file){
    return "https://commons.wikimedia.org/wiki/Special:Redirect/file/"+
      encodeURIComponent(file.replaceAll(" ","_"))+"?width=720";
  }
  function poster(title,kind="work"){
    // Every title has its own locally generated art direction, not a generic placeholder.
    const value=String(title||"Opera");
    const seed=[...value].reduce((a,c)=>(Math.imul(a,33)+c.charCodeAt(0))>>>0,5381);
    const palettes=[["#101c2b","#b48b52","#d8bf94"],["#28332a","#bd9d68","#efe1b4"],
      ["#3d2330","#c09770","#f3d7bb"],["#242d38","#9c9c9b","#eed9a6"],
      ["#3d2b20","#ad916d","#e9bf83"],["#1e343e","#c8a36b","#d2e2df"],
      ["#332539","#d0ab71","#f3ddd2"],["#253b36","#b4a06a","#cfe1cd"]];
    const colors=palettes[seed%palettes.length];
    const icon=seed%5;
    const motifs=[
      '<path d="M225 550Q375 150 525 550M255 550Q375 230 495 550" fill="none" stroke="ACCENT" stroke-width="17"/>',
      '<path d="M195 480Q375 180 555 480Q375 625 195 480Z" fill="none" stroke="ACCENT" stroke-width="17"/><circle cx="375" cy="464" r="62" fill="ACCENT" opacity=".45"/>',
      '<path d="M220 550L310 290L375 420L445 255L530 550Z" fill="none" stroke="ACCENT" stroke-width="14"/><circle cx="375" cy="235" r="50" fill="ACCENT" opacity=".38"/>',
      '<circle cx="375" cy="390" r="145" fill="none" stroke="ACCENT" stroke-width="14"/><path d="M310 260Q450 325 310 530" fill="none" stroke="ACCENT" stroke-width="17"/>',
      '<path d="M200 545Q250 265 375 345Q500 265 550 545M225 505L525 505" fill="none" stroke="ACCENT" stroke-width="17"/>'
    ];
    const motif=motifs[icon].replaceAll("ACCENT",colors[1]);
    const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 750 920">'+
      '<rect width="750" height="920" fill="'+colors[0]+'"/>'+
      '<g opacity=".16" fill="none" stroke="'+colors[2]+'">'+
      '<path d="M30 0V920M110 0V920M640 0V920M720 0V920"/>'+
      '<path d="M0 105H750M0 785H750"/></g>'+
      '<path d="M90 100Q375 185 660 100" fill="none" stroke="'+colors[1]+'" stroke-width="7"/>'+
      '<g opacity=".88">'+motif+'</g>'+
      '<path d="M100 645H650" stroke="'+colors[1]+'" stroke-width="3"/>'+
      '<text x="375" y="695" text-anchor="middle" fill="'+colors[2]+'" font-family="Georgia,serif" font-size="25" letter-spacing="5">OPERA+ ATLAS</text>'+
      '<text x="375" y="760" text-anchor="middle" fill="'+colors[2]+'" font-family="Georgia,serif" font-size="35" textLength="570" lengthAdjust="spacingAndGlyphs">'+esc(value)+'</text>'+
      '<text x="375" y="845" text-anchor="middle" fill="'+colors[1]+'" font-family="Georgia,serif" font-size="19" letter-spacing="5">IL TEATRO D’OPERA IN ITALIA</text>'+
      '</svg>';
    return "data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
  }
  function photo(file,alt,key){
    return {src:commons(file),alt,fallbackSrc:poster(key||alt)};
  }
  function work(event){
    const title=event?.title||"Opera";
    const slug=event?.work_slug||normalize(title);
    const pinned=event?.work_id && HISTORIC_POSTER_PINS[event.work_id];
    if(pinned && event?.composer===pinned.composer){
      return {src:commons(pinned.file),
        alt:"Manifesto o documento d’archivio di "+title+" — "+pinned.composer,
        fallbackSrc:null,
        sourceUrl:"https://commons.wikimedia.org/wiki/File:"+
          encodeURIComponent(pinned.file.replaceAll(" ","_")),
        credit:"Documento storico · Wikimedia Commons",
        kind:"archival_work_image"};
    }

    // V2 is keyed by permanent work ID, not by title; e.g. Puccini and
    // Leoncavallo both have an opera called La bohème.
    // Legacy title-keyed artwork is not authoritative for a canonical work.
    // Only work-ID keyed evidence may select a published poster.
    const chosen=(posterSchema===2 && event?.work_id ? posters[event?.work_id] : null);
    // TicketOne artwork is explicitly approved for this one canonical work.
    // Never accept arbitrary ticketing artwork by title or for a different work.
    const approvedTicketingArt=event?.work_id==="oa-w-000074" &&
      event?.composer==="Nicola Sani" && title==="Code: Unknown" &&
      chosen?.kind==="ticketing_event_artwork" &&
      chosen?.image_url==="https://www.ticketone.it/obj/media/IT-eventim/teaser/evo/artwork/2027/code-unknow-biglietti.jpg";
    if(chosen && (chosen.kind==="official_production_image" ||
                  chosen.kind==="archival_work_image" ||
                  chosen.kind==="official_coproduction_poster" ||
                  chosen.kind==="official_original_work_artwork" ||
                  chosen.kind==="official_civic_production_image" ||
                  chosen.kind==="verified_historical_theatre_poster" || approvedTicketingArt) &&
       typeof chosen.image_url==="string" && chosen.image_url.startsWith("https://")){
      return {src:chosen.image_url,
        alt:chosen.alt||"Immagine autentica dell’opera "+title,
        fallbackSrc:null,
        sourceUrl:chosen.source_url,credit:chosen.credit,
        license:chosen.license||"",kind:chosen.kind};
    }
    // Legacy static snapshot: use only exact, historically sourced imagery.
    // A missing source must never be replaced with fabricated editorial art.
    const distinctRoute=event?.work_route_slug && event.work_route_slug!==slug;
    const file=distinctRoute ? null : WORKS[slug];
    return file
      ? {src:commons(file),alt:"Documento d’archivio legato a "+title,
         fallbackSrc:null,kind:"archival_work_image"}
      : {src:"",alt:"Immagine autentica non disponibile",kind:"unavailable"};
  }
  function program(event){
    // Only verified component identities can supply a repertoire fallback.
    const alternatives=(event?.program_components||[]).filter(c=>c.work_id)
      .map(c=>work({...c,work_slug:normalize(c.title),work_route_slug:c.work_route_slug}))
      .filter(a=>a.src && a.sourceUrl && a.kind!=="unavailable");
    const fallback=alternatives[0];
    const art=event?.program_artwork;
    if(art?.kind==="official_program_image" && art.credit && art.source_url &&
       event?.sources?.includes(art.source_url) && /^https:\/\//.test(art.image_url) &&
       /^https:\/\//.test(art.source_url)){
      return {src:art.image_url,alt:art.alt||"Grafica ufficiale del programma",
        fallbackSrc:fallback?.src||null,sourceUrl:art.source_url,credit:art.credit,
        license:art.license||"",kind:art.kind,fallbackArtwork:fallback};
    }
    return fallback ? {...fallback,alt:"Immagine di una delle opere del programma: "+fallback.alt,
      kind:"program_component_image"} : {src:"",alt:"Immagine autentica del programma non disponibile",kind:"unavailable"};
  }
  function venue(event){
    const city=commune(event?.municipality||event?.city);
    const title=event?.venue||event?.name||("Teatro di "+(event?.municipality||event?.city||"Italia"));
    // A city may have several opera theatres: do not show an Arena photo
    // as if it were a photograph of Teatro Filarmonico.
    // Use each theatre's verified file, never a photo of another venue
    // in the same city. Unknown images retain a visibly editorial fallback.
    // The homepage may render a staging before the separate venue directory
    // has finished loading. Use only a venue-specific, sourced photo here,
    // never assume all theatres in one city share the same building.
    const knownVenueFile=city==="genova" && title==="Teatro Carlo Felice"
      ? "Genova - Teatro Carlo Felice.jpg" : null;
    // An explicitly sourced and credited venue photograph may be hosted outside Commons.
    const external=event?.photo_url;
    // Explicitly pin the municipal photograph to this Rome venue: no city-wide
    // fallback or attribution to the separate Teatro Costanzi.
    if(title==="Teatro Nazionale" && city==="roma" &&
       external==="https://www.comune.roma.it/web-resources/cms/images/teatro_nazionale_d0.jpg" &&
       event?.photo_source_url==="https://www.turismoroma.it/it/luoghi/teatro-nazionale" && event?.photo_credit){
      return {src:external,alt:"Fotografia del Teatro Nazionale a Roma",
        fallbackSrc:poster(title),sourceUrl:event.photo_source_url,
        credit:event.photo_credit,license:event.photo_license||""};
    }
    if(city==="trapani" && title==="Teatro M° Tonino Pardo" &&
       external==="https://www.tp24.it/immagini_articoli/05-05-2023/1683241767-0-trapani-riaperto-il-teatro-pardo-a-che-punto-sono-i-lavori-al-tito-marrone.jpg" && event?.photo_credit && event?.photo_source_url){
      return {src:external,alt:"Platea e palcoscenico del Teatro M° Tonino Pardo a Trapani",
        fallbackSrc:null,sourceUrl:event.photo_source_url,
        credit:event.photo_credit,license:event.photo_license||""};
    }
    if(typeof external==="string" && /^https:\/\/salentosagreeventi\.it\/media\/places\/[a-zA-Z0-9/_-]+\.webp$/.test(external)
       && event?.photo_source_url && event?.photo_credit){
      return {src:external,alt:"Fotografia del "+title+" a "+(event?.municipality||event?.city),
        fallbackSrc:poster(title),sourceUrl:event.photo_source_url,
        credit:event.photo_credit,license:event.photo_license||""};
    }
    if(city==="trento" && title==="Sanbàpolis" &&
       external==="https://www.cultura.trentino.it/var/001/storage/images/media/images/teatro-sanbapolis/16381731-1-ita-IT/Teatro-Sanbapolis_imagefullwide.jpg" &&
       event?.photo_source_url==="https://www.cultura.trentino.it/Luoghi/Tutti-i-luoghi-della-cultura/Teatri-e-sale/Teatro-Sanbapolis" && event?.photo_credit){
      return {src:external,alt:"Platea del Teatro Sanbàpolis a Trento",
        fallbackSrc:null,sourceUrl:event.photo_source_url,
        credit:event.photo_credit,license:event.photo_license||""};
    }
    const verified=event?.photo_file || knownVenueFile;
    // Never infer a photographed building from its city. A city can host
    // multiple theatres, including distinct historic and temporary venues.
    const file=typeof verified==="string" && /^[^/\\]+\.(jpe?g|png|webp)$/i.test(verified)
      ? verified : (VENUE_NAMES[city]?.includes(title) ? FILES[city] : null);
    if(!file)return {src:poster(title,"venue"),alt:"Illustrazione editoriale del "+title};
    const result=photo(file,"Fotografia del "+title+" a "+(event?.municipality||event?.city),title);
    if(verified && event.photo_source_url)result.sourceUrl=event.photo_source_url;
    return result;
  }
  function festival(event){
    // Festival photos are identity-specific, not chosen by city: a single
    // municipality may host several unrelated venues or festivals.
    if(typeof event?.photo_file==="string" && event.photo_file &&
       typeof event?.photo_source_url==="string" &&
       event.photo_source_url.startsWith("https://commons.wikimedia.org/wiki/File:")){
      return {src:commons(event.photo_file),
        alt:event.photo_alt||"Sede del festival "+(event.name||""),
        fallbackSrc:null,sourceUrl:event.photo_source_url,
        credit:event.photo_credit||"Wikimedia Commons",kind:"verified_festival_venue"};
    }
    return {src:"",alt:"Fotografia verificata non disponibile",kind:"unavailable"};
  }
  function element(item,cls="card-image"){
    const picture=document.createElement("img");
    picture.className=cls;
    picture.alt=item.alt;
    picture.loading="lazy";
    picture.decoding="async";
    picture.referrerPolicy="no-referrer";
    picture.addEventListener("error",()=>{
      if(item.fallbackSrc && picture.src!==item.fallbackSrc){
        picture.src=item.fallbackSrc;
        if(item.fallbackArtwork){
          const a=item.fallbackArtwork;
          picture.alt="Immagine di una delle opere del programma: "+a.alt;
          picture.title=(a.credit||"")+(a.license?" · "+a.license:"");
        }
      }
      else {picture.hidden=true;picture.removeAttribute("src");}
    },{once:true});
    if(item.credit)picture.title=item.credit+(item.license?" · "+item.license:"");
    if(item.src)picture.src=item.src;
    else picture.hidden=true;
    return picture;
  }
  function bindHero(){
    const hero=document.querySelector(".hero-image");
    if(!hero)return;
    hero.addEventListener("error",()=>{hero.src=poster("Il teatro d'opera");},{once:true});
  }
  bindHero();
  return {work,program,venue,festival,element,poster,load,FILES,WORKS};
})());