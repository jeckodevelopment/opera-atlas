# Opera Atlas

Catalogo nazionale delle rappresentazioni di opera lirica in Italia e osservatorio statistico collegato al progetto culturale Opera+.

> Stato: sviluppo Fasi 1–3 — modello SQLite, acquisizioni controllate e **primo catalogo web statico** disponibili. Prima pubblicazione editoriale di 19 recite confermate sulle pagine ufficiali di due organizzatori, con data e sede verificati; acquisizione automatica continua e completezza nazionale da completare.

## Obiettivi

- Catalogo di opere, produzioni, recite, teatri, festival e organizzatori, senza duplicati.
- Mappa interattiva dei luoghi e geolocalizzazione facoltativa.
- Raccolta automatica e tracciabile da fonti ufficiali, con controlli di qualità.
- Statistiche sul repertorio e sulla distribuzione geografica e temporale.

## Sviluppo locale

Richiede Python 3.12+ e SQLite con JSON1 (nessuna dipendenza Python esterna per lo storage).

```bash
python -m unittest discover -s tests -v
python -c "from opera_atlas.db import connect, migrate; c=connect('atlas.sqlite3'); migrate(c); c.close()"
```

Il file `atlas.sqlite3` è un artefatto locale di lavorazione, non un dataset pubblico di spettacoli. Vedi [schema, riconciliazione e limitazioni](docs/STORAGE.md), [piano 1.0.0](docs/PROJECT_PLAN.md) e [registro delle fonti](docs/SOURCE_REGISTRY.md).

## Processo

Tutte le modifiche funzionali tramite pull request con test, documentazione nella stessa PR e Semantic Versioning. Licenze e policy di raccolta dati, mappe e materiali di terze parti saranno verificate prima della pubblicazione.

## Registro sorgenti
Gli otto ingressi ufficiali iniziali verificati sono in [data/sources.json](data/sources.json). Per validarli e importarli nel database di lavorazione, dopo la migrazione:
```bash
python -c "from opera_atlas.db import connect,migrate; from opera_atlas.source_registry import seed_sources; c=connect('atlas.sqlite3'); migrate(c); print(seed_sources(c)); c.commit(); c.close()"
```
Le sorgenti sono inizialmente `pending`: nessuna scansione automatica è attivata da questa operazione.

## Importazione offline: primo connettore
Disponibile la pipeline di parsing, riconciliazione ed esportazione JSON per snapshot salvati delle pagine di dettaglio del Teatro Regio di Torino. **Non è ancora attiva una scansione automatica del sito.** Il parser richiede date/ore effettive, opera e compositore canonici, fonte approvata e luogo verificato; ignora i periodi generici delle stagioni. Vedi [guida al connettore](docs/REGIO_CONNECTOR.md) e relativi test.

### Controllo dell'accesso e monitoraggio
Il modulo `opera_atlas.scan_cli` consente una **singola** richiesta HTTP per pagina, solo se il gestore ha già verificato e approvato la fonte nel database. Richiede `--allow-network` e controlla `robots.txt` prima della pagina; indisponibilità o divieto bloccano l'accesso. Nessun crawler periodico è attivato. Gli esiti sono in `source_checks` (solo metadati), migrazione v4. Dettagli in [REGIO_CONNECTOR](docs/REGIO_CONNECTOR.md).

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

### Batch di produzioni (Fase 2)
Disponibile `python -m opera_atlas.batch_cli` con manifesto JSON verificato, massimo 20 pagine, preflight delle sorgenti e savepoint di isolamento per pagina. Richiede `--allow-network` per qualsiasi accesso e `--apply` per salvare il risultato. Nessuna scansione periodica o autorizzazione implicita. Vedi [guida al connettore](docs/REGIO_CONNECTOR.md).

### Variazioni di stato delle recite
Le conferme, i rinvii e gli annullamenti verificati possono essere registrati tramite `opera_atlas.changes.set_performance_status` con fonte approvata e motivazione. La cronologia è append-only nella migrazione SQLite v5. Non sono dedotti annullamenti dalle recite scomparse e non è ancora attivo il rilevamento automatico dei cambi data. [Dettagli e collaudi](docs/REGIO_CONNECTOR.md).

### Riconciliazione incrementale
La migrazione SQLite v6 registra anomalie tra scansioni della stessa pagina (`source_snapshot_deltas`). Il parser può usare ID ufficiali `data-event-id` quando presenti; senza tali ID, scomparsa e comparsa contemporanea di date avviano una revisione e **non creano recite duplicative**. I dati storici restano intatti. Vedi [REGIO_CONNECTOR](docs/REGIO_CONNECTOR.md) per prove e limitazioni.

### Fonti con calendari parziali (OperaLombardia)
Il modulo `opera_atlas.operalombardia` e la CLI `opera_atlas.stage_cli` conservano nel database **soltanto come dati da approfondire** le date e sedi di produzioni ufficiali senza orario. L'importazione è offline, richiede fonte approvata e `--apply` esplicito. **Le date con titolo dell'opera, teatro e città espliciti compaiono nell'export pubblico**, anche senza orario, con `starts_at: null`, `time_known: false`, `time_label: "Orario da confermare"` e URL della fonte. Nessun orario viene inventato. Le date scartate/in revisione e le fonti non approvate restano escluse.
```sh
python -m opera_atlas.stage_cli --db atlas.sqlite3 --html path/to/authorized-page.html --url https://www.operalombardia.it/l-italiana-in-algeri/ --title "L’italiana in Algeri" --source-id 2
```
Per finalizzare manualmente gli orari servono ulteriori prove dalle fonti ufficiali. Il ROF non è ancora integrato a causa di risposte 403 nella verifica delle pagine. Vedi [SOURCE_REGISTRY](docs/SOURCE_REGISTRY.md).

### Regola editoriale: recite con orario non disponibile
Nel catalogo, una recita verificata con **opera, data, teatro e città** è un contenuto utile e deve essere mostrato anche senza orario. Il JSON esporta recite complete e parziali nello stesso array `performances`; per quelle senza ora usa `starts_at: null` e `time_known: false`, mantenendo giorno, opera, teatro, città, URL originale e label `Orario da confermare`. Quando una recita con ora confermata presenta lo stesso titolo, teatro, città e giorno, prevale la scheda completa nell'export; la prova parziale rimane nel database. La futura UI dovrà rendere visibile l'indicatore e non formattare un valore null come mezzanotte.

## Primo catalogo web pubblico (Fase 3, implementazione iniziale)
È disponibile `site/index.html` con ricerca, filtri per città/regione/date/orario e schede delle recite tratte dal JSON esportato dal database. Le recite prive di orario sono mostrate come **Orario da confermare**. Il file `site/performances.json` contiene **19 recite verificate singolarmente** da Teatro Regio Torino e OperaLombardia, rigenerabili dal manifesto editoriale `data/verified-launch-catalog.json`. Nessun evento inventato. Per il collaudo locale:
```sh
python -m opera_atlas.ingest_cli --db atlas.sqlite3 export --output site/performances.json
python -m http.server 8000 --directory site
```
**Esportare solo un database con fonti approvate e dati effettivamente verificati.** Vedi [guida catalogo](docs/PUBLIC_CATALOG.md). La mappa e le altre funzionalità F3 sono ancora da realizzare.

### Schede di dettaglio e pubblicazione
Il catalogo comprende le schede dinamiche per **opera, recita e teatro** in `site/detail.html` (parametri `type` e `key`), tutte derivate dall'export pubblico verificato e navigabili dalle schede del calendario. Le recite con orario mancante conservano la dicitura **Orario da confermare** anche nel dettaglio. Non vengono copiati testi editoriali o immagini di terzi.

Il frontend viene distribuito in `https://jeckodevelopment.com/dev/opera-atlas/` tramite il workflow SFTP dedicato **nel repository `jeckodevelopment/jeckodevsite`**, che utilizza gli stessi secret SFTP e il rollback già operativi per le altre applicazioni. Il deploy verifica via HTTPS ogni asset pubblicato; l'export iniziale rimane `performances: []`, non vengono inventate recite. Vedi [catalogo pubblico](docs/PUBLIC_CATALOG.md).

### Primo popolamento editoriale e identità grafica
Il 20 novembre 2026 sono stati verificati sulle pagine ufficiali: **11 recite di La traviata** al Teatro Regio di Torino (26/02–10/03/2027, orari riportati), **8 recite di L’italiana in Algeri** per OperaLombardia (13/11–12/12/2026: teatro e data, ma nessun orario). Le pagine ufficiali sono collegate in ogni evento. Il manifesto sorgente curato è `data/verified-launch-catalog.json`; rigenerare o controllare il JSON pubblicabile con:
```sh
python -m scripts.build_verified_catalog --check
python -m unittest discover -s tests -v
```
Non è una scansione automatica, non cambia lo stato delle fonti nel database SQLite e non dimostra la copertura nazionale. Conservare la provenienza e aggiornare le date solo dopo nuova verifica ufficiale; non ripubblicare dati obsoleti in automatico.

Il frontend adotta una **prima identità grafica Opera Atlas**, ispirata a Opera+ Funding senza riprenderne logo o marchio: palette avorio/bianco con accenti oro, titoli serif, controlli compatti, metriche sintetiche e schede orizzontali con data laterale. Il marchio è per ora testuale, predisposto per un futuro logo specifico.

## Architettura durevole catalogo v2 — ID e dati indipendenti dal frontend

La fonte canonica è `data/verified-launch-catalog.json` con registro di identità permanente `data/identity-registry.json`. Il modulo `scripts.publish_catalog_v2` genera quattro insiemi JSON separati (`works`, `venues`, `stagings`, `performances`) sotto `public/catalog/v2/data/`. Ogni file ha un nome legato al digest SHA-256; il puntatore pubblico `public/catalog/v2/manifest.json` è scritto **dopo** i dati. Un aggiornamento non può cambiare un ID senza revisione: anche un cambio di data non provoca una nuova identità automatica.

Il frontend ha una libreria condivisa `site/catalog-client.js`: consulta direttamente l'endpoint statico GitHub `https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/manifest.json`, verifica i digest dei file, ricompone le entità e conserva un fallback dell'ultima versione SFTP con avviso di dati non verificati in quel momento. I cambi di catalogo **non richiedono SFTP**. L'aggiornamento dei file web continua a usare il publisher dedicato in `jeckodevsite` solo quando cambia l'interfaccia.

```sh
python -m unittest discover -s tests -v
python -m scripts.publish_catalog_v2
python -m scripts.publish_catalog_v2 --check
```

Il workflow `refresh-catalog.yml` in **opera-atlas** esegue validazione e rigenerazione **quotidianamente alle 07:17 UTC** (e a fronte di modifiche del manifesto o del codice). Esegue commit solo se il contenuto approvato cambia, preservando la versione precedente e minimizzando il consumo di Actions. **Attenzione: non significa ancora scansione live automatica delle fonti**. Tutte le otto fonti registrate restano da verificare/autorizzare per una raccolta schedulata. Il job quotidiano oggi valida, pubblica e mantiene accessibili le osservazioni già approvate. Gli eventuali parser futuri dovranno inserirsi nella pipeline soltanto dopo approvazione della fonte e controllo di robots/termini, senza cancellazioni per errori di fetch. Nessun database cloud o backend è richiesto. Dettagli in [ARCHITECTURE](docs/ARCHITECTURE.md).
