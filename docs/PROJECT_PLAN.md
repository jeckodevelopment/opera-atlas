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

## F3 — URL canonici e calendario di produzione
- [x] Frontend: doppia vista per recita e per messa in scena; una messa in scena raggruppa le repliche.
- [x] Scheda opera: tutte le messe in scena nazionali presenti nel feed v2, per teatro e date.
- [x] Scheda teatro: elenco delle messe in scena e loro repliche.
- [x] Scheda messa in scena: replica/date/orario e fonte condivisi.
- [x] URL canonici descrittivi e rewrite Apache, con base href che preserva gli asset nei percorsi profondi; controllo live sul server da completare dopo deploy.
- [x] Compatibilità dei vecchi link parametrizzati quando gli ID legacy sono riconosciuti.
- [ ] Collisioni fra stagioni/produzioni successive: il generatore v2 rifiuta conflitti; assegnazione di slug qualificati e alias da automatizzare.
- [ ] Verifica accessibilità nel browser e collaudo SEO dei percorsi dopo deploy.

## F2 — acquisizione schedulata fail-closed
- [x] Job quotidiano in `opera-atlas` con fetch condizionato a `access_status=approved` ed evidenza di review del permesso.
- [x] Stato persistente nel Git: osservazioni normalizzate e ID canonici, senza servizio SQLite gestito.
- [x] Aggiunta idempotente di nuove date sicure e blocco dei possibili rinvii, cambi orario, venue ignote e fonti non raggiungibili.
- [x] Registro compatto degli esiti delle scansioni approvate e data dell'ultima verifica editoriale nel frontend.
- [ ] Approvazione effettiva delle fonti: entrambe le pagine iniziali ancora `pending`, robots non verificabile; nessun fetch live autorizzato al momento.
- [ ] Connettori per nuove produzioni e teatri oltre alle due pagine iniziali, calibrazione su HTML reale autorizzato.

### F2 — evidenza oraria da più fonti (20/11/2026)
- [x] Entità replica immutabile anche quando una fonte teatro/comune precisa un'ora assente nella fonte circuito.
- [x] Evidenze orarie per sei repliche da tre siti ufficiali; tutte con pagina fonte conservata e controlli per teatro, giorno, formato e contraddizioni.
- [x] Feed v1 e v2 sincronizzati con orari arricchiti (19 recite, 17 con ora, 2 senza) e metadati di provenienza.
- [x] Workflow di aggiornamento in grado di rigenerare il v2 quando l'input approvato cambia senza fallire prima della build.
- [ ] Verifica e autorizzazione formale della scansione ricorrente; fonti nuove e connettori live ancora `pending`.

### F2 — source readiness e correzioni di affidabilità
- [x] Verifica delle pagine di dettaglio ufficiali Regio/OperaLombardia; robots.txt non verificabile: entrambe le fonti rimangono `pending` (nessuna falsa autorizzazione).
- [x] Riconciliazione della singola pagina tutta-o-niente: una qualsiasi anomalia blocca ogni nuova recita proposta dalla pagina, senza cancellare il catalogo valido.
- [x] Ora locale `Europe/Rome`, corretta in estate e inverno, con esclusione di ore inesistenti o ambigue.
- [x] Test per mutazioni parziali, duplicati conflittuali, passaggi ora legale e fonti ancora non autorizzate.
- [ ] Concludere la verifica dei permessi robots/termini e collaudare HTML live autorizzato **prima** di attivare i crawler.

### F2 — autorizzazione condizionata a scansioni robots-gated
- [x] Consenso dell'operatore registrato per provare la lettura delle due pagine ufficiali, sempre con controllo robots.txt runtime prima di ogni fetch.
- [x] Rifiuto di robots assente, malformato/HTML, negato o rediretto; test di non-accesso alle pagine vietate.
- [ ] Verificare il primo risultato di GitHub Actions da rete del runner: non dichiarare acquisizione funzionante se robots è negato o non leggibile.
- [ ] Validare sul sito l'HTML reale e la resa del parser, espandendo poi il catalogo di opere/sedi.

### F2 — estensione del calendario Regio 2026/27
- [x] Due nuove opere / messe in scena: *Edgar* (Puccini, 7 recite) e *Salome* (Strauss, 6 recite) al Teatro Regio Torino, con giorno/ora verificati su pagina ufficiale.
- [x] 13 nuovi ID permanenti replica e 2 nuovi ID opera/messa in scena; nessun cambiamento agli ID dei record precedenti.
- [x] Nuove pagine di produzione incluse nell'allowlist editoriale e nel monitoraggio condizionato giornaliero di `opera-atlas`, con controllo robots runtime.
- [x] Test su integrità referenziale, date/orari, URL canonici e conteggi: 32 recite, 4 opere, 5 teatri, 7 messe in scena.
- [ ] Ampliare a nuove città e fonti oltre Regio/OperaLombardia; verificare altre opere del Regio con eventuali caratteristiche del parser differenti.

### F2 — chiusura cartellone principale Regio 2026/27 (20/11/2026)
- [x] Nove opere rappresentate nella sala principale: 73 recite puntuali verificate nelle pagine ufficiali, 49 appena aggiunte.
- [x] Distinzione titolo/compositore (*La bohème* di Leoncavallo) e due opere del dittico Cavalleria/Pagliacci che condividono giorno/ora senza fondere gli ID opera.
- [x] Balletti, concerti e oratorio *Juditha triumphans* esclusi coerentemente dal genere opera.
- [x] Orari locali verificati in ottobre e dopo passaggio ora legale; acquisizione quotidiana condizionata a robots valida.
- [ ] Eventi educativi, eventi in sede Piccolo Regio Puccini e possibili programmi fuori dalla sala principale: perimetro distinto, da censire dopo verifica del genere.
- [ ] Completare le altre quattro produzioni OperaLombardia 2026/27 e quindi gli altri sei enti del registro fonti.

### F2 — OperaLombardia, programmi verificati Teatro Fraschini Pavia
- [x] Verifica delle altre quattro produzioni della stagione 2026/27 presso il partner Teatro Fraschini Pavia: Turandot (2 recite), Cavalleria rusticana/Pagliacci (2 date, 2 opere), Un ballo in maschera (2 recite), Death in Venice (2 recite).
- [x] Dieci nuove repliche, cinque nuove messe in scena, tre nuove opere canoniche e zero nuove sedi fittizie; gli ID restano immutabili.
- [x] Adapter Fraschini che accetta soltanto intestazione opera con compositore e coppia di date/orari espliciti, previa verifica robots.txt; controllo idempotenza e provenienza.
- [ ] Completare la copertura di tutte le sedi della rete OperaLombardia per i quattro spettacoli (Como, Brescia, Cremona e altri partner effettivamente documentati) con date/ore esatte o null quando assenti.
- [ ] Completare altri sei enti del registro fonti.

### F2 — prime produzioni dalle altre sei fonti (20/11/2026)
- [x] Prima tranche editoriale verificata su Scala (Otello, 9 recite), Arena di Verona (Aida de Bosio, 9), La Fenice (Fedora, 7 attive), Teatro Massimo Palermo (Samson et Dalila 6, Macbeth 5) e Teatro Regio Parma (Madama Butterfly, 4): 40 nuove recite.
- [x] Cinque nuove sedi canonicalizzate, 6 opere nuove, 6 messe in scena e 40 ID replica senza alterare i 91 precedenti.
- [x] Annullamento Fedora del 13/11/26 escluso e prove Butterfly 12/14 aprile escluse dalle recite ordinarie.
- [x] Rapporto di copertura per tutte le otto fonti richieste con separazione esplicita censimento/completezza/automazione.
- [ ] Teatro Regio Parma, Scala, Arena, Fenice e Massimo: estendere alle altre produzioni, completare adapters e permessi robots.
- [ ] Rossini Opera Festival: recuperare dati puntuali tramite pagine ufficiali accessibili; calendario originario con blocco 403, non aggirarlo.
- [ ] Completare OperaLombardia per tutti i teatri coinvolti e deduplicare le tournée.


### F2 — estensione verificata 2026/27 (Venezia, Palermo)
- [x] Registrate cinque nuove messe in scena da pagine ufficiali individuali con 39 date/ore, ID canonici e relazioni teatrali preservate.
- [x] Riutilizzati gli ID delle opere Carmen e Madama Butterfly già esistenti; nuove identità solo per nuove opere o messe in scena.
- [x] Test su numeri, date/orari, fonti, DST e assenza di duplicati; JSON locale di compatibilità aggiornato insieme agli input.
- [ ] Connettori automatici Fenice e Massimo, ancora da sviluppare e collaudare con robots.txt runtime; **non** equiparare una fonte editoriale verificata a un feed automatico.
- [ ] Completamento per stagione delle prime fonti Regio Torino e OperaLombardia (indice generale e nuove produzioni non ancora monitorate).
- [ ] Completamento altre fonti in `data/sources.json`: Scala, Arena, Fenice, Parma, Massimo e Rossini Opera Festival.


### F2 — completamento primo inventario OperaLombardia 2026/27
- [x] 38 nuove date documentate dalla pagina di calendario 2026/27, con 19 nuove messe in scena ed estensione a quattro nuove città.
- [x] Nessuna ora indovinata: 38 nuove date con `time_known: false`, conservazione degli orari dimostrati da fonti partner per le recite già esistenti.
- [x] ID canonici persistenti, 14 teatri / 48 messe in scena / 208 repliche, collegamento alla pagina ufficiale.
- [ ] Parsing automatico dell'indice completo per accorgersi di nuove produzioni e cambi; il monitoraggio corrente controlla solo le pagine di produzione approvate.
- [ ] Verifica incrociata di tutti gli orari tramite le singole biglietterie; non indovinare.
