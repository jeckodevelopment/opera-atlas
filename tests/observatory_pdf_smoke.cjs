"use strict";
const assert=require("node:assert/strict");
const {pdfBytes,summarize}=require("../observatory/report-pdf.js");
const row=(id,day,workId,work,composer,venueId,venue,city,region,stagingId)=>({
  id,date:day,year:day.slice(0,4),season:"2026-2027",region,city,venueId,venue,workId,work,composer,stagingId
});
const rows=[
 row("a","2026-11-14","w1","L'esecuzione","Salvatore Passantino","v1","Teatro Pergolesi","Jesi","Marche","s1"),
 row("b","2026-11-15","w1","L'esecuzione","Salvatore Passantino","v1","Teatro Pergolesi","Jesi","Marche","s1"),
 row("c","2026-11-20","w1","L'esecuzione","Salvatore Passantino","v2","Teatro di Prova","Torino","Piemonte","s2"),
 row("d","2026-12-21","w2","La traviata","Giuseppe Verdi","v2","Teatro di Prova","Torino","Piemonte","s3"),
];
const input={rows,allRows:rows,year:"2026",season:"all",region:"all",reviewedOn:"2026-11-23",
 editorials:new Map([["w1",{work:{title:"L'esecuzione",composer:"Salvatore Passantino"},history:{
   premiere_year:2026,premiere_date:"2026-11-14",sources:["https://example.org/official"]}}]])};
const summary=summarize(input);
assert.equal(summary.counts.recite,4);
assert.equal(summary.counts.venues,2);
assert.equal(summary.counts.works,2);
assert.equal(summary.counts.stagings,3);
assert.equal(summary.months.reduce((a,b)=>a+b,0),4);
assert.equal(summary.weekdays.reduce((a,b)=>a+b,0),4);
assert.equal(summary.circulation.find(w=>w.title==="L'esecuzione").venues.size,2);
assert.equal(summary.circulation.find(w=>w.title==="L'esecuzione").regions.size,2);
assert.equal(summary.premieres.length,1);
function validatePdf(params){
 const bytes=pdfBytes(params);
 const source=Buffer.from(bytes).toString("latin1");
 assert.ok(source.startsWith("%PDF-1.4\n"));
 assert.equal((source.match(/\/Type \/Page \/Parent/g)||[]).length,11);
 const xref=Number(source.match(/startxref\n(\d+)\n%%EOF$/)?.[1]);
 assert.equal(source.slice(xref,xref+5),"xref\n");
 assert.match(source,/Associazione Opera/);
 assert.match(source,/METODOLOGIA/);
 assert.match(source,/La traviata/);
 assert.ok(!source.includes("NaN"),"PDF must contain no NaN coordinates");
 assert.ok(bytes.length>15000);
 return source;
}
const accentedRows=[{...rows[0],work:"Città e libertà",composer:"André Chénier",venue:"Teatro dell'Università",city:"Forlì",region:"Emilia-Romagna"}];
const accentedPdf=validatePdf({...input,rows:accentedRows,allRows:accentedRows,region:"Emilia-Romagna"});
// WinAnsi strings in PDF content streams must retain the literal accented
// bytes instead of replacing them with unaccented approximations.
for(const word of ["attività","città","è","più","varietà","libertà","Forlì","Università","André"]){
 assert.ok(accentedPdf.includes(word),"Missing accented glyph in PDF: "+word);
}
assert.ok(!accentedPdf.includes("L'attivita mese per mese"));
validatePdf(input);
const missing=validatePdf({...input,editorials:null});
assert.match(missing,/Dati editoriali non disponibili/);
const noYear=validatePdf({...input,year:"all"});
assert.match(noYear,/Seleziona un singolo anno solare/);
const zero=pdfBytes({...input,rows:[],allRows:[],editorials:new Map()});
assert.equal((Buffer.from(zero).toString("latin1").match(/\/Type \/Page \/Parent/g)||[]).length,11);
console.log("PDF smoke tests passed: 11 pages, xref, filtering, missing data, empty selection.");
