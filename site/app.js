"use strict";

/* The only external input is a generated, operator-reviewed JSON export.
   Render via DOM text nodes, not innerHTML; never invent missing times. */
const SOURCE = "./performances.json";
const PAGE_SIZE = 12;
const controls = {
  query: document.getElementById("search"),
  city: document.getElementById("city"),
  region: document.getElementById("region"),
  from: document.getElementById("from"),
  to: document.getElementById("to"),
  time: document.getElementById("time-filter"),
};
const list = document.getElementById("events");
const message = document.getElementById("message");
const count = document.getElementById("count");
const pageLabel = document.getElementById("page-label");
const pager = document.querySelector(".pagination");
const prev = document.getElementById("previous");
const next = document.getElementById("next");
let catalog = [];
let page = 0;

function safeSource(uri) {
  try {
    const parsed = new URL(uri);
    return parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function validEvent(event) {
  return event && typeof event.title === "string" && event.title.trim()
    && typeof event.venue === "string" && event.venue.trim()
    && typeof event.municipality === "string" && event.municipality.trim()
    && typeof event.local_date === "string"
    && /^\d{4}-\d{2}-\d{2}$/.test(event.local_date)
    && typeof event.time_known === "boolean"
    && (event.time_known
      ? typeof event.starts_at === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(event.starts_at)
      : event.starts_at === null)
    && Array.isArray(event.sources)
    && event.sources.some(safeSource);
}

function normalized(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("it").trim();
}

function matches(event) {
  const phrase = normalized(controls.query.value);
  if (phrase && !normalized([event.title, event.composer, event.venue, event.municipality, event.region].join(" ")).includes(phrase)) return false;
  if (controls.city.value && event.municipality !== controls.city.value) return false;
  if (controls.region.value && (event.region || "") !== controls.region.value) return false;
  if (controls.from.value && event.local_date < controls.from.value) return false;
  if (controls.to.value && event.local_date > controls.to.value) return false;
  if (controls.time.value === "known" && !event.time_known) return false;
  if (controls.time.value === "unknown" && event.time_known) return false;
  return true;
}

function node(tag, cls, text) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (text !== undefined) element.textContent = text;
  return element;
}

function dateLabel(iso) {
  const d = new Date(iso + "T12:00:00Z");
  return new Intl.DateTimeFormat("it-IT", {day:"numeric",month:"long",year:"numeric",timeZone:"UTC"}).format(d);
}

function createCard(event) {
  const article = node("article","event");
  const main = node("div","event-main");
  main.append(node("div","event-meta","Opera lirica · "+event.municipality));
  const heading = node("h3");
  const title = node("a",null,event.title);
  title.href = "./detail.html?type=work&key="+encodeURIComponent(normalized(event.title));
  heading.append(title);
  main.append(heading);
  if (event.composer) main.append(node("p","composer",event.composer));
  const details = node("div","event-details");
  const venue = node("div","venue");
  const venueLink = node("a",null,event.venue);
  venueLink.href = "./detail.html?type=venue&key="+encodeURIComponent(
    normalized(event.venue)+"|"+normalized(event.municipality));
  venue.append(venueLink);
  details.append(venue);
  details.append(node("div","city",[event.municipality,event.region].filter(Boolean).join(" · ")));
  details.append(node("div","time"+(event.time_known?"":" unknown"),
    event.time_known ? "Ore "+event.starts_at.slice(11,16) : "Orario da confermare"));
  main.append(details);
  const detail = node("a","detail-link","Esamina la recita");
  detail.href = "./detail.html?type=performance&key="+encodeURIComponent(String(event.id));
  main.append(detail);
  const links = node("ul","source-links");
  for (const url of [...new Set(event.sources)]) {
    const href = safeSource(url);
    if (!href) continue;
    const li = node("li");
    const anchor = node("a",null,"Fonte ufficiale");
    anchor.href = href;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    li.append(anchor);
    links.append(li);
  }
  main.append(links);
  article.append(main);
  const side = node("div","event-side");
  const calendar = node("div","calendar");
  const parts = event.local_date.split("-");
  const month = new Intl.DateTimeFormat("it-IT",{month:"short",timeZone:"UTC"})
    .format(new Date(event.local_date+"T12:00:00Z"));
  calendar.append(node("span","calendar-month",month));
  calendar.append(node("span","calendar-day",String(Number(parts[2]))));
  calendar.append(node("span","calendar-year",parts[0]));
  side.append(calendar);
  article.append(side);
  return article;
}

function fillOptions(select, values) {
  for (const value of [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b,"it"))) {
    const option = node("option",null,value);
    option.value = value;
    select.append(option);
  }
}

function render() {
  const filtered = catalog.filter(matches);
  const pages = Math.ceil(filtered.length / PAGE_SIZE);
  page = Math.max(0, Math.min(page, Math.max(0,pages-1)));
  list.replaceChildren();
  const visible = filtered.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);
  visible.forEach(event=>list.append(createCard(event)));
  if (!filtered.length) {
    const empty = node("div","empty");
    empty.append(node("strong",null,catalog.length ? "Nessuna recita per questi filtri." : "Nessuna recita pubblicata."));
    empty.append(node("p",null,catalog.length ? "Prova a modificare o azzerare i filtri." : "Le recite verranno mostrate quando saranno disponibili dati ufficiali verificati."));
    list.append(empty);
  }
  count.textContent = filtered.length === 1 ? "1 recita" : filtered.length+" recite";
  pager.hidden = pages <= 1;
  prev.disabled = page===0;
  next.disabled = page>=pages-1;
  pageLabel.textContent = pages ? "Pagina "+(page+1)+" di "+pages : "";
}

async function initialize() {
  try {
    const response = await fetch(SOURCE, {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP "+response.status);
    const documentData = await response.json();
    if (!documentData || documentData.schema_version !== 1 || !Array.isArray(documentData.performances)) {
      throw new Error("schema non supportato");
    }
    const raw = documentData.performances;
    catalog = raw.filter(validEvent).sort((a,b)=>a.local_date.localeCompare(b.local_date) ||
      (a.starts_at || "").localeCompare(b.starts_at || ""));
    if (raw.length !== catalog.length) {
      message.textContent = "Alcune recite con dati non validi non sono state mostrate.";
    }
    document.getElementById("metric-events").textContent = String(catalog.length);
    document.getElementById("metric-works").textContent =
      String(new Set(catalog.map(x=>normalized(x.title))).size);
    document.getElementById("metric-venues").textContent =
      String(new Set(catalog.map(x=>normalized(x.venue)+"|"+normalized(x.municipality))).size);
    document.getElementById("metric-unknown").textContent =
      String(catalog.filter(x=>!x.time_known).length);
    fillOptions(controls.city,catalog.map(x=>x.municipality));
    fillOptions(controls.region,catalog.map(x=>x.region));
    render();
  } catch {
    count.textContent = "Dati non disponibili";
    list.replaceChildren(node("p","empty","Non è stato possibile caricare il catalogo verificato. Riprova più tardi."));
    pager.hidden = true;
  }
}

document.getElementById("filters").addEventListener("submit",event=>event.preventDefault());
Object.values(controls).forEach(control=>control.addEventListener("input",()=>{page=0;render();}));
document.getElementById("reset").addEventListener("click",()=>{
  Object.values(controls).forEach(control=>control.value="");
  page=0;render();controls.query.focus();
});
prev.addEventListener("click",()=>{page--;render();});
next.addEventListener("click",()=>{page++;render();});
initialize();
