"use strict";

/* The only external input is a generated, operator-reviewed JSON export.
   Render via DOM text nodes, not innerHTML; never invent missing times. */
/* Data are loaded from the canonical GitHub feed, not the SFTP copy. */
const PAGE_SIZE = 12;
let viewMode = "staging";
const controls = {
  query: document.getElementById("search"),
  location: document.getElementById("location"),
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
  if (normalized(controls.location.value) && !normalized(event.municipality).includes(normalized(controls.location.value))) return false;
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
  title.href = window.OperaAtlasCatalog.urls(event).work;
  heading.append(title);
  main.append(heading);
  if (event.composer) main.append(node("p","composer",event.composer));
  const details = node("div","event-details");
  const venue = node("div","venue");
  const venueLink = node("a",null,event.venue);
  venueLink.href = window.OperaAtlasCatalog.urls(event).venue;
  venue.append(venueLink);
  details.append(venue);
  details.append(node("div","city",[event.municipality,event.region].filter(Boolean).join(" · ")));
  details.append(node("div","time"+(event.time_known?"":" unknown"),
    event.time_known ? "Ore "+event.starts_at.slice(11,16) : "Orario da confermare"));
  main.append(details);
  const detail = node("a","detail-link","Esamina la recita");
  detail.href = window.OperaAtlasCatalog.urls(event).staging;
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

function createStagingCard(events) {
  const first = events[0];
  const article = node("article","event");
  const main = node("div","event-main");
  main.append(node("div","event-meta",first.municipality+" · "+events.length+" repliche"));
  const heading = node("h3");
  const title = node("a",null,first.title);
  title.href = window.OperaAtlasCatalog.urls(first).staging;
  heading.append(title);
  main.append(heading);
  if (first.composer) main.append(node("p","composer",first.composer));
  const theatre = node("p","composer",first.venue+" · "+first.municipality);
  main.append(theatre);
  const dates = node("div","staging-repliche");
  for (const recita of events.slice(0,12)) {
    dates.append(node("span","replica-chip",
      dateLabel(recita.local_date)+" · "+
      (recita.time_known ? recita.starts_at.slice(11,16) : "Ora da confermare")));
  }
  if (events.length>12) dates.append(node("span","replica-chip","+"+(events.length-12)+" altre"));
  main.append(dates);
  const link = node("a","detail-link","Esamina la messa in scena");
  link.href = window.OperaAtlasCatalog.urls(first).staging;
  main.append(link);
  article.append(main);
  return article;
}

function groupByStaging(events) {
  const groups = new Map();
  for (const e of events) {
    const key = e.staging_id || window.OperaAtlasCatalog.urls(e).staging;
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(e);
  }
  return [...groups.values()];
}

function renderDiscoveries() {
  const works = new Map(), venues = new Map();
  for (const event of catalog) {
    const urls = window.OperaAtlasCatalog.urls(event);
    if (!works.has(urls.work)) works.set(urls.work, event.title);
    if (!venues.has(urls.venue)) venues.set(urls.venue, event.venue+" · "+event.municipality);
  }
  for (const [id, items] of [["discover-works",works],["discover-venues",venues]]) {
    const target = document.getElementById(id);
    if (!target) continue;
    target.replaceChildren();
    for (const [href, label] of [...items].sort((a,b)=>a[1].localeCompare(b[1],"it")).slice(0,12)) {
      const a = node("a","discovery-link",label);
      a.href = href;
      target.append(a);
    }
    if (!items.size) target.append(node("p",null,"Nessun contenuto verificato disponibile."));
  }
}
function todayInItaly() {
  const parts = new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const part = key => parts.find(p=>p.type===key).value;
  return part("year")+"-"+part("month")+"-"+part("day");
}
function defaultPeriod() {
  const today = todayInItaly();
  const end = new Date(today+"T12:00:00Z");
  end.setUTCDate(end.getUTCDate()+29);
  controls.from.value = today;
  controls.to.value = end.toISOString().slice(0,10);
}
function render() {
  const filtered = catalog.filter(matches);
  const entries = viewMode === "staging" ? groupByStaging(filtered) : filtered;
  const pages = Math.ceil(entries.length / PAGE_SIZE);
  page = Math.max(0, Math.min(page, Math.max(0,pages-1)));
  list.replaceChildren();
  const visible = entries.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);
  if (viewMode === "staging") visible.forEach(group=>list.append(createStagingCard(group)));
  else visible.forEach(event=>list.append(createCard(event)));
  if (!filtered.length) {
    const empty = node("div","empty");
    empty.append(node("strong",null,catalog.length ? "Nessuna recita per questi filtri." : "Nessuna recita pubblicata."));
    empty.append(node("p",null,catalog.length ? "Prova a modificare o azzerare i filtri." : "Le recite verranno mostrate quando saranno disponibili dati ufficiali verificati."));
    list.append(empty);
  }
  count.textContent = viewMode === "staging"
    ? entries.length+" messe in scena · "+filtered.length+" recite"
    : (filtered.length === 1 ? "1 recita" : filtered.length+" recite");
  pager.hidden = pages <= 1;
  prev.disabled = page===0;
  next.disabled = page>=pages-1;
  pageLabel.textContent = pages ? "Pagina "+(page+1)+" di "+pages : "";
}

async function initialize() {
  try {
    const documentData = await window.OperaAtlasCatalog.load();
    if (documentData.warning) message.textContent = documentData.warning;
    else if (documentData.reviewed_on)
      message.textContent = "Dati verificati il " + documentData.reviewed_on.split("-").reverse().join("/");
    if (!documentData || documentData.schema_version !== 1 || !Array.isArray(documentData.performances)) {
      throw new Error("schema non supportato");
    }
    const raw = documentData.performances;
    catalog = raw.filter(validEvent).sort((a,b)=>a.local_date.localeCompare(b.local_date) ||
      (a.starts_at || "").localeCompare(b.starts_at || ""));
    if (raw.length !== catalog.length) {
      message.textContent = "Alcune recite con dati non validi non sono state mostrate.";
    }

    fillOptions(controls.city,catalog.map(x=>x.municipality));
    renderDiscoveries();
    fillOptions(controls.region,catalog.map(x=>x.region));
    render();
  } catch {
    count.textContent = "Dati non disponibili";
    list.replaceChildren(node("p","empty","Non è stato possibile caricare il catalogo verificato. Riprova più tardi."));
    pager.hidden = true;
  }
}

document.getElementById("filters").addEventListener("submit",event=>event.preventDefault());
document.querySelectorAll("[data-catalog-view]").forEach(button=>{
  button.addEventListener("click",()=>{
    viewMode = button.dataset.catalogView;
    document.querySelectorAll("[data-catalog-view]").forEach(item=>{
      const active = item === button;
      item.classList.toggle("active",active);
      item.setAttribute("aria-pressed",active?"true":"false");
    });
    page=0;render();
  });
});
Object.values(controls).forEach(control=>control.addEventListener("input",()=>{page=0;render();}));
document.getElementById("reset").addEventListener("click",()=>{
  Object.values(controls).forEach(control=>control.value="");
  controls.location.value="Torino";
  defaultPeriod();
  page=0;render();controls.query.focus();
});
prev.addEventListener("click",()=>{page--;render();});
next.addEventListener("click",()=>{page++;render();});
defaultPeriod();
initialize();
