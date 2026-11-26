"use strict";
const assert=require("node:assert/strict");
const D=require("../observatory-explore/data.js");
const E=require("../observatory-explore/engine.js");
const data={source:"github",reviewed_on:"2026-11-26",works:[],performances:[
 {id:"r1",staging_id:"s1",venue_id:"v1",title:"Rigoletto",work_id:"w1",composer:"Verdi",venue:"Regio",municipality:"Torino",region:"Piemonte",local_date:"2026-12-01"},
 {id:"r2",staging_id:"s2",venue_id:"v2",title:"Tosca",work_id:"w2",composer:"Puccini",venue:"Scala",municipality:"Milano",region:"Lombardia",local_date:"2027-01-01"},
 {id:"pr1",program_id:"p1",staging_id:"p1",venue_id:"v2",title:"Dittico",program_components:[{work_id:"w1",title:"Rigoletto",composer:"Verdi"},{work_id:"w2",title:"Tosca",composer:"Puccini"}],venue:"Scala",municipality:"Milano",region:"Lombardia",local_date:"2026-12-01"}
]};
const programs={schema_version:1,programs:[{id:"p1",components:[],performances:[{id:"pr1",local_date:"2026-12-01"}]}]};
const festivals={schema_version:1,festivals:[{id:"f1",name:"Festival",staging_ids:["s1"]}]};
const response=value=>({ok:true,json:async()=>value});
const fetcher=async url=>response(url.endsWith("programs.json")?programs:festivals);
async function run(){
 const loaded=await D.load({load:async()=>data},fetcher);
 assert.equal(loaded.mirror,false);
 const rows=E.normalize(loaded.data.performances,loaded.festivals);
 assert.equal(E.summary(rows).performances,3);
 assert.equal(D.options(rows,"work").length,2);
 assert.equal(D.options(rows,"city",["Piemonte"]).length,1);
 assert.equal(D.options(rows,"venue",["Lombardia"])[0].id,"v2");
 assert.equal(D.options(rows,"year")[0].id,"2027");
 assert.equal(D.today(new Date("2026-12-31T23:30:00Z")),"2027-01-01");
 assert.equal(D.atlasRoute("/programmi/oa-p-123/"),"https://opera.plus/atlas/programmi/oa-p-123/");
 assert.equal(D.atlasRoute("//evil.test/"),null);
 assert.equal(D.sourceUrl("javascript:alert(1)"),null);
 assert.deepEqual(D.sortRows([{id:"a",n:2},{id:"b",n:11}],"n",true).map(x=>x.id),["b","a"]);
 assert.throws(()=>D.validateCompanions(data,{...programs,programs:[]},festivals),/programmi/);
 assert.throws(()=>D.validateCompanions(data,programs,{...festivals,festivals:[{id:"f",name:"F",staging_ids:["missing"]}]}),/festival/);
 await assert.rejects(()=>D.load({load:async()=>({...data,source:"fallback"})},fetcher),/remoto/);
 await assert.rejects(()=>D.load({load:async()=>data},async()=>({ok:false,status:404})),/Indici/);
 const mirror=await D.load({load:async()=>data},async url=>url.includes("raw.githubusercontent")?{ok:false,status:503}:fetcher(url));
 assert.equal(mirror.mirror,true);
 console.log("Explore loader and filter helpers passed");
}
run().catch(error=>{console.error(error);process.exitCode=1});
