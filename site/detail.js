"use strict";

/* Details are derived exclusively from the verified, public JSON snapshot.
   Escaping is automatic: all source text is inserted as textContent. */
const dataset = "./performances.json";
const params = new URLSearchParams(window.location.search);
const type = params.get("type");
const key = params.get("key");
const title = document.getElementById("detail-title");
const subtitle = document.getElementById("detail-subtitle");
const kind = document.getElementById("kind");
const status = document.getElementById("detail-status");
const content = document.getElementById("detail-content");
const results = document.getElementById("detail-events");

function textNode(tag, cls, value) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  n.textContent = value ?? "";
  return n;
}
function normalize(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase("it").trim();
}
function venueKey(e) {
  return normalize(e.venue) + "|" + normalize(e.municipality);
}
function validSource(value) {
  try {
    const u = new URL(value);
    return u.protocol === "https:" ? u.href : null;
  } catch { return null; }
}
function showSources(parent, events) {
  const list = textNode("ul", "source-links");
  const unique = [...new Set(events.flatMap(e => e.sources || []))];
  for (const source of unique) {
    const uri = validSource(source);
    if (!uri) continue;
    const item = textNode("li");
    const link = textNode("a", null, "Sito ufficiale");
    link.href = uri;
    link.rel = "noopener noreferrer";
    link.target = "_blank";
    item.append(link);
    list.append(item);
  }
  parent.append(list);
}
function urlFor(type, key) {
  return "./detail.html?type=" + encodeURIComponent(type)
    + "&key=" + encodeURIComponent(key);
}
function dateLabel(day) {
  return new Intl.DateTimeFormat("it-IT",{day:"numeric",month:"long",year:"numeric",timeZone:"UTC"})
    .format(new Date(day + "T12:00:00Z"));
}
function linkCard(label, target) {
  const link = textNode("a","detail-link",label);
  link.href = target;
  return link;
}
function showEvent(e) {
  const card = textNode("article","event");
  card.append(textNode("div","date",dateLabel(e.local_date)));
  const heading = textNode("h3");
  heading.append(linkCard(e.title,urlFor("work",normalize(e.title))));
  card.append(heading);
  const place = textNode("p","composer");
  place.append(linkCard(e.venue + " · " + e.municipality,
    urlFor("venue",venueKey(e))));
  card.append(place);
  card.append(textNode("p","time"+(e.time_known?"":" unknown"),
    e.time_known ? "Ore " + e.starts_at.slice(11,16) : "Orario da confermare"));
  const eventLink = linkCard("Dettaglio recita",urlFor("performance",String(e.id)));
  card.append(eventLink);
  showSources(card,[e]);
  results.append(card);
}
function missing(message) {
  title.textContent = "Scheda non disponibile";
  subtitle.textContent = "";
  status.textContent = message;
}
function acceptable(e) {
  return e && (typeof e.id === "number" || typeof e.id === "string")
    && typeof e.title === "string" && e.title.trim()
    && typeof e.venue === "string" && e.venue.trim()
    && typeof e.municipality === "string" && e.municipality.trim()
    && typeof e.local_date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(e.local_date)
    && typeof e.time_known === "boolean"
    && (!e.time_known || (typeof e.starts_at === "string" && e.starts_at.startsWith(e.local_date)))
    && Array.isArray(e.sources) && e.sources.some(validSource);
}
async function init() {
  if (!["work","performance","venue"].includes(type) || !key || key.length > 512) {
    missing("Il collegamento non identifica una scheda valida.");
    return;
  }
  try {
    const response = await fetch(dataset,{cache:"no-store"});
    if (!response.ok) throw Error("data unavailable");
    const data = await response.json();
    if (data.schema_version !== 1 || !Array.isArray(data.performances)) throw Error("bad schema");
    const events = data.performances.filter(acceptable);
    let related;
    if (type === "performance") {
      related = events.filter(e=>String(e.id)===key);
      if (related.length > 1) {
        missing("Identificatore di recita ambiguo.");
        return;
      }
    } else if (type === "work") {
      related = events.filter(e=>normalize(e.title)===key);
    } else {
      related = events.filter(e=>venueKey(e)===key);
    }
    if (!related.length) {
      missing("Questa scheda non è presente nei dati pubblicati.");
      return;
    }
    const first = related[0];
    if (type === "performance") {
      kind.textContent = "Recita";
      title.textContent = first.title;
      subtitle.textContent = dateLabel(first.local_date) + " · " + first.venue + ", " + first.municipality;
      content.append(textNode("p","time"+(first.time_known?"":" unknown"),
        first.time_known ? "Ore " + first.starts_at.slice(11,16) : "Orario da confermare"));
      content.append(textNode("p",null,"Stato: "+ (first.status === "confirmed" ? "Confermata" : "Annunciata")));
      content.append(linkCard("Vai alla scheda dell'opera",urlFor("work",normalize(first.title))));
      content.append(textNode("p"));
      content.append(linkCard("Vai alla scheda del teatro",urlFor("venue",venueKey(first))));
    } else if (type === "work") {
      kind.textContent = "Opera";
      title.textContent = first.title;
      subtitle.textContent = first.composer ? "Compositore: " + first.composer : "Compositore non verificato";
      content.append(textNode("p",null,related.length+" recite in catalogo"));
    } else {
      kind.textContent = "Teatro";
      title.textContent = first.venue;
      subtitle.textContent = [first.municipality,first.region].filter(Boolean).join(" · ");
      content.append(textNode("p",null,related.length+" recite in catalogo"));
    }
    showSources(content,related);
    for (const e of related.slice(0,60)) showEvent(e);
    if (related.length>60) status.textContent="Sono visualizzate le prime 60 recite.";
    document.title=title.textContent+" — Opera Atlas";
  } catch {
    missing("Non è stato possibile caricare il catalogo.");
  }
}
init();
