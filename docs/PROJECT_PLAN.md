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
- [ ] Connettori per fonti HTML strutturate, JSON-LD/API e PDF quando autorizzati. **Adapter Teatro Regio e staging offline di date OperaLombardia disponibili; ROF 403 in verifica, nessun fetch ROF. Fetch manuale Teatro Regio con robots fail-closed e audit v4; altri formati/fonti ancora aperti.**
- [ ] Parsing e normalizzazione di date, orari, produzione, venue e collegamenti. **Timestamp espliciti e identità canoniche già gestiti nel primo adapter; le recite con data/teatro/città ma senza orario sono ora esportabili con etichetta esplicita. Verifica su HTML live necessaria.**
- [ ] Import incrementale con idempotenza, riconciliazione e deduplicazione tra festival e teatri. **Pipeline transazionale SQLite e import opt-in multi-pagina (massimo 20, mapping curati e savepoint per pagina) disponibili; deduplicazione reale multi-fonte ancora da provare.**
- [ ] Gestione modifiche/rinvii/annullamenti, senza cancellazioni silenziose. **API di cambio stato con prova ufficiale e cronologia v5 implementata; rilevamento conservativo di date rimosse/aggiunte e di ID ufficiali stabili implementato (v6); risoluzione dei casi ambigui e collaudo live ancora aperti.**
- [ ] Monitoraggio scansioni, errori, obsolescenza, copertura e casi da verificare.
- [ ] Pianificazione GitHub Actions con rispetto di robots.txt, condizioni di utilizzo, rate limit e caching.

### F3 — Portale pubblico
- [ ] Catalogo eventi con filtri (date, opera, compositore, città, regione, teatro, festival). **Prima UI statica con ricerca opera/compositore/teatro, filtri città/regione/date/orario e paginazione implementata; filtro festival e funzioni avanzate da sviluppare.**
- [ ] Pagine opera, produzione, recita e luogo; URL ufficiale della biglietteria quando disponibile. **Primi dettagli opera, recita e teatro implementati via JSON e link navigabili; produzione, biglietteria e pagine SEO canoniche ancora da sviluppare.**
- [ ] Mappa Leaflet/OSM con gruppi di marcatori, filtri e route esterne.
- [ ] Geolocalizzazione solo su consenso, senza archiviazione delle coordinate personali.
- [ ] UI responsive, accessibilità, chiarezza dati incompleti e data ultimo aggiornamento. **Prima versione responsive con stile coerente con Opera+ Funding, etichette, focus e visualizzazione esplicita di orario mancante; verifiche browser/accessibilità e metadati aggiornamento ancora da completare.**

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
Schema, validatori del repertorio e test dell'issue #2 in corso; riconciliazione deterministica e API di revisione dell'issue #3 implementate, ma non sono presenti connettori reali o UI di revisione; otto fonti con URL ufficiale in JSON e da autorizzare prima di qualunque acquisizione; inventario nazionale incompleto e adapter Teatro Regio, fetch opt-in, audit scansioni v4 e stati recite v5 implementati; batch multi-produzione e confronti incrementali delle recite disponibili; staging date-only OperaLombardia v7 disponibile e recite con dati essenziali esportabili nel catalogo pubblico; ROF da verificare per blocco HTTP 403; nessun job di acquisizione programmata; primo frontend pubblico e dettagli opera/recita/teatro già pubblicati. Integrazione editoriale iniziale di 19 recite verificate su 2 pagine ufficiali (11 con ora, 8 senza), senza ancora copertura nazionale né sincronizzazione live. Non attribuire percentuali di completamento ai requisiti non ancora chiusi.

## Esecuzione controllata e audit (migrazione v4)
Il 20/11/2026 il percorso ufficiale `/opera-e-balletto-2026-2027/la-traviata` mostrava 11 righe distinte di recite (dal 26 febbraio al 10 marzo 2027), tra cui recite pomeridiane alle 15:00. Questa verifica è stata fatta consultando la pagina pubblica, **non** eseguendo il crawler della repository. Il parser rimane da confrontare con la sorgente HTML effettivamente scaricabile, che può avere struttura diversa da quella visibile nelle pagine renderizzate.

`robots.txt` non è risultato accessibile dal sistema di verifica; il comportamento necessario è **fail closed** fino a verifica da ambiente operativo. Nessuna approvazione di crawling discende dalla presenza di un URL pubblico.

```sh
# Esegue una singola verifica controllata (solo se fonte già approvata nel DB)
python -m opera_atlas.scan_cli --db atlas.sqlite3 --url https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata --source-id 1 --venue-id 1 --production-id 1 --title "La traviata" --composer "Giuseppe Verdi" --allow-network
# Il comando senza --apply esegue rollback delle modifiche e non conserva il log.
# Con --apply salva recite e metadati di verifica nel database (mai HTML integrale).
```

La verifica rispetta: URL HTTPS e hostname esatto, redirects rifiutati, richiesta robots.txt precedente alla pagina, User-Agent identificabile, response HTML, limite 2 MB, timeout 12 secondi. Nessun retry e nessuna scansione ricorsiva. Lo storico `source_checks` registra esito, impronta SHA-256, dimensione e numero di recite, senza copiare il testo dell'ente. Le scansioni negate registrano solo il motivo tecnico se `--apply` è usato.

**Limiti:** la soluzione non gestisce rate limiting globale tra esecuzioni, ETag/304, parser per altri teatri, errori di import con log persistente o gestione completa degli spostamenti di programma. Prima di abilitare schedulazioni serviranno policy di accesso verificate, monitoraggio delle frequenze e collaudi live. Le fixture di test sono sintesi redatte autonomamente, non copie della pagina.

## Blocco implementativo — feed canonico v2 (2026-11-20)
- [x] Registro di ID opachi immutabili: 2 opere, 5 teatri, 5 messe in scena, 19 repliche. Lo slug è separato dall'identità.
- [x] Feed statici distinti e versionati per entità, con hash SHA-256 e puntatore pubblico scritto per ultimo.
- [x] Frontend collegato al feed GitHub, con fallback esplicito allo snapshot SFTP in caso di problemi di rete.
- [x] Job quotidiano di validazione e pubblicazione canonica su GitHub Actions nella repository del prodotto, senza servizio server o SFTP.
- [ ] Import quotidiano dalle pagine ufficiali: fonti e policy live ancora da approvare; niente scraping implicito.
- [ ] Routing SEO leggibile su hosting e pagine delle messe in scena raggruppate: registri e URL canonici già modellati, frontend e server rewrite da integrare.
- [ ] Risoluzione automatica sicura dei cambi identità in presenza di date modificabili e fonte non stabile: revisione umana ancora necessaria.
