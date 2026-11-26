"use strict";
// Isolated report renderer; PDF primitives adapted from the existing Observatory.
(function(root,factory){const api=factory();if(typeof module==="object"&&module.exports)module.exports=api;else root.OperaPlusExplorePdf=api;})(globalThis,function(){
  const W=595.28,H=841.89,L=44,R=44,CW=W-L-R;
  const NAVY=[16,28,43], BURGUNDY=[142,31,69], GOLD=[186,147,85],
    INK=[39,41,52], MUTED=[100,104,115], IVORY=[250,248,245],
    PALE=[247,237,241], WHITE=[255,255,255], BORDER=[226,218,220];
  const MONTHS=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"];
  const DAYS=["Lun","Mar","Mer","Gio","Ven","Sab","Dom"];
  const num=n=>new Intl.NumberFormat("it-IT").format(n);
  const unique=a=>new Set(a).size;
  const countBy=(items,fn)=>{
    const m=new Map();for(const x of items){const k=fn(x);if(k!==null&&k!==undefined&&k!=="")m.set(k,(m.get(k)||0)+1)}
    return [...m].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0]),"it"));
  };
  function serializeText(s){
    let t=String(s??"").normalize("NFC");
    t=t.replace(/[\u2018\u2019\u02BC]/g,"'").replace(/[\u2013\u2014]/g,"-")
       .replace(/\u2026/g,"...").replace(/\u00a0/g," ").replace(/[\u2022\u25cf]/g,"-");
    return Array.from(t).map(ch=>{
      const cp=ch.codePointAt(0);
      // WinAnsi (Windows-1252) Type 1 fonts preserve Latin-1 Italian vowels.
      // Code points U+0080..U+009F are controls, not ordinary glyphs.
      if(cp>=32&&cp<=255&&(cp<127||cp>=160))return ch;
      if(ch==="\n")return " ";
      const decomp=ch.normalize("NFKD").replace(/[\u0300-\u036f]/g,"");
      const c=decomp.codePointAt(0);
      return c>=32&&c<=255?decomp:"?";
    }).join("");
  }
  const pdfText=s=>serializeText(s).replace(/\\/g,"\\\\").replace(/\(/g,"\\(").replace(/\)/g,"\\)");
  const rgb=c=>c.map(v=>(v/255).toFixed(3)).join(" ");
  const approx=(s,sz,kind="sans")=>Array.from(serializeText(s)).reduce((w,c)=>
    w+(c===" "?0.24:/[iIl!.,:;|']/.test(c)?0.27:/[mwMW@]/.test(c)?0.83:0.51)*sz,0)*(kind==="serif"?1.02:1);
  function splitLines(value,width,size,limit=10){
    const words=serializeText(value).split(/\s+/),out=[];let line="";
    for(const word of words){
      const next=line?line+" "+word:word;
      if(approx(next,size)>width && line){out.push(line);line=word}
      else line=next;
    }
    if(line)out.push(line);
    if(out.length>limit){
      out.length=limit;
      let last=out[limit-1];
      while(approx(last+"...",size)>width&&last.length)last=last.slice(0,-1);
      out[limit-1]=last+"...";
    }
    return out;
  }
  class PdfDocument{
    constructor(){
      this.objects=[""];this.pages=[];this.pagesId=this.object("");
      this.fonts={
        sans:this.object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"),
        bold:this.object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"),
        serif:this.object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>"),
        display:this.object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>")
      };
    }
    object(s){this.objects.push(s);return this.objects.length-1}
    addPage(ops,extra=""){
      if(this.logoId)extra+=" /XObject << /Logo "+this.logoId+" 0 R >>";
      const content=ops.join("\n");
      const dataId=this.object("<< /Length "+content.length+" >>\nstream\n"+content+"\nendstream");
      const ref=this.object("<< /Type /Page /Parent "+this.pagesId+" 0 R /MediaBox [0 0 "+W+" "+H+"] "+
        "/Resources << /Font << /F1 "+this.fonts.sans+" 0 R /F2 "+this.fonts.bold+" 0 R /F3 "+this.fonts.serif+" 0 R /F4 "+this.fonts.display+" 0 R >> "+extra+" >> "+
        "/Contents "+dataId+" 0 R >>");
      this.pages.push(ref);
    }
    addJpeg(binary,width,height){
      this.logoId=this.object("<< /Type /XObject /Subtype /Image /Width "+width+" /Height "+height+
        " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "+binary.length+" >>\nstream\n"+binary+"\nendstream");
    }
    binary(){
      this.objects[this.pagesId]="<< /Type /Pages /Count "+this.pages.length+" /Kids ["+
        this.pages.map(id=>id+" 0 R").join(" ")+"] >>";
      const catalog=this.object("<< /Type /Catalog /Pages "+this.pagesId+" 0 R >>");
      let out="%PDF-1.4\n%\xE2\xE3\xCF\xD3\n",positions=[0];
      for(let i=1;i<this.objects.length;i++){
        positions[i]=out.length;
        out+=i+" 0 obj\n"+this.objects[i]+"\nendobj\n";
      }
      const xref=out.length;
      out+="xref\n0 "+this.objects.length+"\n0000000000 65535 f \n";
      for(let i=1;i<this.objects.length;i++)out+=String(positions[i]).padStart(10,"0")+" 00000 n \n";
      out+="trailer\n<< /Size "+this.objects.length+" /Root "+catalog+" 0 R >>\nstartxref\n"+xref+"\n%%EOF";
      return new Uint8Array(Array.from(out,c=>c.charCodeAt(0)&255));
    }
  }
  class Page{
    constructor(label,index){
      this.ops=[];
      if(index===1)return;
      this.rect(0,0,W,9,NAVY);
      this.text("OPERA+",L,27,12,"display",BURGUNDY);
      this.text("OSSERVATORIO  /  "+serializeText(label).toUpperCase(),L,45,8,"bold",MUTED);
      this.line(L,60,W-R,60,BORDER,.7);
      this.line(L,H-50,W-R,H-50,BORDER,.7);
      this.text("Associazione Opera+  -  C.F. 97925160018",L,H-34,8,"sans",MUTED);
      this.text(String(index).padStart(2,"0"),W-R-18,H-34,9,"bold",BURGUNDY);
    }
    rect(x,y,w,h,color){this.ops.push(rgb(color)+" rg "+x.toFixed(2)+" "+(H-y-h).toFixed(2)+" "+w.toFixed(2)+" "+h.toFixed(2)+" re f")}
    line(x,y,x2,y2,color,width=1){this.ops.push(rgb(color)+" RG "+width+" w "+x+" "+(H-y)+" m "+x2+" "+(H-y2)+" l S")}
    text(value,x,y,size=11,font="sans",color=INK){
      this.ops.push(rgb(color)+" rg BT /F"+({sans:1,bold:2,serif:3,display:4}[font]||1)+" "+size+" Tf "+
        x.toFixed(2)+" "+(H-y-size).toFixed(2)+" Td ("+pdfText(value)+") Tj ET");
    }
    paragraph(value,x,y,w,size=10,leading=15,color=INK,maxLines=12,font="sans"){
      const lines=splitLines(value,w,size,maxLines);
      for(let i=0;i<lines.length;i++)this.text(lines[i],x,y+i*leading,size,font,color);
      return y+lines.length*leading;
    }
    section(no,title,subtitle){
      this.text(no,L,82,9,"bold",BURGUNDY);
      this.text(title,L,101,27,"display",NAVY);
      this.paragraph(subtitle,L,143,CW,10,15,MUTED,3);
    }
    pill(value,x,y,w){
      this.rect(x,y,w,32,IVORY);
      this.text(value,x+12,y+10,10,"bold",BURGUNDY);
    }
    bars(pairs,x,y,w,{limit=12,step=35,labelWidth=134,barColor=BURGUNDY,format=num}={}){
      const values=pairs.slice(0,limit),max=Math.max(1,...values.map(v=>v[1]));
      if(!values.length){this.paragraph("Nessun dato disponibile per la selezione.",x,y,w,11,15,MUTED);return}
      const barW=Math.max(35,w-labelWidth-65);
      values.forEach(([label,val],i)=>{
        const top=y+i*step;
        const labelString=splitLines(label,labelWidth-8,9.5,1)[0]||"";
        this.text(labelString,x,top+4,9.5,"sans",INK);
        this.rect(x+labelWidth,top+3,barW,15,PALE);
        if(val>0)this.rect(x+labelWidth,top+3,barW*val/max,15,barColor);
        this.text(format(val),x+labelWidth+barW+9,top+5,9.5,"bold",INK);
      });
    }
    numbers(entries,x,y,colW=160){
      for(let i=0;i<entries.length;i++){
        const col=i%2,row=Math.floor(i/2),xx=x+col*(colW+15),yy=y+row*94;
        this.rect(xx,yy,colW,79,IVORY);
        this.text(num(entries[i][1]),xx+13,yy+11,28,"display",BURGUNDY);
        this.paragraph(entries[i][0],xx+13,yy+51,colW-22,9,12,MUTED,2);
      }
    }
  }

 function create(input){
  const doc=new PdfDocument();let p,index=0,y=0;
  const start=(label)=>{if(p)doc.addPage(p.ops);p=new Page(label,++index+1);y=82};
  const title=(value)=>{p.text(value,L,y,24,"display",NAVY);y+=39};
  const para=(value)=>{for(const line of splitLines(value,CW,10,10000)){if(y>765)start("Filtri e metodologia");p.text(line,L,y,10,"sans",MUTED);y+=15}y+=7};
  const table=(label,headers,widths,records)=>{
   const header=()=>{start(label);title(label);p.rect(L,y,CW,28,NAVY);let x=L;
    headers.forEach((h,i)=>{p.text(h,x+5,y+8,8,"bold",WHITE);x+=widths[i]});y+=28};
   header();
   if(!records.length){para("Nessun dato nel campione selezionato.");return}
   for(const record of records){
    const lines=record.map((v,i)=>splitLines(String(v??""),widths[i]-10,9,8));
    const height=Math.max(24,...lines.map(a=>a.length*12+10));
    if(y+height>775)header();
    let x=L;lines.forEach((a,i)=>{a.forEach((line,j)=>p.text(line,x+5,y+6+j*12,9));x+=widths[i]});
    p.line(L,y+height,W-R,y+height,BORDER,.5);y+=height;
   }
  };
  start("Esplora i dati");title("Esplora i dati");
  para("Rapporto personalizzato sulla programmazione lirica italiana rilevata da Opera+ Atlas.");
  para("Versione catalogo: "+input.reviewedOn+" | Elaborazione: "+input.generatedOn);
  para("Filtri applicati: "+input.context);
  para("Raggruppamento: "+input.groupLabel+" | Indicatore: "+input.metricLabel);
  if(y>375)start("Indicatori");
  p.numbers(Object.entries(input.counts).map(([k,v])=>[input.labels[k]||k,v]),L,y,245);y+=385;
  if(y>680)start("Metodologia");
  para("Recite e produzioni contate per identità distinta. I programmi composti possono comparire in più gruppi. Zero indica assenza di dati rilevati, non assenza di attività. Le date trascorse non provano l'effettivo svolgimento. Annullamenti e rinvii esclusi.");
  start("Confronti");title("Confronto per "+input.groupLabel.toLocaleLowerCase("it"));
  const bars=input.groups.slice(0,12);
  p.bars(bars.map(g=>[g.label,g[input.metric]]),L,y+12,CW,{limit:12,step:35,labelWidth:205});
  y+=Math.max(55,bars.length*35+22);
  para("Grafico: "+bars.length+" di "+input.groups.length+" gruppi. Tabella completa nelle pagine successive.");
  table("Distribuzione mensile",["Mese","Recite","Produzioni"],[CW-150,75,75],input.months.map(g=>[g.label,num(g.performances),num(g.productions)]));
  table("Distribuzione territoriale",["Regione","Recite","Produzioni"],[CW-150,75,75],input.regions.map(g=>[g.label,num(g.performances),num(g.productions)]));
  table("Risultati aggregati",["Gruppo","Recite","Prod.","Sedi","Opere","Autori","Città","Reg.","Fest."],[CW-8*36,36,36,36,36,36,36,36,36],input.groups.map(g=>[g.label,...["performances","productions","venues","works","composers","cities","regions","festivals"].map(k=>num(g[k]))]));
  table("Dettaglio produzioni",["Opera / programma","Teatro e sede","Prima / ultima","Recite"],[CW-265,130,100,35],input.productions.map(r=>[r.title,r.venue+" · "+r.city,r.first+" / "+r.last,num(r.performances)]));
  if(p)doc.addPage(p.ops);return new Blob([doc.binary()],{type:"application/pdf"});
 }
 return Object.freeze({create});
});
