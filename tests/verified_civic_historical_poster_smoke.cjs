"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const root=path.join(__dirname,"..");
const registry=JSON.parse(fs.readFileSync(path.join(root,"public/catalog/work-posters.json"),"utf8"));
const script=fs.readFileSync(path.join(root,"site/image-client.js"),"utf8");
const context={
  window:{},
  document:{querySelector(){return null}},
  console,
  fetch:async()=>({ok:true,json:async()=>registry})
};
vm.runInNewContext(script,context);
(async()=>{
  const images=context.window.OperaAtlasImages;
  await images.load();
  for(const [id,title,composer,kind] of [
    ["oa-w-000097","I salvatori della mezzanotte","Daniele Furlati","official_civic_production_image"],
    ["oa-w-000098","Candide","Leonard Bernstein","verified_historical_theatre_poster"]
  ]){
    const expected=registry.works[id];
    assert.ok(expected, `Missing work poster ${id}`);
    assert.equal(expected.kind,kind);
    const selected=images.work({work_id:id,title,composer});
    assert.equal(selected.src,expected.image_url,`Image must render for ${title}`);
    assert.equal(selected.kind,kind);
    assert.equal(selected.sourceUrl,expected.source_url);
    assert.equal(selected.credit,expected.credit);
    assert.equal(images.work({work_id:"oa-w-999999",title}).src,"",
      "Unknown canonical IDs must not reuse an image with the same title");
  }
  console.log("Verified historical and civic images resolve by canonical work ID");
})().catch(error=>{console.error(error);process.exitCode=1});
