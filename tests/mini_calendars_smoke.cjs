"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
class El {
  constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.handlers={};this.className="";this.textContent="";
    this.classList={toggle:(c,on)=>{if(on)this.className+=" "+c;else this.className=this.className.replace(" "+c,"");}};}
  append(...args){this.children.push(...args);}
  replaceChildren(...args){this.children=[...args];}
  setAttribute(name,value){this.attrs[name]=value;}
  addEventListener(name,fn){this.handlers[name]=fn;}
}
const elements={};
const document={
  baseURI:"https://opera.plus/atlas/",createElement(tag){return new El(tag)},getElementById(id){return elements[id]||(elements[id]=new El("div"))}};
const root=path.join(__dirname,"..");
let code=fs.readFileSync(path.join(root,"site/detail.js"),"utf8");
code=code.replace(/\ninitialize\(\);\s*$/,"");
const context={document,console,URL,window:{location:{pathname:"/atlas/"}}};
vm.createContext(context);
vm.runInContext(code,context);
const dateSelector=vm.runInContext("dateSelector",context);
const events=[
 {local_date:"2026-12-12",time_known:true,starts_at:"2026-12-12T20:00",venue:"Teatro Regio",municipality:"Torino"},
 {local_date:"2026-12-14",time_known:true,starts_at:"2026-12-14T15:00",venue:"Teatro Regio",municipality:"Torino"},
 {local_date:"2026-12-19",time_known:false,starts_at:null,venue:"Teatro Regio",municipality:"Torino"}
];
const component=dateSelector(events);
assert.equal(component.children.length,2,"calendar and selected details");
const [grid,panel]=component.children;
assert.equal(grid.children.length,3);
for(const leaf of grid.children){
  assert.equal(leaf.tag,"button");
  assert.ok(leaf.children.some(c=>c.className==="mini-calendar-month"));
  assert.ok(leaf.children.some(c=>c.className==="mini-calendar-day"));
  assert.ok(leaf.children.some(c=>c.className==="mini-calendar-weekday"));
  assert.ok(!leaf.children.some(c=>String(c.textContent).includes("20:00")),"time should not appear in miniature");
}
assert.equal(grid.children[0].attrs["aria-pressed"],"true","first performance selected");
assert.equal(panel.children[1].textContent,"Inizio alle ore 20:00");
grid.children[1].handlers.click();
assert.equal(grid.children[1].attrs["aria-pressed"],"true");
assert.equal(grid.children[0].attrs["aria-pressed"],"false");
assert.equal(panel.children[1].textContent,"Inizio alle ore 15:00");
grid.children[2].handlers.click();
assert.equal(panel.children[1].textContent,"Orario da confermare");
assert.equal(panel.children[2].textContent,"Teatro Regio · Torino");
console.log("mini calendars: selectable dates, dynamic time and theatre, accessibility state OK");
