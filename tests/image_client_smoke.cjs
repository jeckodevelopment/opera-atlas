"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync(require("node:path").join(__dirname,"../site/image-client.js"),"utf8");
const images=[];
const hero={
  complete:true,naturalWidth:0,handlers:{},classList:{add(){}},
  addEventListener(type,fn){this.handlers[type]=fn},
  removeAttribute(name){delete this[name]}
};
const doc={
  querySelector(sel){return sel===".hero-image"?hero:null},
  createElement(tag){
    assert.equal(tag,"img");
    const image={tag,handlers:{},classList:{added:[],add(v){this.added.push(v)}},
      addEventListener(type,fn){this.handlers[type]=fn},
      removeAttribute(name){delete this[name]}};
    images.push(image);return image;
  }
};
const context={window:{},document:doc,console};
vm.runInNewContext(source,context);
const lib=context.window.OperaAtlasImages;
assert.ok(lib);
assert.match(hero.src,/opera-stage\.svg$/);
for(const work of ["Carmen","La traviata","Tosca","Rigoletto"]){
  const photo=lib.element(lib.work({title:work}),"event-image");
  assert.match(photo.src,/commons.wikimedia.org\/wiki\/Special:Redirect\/file\//);
  photo.handlers.error();
  assert.equal(photo.src,"./opera-stage.svg");
  assert.deepEqual(photo.classList.added,["image-fallback"]);
}
assert.match(lib.venue({city:"Venezia"}).src,/Teatro-la-fenice/);
assert.match(lib.venue({city:"Torino"}).src,/Teatro_Regio/);
assert.ok(fs.statSync(require("node:path").join(__dirname,"../site/opera-stage.svg")).size>1000);
process.stdout.write("image library loaded; opera, venue and local fallbacks verified\n");
