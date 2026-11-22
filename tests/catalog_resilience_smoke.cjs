"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ROOT=path.resolve(__dirname,"..");
global.window=global;
global.document={baseURI:"https://opera.plus/atlas/"};
if(!global.crypto || !global.crypto.subtle)Object.defineProperty(global,"crypto",{value:require("node:crypto").webcrypto,configurable:true});
const RAW="https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/";
const MIRROR="https://cdn.jsdelivr.net/gh/jeckodevelopment/opera-atlas@main/public/catalog/v2/";
require(path.join(ROOT,"site/catalog-client.js"));
function mockResponse(buffer){return {ok:true,status:200,async arrayBuffer(){return Uint8Array.from(buffer).buffer;},async json(){return JSON.parse(buffer.toString("utf8"));}};}
function useFetch(mode){
 global.fetch=async input=>{
   const url=String(input);
   if(mode==="raw-blocked" && url.startsWith(RAW))throw Error("raw blocked");
   if(mode==="offline" && (url.startsWith(RAW)||url.startsWith(MIRROR)))throw Error("offline");
   let file;
   if(url===RAW.replace(/v2\/$/,"")+"programs.json" ||
      url===MIRROR.replace(/v2\/$/,"")+"programs.json")
      file=path.join(ROOT,"public/catalog/programs.json");
   else if(url===RAW.replace(/v2\/$/,"")+"venue-directory.json" ||
      url===MIRROR.replace(/v2\/$/,"")+"venue-directory.json")
      file=path.join(ROOT,"public/catalog/venue-directory.json");
   else if(url.startsWith(RAW))file=path.join(ROOT,"public/catalog/v2",url.slice(RAW.length).split("?")[0]);
   else if(url.startsWith(MIRROR))file=path.join(ROOT,"public/catalog/v2",url.slice(MIRROR.length).split("?")[0]);
   else if(url==="./performances.json")file=path.join(ROOT,"site/performances.json");
   else throw Error("Unexpected URL: "+url);
   return mockResponse(fs.readFileSync(file));
 };
}
(async()=>{
  useFetch("online");
  let data=await OperaAtlasCatalog.load();
  assert.equal(data.source,"github");
  assert.ok(data.performances.length>=200);
  assert.equal(data.performances.filter(x=>x.program_id==="oa-p-a12dbb283b490075").length,7);
  assert.ok(data.performances.some(x=>x.program_id&&x.municipality==="Jesi"&&x.venue_slug==="teatro-giovan-battista-pergolesi"));
  assert.ok(data.performances.some(x=>x.production_group_id==="oa-g-lombardia-italiana-2026"));
  useFetch("raw-blocked");
  data=await OperaAtlasCatalog.load();
  assert.equal(data.source,"github");
  assert.ok(data.performances.length>=200);
  useFetch("offline");
  data=await OperaAtlasCatalog.load();
  assert.equal(data.source,"fallback");
  assert.ok(data.performances.length>=200);
  process.stdout.write("catalog: primary, mirror and snapshot all pass\n");
})().catch(e=>{console.error(e);process.exitCode=1;});