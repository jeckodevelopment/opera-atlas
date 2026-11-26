"use strict";
const assert=require("node:assert/strict");
const e=require("../observatory-explore/engine.js");
const base={venue_id:"v1",venue:"Teatro A",municipality:"Torino",region:"Piemonte",status:"announced",season:"2026-2027"};
const events=[
 {...base,id:"r1",staging_id:"s1",work_id:"w1",title:"Rigoletto",composer:"Verdi",local_date:"2026-12-31"},
 {...base,id:"r2",staging_id:"s1",work_id:"w1",title:"Rigoletto",composer:"Verdi",local_date:"2027-01-01"},
 {...base,id:"r3",staging_id:"p1",title:"Dittico",local_date:"2026-10-01",program_components:[
  {work_id:"w1",title:"Rigoletto",composer:"Verdi"},{work_id:"w2",title:"Tosca",composer:"Puccini"},
  {title:"Non identificata",composer:""}]},
 {...base,id:"r4",staging_id:"s2",work_id:"w3",title:"Rigoletto",composer:"Altro",local_date:"2026-11-01",status:"cancelled"},
 {...base,id:"r5",staging_id:"s3",work_id:"w1",title:"Rigoletto",composer:"Verdi",local_date:"2026-11-01",status:"postponed"},
 {...base,id:"r6",staging_id:"s4",venue_id:"v2",venue:"Teatro B",municipality:"Milano",region:"Lombardia",work_id:"w1",title:"Rigoletto",composer:"Verdi",local_date:"2026-11-01"}
];
const rows=e.normalize(events,[{id:"f1",name:"Festival",staging_ids:["s1"]},{id:"f2",name:"Secondo festival",staging_ids:["s1"]}]);
assert.equal(rows.length,4);
assert.equal(e.summary(rows).performances,4);
assert.equal(e.summary(rows).productions,3);
assert.equal(e.summary(rows).works,2);
assert.equal(e.summary(rows).festivals,2);
assert.equal(e.summary(rows).venues,2);
const selected=e.select(rows,{year:["2026"],work:["w1"]});
assert.equal(e.summary(selected).performances,3);
assert.equal(e.summary(selected).works,1);
assert.equal(e.group(selected,"work")[0].performances,3);
assert.equal(e.group(rows,"work").find(x=>x.id==="w2").performances,1);
assert.equal(e.select(rows,{work:["w1"],composer:["Puccini"]}).length,0);
assert.equal(e.select(rows,{year:["2027"],season:["2026-2027"]}).length,1);
assert.equal(e.select(rows,{festival:["f1"],type:"festival"}).length,2);
assert.equal(e.summary(e.select(rows,{festival:["f1"]})).festivals,1);
assert.equal(e.select(rows,{region:["Lombardia"],city:[JSON.stringify(["Lombardia","Milano"])]}).length,1);
assert.equal(e.select(rows,{temporal:"future"},"2026-12-31").length,2);
assert.equal(e.select(rows,{temporal:"past"},"2026-12-31").length,2);
assert.equal(e.select(rows,{from:"2026-10-01",to:"2026-10-01"}).length,1);
assert.equal(e.productions(selected).find(p=>p.id==="s1").performances,1);
assert.equal(e.productions(rows).find(p=>p.id==="s1").performances,2);
assert.throws(()=>e.normalize([...events,events[0]],[]),/duplicata/);
assert.throws(()=>e.select(rows,{from:"2027-01-01",to:"2026-01-01"}),/Intervallo/);
assert.equal(e.summary([]).performances,0);
console.log("Explore engine smoke tests passed");
