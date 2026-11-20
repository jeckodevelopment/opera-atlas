"use strict";
/* Photo selections are historical/illustrative, never photos of the current production.
   Commons file pages and license/attribution sources are listed in credits.html.
   Every venue gets its own Commons image; other operas have individually composed artwork. */
window.OperaAtlasImages=Object.freeze((()=>{
  const FILES={
    "torino":"Teatro Regio - foto aerea.jpg",
    "como":"Teatro Sociale di Como.jpg",
    "pavia":"Teatro Fraschini - Pavia.jpg",
    "brescia":"Teatro Grande (Sala).jpg",
    "cremona":"Teatro Ponchielli in Cremona (1).jpg",
    "milano":"Teatro alla Scala interior Milan.jpg",
    "verona":"Verona-Arena-206-Poltronissima leer-1997-gje.jpg",
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
    "iris":"Iris, opera by Pietro Mascagni, poster by Adolf Hohenstein.jpg"
  };
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
    const file=WORKS[slug];
    return file?photo(file,"Locandina o immagine storica di "+title,title):
      {src:poster(title),alt:"Illustrazione editoriale originale per "+title};
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
    picture.src=item.src;
    return picture;
  }
  function bindHero(){
    const hero=document.querySelector(".hero-image");
    if(!hero)return;
    hero.addEventListener("error",()=>{hero.src=poster("Il teatro d'opera");},{once:true});
  }
  bindHero();
  return {work,venue,festival,element,poster,FILES,WORKS};
})());