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
  const WORKS={
    "la-traviata":"Traviata.jpg",
    "carmen":"1875 Carmen poster.jpg",
    "tosca":"Puccini Tosca.jpg",
    "rigoletto":"Rigoletto premiere poster.jpg",
    "aida":"Giuseppe Verdi - Hippodrome Opera Company - Aida poster.jpg",
    "la-boheme":"La Boheme poster by Hohenstein.PNG",
    "turandot":"Poster Turandot.jpg",
    "salome":"Max Tilke- Poster-of-opera-salome-richard-strauss.jpg",
    "nabucco":"Nabucco poster.jpg",
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
    "death-in-venice":"-13.2- Thomas Mann Atlas Haack.jpg"
  };
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
    // V2 is keyed by permanent work ID, not by title; e.g. Puccini and
    // Leoncavallo both have an opera called La bohème.
    // Legacy title-keyed artwork is not authoritative for a canonical work.
    // Only work-ID keyed evidence may select a published poster.
    const chosen=(posterSchema===2 && event?.work_id ? posters[event?.work_id] : null);
    if(chosen && (chosen.kind==="official_production_image" ||
                  chosen.kind==="archival_work_image") &&
       typeof chosen.image_url==="string" && chosen.image_url.startsWith("https://")){
      return {src:chosen.image_url,
        alt:chosen.alt||"Immagine ufficiale della produzione di "+title,
        fallbackSrc:poster(title),
        sourceUrl:chosen.source_url,credit:chosen.credit,
        license:chosen.license||"",kind:chosen.kind};
    }
    const originalCovers={
      "oa-w-000020":"cover-jenufa.svg",
      "oa-w-000034":"cover-nixon-in-china.svg"
    };
    const localCover=originalCovers[event?.work_id] ||
      (slug==="jenufa"?"cover-jenufa.svg":null) ||
      (slug==="nixon-in-china"?"cover-nixon-in-china.svg":null);
    if(localCover){
      return {src:"./"+localCover,alt:"Copertina editoriale originale per "+title,
        fallbackSrc:poster(title),kind:"original_editorial_cover"};
    }
    // An archival cover selected by title cannot be reused for another
    // composition sharing that title. The ID-aware feed is preferred.
    const distinctRoute=event?.work_route_slug && event.work_route_slug!==slug;
    const file=distinctRoute ? null : WORKS[slug];
    return file?photo(file,"Documento d’archivio legato a "+title+" (non allestimento in calendario)",title):
      {src:poster(title),alt:"Copertina editoriale originale per "+title};
  }
  function venue(event){
    const city=commune(event?.municipality||event?.city);
    const title=event?.venue||event?.name||("Teatro di "+(event?.municipality||event?.city||"Italia"));
    const file=FILES[city];
    return file?photo(file,"Veduta del "+title+" a "+(event?.municipality||event?.city),title):
      {src:poster(title,"venue"),alt:"Illustrazione editoriale del "+title};
  }
  function festival(event){
    const title=event?.name||"Festival";
    const city=commune(event?.city);
    const file=FILES[city];
    return file?photo(file,"Veduta del teatro o luogo del festival a "+event.city,title):
      {src:poster(title,"festival"),alt:"Illustrazione originale del festival "+title};
  }
  function element(item,cls="card-image"){
    const picture=document.createElement("img");
    picture.className=cls;
    picture.alt=item.alt;
    picture.loading="lazy";
    picture.decoding="async";
    picture.referrerPolicy="no-referrer";
    picture.addEventListener("error",()=>{
      if(item.fallbackSrc && picture.src!==item.fallbackSrc)picture.src=item.fallbackSrc;
    },{once:true});
    if(item.credit)picture.title=item.credit+(item.license?" · "+item.license:"");
    picture.src=item.src;
    return picture;
  }
  function bindHero(){
    const hero=document.querySelector(".hero-image");
    if(!hero)return;
    hero.addEventListener("error",()=>{hero.src=poster("Il teatro d'opera");},{once:true});
  }
  bindHero();
  return {work,venue,festival,element,poster,load,FILES,WORKS};
})());