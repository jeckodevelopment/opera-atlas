"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const code=fs.readFileSync(path.join(__dirname,"../site/catalog-client.js"),"utf8");
const ctx={window:{},document:{baseURI:"https://opera.plus/atlas/"},URL,console};
vm.createContext(ctx);
vm.runInContext(code,ctx);
const urls=ctx.window.OperaAtlasCatalog.urls({
  title:"Cavalleria rusticana",work_slug:"cavalleria-rusticana",
  municipality:"Torino",city_slug:"torino",
  venue:"Teatro Regio",venue_slug:"teatro-regio",
  staging_url:"/torino/teatro-regio/cavalleria-rusticana/"
});
assert.equal(urls.work,"/atlas/opere/cavalleria-rusticana/");
assert.equal(urls.venue,"/atlas/torino/teatro-regio/");
assert.equal(urls.staging,"/atlas/torino/teatro-regio/cavalleria-rusticana/");
assert.equal(urls.production,urls.staging);
const group=ctx.window.OperaAtlasCatalog.urls({
  title:"L'italiana in Algeri",municipality:"Como",venue:"Teatro Sociale",
  production_group_id:"oa-g-lombardia-italiana-2026"
});
assert.equal(group.production,"/atlas/produzioni/oa-g-lombardia-italiana-2026/");
assert.ok(Object.values(urls).every(x=>!x.includes("/dev/opera-atlas")));
const leoncavallo=ctx.window.OperaAtlasCatalog.urls({
  title:"La bohème",composer:"Ruggero Leoncavallo",work_id:"oa-w-000007",
  work_slug:"la-boheme",work_route_slug:"la-boheme-leoncavallo",
  city_slug:"torino",venue_slug:"teatro-regio",
  staging_url:"/torino/teatro-regio/la-boheme/"
});
const puccini=ctx.window.OperaAtlasCatalog.urls({
  title:"La bohème",composer:"Giacomo Puccini",work_id:"oa-w-000024",
  work_slug:"la-boheme",work_route_slug:"la-boheme-puccini",
  city_slug:"milano",venue_slug:"teatro-alla-scala",
  staging_url:"/milano/teatro-alla-scala/la-boheme/"
});
assert.equal(leoncavallo.work,"/atlas/opere/la-boheme-leoncavallo/");
assert.equal(puccini.work,"/atlas/opere/la-boheme-puccini/");
assert.notEqual(leoncavallo.work,puccini.work);
assert.equal(leoncavallo.staging,"/atlas/torino/teatro-regio/la-boheme/");
assert.equal(puccini.staging,"/atlas/milano/teatro-alla-scala/la-boheme/");
const regio=ctx.window.OperaAtlasCatalog.urls({
  venue:"Teatro Regio di Torino",municipality:"Torino",venue_slug:"teatro-regio",city_slug:"torino",
  title:"La bohème",work_slug:"la-boheme",work_route_slug:"la-boheme-leoncavallo",
  staging_url:"/torino/teatro-regio/la-boheme/"
});
assert.equal(regio.venue,"/atlas/torino/teatro-regio/");
assert.equal(regio.staging,"/atlas/torino/teatro-regio/la-boheme/");
console.log("Verified new opera.plus/atlas routes for opera, theatre, staging and production group.");
