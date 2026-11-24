"use strict";
/* Small editorial festival index, hosted with the GitHub catalog rather than SFTP.
   Festival events must join existing canonical staging IDs. No inferred listings. */
window.OperaAtlasFestivals=Object.freeze({
  async load(){
    const url="https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/festival-directory.json";
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("Festival catalog HTTP "+response.status);
    const doc=await response.json();
    if(doc.schema_version!==1||!Array.isArray(doc.festivals))throw Error("Unsupported festival catalog");
    const ids=new Set();
    return doc.festivals.filter(x=>{
      if(!x||typeof x.id!=="string"||!/^[a-z0-9-]{3,80}$/.test(x.id)||ids.has(x.id)||
        typeof x.name!=="string"||typeof x.city!=="string"||
        !Array.isArray(x.editions)||!Array.isArray(x.staging_ids)||x.staging_ids.some(id=>typeof id!=="string")||
        typeof x.official_url!=="string"||!x.official_url.startsWith("https://"))return false;
      ids.add(x.id);return true;
    });
  }
});