# Opera Atlas — piano di sviluppo 1.0.0

## Obiettivo
Realizzare un catalogo nazionale delle rappresentazioni operistiche in Italia, con mappe, ricerca e osservatorio statistico, alimentato da fonti ufficiali. Opera Atlas è un progetto autonomo collegato culturalmente a Opera+.

## Fasi e criteri di completamento

### F1 — Fondamenta
- [ ] Inventario completo delle sedi e degli organizzatori/festival con URL ufficiali verificati, stato e data di verifica. **Otto fonti ufficiali in JSON strutturato con accesso pending; inventario nazionale e policy di accesso ancora da completare.**
- [ ] Modello dati completamente validato: work, production, performance, venue, organizer, festival, season, source, observation. **Schema SQLite baseline implementato; validazioni/casi limite e deduplicazione cross-source deterministica implementata; API di risoluzione manuale disponibile; rimangono mapping canonici verificati, UI e integrazione con fonti reali.**
- [ ] Tassonomia editoriale: opera lirica distinta da balletto, concerto e prosa; eccezioni esplicite. **Tipi codificati e validati via API; policy editoriale sui casi limite da completare.**
- [ ] Normalizzazione titoli, alias e compositori; gestione verificata delle sedi temporanee. **Normalizzazione Unicode/whitespace/case e alias curati disponibili; mapping da fonti reali ancora da validare.**
- [ ] Tests schema, validazione dati e registrazione della provenienza. **Suite iniziale e test di riconciliazione disponibili; ulteriori integrazioni necessarie.**

### F2 — Acquisizione automatica
- [ ] Connettori per fonti HTML strutturate, JSON-LD/API e PDF quando autorizzati.
- [ ] Parsing e normalizzazione di date, orari, produzione, venue e collegamenti.
- [ ] Import incrementale con idempotenza, riconciliazione e deduplicazione tra festival e teatri.
- [ ] Gestione modifiche/rinvii/annullamenti, senza cancellazioni silenziose.
- [ ] Monitoraggio scansioni, errori, obsolescenza, copertura e casi da verificare.
- [ ] Pianificazione GitHub Actions con rispetto di robots.txt, condizioni di utilizzo, rate limit e caching.

### F3 — Portale pubblico
- [ ] Catalogo eventi con filtri (date, opera, compositore, città, regione, teatro, festival).
- [ ] Pagine opera, produzione, recita e luogo; URL ufficiale della biglietteria quando disponibile.
- [ ] Mappa Leaflet/OSM con gruppi di marcatori, filtri e route esterne.
- [ ] Geolocalizzazione solo su consenso, senza archiviazione delle coordinate personali.
- [ ] UI responsive, accessibilità, chiarezza dati incompleti e data ultimo aggiornamento.

### F4 — Osservatorio e rilascio
- [ ] KPI coerenti (opere distinte, produzioni, recite, teatri attivi, regioni, classifiche).
- [ ] Definizione e trasparenza delle metriche, inclusi denominatori e filtri temporali.
- [ ] Esportazione aggregati, controlli di qualità e verifica copertura fonti.
- [ ] CI, release SemVer, documentazione, pubblicazione e collaudi finali. **CI unit test introdotta in F1; non equivale al completamento F4.**

## Definizione di completamento (DoD)
Ogni issue funzionale chiusa deve avere implementazione verificata, test automatici ove applicabile, istruzioni di collaudo manuale e aggiornamento della documentazione nella stessa PR. Non si considera implementato ciò che è solo previsto o abbozzato.

## Convenzioni PR
Ogni PR include: scopo e issue collegate; comportamenti da testare; risultati test; rischi; modifiche alla documentazione; impatto SemVer. A merge effettuato, aggiornare avanzamento per requisiti completati (mai una percentuale arbitraria). Le milestone F1–F4 sono organizzative, mentre 1.0.0 è il traguardo di prodotto.

## Esclusioni iniziali
Account personali, social, vendita biglietti, copie non autorizzate di testi/foto e calcolo di percorsi stradali su infrastrutture proprie.

## Stato attuale
Schema, validatori del repertorio e test dell'issue #2 in corso; riconciliazione deterministica e API di revisione dell'issue #3 implementate, ma non sono presenti connettori reali o UI di revisione; otto fonti con URL ufficiale in JSON e da autorizzare prima di qualunque acquisizione; inventario nazionale incompleto e nessun connettore/catalogo pubblico completato. Non attribuire percentuali di completamento ai requisiti non ancora chiusi.
