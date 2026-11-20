"use strict";
/* Public static client. No credentials, server or runtime dependencies.
   Reads the mutable v2 manifest, then immutable SHA-256-addressed channels.
   A failed/incomplete remote release falls back to the last SFTP snapshot
   with an explicit warning. The SFTP fallback is not a live data source. */
window.OperaAtlasCatalog = (() => {
  const BASE = "https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/";
  const CHANNELS = ["works","venues","stagings","performances"];

  const PREFIX = "/dev/opera-atlas";

  function slugify(text) {
    return String(text || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("it").replace(/^l['’]/, "")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function urls(event) {
    const city = event.city_slug || slugify(event.municipality);
    const theatre = event.venue_slug || slugify(event.venue);
    const work = event.work_slug || slugify(event.title);
    const staging = event.staging_url || ("/" + city + "/" + theatre + "/" + work + "/");
    return {
      work: PREFIX + "/opere/" + work + "/",
      venue: PREFIX + "/" + city + "/" + theatre + "/",
      staging: PREFIX + staging,
    };
  }


  async function jsonFrom(url, digest) {
    const response = await fetch(url, {cache:"no-store"});
    if (!response.ok) throw new Error("Catalog HTTP " + response.status);
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength > 12 * 1024 * 1024) throw new Error("Catalog part too large");
    if (digest) {
      if (!globalThis.crypto || !crypto.subtle) throw new Error("Secure digest unavailable");
      const actual = await crypto.subtle.digest("SHA-256", bytes);
      const hex = [...new Uint8Array(actual)].map(x => x.toString(16).padStart(2,"0")).join("");
      if (hex !== digest) throw new Error("Catalog digest mismatch");
    }
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  function validateChannel(key, manifest, part) {
    if (part.schema_version !== 2 || !Array.isArray(part[key])) throw new Error("Invalid feed channel");
    if (part[key].length !== manifest.files[key].count) throw new Error("Catalog count differs");
    return part[key];
  }

  async function remote() {
    const manifest = await jsonFrom(BASE + "manifest.json");
    if (manifest.schema_version !== 2 || !manifest.files || !/^\d{4}-\d{2}-\d{2}$/.test(manifest.reviewed_on)) {
      throw new Error("Unsupported manifest");
    }
    const parts = await Promise.all(CHANNELS.map(async channel => {
      const spec = manifest.files[channel];
      if (!spec || !new RegExp("^data/" + channel + "\\.[a-f0-9]{16}\\.json$").test(spec.path)
          || !/^[a-f0-9]{64}$/.test(spec.sha256) || !Number.isSafeInteger(spec.count)) {
        throw new Error("Unsafe catalog reference");
      }
      const doc = await jsonFrom(BASE + spec.path + "?v=" + spec.sha256.slice(0,16), spec.sha256);
      return validateChannel(channel,manifest,doc);
    }));
    const [works,venues,stagings,recite] = parts;
    const byWork = new Map(works.map(x=>[x.id,x]));
    const byVenue = new Map(venues.map(x=>[x.id,x]));
    const byStaging = new Map(stagings.map(x=>[x.id,x]));
    if (byWork.size !== works.length || byVenue.size !== venues.length
        || byStaging.size !== stagings.length) throw new Error("Duplicate canonical IDs");
    const ids = new Set();
    const performances = recite.map(item => {
      if (ids.has(item.id)) throw new Error("Duplicate performance ID");
      ids.add(item.id);
      const staging = byStaging.get(item.staging_id);
      const work = staging && byWork.get(staging.work_id);
      const venue = staging && byVenue.get(staging.venue_id);
      if (!work || !venue || !/^\d{4}-\d{2}-\d{2}$/.test(item.local_date)
          || (item.time_known ? typeof item.starts_at !== "string" : item.starts_at !== null)) {
        throw new Error("Invalid canonical relationship");
      }
      return {
        id:item.id, legacy_id:item.legacy_id, staging_id:staging.id,work_id:work.id,venue_id:venue.id,
        staging_url:staging.url, season:staging.season, work_slug:work.slug,
        venue_slug:venue.slug, city_slug:venue.city_slug,
        local_date:item.local_date,starts_at:item.starts_at,
        time_known:item.time_known, status:item.status,
        title:work.title, composer:work.composer,
        venue:venue.name,municipality:venue.city,region:venue.region,
        sources:[staging.source_url],
      };
    });
    return {schema_version:1,performances,source:"github",reviewed_on:manifest.reviewed_on};
  }

  async function load() {
    try {
      return await remote();
    } catch (error) {
      // Preserve the previous usable public catalog, but NEVER imply it is current.
      const snapshot = await jsonFrom("./performances.json");
      if (snapshot.schema_version !== 1 || !Array.isArray(snapshot.performances))
        throw new Error("No valid remote or fallback catalog");
      return {...snapshot,source:"fallback",warning:"Catalogo di riserva: l’aggiornamento remoto non è momentaneamente verificabile."};
    }
  }
  return Object.freeze({load, urls, slugify});
})();
