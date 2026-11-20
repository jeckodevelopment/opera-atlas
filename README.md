# Opera Atlas

Catalogo nazionale delle rappresentazioni di opera lirica in Italia e osservatorio statistico collegato al progetto culturale Opera+.

> Stato: sviluppo Fasi 1–3 — modello SQLite, acquisizioni controllate e **primo catalogo web statico** disponibili. Prima pubblicazione editoriale di 19 recite confermate sulle pagine ufficiali di due organizzatori, con data e sede verificati; acquisizione automatica continua e completezza nazionale da completare.

## Obiettivi

- Catalogo di opere, produzioni, recite, teatri, festival e organizzatori, senza duplicati.
- Mappa interattiva dei luoghi e geolocalizzazione facoltativa.
- Raccolta automatica e tracciabile da fonti ufficiali, con controlli di qualità.
- Statistiche sul repertorio e sulla distribuzione geografica e temporale.

## Interfaccia visitatori

L'esperienza pubblica è in `site/`: ricerca geografica indicativa, viste elenco/calendario/mappa schematica, directory Opere/Teatri/Festival e schede produzione orientate alle rappresentazioni future. Le decisioni UX, i limiti geografici e i collaudi sono documentati in [docs/ATLAS_UI_APPROVED.md](docs/ATLAS_UI_APPROVED.md). Il catalogo, i gruppi di coproduzione e l'indice festival sono pubblicati da `opera-atlas` su GitHub, separatamente dalla pubblicazione SFTP del frontend.

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

### URL leggibili e schede raggruppate (Fase 3)
Le nuove schede statiche sono raggiungibili tramite URL **senza query** quando l'hosting Apache applica le rewrite presenti in `site/.htaccess`:
- `/dev/opera-atlas/opere/la-traviata/` — tutte le messe in scena censite in Italia, raggruppate per teatro.
- `/dev/opera-atlas/torino/teatro-regio/` — tutte le messe in scena di un teatro.
- `/dev/opera-atlas/torino/teatro-regio/la-traviata/` — **un'unica messa in scena con tutte le sue repliche**, anche se alcune non hanno orario.

Il frontend offre le modalità **Per data** e **Per messa in scena**. Gli ID permanenti nel feed JSON restano indipendenti dai percorsi; i vecchi link `detail.html?type=...` sono ancora riconosciuti e instradati verso la pagina canonica. I cambi dei dati si propagano tramite il JSON GitHub senza nuova pubblicazione SFTP. Dopo un deploy UI è indispensabile il collaudo HTTP delle rewrite, perché il funzionamento dipende dal server.

## Scansione giornaliera con accesso autorizzato (Fase 2)

La stessa GitHub Action `refresh-catalog.yml`, eseguita una volta al giorno nel repository Opera Atlas, ora integra `scripts.daily_ingest`: verifica il registro `data/daily-source-config.json` e **scarica esclusivamente pagine esplicitamente approvate**, con controllo `robots.txt` obbligatorio, un URL per produzione, timeout e limiti. Oggi le due fonti iniziali sono ancora `pending`: il job aggiorna e valida il catalogo editoriale, ma non può affermare di scoprire nuove recite via web finché le verifiche di accesso e parser live non saranno completate.

Lo stato canonico sopravvive ai runner effimeri attraverso il manifesto editoriale e il registro degli ID. Nuove date non ambigue di una produzione curata ricevono un ID permanente, senza cancellare date che scompaiono da una scansione; cambi di orario, rinvii probabili e sedi ignote entrano nella coda di verifica, senza alterazione automatica. Eventuali problemi non azzerano il catalogo pubblico. Lo stato operativo delle fonti approvate è in `data/catalog-source-health.json`; l'ultima data di verifica editoriale è visibile sul frontend. Il processo non esegue SFTP.

Procedura per l'approvazione sicura, limiti e collaudi: [SOURCE_ONBOARDING](docs/SOURCE_ONBOARDING.md).

### Arricchimento incrociato degli orari verificati (Fase 2)

Una singola pagina del circuito può certificare data e sede senza indicare l'ora. Opera Atlas ora supporta `data/verified-time-evidence.json`, che associa a una **replica già censita** l'orario e una **seconda fonte ufficiale** (teatro o Comune). Il generatore conserva gli ID `oa-r-...`, la pagina originale di OperaLombardia e la nuova fonte dell'orario. Un orario non verificato rimane `null`; una fonte estranea, un giorno sbagliato o un'ora contraddittoria bloccano la build.

Prima tranche: 6 orari confermati per L’italiana in Algeri (Como 13/15 novembre, Pavia 20/22 novembre, Cremona 10/12 dicembre 2026). Rimangono 2 recite di Brescia senza ora. **Il catalogo contiene ancora 19 repliche: 17 con ora e 2 senza.** Nessun nuovo connettore live è stato autorizzato. Le fonti e la policy sono spiegate in [SOURCE_ONBOARDING](docs/SOURCE_ONBOARDING.md). Gli aggiornamenti del JSON v2 seguono il normale workflow di `opera-atlas`, senza SFTP.

### Verifica connettori e integrità dei dati (F2, novembre 2026)
La consultazione manuale delle pagine Teatro Regio Torino e OperaLombardia ha confermato che i dati editoriali iniziali sono presenti, ma **non ha consentito di verificare robots.txt**. Le due fonti rimangono quindi `pending`: nessun fetch automatico live è stato autorizzato. La pipeline è stata irrobustita: se una pagina contiene una data nuova e una qualsiasi anomalia, non pubblica un sottoinsieme delle proposte; mantiene il catalogo precedente e gli ID canonici. Gli orari nuovi sono convertiti con `Europe/Rome`, rispettando l'ora legale e rifiutando ore ambigue o inesistenti. Evidenze, limiti e prossimi passi: [SOURCE_READINESS_2026-11-20](docs/SOURCE_READINESS_2026-11-20.md).

### Attivazione condizionata delle due fonti (20/11/2026)
Le prime due produzioni sono ora abilitate a **tentare** la verifica automatica quotidiana in seguito all'autorizzazione dell'operatore; ogni fetch della pagina resta subordinato a un `robots.txt` leggibile, valido e permissivo per la pagina specifica. Una pagina vietata, robots irraggiungibile o parsing dubbio non produce modifiche ai dati. Lo stato `approved` non è una dichiarazione di consenso da parte del sito sorgente. Esito tecnico in `data/catalog-source-health.json` dopo ogni controllo, se pubblicato. Nessuna pubblicazione SFTP. Vedi [SOURCE_ONBOARDING](docs/SOURCE_ONBOARDING.md).

### Ampliamento verificato del Regio (novembre 2026)
Due nuove messe in scena del Teatro Regio di Torino, stagione 2026/27, con **13 nuove recite puntuali** documentate sulle pagine ufficiali: *Edgar* di Puccini (7 date, dal 22 gennaio al 6 febbraio 2027) e *Salome* di Strauss (6 date, dal 2 al 17 aprile 2027). Calendari ufficiali: [Edgar](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/edgar) e [Salome](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/salome). Sono conservate anche le recite di anteprima giovani quando esplicitamente presenti nel calendario, senza inventarne orari. Il catalogo passa da 19 a **32 recite**, 4 opere, 5 teatri e 7 messe in scena; 30 con orario, 2 senza. Ogni nuova replica ha ID canonico e scheda della produzione, mentre i vecchi ID rimangono invariati. Le due pagine entrano nella lista del monitoraggio giornaliero *condizionato* alle regole `robots.txt` runtime; nessun SFTP per aggiornare il JSON.

### Completamento cartellone operistico Teatro Regio 2026/27
Le **nove produzioni d'opera del cartellone principale** hanno ora date e ore ufficiali censite: Cavalleria rusticana e Pagliacci (9 recite ciascuna, in dittico), La bohème di **Ruggero Leoncavallo** (6), Iris (7), Edgar (7), La traviata (11), Salome (6), Carmen (11), Evgenij Onegin (7). Il titolo *Juditha triumphans* è un **oratorio** e viene escluso dal catalogo lirico; restano esclusi balletti e concerti. La distinzione tra *La bohème* di Leoncavallo e quella di Puccini è preservata grazie alla chiave canonica titolo+compositore. Le nuove produzioni sono monitorate condizionatamente da robots.txt ogni giorno come quelle già operative. Nel catalogo complessivo attuale: **81 recite, 10 opere, 5 sedi e 13 messe in scena; 79 orari noti, 2 ignoti**. L'estensione a OperaLombardia e alle altre fonti prosegue separatamente. Nessun deployment SFTP per i dati.

### OperaLombardia — ampliamento attraverso i partner territoriali (20/11/2026)
Dopo il censimento di *L'italiana in Algeri*, sono state verificate presso il partner ufficiale [Teatro Fraschini di Pavia](https://www.teatrofraschini.it/stagione/) le altre quattro produzioni della stagione lirica 2026/27: [Turandot](https://www.teatrofraschini.it/programma/turandot/), [Cavalleria rusticana / Pagliacci](https://www.teatrofraschini.it/programma/cavalleria-rusticana-pagliacci/), [Un ballo in maschera](https://www.teatrofraschini.it/programma/un-ballo-in-maschera/) e [Death in Venice](https://www.teatrofraschini.it/programma/death-in-venice/). Sono state aggiunte 10 recite documentate con giorno e ora (Cavalleria e Pagliacci mantengono due identità di opera separate nella stessa serata), senza modificare gli ID precedenti. Il totale sale a **91 recite, 13 opere, 5 teatri, 18 messe in scena**, con 2 orari ancora non noti a Brescia. Il partner è monitorato attraverso l'adapter conservativo `opera_atlas/fraschini_parser.py`, con verifica `robots.txt` obbligatoria a ogni scan. **Non** equivale al completamento delle tournée OperaLombardia negli altri teatri: occorre riconciliare Como/Brescia/Cremona per ogni opera. Nessuna pubblicazione SFTP.

### Apertura delle altre fonti iniziali (20/11/2026)
Il catalogo nazionale include ora un primo blocco di **40 nuove recite verificabili** dalle pagine ufficiali di Scala, Arena di Verona, Fenice, Teatro Massimo Palermo e Regio Parma. Dettagli delle produzioni, date, eccezioni e stato di tutti gli otto enti nel [rapporto di copertura](docs/INITIAL_SOURCE_COVERAGE_2026-11-20.md). Il totale sale a **131 recite, 19 opere, 10 teatri e 24 messe in scena** (129 orari noti, 2 ignoti). La prima *Fedora* della Fenice del 13/11, espressamente annullata, **non compare** tra le recite attive; non sono incluse le prove Under30 e aperte di Butterfly a Parma. L'acquisizione di queste cinque nuove fonti è ancora **editoriale**: gli adapter live non sono attivati fino al collaudo robots e parser sul dominio esatto. Nessuna nuova infrastruttura o pubblicazione SFTP per il JSON.


### Nuove produzioni Venezia/Palermo — novembre 2026
Cinque produzioni con 39 recite puntuali sono state verificate sulle pagine ufficiali della Fenice e del Massimo: Jenůfa (5), Madama Butterfly (9), Carmen (8), Lucia di Lammermoor (8), Tosca (9). Gli orari sono quelli pubblicati dall'ente, senza inferenze; nessun testo di programma o immagine è copiato. I nuovi record mantengono la relazione unica opera–messa in scena–teatro–repliche e gli ID delle produzioni già presenti. I link sono negli eventi e nella documentazione `docs/PUBLIC_CATALOG.md`. Dopo pubblicazione JSON: 170 recite, 29 messe in scena, 22 opere e 10 teatri. Queste cinque pagine sono per ora **seed editoriali verificati**, non ancora connettori quotidiani: prima di iscriverle allo scheduler servono parser specifici e verifica runtime robots. I dati JSON continuano a essere pubblicati senza SFTP.


### Circuito OperaLombardia: calendario 2026/27 riconciliato
Dal [calendario ufficiale](https://www.operalombardia.it/calendario/) sono state censite 38 recite aggiuntive, in 19 messe in scena, per Turandot, Death in Venice, il dittico Cavalleria rusticana / Pagliacci e Un ballo in maschera. Gli eventi interessano anche Bergamo, Novara, Reggio Emilia e Ravenna. Sono pubblicate **solo data, opera, città e teatro**, senza inventare gli orari che il calendario non riporta. Rimangono intatti gli ID delle 170 recite precedenti; il nuovo totale è 208 recite / 48 messe in scena / 22 opere / 14 teatri, 40 orari mancanti. Gli orari già verificati su pagine di partner (ad esempio Pavia) continuano a comparire. La raccolta *live* di tutte le righe del calendario mediante parser dedicato non è ancora implementata: questo è un seed editoriale verificato con fonte ufficiale, non un monitoraggio automatico dei nuovi titoli. Nessun deploy SFTP.

### Acquisizione quotidiana dell'indice completo OperaLombardia
L'adapter `operalombardia_calendar` legge una volta al giorno `https://www.operalombardia.it/calendario/`, dopo un controllo robots.txt valido/permissivo. Verifica la tabella multi-opera/teatro, identificando opere (incluso il dittico Cavalleria/Pagliacci), giorni, sedi e città. Gli orari non pubblicati rimangono null. Le osservazioni sono riconciliate con ID stabili; gli orari provati dalle pagine dei teatri non vengono cancellati da un indice solo-data. Un titolo nuovo, sede non riconosciuta, markup incompleto o spostamento ambiguo richiede revisione e non modifica il catalogo valido.

### Copertura trasparente delle otto fonti ufficiali
Il workflow quotidiano di `opera-atlas` genera anche `public/catalog/coverage.json`, senza SFTP. Per ciascuna delle otto fonti del registro fornisce numero di messe in scena e recite effettivamente censite, URL ufficiale, numero di pagine monitorate, ultimo esito tecnico e stato (`calendar_index_verified`, `detail_pages_verified`, `configured_not_verified`, `editorial_only`, `not_started`). **Nessuna fonte è dichiarata stagione completa senza un audit indipendente di titoli e date.** Il Rossini Opera Festival rimane non avviato, mentre i cinque teatri nazionali già presenti come seed editoriale non sono falsamente mostrati come scanner automatici. Serve a programmare l'espansione ed evitare che una fonte mancante passi inosservata.

### Secondo ampliamento nazionale — Scala e Arena, 20/11/2026
Aggiunte le produzioni documentate da pagine ufficiali **Don Giovanni** di Mozart (10 recite, Scala Milano), **La bohème** di Puccini (8 recite, Scala Milano) e **Nabucco** di Verdi (6 recite, Arena Verona). La recita di *Nabucco* del 27 agosto 2027 **non è pubblicata**: la Fondazione Arena annuncia esplicitamente la sostituzione con *Carmen*. I dati risultano in `data/verified-launch-catalog.json` e nel registry canonico con 24 nuovi ID, senza riassegnare gli ID preesistenti. Il catalogo conta **232 recite**, **25 opere**, **14 teatri** e **51 messe in scena**. I nuovi parser `opera_atlas/scala_arena_parser.py` analizzano date e orari soltanto dalle pagine individuali, con host ufficiali e controlli robots runtime quando la fonte sarà abilitata. Attualmente le tre nuove sorgenti sono `pending` finché il parser non viene collaudato su HTML ufficiale tramite GitHub Actions; la pubblicazione del JSON **non richiede SFTP**.

### Collaudo live non distruttivo di nuove fonti (Scala/Arena)
Per verificare i nuovi parser Scala e Arena prima dell'attivazione della scansione quotidiana, il workflow `source-probe.yml` in **opera-atlas** effettua un controllo **senza commit** di robots.txt e delle singole pagine ufficiali, confrontando il calendario reale con le date canoniche già verificate. Si attiva su merge del codice del probe o manualmente. Se robots è indisponibile, negato, la pagina è mutata o manca una data/ora, il job fallisce e non modifica stato o catalogo. Non significa che fonti `pending` siano state approvate. Tutti i test restano in `opera-atlas`; nessun SFTP.

### Attivazione monitoraggio Arena e adattamento live della Scala
Il primo collaudo live da GitHub Actions ([run 44809106408](https://github.com/jeckodevelopment/opera-atlas/actions/runs/44809106408)) ha verificato robots.txt e **sei recite esatte di Nabucco** sulla pagina Arena. Da qui, `arena-nabucco-2027` è stato promosso a scansione quotidiana `approved`, sempre con robots runtime. Le due pagine Scala non erano state riconosciute dal parser; ora il modulo cerca direttamente date complete con ore adiacenti, evitando dipendenza da intestazioni o immagini non testuali. Finché il nuovo probe non le conferma, entrambe restano `pending`. Dati pubblici invariati e nessun SFTP.

### Scala e Arena: scansioni giornaliere verificate (20/11/2026)
La seconda esecuzione live [source-probe 44809794379](https://github.com/jeckodevelopment/opera-atlas/actions/runs/44809794379) ha superato **tutte le tre verifiche di robots.txt e corrispondenza del calendario**: Scala *Don Giovanni* 10/10, Scala *La bohème* 8/8, Arena *Nabucco* 6/6. Di conseguenza le due pagine Scala passano a `approved` nel registro e vengono monitorate quotidianamente da `refresh-catalog.yml`, come la pagina Arena già attivata. Ogni richiesta ricontrolla robots e fallisce senza cancellare dati se il sito cambia o nega l'accesso. Per permettere l'espansione alle restanti fonti censite, la capacità configurabile è stata innalzata da 20 a **48 URL approvati** con timeout workflow di 25 minuti; in seguito privilegiare indici di stagione per ridurre richieste e manutenzione.

### Correzione dei controlli post-attivazione Scala/Arena
La prima esecuzione quotidiana dopo la promozione live ha riportato Scala e Arena come `detail_pages_verified`. Il test storico che le classificava sempre `editorial_only` non era più attuale: i controlli ora accettano lo stato verificato **soltanto per le due fonti con scan live documentata**, lasciando separate le altre fonti ancora solo editoriali. Il workflow di rigenerazione è ora eseguito anche quando cambiano test o logica del report di copertura, così le transizioni dei connettori non sono nuovamente bloccate da verifiche obsolete.
