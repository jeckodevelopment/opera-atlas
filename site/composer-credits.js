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
      const entries = index.entities.filter(e => e.type === "composer" && (e.image || e.editorial_image || e.source_reference))
        .sort((a,b) => a.title.localeCompare(b.title, "it"));
      const fragment = document.createDocumentFragment();
      for (const e of entries) {
        for (const photo of [e.image, e.editorial_image].filter(Boolean)) {
          const li = document.createElement("li");
          li.append(e.title + ": " + photo.credit + " — ",
            link(photo.source_url, "Fonte"), " · ", link(photo.license_url, "Diritti"));
          fragment.append(li);
        }
      }
      const references = entries.filter(e => e.source_reference && !e.image && !e.editorial_image);
      for (const e of references) {
        const ref = e.source_reference;
        const li = document.createElement("li");
        li.append(e.title + ": ", link(ref.source_url, ref.source));
        if (ref.image_url) li.append(" — ", link(ref.image_url, "Ritratto presso la fonte"), " — " + ref.author);
        li.append(" (fonte esterna; riutilizzo non verificato)");
        fragment.append(li);
      }
      list.replaceChildren(fragment);
      if (!entries.length) list.textContent = "Nessun ritratto disponibile.";
    })
    .catch(() => { list.textContent = "Crediti temporaneamente non disponibili."; });
})();
