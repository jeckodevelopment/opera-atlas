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

## Pagine canoniche HTML leggibili senza JavaScript

La pubblicazione SFTP genera ora documenti statici distinti per ciascuna
opera, teatro, allestimento, coproduzione e programma composto risolto dal
catalogo canonico: `/<entità>/.../index.html`. Apache serve tali pagine
all'URL canonico già esistente, senza modificare gli identificativi né il
client dinamico. Ogni HTML contiene titolo, descrizione, canonical, metatag
Open Graph/Twitter, immagine collegata al `work_id` o alla sede verificata,
un titolo di pagina e un breve riepilogo leggibili anche senza JavaScript.
Quando i dati dinamici sono disponibili, l'interfaccia rimuove il
riepilogo statico e renderizza la scheda aggiornata.

La generazione avviene **soltanto dai dati già pubblicati**. Le nuove
entità diventano indicizzabili al successivo deploy SEO, programmato
ogni giorno alle 13:11 UTC. Il refresh del catalogo resta indipendente
e non viene attivato per la sola SEO. In caso di fetch fallito nel browser,
il riepilogo iniziale resta consultabile.

**Limiti residui:** le pagine basate esclusivamente su parametri query,
soprattutto gli approfondimenti festival, hanno metatag differenziati
solo dopo l'esecuzione di JavaScript. Le immagini di singola produzione
possono usare un documento storico associato all'opera, chiaramente
distinto da una foto dello specifico allestimento. La cache dei crawler
non è controllabile e le date cambiate dopo il deploy verranno
aggiornate al successivo ciclo.

## Collaudi

- Codice HTTP 200, MIME image/png e dimensioni del file OG.
- HTML iniziale: tag SEO non duplicati e link canonici corretti.
- Deep link e schema.org verificati su esempi di opera, teatro, allestimento.
- XML sitemap parsabile, URL assoluti, nessun duplicato.
- Verifica in Google Search Console e debugger social dopo la pubblicazione:
  CI e build non provano l'anteprima effettiva presso i crawler terzi.
