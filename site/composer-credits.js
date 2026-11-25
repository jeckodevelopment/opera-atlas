(() => {
  const list = document.getElementById("composer-credit-list");
  if (!list) return;
  const link = (url, label) => {
    const a = document.createElement("a");
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") throw new Error("Invalid credit URL");
    a.href = parsed.href;
    a.textContent = label;
    return a;
  };
  fetch(new URL("integrations/v1/entities.json", document.baseURI))
    .then(response => { if (!response.ok) throw new Error("Index unavailable"); return response.json(); })
    .then(index => {
      const entries = index.entities.filter(e => e.type === "composer" && e.image)
        .sort((a,b) => a.title.localeCompare(b.title, "it"));
      const fragment = document.createDocumentFragment();
      for (const e of entries) {
        const li = document.createElement("li");
        li.append(e.title + ": " + e.image.credit + " — ",
          link(e.image.source_url, "Fonte"), " · ", link(e.image.license_url, "Diritti"));
        fragment.append(li);
      }
      list.replaceChildren(fragment);
      if (!entries.length) list.textContent = "Nessun ritratto disponibile.";
    })
    .catch(() => { list.textContent = "Crediti temporaneamente non disponibili."; });
})();
