"use strict";
const assert=require("node:assert/strict");
const E=require("../observatory-explore/engine.js");
const A=require("../observatory-explore/analysis.js");
const event=(id,stage,work,title,composer,date,extra={})=>({
 id,staging_id:stage,work_id:work,title,composer,local_date:date,venue_id:"v1",venue:"Teatro",municipality:"Torino",region:"Piemonte",status:"announced",...extra
});
const rows=E.normalize([
 event("r1","s1","w1","Rigoletto","Verdi","2026-01-03"),
 event("r2","s1","w1","Rigoletto","Verdi","2026-01-04"),
 event("r3","s1","w1","Rigoletto","Verdi","2026-03-05"),
 event("r4","s1","w1","Rigoletto","Verdi","2027-01-01"),
 event("r5","p1",null,"Dittico","","2026-03-06",{program_components:[
  {work_id:"w1",title:"Rigoletto",composer:"Verdi"},{work_id:"w2",title:"Tosca",composer:"Puccini"}
 ]}),
 event("r6","s2","w3","Opera rara","Autore","2026-02-02",{venue_id:"v2",venue:"Altro teatro",municipality:"Milano",region:"Lombardia"}),
 event("r7","s3","w4","Opera annullata","Autore","2026-02-02",{status:"cancelled"})
],[{id:"f1",name:"Festival",staging_ids:["s1"]}]);
const year=E.select(rows,{year:["2026"]});
assert.equal(year.length,5);
const groups=A.compare(year,"work");
assert.equal(groups[0].performances,4);
assert.equal(groups[0].productions,2);
assert.equal(groups.find(g=>g.id==="w2").performances,1);
assert.equal(groups.reduce((n,g)=>n+g.performances,0),6);
assert.equal(E.summary(year).performances,5);
const rare=A.scope(year,"rare");
assert.equal(E.summary(rare).performances,2);
assert.equal(E.summary(rare).works,2);
assert.ok(rare.every(r=>r.works.every(w=>w.id!=="w1")));
assert.equal(A.scope(year,"custom"),year);
assert.equal(A.compare(year,"venue","works")[0].id,"v1");
assert.deepEqual(A.compare(rows,"year").map(g=>g.id),["2026","2027"]);
assert.deepEqual(A.compare(year,"region","performances","asc").map(g=>g.id),["Lombardia","Piemonte"]);
const months=A.monthly(year,{year:["2026"]});
assert.equal(months.length,12);
assert.equal(months[0].performances,2);
assert.equal(months[2].performances,2);
assert.equal(months[3].performances,0);
assert.equal(months[3].label,"Apr 2026");
assert.equal(A.monthly(year,{year:["2026"],from:"2026-02-01",to:"2026-03-01"}).length,2);
assert.equal(A.monthly([],{}).length,0);
assert.equal(A.monthly([],{year:["2026"]}).length,12);
assert.equal(A.monthly(rows,{}).length,13);
assert.equal(A.chartSubset(groups,"work","auto",2).total,3);
assert.equal(A.chartSubset(groups,"work","auto",2).items.length,2);
const scaled=A.barScale(groups,["performances","productions"]);
assert.equal(scaled[0].bars[0].percent,100);
assert.equal(scaled[0].bars[1].percent,50);
assert.equal(A.barScale([{performances:0}],["performances"])[0].bars[0].percent,0);
assert.throws(()=>A.compare(rows,"work","bad"),/Indicatore/);
assert.throws(()=>A.scope(rows,"bad"),/predefinita/);
console.log("Explore analysis, comparisons and presets passed");
