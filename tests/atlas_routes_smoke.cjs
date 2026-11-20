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
console.log("Verified new opera.plus/atlas routes for opera, theatre, staging and production group.");
