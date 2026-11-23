# Opera+ Atlas — SEO del portale pubblico

## URL pubblici e indicizzazione

- Dominio canonico: `https://opera.plus/atlas/`.
- Home, «In scena», directory e pagine legali espongono già nell'HTML titolo,
  descrizione, tag Open Graph/Twitter e immagine condivisibile `og-atlas.png`.
- «In scena» usa il canonical senza slash finale; date e filtri della pagina
  non hanno un URL indicizzabile diverso dal cartellone principale.
- La directory opera/teatro/festival e le schede canoniche sono dinamiche:
  dopo il caricamento dei dati il browser aggiorna canonical, title,
  description, Open Graph e JSON-LD, in base all'identificativo verificato.
- Il feed è la fonte unica; i metadati non introducono spettacoli, prezzi,
  disponibilità o dettagli storici non presenti nei dati canonici.

## Immagine Open Graph

Il generatore `scripts/atlas_seo.py` produce un'immagine originale PNG
1200 × 630 senza riciclare poster delle produzioni, fotografie o materiali
esterni. È parte della build SFTP e non è richiesto alcun font aggiuntivo.
L'URL condiviso è `https://opera.plus/atlas/og-atlas.png`.

## Sitemap

`https://opera.plus/atlas/sitemap.xml` è generata a ogni deploy frontend
dai registri versionati per opere, teatri, allestimenti, produzioni condivise,
programmi composti e festival con legami canonici validati. Evita ID temporanei
e date non certificate. La sitemap è una fotografia del catalogo al momento
del deploy e deve essere rigenerata dopo variazioni del feed canonico
per essere costantemente aggiornata.

**Attività operative esterne al deploy di Atlas:** includere
`Sitemap: https://opera.plus/atlas/sitemap.xml` nel `robots.txt`
di **radice dominio**, `https://opera.plus/robots.txt`, assicurando che
non blocchi `/atlas/`, e registrare la sitemap in Google Search Console
e Bing Webmaster Tools. Non modificare automaticamente il `robots.txt`
del sito madre: la gestione di tale file appartiene alla root di Opera+.

## Limite attuale dei deep link

Il frontend è statico e tutte le schede di dettaglio condividono la risposta
HTML iniziale di `detail.html`. Google può elaborare i metadati inseriti dal
JavaScript, ma molti social crawler non lo eseguono. Le **anteprime social
individuali** di opera/teatro/produzione sono per ora quelle generiche di
Opera+ Atlas, non foto o testi personalizzati per ogni entità. Anche le
varianti della directory condividono una risposta iniziale comune.

Per avere anteprime social specifiche e indicizzazione robusta anche sui
crawler senza JS serve una successiva evoluzione di pubblicazione:
**HTML statici precalcolati per le route canoniche**, mantenuti sincronizzati
al catalogo senza richiedere scraping o nuove banche dati. La funzionalità
non va dichiarata completata finché questo limite persiste.

## Collaudi

- Codice HTTP 200, MIME image/png e dimensioni del file OG.
- HTML iniziale: tag SEO non duplicati e link canonici corretti.
- Deep link e schema.org verificati su esempi di opera, teatro, allestimento.
- XML sitemap parsabile, URL assoluti, nessun duplicato.
- Verifica in Google Search Console e debugger social dopo la pubblicazione:
  CI e build non provano l'anteprima effettiva presso i crawler terzi.
