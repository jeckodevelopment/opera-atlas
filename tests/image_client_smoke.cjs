"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const root=path.join(__dirname,"..");
const source=fs.readFileSync(path.join(root,"site/image-client.js"),"utf8");
const photos=[];
const hero={addEventListener(type,handler){this[type]=handler},src:"broken",classList:{add(){}}};
const doc={
  querySelector(sel){return sel===".hero-image"?hero:null},
  createElement(tag){
    assert.equal(tag,"img");
    const img={handlers:{},classList:{add(){}},addEventListener(type,handler){this.handlers[type]=handler},removeAttribute(name){if(name==="src")this.src=""}};
    photos.push(img);return img;
  }
};
const context={window:{},document:doc,console};
vm.runInNewContext(source,context);
const lib=context.window.OperaAtlasImages;
assert.ok(lib,"image library must initialize");
assert.equal(Object.keys(lib.FILES).length,15,"one theatre photo per city and a separate festival venue");
assert.ok(Object.keys(lib.WORKS).length>=12,"opera-specific historic posters");
const venues=[
  ["Torino","Teatro Regio"],["Como","Teatro Sociale"],["Pavia","Teatro Fraschini"],
  ["Brescia","Teatro Grande"],["Cremona","Teatro Ponchielli"],["Milano","Teatro alla Scala"],
  ["Verona","Arena di Verona"],["Venezia","Teatro La Fenice"],["Palermo","Teatro Massimo"],
  ["Parma","Teatro Regio di Parma"],["Novara","Teatro Coccia"],["Bergamo","Teatro Donizetti"],
  ["Reggio Emilia","Teatro Valli"],["Ravenna","Teatro Dante Alighieri"]
];
const ids=new Set(venues.map(([city,name])=>lib.venue({municipality:city,venue:name}).src));
assert.equal(ids.size,venues.length,"each theatre needs a different image");
for(const [city,name] of venues){
  const item=lib.venue({municipality:city,venue:name});
  assert.ok(item.src.startsWith("https://commons.wikimedia.org/wiki/Special:Redirect/file/"),city);
  const img=lib.element(item,"directory-image");
  assert.ok(img.handlers.error,city);
  img.handlers.error();
  assert.ok(img.src.startsWith("data:image/svg+xml"),"theatre fallback is self-contained");
}
const posterWorks=[
 "La traviata","L'italiana in Algeri","Edgar","Salome","Cavalleria rusticana",
 "Pagliacci","La bohème","Iris","Carmen","Evgenij Onegin","Turandot",
 "Un ballo in maschera","Death in Venice","Otello","Aida","Fedora",
 "Samson et Dalila","Macbeth","Madama Butterfly","Jenůfa","Lucia di Lammermoor",
 "Tosca","Don Giovanni","Nabucco","Rigoletto"];
const images=posterWorks.map(title=>lib.work({title}));
assert.ok(Object.keys(lib.WORKS).length>=25,"legacy operas must map to authentic sources");
for(const title of posterWorks){
  const item=lib.work({title});
  assert.ok(item.src.startsWith("https://commons.wikimedia.org/"),
    title+" must use archival material, never a fictional primary poster");
}
assert.match(lib.WORKS["cavalleria-rusticana"],/Cavalleria rusticana poster/);
assert.match(lib.WORKS["pagliacci"],/Pagliacci Original Score Cover/);
assert.match(lib.WORKS["un-ballo-in-maschera"],/Vocal score frontispiece/);
assert.ok(lib.work({title:"Nixon in China",work_id:"oa-w-000034"}).src.includes("Dortmund_Kampstr_Nixon_in_China"));
assert.ok(lib.work({title:"Jenůfa",work_id:"oa-w-000020"}).src.includes("Jenufa.jpg"));

const restored=[
  ["oa-w-000001","Giuseppe Verdi","Traviata.jpg"],
  ["oa-w-000002","Gioachino Rossini","1930-Italiana-in-Algeri.jpg"],
  ["oa-w-000006","Ruggero Leoncavallo","Pagliacci_Original_Score_Cover.jpg"],
  ["oa-w-000010","Pëtr Il'ič Čajkovskij","Yerevan_Opera_Theatre.jpg"],
  ["oa-w-000011","Giacomo Puccini","Poster_Turandot.jpg"],
  ["oa-w-000025","Giuseppe Verdi","Nabucco_-_1852_cover.jpg"]
];
for(const [work_id,composer,file] of restored){
  const item=lib.work({title:"opera",work_id,composer});
  assert.equal(item.kind,"archival_work_image",work_id);
  assert.ok(item.src.includes(file),work_id+" must not use cached staging photo");
  assert.ok(item.sourceUrl.startsWith("https://commons.wikimedia.org/wiki/File:"),work_id);
}
assert.equal(new Set(images.map(x=>x.src)).size,images.length,"every opera needs a distinct image");
for(const item of images){
  if(item.src.startsWith("https://")){
    const img=lib.element(item,"event-image");
    img.handlers.error();
    assert.equal(img.hidden,true,"broken historical image must hide instead of showing fictional art");
  }else assert.equal(item.src,"","missing real artwork must not become fictional art");
}
hero.error();
assert.ok(hero.src.startsWith("data:image/svg+xml"),"hero should not be an empty image");
console.log("theatre photos: 14 distinct; opera art: authentic sourced only; no fictitious covers");
