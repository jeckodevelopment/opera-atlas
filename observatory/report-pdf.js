"use strict";
/*
 * Opera+ Observatory: dependency-free, client-side, A4 editorial PDF.
 * Uses only filtered, verified public catalogue data. No external PDF service.
 * PDF 1.4 / WinAnsi Type 1 base fonts / vector charts.
 */
(function (root, factory) {
  const api=factory();
  if (typeof module==="object" && module.exports)module.exports=api;
  if (root)root.OperaPlusPdfReport=api;
})(typeof window!=="undefined"?window:null,function(){
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
  function summarize(input){
    const selected=input.rows||[],all=input.allRows||selected;
    const grouped=new Map();
    for(const r of selected){
      if(!grouped.has(r.workId))grouped.set(r.workId,{
        title:r.work,composer:r.composer,venues:new Set(),cities:new Set(),regions:new Set()});
      const g=grouped.get(r.workId);
      g.venues.add(r.venueId);
      if(r.city && r.city!=="Non indicata")g.cities.add(JSON.stringify([r.region,r.city]));
      if(r.region&&r.region!=="Non indicata")g.regions.add(r.region);
    }
    const circulation=[...grouped.values()].sort((a,b)=>
      b.venues.size-a.venues.size||b.cities.size-a.cities.size||a.title.localeCompare(b.title,"it"));
    const months=Array(12).fill(0),weekdays=Array(7).fill(0);
    for(const r of selected){
      const m=Number(r.date.slice(5,7));
      if(m>=1&&m<=12)months[m-1]++;
      const [y,mo,d]=r.date.split("-").map(Number);
      if(y&&mo&&d)weekdays[(new Date(Date.UTC(y,mo-1,d)).getUTCDay()+6)%7]++;
    }
    const regions=countBy(selected,r=>r.region);
    const cities=countBy(selected,r=>r.city&&r.city!=="Non indicata"?JSON.stringify([r.region,r.city]):null)
      .map(([k,v])=>[JSON.parse(k)[1]+"  ("+JSON.parse(k)[0]+")",v]);
    const venues=countBy(selected,r=>r.venueId).map(([key,value])=>
      [selected.find(r=>r.venueId===key)?.venue||"Sede non indicata",value]);
    const works=countBy(selected,r=>r.workId).map(([key,value])=>
      [selected.find(r=>r.workId===key)?.work||"Opera non indicata",value]);
    const composers=countBy(selected,r=>r.composer!=="Non indicato"?r.composer:null);
    const staging=countBy(selected,r=>r.stagingId).map(([key,value])=>
      [(selected.find(r=>r.stagingId===key)?.work||"Allestimento")+" - "+
        (selected.find(r=>r.stagingId===key)?.venue||""),value]);
    const rare=works.filter(w=>w[1]<=3);
    const diversity=new Map();
    for(const r of selected){
      if(!diversity.has(r.region))diversity.set(r.region,new Set());
      diversity.get(r.region).add(r.workId);
    }
    const varied=[...diversity].map(([k,v])=>[k,v.size])
      .sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],"it"));
    const year=String(input.year||"all"),season=String(input.season||"all"),region=String(input.region||"all");
    const filterRows=all.filter(r=>(season==="all"||r.season===season)&&(region==="all"||r.region===region));
    const allowed=new Set(filterRows.map(r=>r.workId));
    const editorials=input.editorials;
    const premieres=year!=="all" && editorials instanceof Map?
      [...editorials].filter(([id,x])=>allowed.has(id)&&Number(x.history?.premiere_year)===Number(year))
      .map(([,x])=>x).sort((a,b)=>a.work.title.localeCompare(b.work.title,"it")):null;
    return {selected,months,weekdays,regions,cities,venues,works,composers,staging,rare,varied,circulation,premieres,
      counts:{recite:selected.length,venues:unique(selected.map(r=>r.venueId)),
        works:unique(selected.map(r=>r.workId)),stagings:unique(selected.map(r=>r.stagingId))},
      year,season,region,reviewedOn:String(input.reviewedOn||"non indicata")};
  }
  function page(doc,label,index,fn){
    const p=new Page(label,index);fn(p);doc.addPage(p.ops);
  }
  function listPairs(p,pairs,y,{title,subtitle,limit=10}={}){
    if(title)p.text(title,L,y,16,"display",NAVY);
    if(subtitle)p.paragraph(subtitle,L,y+27,CW,10,15,MUTED,2);
    let top=y+(subtitle?65:40);
    for(const [name,val] of pairs.slice(0,limit)){
      p.line(L,top+27,W-R,top+27,BORDER,.55);
      p.text(splitLines(name,CW-120,10,1)[0]||"",L,top+6,10,"sans",INK);
      p.text(num(val),W-R-31,top+6,11,"bold",BURGUNDY);
      top+=32;
    }
    if(!pairs.length)p.text("Nessuna voce nel campione.",L,top+7,10,"sans",MUTED);
  }
  function pdfBytes(input){
    const s=summarize(input),doc=new PdfDocument();
    if(input.logo&&typeof input.logo.binary==="string")doc.addJpeg(input.logo.binary,input.logo.width,input.logo.height);
    const selection=[
      "Anno solare: "+(s.year==="all"?"tutti":s.year),
      "Stagione: "+(s.season==="all"?"tutte":s.season),
      "Territorio: "+(s.region==="all"?"tutta Italia":s.region)
    ];
    // 01 - Cover
    page(doc,"Copertina",1,p=>{
      p.rect(0,0,W,H,NAVY);
      p.rect(W-146,0,146,H,[26,31,45]);
      for(let i=0;i<5;i++)p.line(W-160+i*24,0,W-290+i*24,H,[43,43,55],2);
      p.rect(L,73,92,2,GOLD);
      if(doc.logoId){p.ops.push("q 156 0 0 73 "+L+" "+(H-102-73)+" cm /Logo Do Q")}
      else p.text("Opera+",L,100,35,"display",WHITE);
      p.text("OSSERVATORIO",L,173,12,"bold",GOLD);
      p.text("L'opera in Italia",L,227,40,"display",WHITE);
      p.paragraph("Rapporto sull'attività operistica rilevata da Opera+ Atlas.",
        L,289,375,15,23,[218,215,214],3,"serif");
      p.rect(L,371,CW,1,GOLD);
      p.text("PERIMETRO DELL'ANALISI",L,397,9,"bold",GOLD);
      selection.forEach((x,i)=>p.text(x,L,420+i*25,12,"sans",WHITE));
      p.text("Edizione dati: "+s.reviewedOn,L,523,10,"sans",[222,214,212]);
      const ks=[["Recite",s.counts.recite],["Teatri e sedi",s.counts.venues],
        ["Opere",s.counts.works],["Allestimenti",s.counts.stagings]];
      ks.forEach(([label,n],i)=>{
        let x=L+(i%2)*250,y=576+Math.floor(i/2)*67;
        p.text(num(n),x,y,28,"display",WHITE);p.text(label,x,y+34,10,"sans",[201,195,198]);
      });
      p.line(L,H-87,W-R,H-87,GOLD,1);
      p.text("Associazione Opera+  -  C.F. 97925160018",L,H-67,10,"sans",WHITE);
      p.paragraph("Dati non esaustivi del territorio italiano. Nessuna stima di spettatori o copertura nazionale.",
        L,H-44,CW,9,13,[213,208,208],2);
    });
    // 02 - Panorama
    page(doc,"Il quadro generale",2,p=>{
      p.section("01 / QUADRO GENERALE","La programmazione rilevata",
        "I numeri descrivono esclusivamente le recite pubblicate nel catalogo verificato.");
      p.numbers([["Recite rilevate",s.counts.recite],["Teatri e sedi con recite",s.counts.venues],
        ["Opere canoniche",s.counts.works],["Allestimenti",s.counts.stagings]],L,195,236);
      p.text("LETTURA DEL CAMPIONE",L,437,10,"bold",BURGUNDY);
      p.paragraph("Ogni recita è contata una sola volta. Titoli identici ma opere differenti mantengono identità canoniche separate. Le sedi sono contate solo quando presentano recite nel periodo selezionato.",
        L,463,CW,11,19,INK,6);
      p.rect(L,584,CW,102,PALE);
      p.text("Un dato da interpretare, non una classifica nazionale",L+20,606,15,"display",BURGUNDY);
      p.paragraph("L'Osservatorio misura ciò che è stato verificato e pubblicato da Atlas. Connettori, stagioni e repertorio possono avere coperture diverse: non stimiamo ciò che non è censito.",
        L+20,638,CW-40,10,15,INK,4);
    });
    // 03 - calendar months
    page(doc,"La programmazione mensile",3,p=>{
      p.section("02 / TEMPO","L'attività mese per mese",
        s.year==="all"?"Somma delle recite per mese su tutte le annualita selezionate.":"Calendario civile "+s.year+", con gli altri filtri applicati.");
      const top=235,graph=310,max=Math.max(1,...s.months),gap=8,bw=(CW-11*gap)/12;
      p.line(L,top+graph,W-R,top+graph,BORDER,1);
      s.months.forEach((value,i)=>{
        const x=L+i*(bw+gap),height=(value/max)*(graph-30);
        p.rect(x,top+graph-height,bw,height,BURGUNDY);
        p.text(num(value),x,top+graph-height-19,9,"bold",BURGUNDY);
        p.text(MONTHS[i],x,top+graph+10,8,"bold",INK);
      });
      p.rect(L,638,CW,76,IVORY);
      p.paragraph("Un valore zero significa nessuna recita rilevata nel catalogo per quel mese e per i filtri scelti, non assenza di attività sul territorio.",
        L+18,658,CW-36,10,16,MUTED,4);
    });
    // 04 - weekdays
    page(doc,"Giorni della settimana",4,p=>{
      p.section("03 / TEMPO","La settimana dell'opera",
        "Come si distribuiscono le date delle rappresentazioni dal lunedi alla domenica.");
      p.bars(DAYS.map((x,i)=>[x,s.weekdays[i]]),L,227,CW,{limit:7,step:58,labelWidth:98});
      p.rect(L,681,CW,59,IVORY);
      p.paragraph("I giorni sono letti dalla data locale verificata della recita. Non si ricostruiscono date o orari da un'etichetta di stagione.",
        L+15,696,CW-30,9,14,MUTED,3);
    });
    // 05 - regions and diversity
    page(doc,"Distribuzione territoriale",5,p=>{
      p.section("04 / GEOGRAFIA","Le regioni dell'opera",
        "Distribuzione delle recite e delle opere distinte nelle regioni presenti nel campione.");
      p.text("RECITE PER REGIONE",L,196,11,"bold",BURGUNDY);
      p.bars(s.regions,L,226,CW,{limit:10,step:32,labelWidth:143});
      p.text("VARIETA DEL REPERTORIO",L,606,11,"bold",BURGUNDY);
      p.paragraph("Opere canoniche differenti, indipendentemente dal numero di repliche.",L,628,CW,10,15,MUTED,2);
      p.bars(s.varied.slice(0,3),L,666,CW,{limit:3,step:30,labelWidth:143,barColor:GOLD});
    });
    // 06 - cities and theatres
    page(doc,"Citta e teatri",6,p=>{
      p.section("05 / GEOGRAFIA","Le sedi dell'attività operistica",
        "Graduatorie basate esclusivamente sulle rappresentazioni pubblicate in Atlas.");
      p.text("CITTA CON PIU RECITE RILEVATE",L,206,13,"bold",BURGUNDY);
      p.bars(s.cities,L,242,CW,{limit:7,step:37,labelWidth:171});
      p.text("TEATRI E SEDI CON PIU RECITE",L,553,13,"bold",BURGUNDY);
      p.bars(s.venues,L,591,CW,{limit:5,step:32,labelWidth:177,barColor:GOLD});
    });
    // 07 - repertoire
    page(doc,"Il repertorio",7,p=>{
      p.section("06 / REPERTORIO","Opere e compositori",
        "Il numero di rappresentazioni non è sinonimo di varietà del repertorio.");
      p.text("OPERE CON PIU RECITE",L,207,13,"bold",BURGUNDY);
      p.bars(s.works,L,245,CW,{limit:9,step:33,labelWidth:178});
      p.text("COMPOSITORI CON PIU RECITE",L,577,13,"bold",BURGUNDY);
      p.bars(s.composers,L,614,CW,{limit:5,step:32,labelWidth:178,barColor:GOLD});
    });
    // 08 - circulation
    page(doc,"La circolazione delle opere",8,p=>{
      p.section("07 / CIRCOLAZIONE","La diffusione del repertorio",
        "Numero di sedi, città e regioni differenti in cui ogni opera e presente nel campione.");
      const y=209;
      p.rect(L,y,CW,33,NAVY);
      p.text("OPERA",L+11,y+10,9,"bold",WHITE);
      p.text("SEDI",W-R-142,y+10,9,"bold",WHITE);
      p.text("CITTA",W-R-98,y+10,9,"bold",WHITE);
      p.text("REG.",W-R-44,y+10,9,"bold",WHITE);
      s.circulation.slice(0,12).forEach((w,i)=>{
        const yy=y+34+i*38;
        if(i%2===0)p.rect(L,yy,CW,38,IVORY);
        p.text(splitLines(w.title,269,10,1)[0]||"",L+10,yy+8,10,"bold",INK);
        p.text(splitLines(w.composer,269,8,1)[0]||"",L+10,yy+22,8,"sans",MUTED);
        p.text(String(w.venues.size),W-R-130,yy+12,10,"bold",BURGUNDY);
        p.text(String(w.cities.size),W-R-85,yy+12,10,"bold",INK);
        p.text(String(w.regions.size),W-R-32,yy+12,10,"bold",INK);
      });
      p.paragraph("Ogni opera e identificata dal suo ID canonico: repliche e fonti diverse nella stessa sede non aumentano la diffusione geografica.",
        L,721,CW,9,14,MUTED,4);
    });
    // 09 - premieres
    page(doc,"Prime assolute",9,p=>{
      p.section("08 / NUOVE OPERE","Le prime assolute",
        "Nuove composizioni riconosciute tramite le schede editoriali con anno storico di debutto verificato.");
      if(s.premieres===null){
        const noYear=s.year==="all";
        p.text(noYear?"Seleziona un singolo anno solare":"Dati editoriali non disponibili",L,221,22,"display",BURGUNDY);
        p.paragraph(noYear?"Il report non aggrega prime assolute di secoli diversi quando il filtro Anno solare è impostato su Tutti gli anni. Seleziona un anno nell'Osservatorio e rigenera il PDF.":"Non è stato possibile verificare il feed editoriale delle prime assolute. Nessun numero è stato stimato o inventato.",
          L,271,CW,11,18,MUTED,7);
      }else{
        p.text(num(s.premieres.length),L,202,50,"display",BURGUNDY);
        p.text("Opere con prima assoluta documentata nel "+s.year,L+80,230,12,"bold",INK);
        p.line(L,282,W-R,282,BORDER,.8);
        const limit=10;
        s.premieres.slice(0,limit).forEach((e,i)=>{
          const h=e.history,y=300+i*42;
          p.text(splitLines(e.work.title,270,11,1)[0]||"",L,y,11,"bold",INK);
          p.text(splitLines(e.work.composer,260,9,1)[0]||"",L,y+17,9,"sans",MUTED);
          const when=h.premiere_date||String(h.premiere_year);
          p.text(when,W-R-93,y+3,10,"bold",BURGUNDY);
          p.line(L,y+37,W-R,y+37,BORDER,.6);
        });
        p.paragraph("La data esatta può mancare; una prima annunciata nell'anno non è automaticamente già avvenuta. Stagione e territorio restringono le opere censite in Atlas, non la località storica della prima.",
          L,734,CW,9,14,MUTED,3);
      }
    });
    // 10 - stagings and rarities
    page(doc,"Allestimenti e rarita",10,p=>{
      p.section("09 / APPROFONDIMENTI","Allestimenti e titoli meno frequenti",
        "La stessa opera può avere allestimenti distinti e numeri di repliche differenti.");
      p.text("ALLESTIMENTI CON PIU RECITE",L,210,12,"bold",BURGUNDY);
      p.bars(s.staging,L,243,CW,{limit:8,step:36,labelWidth:206});
      p.text("OPERE CON 1-3 RECITE NEL CAMPIONE",L,582,12,"bold",BURGUNDY);
      const oneThree=s.rare.slice(0,6);
      oneThree.forEach(([name,n],i)=>{
        const yy=621+i*25;
        p.text(splitLines(name,390,9,1)[0]||"",L,yy,9,"sans",INK);
        p.text(num(n),W-R-24,yy,10,"bold",BURGUNDY);
      });
      if(!oneThree.length)p.text("Nessun titolo in questa classe.",L,631,10,"sans",MUTED);
    });
    // 11 - methodology
    page(doc,"Metodologia e fonti",11,p=>{
      p.section("10 / METODOLOGIA","Come leggere il rapporto",
        "Definizioni e limiti indispensabili per un utilizzo corretto dei risultati.");
      const blocks=[
        ["Fonte dei dati","Catalogo pubblico Opera+ Atlas. I quattro canali canonici contengono opere, sedi, allestimenti e recite verificate. Le prime assolute derivano dal distinto feed editoriale pubblico."],
        ["Identita e conteggi","Una recita viene contata una sola volta; le fonti multiple di un medesimo evento non costituiscono recite aggiuntive. Le opere sono distinte per ID canonico, non soltanto per titolo."],
        ["Anno solare e stagione","L'anno solare delle recite è ricavato dalle date verificate, la stagione è quella riportata per l'allestimento. I due filtri sono indipendenti e combinabili."],
        ["Prime assolute","L'anno di prima assoluta è un dato storico dell'opera. Una nuova produzione di un titolo preesistente non viene contata come nuova opera. Le date future e quelle non specificate non sono trattate come eventi già avvenuti."],
        ["Copertura","I dati non rappresentano necessariamente tutte le attività operistiche italiane. Non si formulano stime di pubblico, incassi o percentuali di copertura nazionale; un valore zero significa soltanto zero recite rilevate nel campione."],
        ["Aggiornamento e riproducibilita","Versione catalogo: "+s.reviewedOn+". Filtro anno: "+s.year+"; stagione: "+s.season+"; territorio: "+s.region+". Le classifiche sono ricalcolate a partire da questa selezione."],
      ];
      let y=209;
      for(const [heading,body] of blocks){
        p.text(heading,L,y,12,"bold",BURGUNDY);
        y=p.paragraph(body,L,y+22,CW,9.5,14,INK,4)+19;
      }
      p.line(L,721,W-R,721,BORDER,.8);
      p.text("opera.plus/atlas   |   opera.plus/osservatorio",L,736,10,"bold",BURGUNDY);
    });
    return doc.binary();
  }
  async function logoImage(){
    if(typeof document==="undefined"||typeof Image==="undefined")return null;
    return new Promise(resolve=>{
      const img=new Image();
      img.onload=()=>{
        try{
          const canvas=document.createElement("canvas");
          canvas.width=500;canvas.height=235;
          const context=canvas.getContext("2d");
          if(!context)throw Error("Canvas non disponibile");
          context.fillStyle="#101c2b";context.fillRect(0,0,500,235);
          context.drawImage(img,0,0,500,235);
          const data=canvas.toDataURL("image/jpeg",0.91).split(",")[1];
          resolve({binary:atob(data),width:500,height:235});
        }catch(_error){resolve(null)}
      };
      img.onerror=()=>resolve(null);
      img.src="./opera-plus-logo.svg";
    });
  }
  async function create(input){
    const logo=await logoImage();
    const bytes=pdfBytes({...input,logo});
    return new Blob([bytes],{type:"application/pdf"});
  }
  return {create,pdfBytes,summarize};
});
