"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
class Element {
  constructor(tag){this.tagName=tag;this.className="";this.children=[];this.attrs={};this.insertedAfter=[];this.textContent="";}
  append(...items){this.children.push(...items);}
  prepend(...items){this.children.unshift(...items);}
  after(...items){this.insertedAfter.push(...items);}
  setAttribute(name,value){this.attrs[name]=value;}
  get firstChild(){return this.children[0]||null;}
}
const ids={};
const document={
  baseURI:"https://opera.plus/atlas/",
  getElementById(id){return ids[id]||(ids[id]=new Element("div"));},
  createElement(tag){return new Element(tag);}
};
const context={document,window:{OperaAtlasCatalog:{urls(e){return {work:"/atlas/opere/"+e.work_slug+"/"};}}},console,URL,
  fetch:async url=>{
    let file;
    if(String(url).includes("public/catalog/work-editorial.json"))file="public/catalog/work-editorial.json";
    else if(String(url).includes("work-synopses.json"))file="site/work-synopses.json";
    else if(String(url).includes("work-history.json"))file="site/work-history.json";
    else throw Error("Unexpected fetch "+url);
    return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,file),"utf-8"))};
  }
};
let code=fs.readFileSync(path.join(root,"site/detail.js"),"utf-8").replace(/\ninitialize\(\);\s*$/,"");
vm.createContext(context);
vm.runInContext(code,context);
(async()=>{
  const sample={work_slug:"cavalleria-rusticana"};
  await vm.runInContext("appendSynopsis",context)(sample);
  const content=ids["detail-content"];
  assert.ok(content.children.some(x=>x.className==="brief-synopsis"),"synopsis appended");
  await vm.runInContext("appendHistory",context)(sample);
  const history=content.children.find(x=>x.className.split(" ").includes("work-history"));
  assert.ok(history,"history appended");
  const story=history.children.find(x=>x.className==="work-history-story");
  assert.ok(story,"narrative paragraph expected");
  assert.match(story.textContent,/Giovanni Targioni-Tozzetti/);
  assert.match(story.textContent,/^La prima rappresentazione ebbe luogo nel 1890 al Teatro Costanzi di Roma su libretto di Giovanni Targioni-Tozzetti e Guido Menasci\./);
  assert.match(story.textContent,/L’opera fu composta nel 1889\./);
  assert.match(story.textContent,/1890/);
  assert.match(story.textContent,/Teatro Costanzi di Roma/);
  // Upcoming world premieres must use future tense, including when the
  // editorial feed only provides a year and not an exact date.
  const future={work_id:"oa-w-000074",work_slug:"code-unknown"};
  await vm.runInContext("appendHistory",context)(future);
  const futureStory=content.children.filter(x=>x.className.split(" ").includes("work-history")).at(-1)
    .children.find(x=>x.className==="work-history-story");
  assert.match(futureStory.textContent,/^La prima assoluta è prevista nel 2027 al Teatro Nazionale di Roma/);
  assert.doesNotMatch(futureStory.textContent,/ebbe luogo/);
  assert.ok(!history.children.some(x=>x.tagName==="dl"),"no metadata definition list");
  const links=ids["detail-events"].insertedAfter;
  assert.equal(links.length,1,"one historical source section");
  assert.ok(links[0].children[1].href.includes("archiviostorico.operaroma.it"));
  console.log("Work synopsis, five sourced fields and one footer archival link verified.");
})().catch(error=>{console.error(error);process.exitCode=1;});
