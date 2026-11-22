"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const root=path.join(__dirname,"..");
const script=fs.readFileSync(path.join(root,"site/image-client.js"),"utf8");
const registry=JSON.parse(fs.readFileSync(path.join(root,"public/catalog/work-posters.json"),"utf8"));
const id="oa-w-000079";
assert.equal(registry.schema_version,2);
assert.equal(registry.works[id]?.kind,"official_coproduction_poster",
  "Bona Sforza must have a verified official coproduction poster in the published feed");
const image=registry.works[id].image_url;
const context={
  window:{},
  document:{querySelector(){return null}},
  console,
  fetch:async()=>({ok:true,json:async()=>registry})
};
vm.runInNewContext(script,context);
const lib=context.window.OperaAtlasImages;
(async()=>{
  await lib.load();
  const selected=lib.work({work_id:id,title:"Bona Sforza",composer:"Zygmunt Krauze"});
  assert.equal(selected.src,image,"the frontend must render the verified Bona Sforza poster");
  assert.equal(selected.kind,"official_coproduction_poster");
  assert.equal(selected.sourceUrl,registry.works[id].source_url);
  assert.equal(lib.work({work_id:"oa-w-999999",title:"Unlisted work"}).src,"",
    "unverified works must not receive a fabricated or borrowed poster");
  console.log("Bona Sforza official coproduction poster resolved by work ID");
})().catch(error=>{console.error(error);process.exitCode=1});
