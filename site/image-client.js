"use strict";
/* Curated editorial imagery. These historical/illustrative photographs are NOT
   photos of a production on sale. Credits and licenses: docs/IMAGE_CREDITS.md.
   Asset links use Wikimedia Commons Special:Redirect/file (no unlicensed scraping). */
window.OperaAtlasImages=Object.freeze((()=>{
  const photo=(file,alt)=>({
    src:"https://commons.wikimedia.org/wiki/Special:Redirect/file/"+encodeURIComponent(file.replaceAll(" ","_"))+"?width=900",
    alt
  });
  const theatre=photo("Before the Opera begins.jpg","La sala di un teatro d'opera prima dell'inizio dello spettacolo");
  const stage=photo("Choreographed Opera Performance (Carmen by Bizet).jpg","Una scena dall'opera Carmen in un allestimento teatrale");
  const operaHouse=photo("Before the Opera begins.jpg","Atmosfera di una sala teatrale, fotografia illustrativa");
  const torino=photo("Teatro Regio - foto aerea.jpg","Il Teatro Regio di Torino visto dall'alto");
  const arena=photo("Verona-Arena-206-Poltronissima leer-1997-gje.jpg","L'Arena di Verona in una fotografia storica");
  const fenice=photo("Teatro-la-fenice-sala.jpg","La sala del Teatro La Fenice di Venezia");
  const traviata=photo("La Traviata, Hubbard Hall Opera Theater.jpg","Scena da una rappresentazione de La traviata");
  const tosca=photo("Oper für alle 2010 Tosca Bayerische Staatsoper Nationaltheater.JPG","Rappresentazione di Tosca nel 2010");
  function work(event){
    if(event && /carmen/i.test(event.title||""))return stage;
    if(event && /traviata/i.test(event.title||""))return traviata;
    if(event && /tosca/i.test(event.title||""))return tosca;
    if(event && /aida/i.test(event.title||"") && /verona/i.test(event.municipality||""))return arena;
    return theatre;
  }
  function venue(event){
    if(event && /torino/i.test(event.municipality||event.city||""))return torino;
    if(event && /verona/i.test(event.municipality||event.city||""))return arena;
    if(event && /venezia/i.test(event.municipality||event.city||""))return fenice;
    return theatre;
  }
  function festival(event){return event && /verona/i.test(event.city||"")?arena:theatre;}
  function element(image,cls="card-image"){
    const picture=document.createElement("img");
    picture.className=cls;
    picture.alt=image.alt;
    picture.addEventListener("error",()=>fallback(picture),{once:true});
    picture.src=image.src;
    picture.loading="lazy";
    picture.decoding="async";
    picture.referrerPolicy="no-referrer";
    return picture;
  }
  function fallback(picture){
    picture.onerror=null;
    picture.removeAttribute("src");
    picture.src="./opera-stage.svg";
    picture.alt="Illustrazione di un palcoscenico teatrale";
    picture.classList.add("image-fallback");
  }
  function bindHero(){
    const image=document.querySelector(".hero-image");
    if(!image)return;
    image.addEventListener("error",()=>fallback(image),{once:true});
    if(image.complete && image.naturalWidth===0)fallback(image);
  }
  bindHero();
  return {theatre,stage,operaHouse,torino,arena,fenice,traviata,tosca,work,venue,festival,element};
})());