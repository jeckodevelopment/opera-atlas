"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const script=fs.readFileSync(path.resolve(__dirname,"../site/app.js"),"utf8");
const start=script.indexOf("function renderMap(events) {");
const end=script.indexOf("\nfunction render() {",start);
assert.ok(start>=0&&end>start);
const elements={};
class Element{
  constructor(tag){this.tag=tag;this.attrs={};this.children=[];this.textContent="";this.className="";}
  setAttribute(k,v){this.attrs[k]=String(v);}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=[...children];}
}
const document={
  getElementById(id){return elements[id]||(elements[id]=new Element("div"));},
  createElement(tag){return new Element(tag);},
  createElementNS(ns,tag){return new Element(tag);}
};
const context={
 document,
 Map,
 CITY_CENTERS:{"torino":[45.0703,7.6869],"verona":[45.4384,10.9916]},
 normalized:s=>s.toLowerCase(),
 node:(tag,cls,value)=>{const e=new Element(tag);e.className=cls||"";e.textContent=value||"";return e;},
 window:{OperaAtlasCatalog:{urls:event=>({venue:"/dev/opera-atlas/"+event.municipality.toLowerCase()+"/"+event.venue.toLowerCase().replaceAll(" ","-")+"/"})}}
};
vm.createContext(context);
vm.runInContext(script.slice(start,end),context);
const render=context.renderMap;
function event(venue,municipality){return {venue,municipality};}
render([event("Teatro Regio","Torino"),event("Teatro Regio","Torino")]);
let holder=document.getElementById("atlas-map");
assert.equal(holder.children[0].tag,"svg");
assert.ok(Number(holder.children[0].attrs.viewBox.split(" ")[2])<=350,"Single venue should auto-zoom");
assert.equal(document.getElementById("map-venues").children.length,1);
const anchor=holder.children[0].children.find(x=>x.tag==="a");
assert.ok(anchor.attrs.href.includes("/torino/"));
assert.ok(anchor.attrs["aria-label"].includes("2 rappresentazioni"));
render([]);
holder=document.getElementById("atlas-map");
assert.equal(holder.children[0].className,"map-empty");
assert.match(holder.children[0].children[0].textContent,/Nessun teatro/);
render([event("Teatro Regio","Torino"),event("Arena di Verona","Verona")]);
assert.equal(document.getElementById("map-venues").children.length,2);
assert.equal(holder.children[0].tag,"svg");
console.log("Map renders auto-zoom, navigable markers, per-venue counts and a clear empty state.");
