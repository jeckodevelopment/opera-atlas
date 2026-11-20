# Onboarding sorgenti per acquisizione giornaliera

Il workflow `refresh-catalog.yml` di Opera Atlas esegue giornalmente validazione, acquisizione **solo da pagine esplicitamente approvate** e pubblicazione JSON direttamente dal repository. Nessuna modifica dati invoca SFTP.

## Autorizzazione per singola pagina

Le due pagine iniziali sono in `data/daily-source-config.json` con `access_status: pending`: **non vengono scaricate automaticamente**. Prima di impostare `approved`, controllare manualmente e documentare:

1. Che l'URL HTTPS sia ufficiale e corrisponda alla produzione curata.
2. Che `robots.txt` e le condizioni d'uso permettano la specifica acquisizione. Una risposta `robots.txt` assente o non verificabile non autorizza la scansione.
3. Che il parser sia stato collaudato su HTML reale permesso, con tutti i giorni e gli orari confrontati con la pagina.
4. Che si rispettino frequenza massima **un controllo al giorno per pagina**, nessun redirect automatico, timeout 12 secondi e massimo 2 MB HTML, senza copia di testo integrale.
5. Che l'approvazione venga documentata in `approval_evidence` con riferimento concreto a verifica e data, prima della modifica `access_status: approved`.

La modifica di approvazione passa per PR e test in `opera-atlas`. Non abilitare una fonte se blocca il fetch o se il parser estrae dati incompleti.

## Regole incrementali automatiche

Il runner ricostruisce lo stato canonico da `data/verified-launch-catalog.json` e `data/identity-registry.json`. SQLite temporaneo è utilizzato per il controllo puntuale della fonte, ma **non** è necessario mantenere il file SQLite del runner tra esecuzioni: gli ID, le date e la provenienza restano nel Git versionato.

Per produzioni **già curate e riconosciute**, nuove date complete possono essere aggiunte con ID mai riutilizzati. Le date mancanti non sono cancellate; una data mancante insieme a una nuova è trattata come possibile rinvio e la nuova è bloccata per verifica. Una variazione d'orario su data già nota resta in revisione. Un teatro o produzione che non corrisponde all'archivio viene segnalato, non aggiunto per somiglianza. Un errore rete, robots, parser o pagina senza recite preserva l'ultima versione pubblicata.

Le anomalie e i risultati dei controlli approvati vengono salvati in `data/catalog-source-health.json` con data e tipo di esito, senza HTML originale. I nuovi eventi e ID sono committati **insieme** ai canali JSON con hash, al manifesto e al fallback per mantenere un rilascio coerente.

## Esecuzione e collaudo

```sh
python -m unittest discover -s tests -v
python -m scripts.daily_ingest             # Nessun fetch senza --allow-network
python -m scripts.daily_ingest --allow-network  # Solo fonti già approved
python -m scripts.build_verified_catalog
python -m scripts.publish_catalog_v2
python -m scripts.publish_catalog_v2 --check
```

I test coprono: fonte pending che non fa richieste, evidenza obbligatoria per approvare, acquisizione nuova data, ID persistente, import ripetuto, variazione di orario, possibile rinvio, indisponibilità di robots e conservazione last-known-good.

**Limiti operativi:** i primi due adapter hanno un perimetro ristretto e al momento non risultano autorizzati per la scansione automatica; l'aggiornamento quotidiano del catalogo ha luogo ma non crea rappresentazioni nuove finché non vengono autorizzate e collaudate fonti. Per l'espansione ai teatri nazionali sarà necessario aggiungere produzioni verificate e relativo identificatore canonico, non indiscriminatamente crawling del sito. Il parser Regio accetta soltanto eventi con data e ora espliciti; OperaLombardia può acquisire sole date con teatro e città.

### Gestione degli incidenti

In caso di job fallito, nessun nuovo manifesto deve sostituire il precedente. Gli hash e l'ultimo commit valido consentono di recuperare il catalogo. Se una fonte cambia struttura o smette di essere disponibile, riportarla a `pending` o `blocked`, conservare la cronologia e aggiornare l'adapter soltanto con test. L'ultima verifica editoriale (distinta dalla semplice scansione) è mostrata nel frontend.

## Evidenza secondaria dell'orario ≠ autorizzazione allo scraping

La consultazione manuale di una pagina ufficiale per ricavare un orario **non** conferisce il permesso di raccoglierla periodicamente con software. Le scansioni automatizzate restano `pending` finché robots.txt e condizioni d'uso non sono verificati. Per questo esiste il file `data/verified-time-evidence.json`, separato dal registro di approvazione `data/daily-source-config.json`.

Esempi di corrispondenze verificate il 20/11/2026:
- Teatro Sociale Como: https://teatrosocialecomo.it/spettacoli/l-italiana-in-algeri/ — 13 novembre ore 20:00 e 15 novembre ore 15:30;
- Teatro Fraschini Pavia: https://www.teatrofraschini.it/programma/litaliana-in-algeri/ — 20 novembre ore 20:00, 22 novembre ore 15:30;
- Comune di Cremona, Teatro Ponchielli: https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-litaliana-algeri — 10 dicembre ore 20:00; https://www.comune.cremona.it/vivere-comune/eventi/stagione-dellopera-litaliana-algeri-0 — 12 dicembre ore 16:00.

`scripts.build_verified_catalog.validate_time_evidence` rifiuta fonti non inserite nella whitelist specifica del teatro, date senza ID corrispondente, ore malformate e contraddizioni con il calendario primario. Il v2 eredita l'ora e le due fonti. Aggiornare o aggiungere la prova soltanto dopo nuova verifica ufficiale e test. Questo mantiene l'autonomia degli aggiornamenti del feed senza inventare un'autorizzazione alla lettura live.

## Verifica documentata e regole di atomicità — 20/11/2026
Vedi [SOURCE_READINESS_2026-11-20](SOURCE_READINESS_2026-11-20.md). Entrambe le pagine ufficiali sono consultabili, ma i robots.txt non sono stati verificabili nell'ambiente di controllo: nessuno stato è stato promosso ad `approved`. La sincronizzazione di una pagina deve essere **atomica**: duplicazioni contraddittorie, cambi orario, sedi ignote o sospetti rinvii non possono accompagnarsi a una pubblicazione parziale di nuove recite. L'offset italiano deve essere risolto con la zona `Europe/Rome`, non con `+01:00` fisso; l'ora mancante resta `null`. Il test annuale include intervalli di ora legale/solare.

## Autorizzazione condizionata dell'operatore — 20/11/2026
L'operatore del catalogo ha autorizzato espressamente l'avvio di controlli quotidiani sulle pagine pubbliche di Teatro Regio Torino e OperaLombardia **soltanto in assenza di regole ostative in robots.txt**. La consultazione manuale precedente non aveva consentito di verificare robots.txt: il nuovo stato `approved` in `data/daily-source-config.json` rappresenta **il consenso a tentare la verifica e l'acquisizione condizionata**, non la certificazione che i siti permettano lo scraping.

La funzione `fetch_official_html` verifica **ogni volta** `robots.txt` prima della pagina di produzione. Se il file è irraggiungibile, malformato, contiene un divieto per il nostro user agent o l'URL reindirizza ad altro host, il fetch della pagina non avviene. Le risposte HTML fasulle su `robots.txt` sono trattate come errore. Nessun aggiramento, autenticazione, copia di descrizioni, immagini o HTML integrale; vengono esportati solo titolo, teatro, città, data, ora eventualmente presente e collegamento alla fonte. La frequenza rimane una volta al giorno per pagina, con timeout e limiti esistenti.

**Interpretazione degli stati:** `approved` indica l'autorizzazione dell'operatore a *provare* una scansione sotto controllo, non un permesso attribuito dal teatro; `robots_blocked` o `robots_unavailable` nell'esito operativo prevale sempre e impedisce l'acquisizione. Gli esiti tecnici sono da controllare dopo il primo workflow live, poiché la consultazione esterna non ha potuto accedere a robots.txt.

## Due nuove produzioni monitorate al Regio — 20/11/2026
Sono state verificate separatamente le pagine ufficiali per [Edgar](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/edgar) e [Salome](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/salome), rispettivamente con 7 e 6 singole date/ore. Sono aggiunte a `data/daily-source-config.json` con autorizzazione dell'operatore limitata alla lettura condizionata: il successo di una precedente acquisizione sul medesimo dominio non attribuisce automaticamente il permesso per ciascuna pagina. Il fetch ricontrolla `robots.txt` prima di ogni richiesta, blocca pagine vietate o non raggiungibili e conserva l'ultimo feed valido in caso di anomalie. Non sono scaricati o riprodotti testi di produzione, immagini o materiali promozionali.

## Ampliamento delle pagine monitorate al Regio (20/11/2026)
Sono state documentate altre sei pagine ufficiali di produzione (Cavalleria rusticana, Pagliacci, La bohème di Leoncavallo, Iris, Carmen, Evgenij Onegin) come sorgenti **per singola produzione**. I giorni e gli orari provengono dalle sezioni “Calendario rappresentazioni”, non da intervalli di stagione. Tutte sono ammesse solo con condizione `robots.txt` disponibile e permissiva nel runner GitHub Actions; non viene effettuato crawling ricorsivo. Il ciclo quotidiano controlla ora 10 pagine esatte (9 Regio + 1 OperaLombardia), senza leggere il resto dei portali o copiare materiale redazionale. L'estensione a sedi del circuito e ai nuovi enti richiede altre PR con evidenza e registrazione canonica.

### Partner ufficiale OperaLombardia: Teatro Fraschini Pavia
Le pagine di produzione verificate sono `/programma/turandot/`, `/programma/cavalleria-rusticana-pagliacci/`, `/programma/un-ballo-in-maschera/` e `/programma/death-in-venice/`. Il parser `fraschini_parser.py` estrae solo le **due date e le ore esplicite** dall'intestazione dell'evento, verificando titolo e compositore in HTML e mantenendo la prova HTTPS. In caso di variazioni del markup, titolo ambiguo o mancanza di una data, interrompe la proposta; nessun orario presunto. Le richieste live vengono precedute da `robots.txt` sul dominio ufficiale e rimangono condizionate al suo permesso. Le fonti editoriali partner sono distinte dalle pagine aggregatrici OperaLombardia: non si assumono date per gli altri teatri o un permesso esteso di crawling.


### Indice OperaLombardia completo: gestione editoriale senza orari inventati
Il [calendario 2026/27](https://www.operalombardia.it/calendario/) è una pagina ufficiale multi-opera e multi-sede. L'estrazione controllata ha identificato 38 nuove date con sede/titolo chiari, non incluse nel primo catalogo. **Non** abbiamo aggiunto tale pagina al job `daily-source-config.json` come se fosse una normale scheda di produzione: l'adapter corrente non supporta un indice multi-titolo, e lo interpreterebbe erroneamente. Prima di abilitarne la scansione bisogna implementare un parser specifico e verificare il suo comportamento sul contenuto HTML reale via runner GitHub Actions. Restano attivi gli adapter già collaudati per le schede singole.

### Parsing di un calendario multi-produzione
Il solo URL autorizzato per l'indice è `https://www.operalombardia.it/calendario/`: un fetch dopo verifica robots, nessuna esplorazione ricorsiva. Il parser Python standard `HTMLParser` usa le celle delle tabelle, ricostruisce mese, anno, giorno, titolo, città e teatro; non salva testi di programma e non attribuisce ore. Pagina incompleta, titoli ignoti o variazioni sospette bloccano la riconciliazione e richiedono intervento. Il primo job live deve confermare che il markup reale rispetti le ipotesi del parser; l'errore non autorizza workaround di accesso.

### Nuovi adapter Scala/Arena e limite operativo
Le tre pagine Scala/Arena censite sono inizialmente `pending` nel registro di scansione: l'inclusione editoriale di una recita già verificata **non** implica che un parser sia pronto per l'acquisizione giornaliera. `scala_arena_parser.py` legge solo date/ore puntuali e verifica titolo e compositore; l'adapter Arena non importa la data di `Nabucco` 27 agosto perché la pagina ne annuncia la sostituzione con `Carmen`. Per abilitarne i controlli giornalieri, confermare parser e robots.txt da GitHub Actions sulla pagina ufficiale, senza aggirare 403/404 o redirect, quindi promuovere le specifiche fonti a `approved` con evidenza e test. La dimensione dell'allowlist va sorvegliata: attualmente 19 pagine controllabili a fronte di limite massimo 20 nel runner; per una gestione pluriennale è preferibile ricorrere agli indici di stagione per non moltiplicare richieste per produzione.

### Procedura probe per nuove pagine ufficiali
Prima di attivare un adapter Scala/Arena, usare il workflow `source-probe.yml` o `python -m scripts.probe_pending_sources` dalla rete del runner. Il controllo è read-only: un fetch robots-gated per pagina e confronto dell'insieme completo di date e orari con l'archivio canonico, blocco di righe mancanti, nuove o variate. Solo con il risultato `matched_official_calendar` per la singola fonte è consentita la successiva PR che la promuove da `pending` ad `approved`. Errori di accesso o parser non autorizzano l'aggiramento dei blocchi e non alterano lo storico.

### Esito reale Arena e problema Scala
Il workflow di collaudo `source-probe.yml` (run 44809106408) ha verificato tutte le sei date e orari di *Nabucco* in Arena, con robots accessibile e compatibile. La singola pagina è ora approvata per scansioni giornaliere condizionate, senza estendere automaticamente tale approvazione ad altre pagine Arena. Le due pagine Scala hanno restituito errori di parsing: fino al completamento del secondo collaudo restano in stato `pending`. L'adapter è stato migliorato per utilizzare coppie data/ora adiacenti senza affidarsi ai nomi dei blocchi grafici. Le diagnosi dei futuri job mostrano solo messaggi di validazione interni, mai HTML copiato dai siti.

### Attivazione Scala verificata 2026-11-20
Il secondo collaudo live [run 44809794379](https://github.com/jeckodevelopment/opera-atlas/actions/runs/44809794379) ha confermato **tutti** gli eventi attesi sulle pagine ufficiali Scala Don Giovanni (10) e La bohème di Puccini (8) e Arena Nabucco (6), con robots accessibile e permissivo. Le tre pagine hanno quindi un monitor giornaliero approvato in modo condizionato: ogni nuovo fetch ricontrolla robots. Il limite operativo di sorgenti del singolo job passa da 20 a 48, con timeout massimo 25 minuti; non è un'autorizzazione implicita a nuove URL, che devono essere approvate singolarmente.


## F2 — scoperta quotidiana delle produzioni non ancora censite

Il monitoraggio di un calendario ufficiale può incontrare nuove produzioni o sedi non ancora presenti nel registro canonico. Il job giornaliero salva ora le righe fattuali non riconosciute (titolo, teatro, città, data e ora quando presente, fonte) in una **coda separata di revisione**, senza importarle come spettacoli pubblici e senza generare automaticamente nuovi ID di messa in scena.

- `scripts.daily_ingest` conserva `candidates` negli esiti delle fonti approvate che richiedono revisione. Se la stessa pagina contiene dati non riconosciuti, continua a non pubblicare alcuna modifica parziale di quella pagina.
- `scripts.discovery_queue` consolida giornalmente gli identificativi candidati deterministici, le date osservate, la prima e l'ultima osservazione.
- `data/discovery-candidates.json` è il registro persistente; `public/catalog/discovery.json` rende il risultato disponibile per diagnostica e futura UI di revisione. Non sostituisce e non alimenta automaticamente il feed canonico `public/catalog/v2`.
- La coda include soltanto fatti provenienti da pagine effettivamente lette durante scansioni consentite dal controllo robots runtime; fonti pending, blocked, errori di rete o scansioni non valide non producono candidate.
- La promozione a produzione reale richiede riconciliazione con repertorio, compositore, teatro e identità canonica, confronto completo della fonte e test. Non assumere che una riga dell'indice equivalga a una nuova produzione sicura.

Collaudo: `python -m unittest discover -s tests -v`, quindi workflow `Refresh public Opera Atlas catalog` e verifica che `discovery.json` sia coerente con il registro; nessun SFTP. Le altre fonti ancora editorial-only devono prima acquisire connettori di calendario consentiti: questa funzionalità non costituisce copertura completa delle otto stagioni.


### F2 — correzione scoperta titoli sconosciuti (PR successiva alla #56)

Il parser dell'indice OperaLombardia conserva la modalità rigorosa preesistente: una chiamata senza opzioni rifiuta titoli non riconosciuti. **Solo** la pipeline di scansione giornaliera abilita `allow_unknown_for_review=True`: una riga con titolo sconosciuto e città, teatro, data validi viene inoltrata alla coda di scoperta introdotta dalla PR #56. Il titolo sconosciuto NON è considerato opera verificata: potrebbe anche essere un evento non lirico e richiede classificazione editoriale.

Restano fail-closed calendario parziale, date malformate, righe duplicate, cancellazioni e rinvii. Per una pagina con candidato sconosciuto l'esito è `review_required`, nessuna nuova replica viene pubblicata dalla pagina; il dato fattuale è invece conservato nella coda per successiva validazione. Test: `tests/test_operalombardia_daily_index.py`, oltre alla suite completa. Questo intervento abilita la scoperta effettiva solo per l'indice già approvato di OperaLombardia; **non** dichiara attivi gli indici delle altre sette fonti.


## F2/F3 — nuove opere: scheda editoriale obbligatoria e distribuzione senza SFTP

Il rilevamento di una produzione non equivale automaticamente alla pubblicazione dell'opera. Prima di promuovere un candidato di `data/discovery-candidates.json` è obbligatorio:
1. Stabilire che sia realmente un'opera lirica e verificare **titolo canonico, eventuali omonimie, compositore, teatro, località, produzione, data e provenienza ufficiale**. Se un titolo coincide ma il compositore è diverso, non unificare le opere.
2. Verificare l'identità nel registro canonico e attribuire ID permanenti a nuova opera, sede (solo se realmente nuova), messa in scena e repliche. La coda non produce automaticamente questi identificativi.
3. Scrivere una **sinossi breve e originale in italiano**, indicativamente 1–2 frasi, orientata ad accompagnare il pubblico alla rappresentazione; niente materiali didattici, trame estese, testo copiato dagli organizzatori o informazioni inventate.
4. Includere la sinossi nella fonte editoriale versionata `site/work-synopses.json`; il job `scripts.publish_work_editorial` verifica la corrispondenza 1:1 con le opere canoniche e ne impedisce la pubblicazione se una descrizione manca o non ha lunghezza adeguata.
5. Distribuire `public/catalog/work-editorial.json` assieme al feed v2 tramite GitHub Actions in `opera-atlas`. Le pagine directory/dettaglio leggono il JSON GitHub, con fallback alla precedente copia locale.

**Collaudo:** eseguire `python -m unittest discover -s tests -v`, `python -m scripts.publish_work_editorial`, `python -m scripts.publish_work_editorial --check`; eliminare in fixture una sinossi e verificare il blocco. Dopo la prima pubblicazione SFTP del frontend aggiornato tramite il solo workflow di `jeckodevsite`, ogni nuova sinossi nel feed diventa disponibile senza ulteriori deploy delle pagine. L'aggiornamento dei dati resta esclusivamente nelle Actions di `opera-atlas`.

**Limite esplicito:** non viene generata automaticamente una sinossi sulla sola base di un titolo non classificato. Per nuove opere non già censite occorre un processo affidabile di arricchimento e verifica, da estendere insieme ai connettori completi di Scala, Arena, Fenice, Parma e Palermo. Questa PR implementa il vincolo di completezza e la distribuzione, non dichiara quei connettori completi.


## F2 — monitoraggio degli indici nazionali Scala, Arena, Fenice

Il job `scripts.discover_season_indexes` prende in esame **tre ingressi ufficiali esatti**: stagione lirica Scala 2026/27, spettacoli Arena Opera Festival 2027, categoria opera Fenice 2026/27. Le richieste sono limitate a una pagina di indice per fonte e al relativo robots.txt; lo scanner non segue i collegamenti e non copia pagine di dettaglio.

- Configurazione `data/season-index-config.json`: sorgenti esplicite con controllo runtime robots fail-closed e soglia minima di link; non è una concessione del teatro ad acquisire qualsiasi contenuto del sito.
- I collegamenti candidati devono avere HTTPS, host identico e struttura coerente con la sezione ufficiale prevista. URL esterni, query string e sezioni escluse sono ignorati.
- Identificativi candidati deterministici, `first_seen`, `last_seen`, stato `needs_review` in `data/season-index-candidates.json` e `public/catalog/season-index-candidates.json`. Esiti tecnici in `data/season-index-health.json`.
- In caso di robots negato/indisponibile, pagina incompleta, struttura mutata o errore HTML: nessun nuovo collegamento e conservazione delle candidate precedenti.
- **Non equivale a importare automaticamente le nuove opere:** i collegamenti non dimostrano ancora genere, compositore, teatro, singole recite o cancellazioni. Occorre verifica della pagina di dettaglio e creazione delle entità canoniche, includendo la scheda editoriale e la sinossi originale come richiesto nel blocco F2/F3 precedente.
- Gli indici di Regio Parma e Massimo Palermo, così come il calendario ROF eventualmente inaccessibile, restano fuori dall'attivazione e richiedono un adapter specifico verificato.

Collaudo: `python -m unittest discover -s tests -v`, poi l'esecuzione del workflow `Refresh public Opera Atlas catalog`. Controllare i tre esiti e la coda JSON; nessun SFTP per l'acquisizione. La prima modifica JavaScript frontend del feed editoriale deve essere distribuita separatamente solo con il workflow SFTP di `jeckodevsite`.


## F2 — triage dei primi 45 link live Scala/Arena/Fenice

La prima esecuzione reale degli indici in GitHub Actions (20/11/2026 21:01 UTC) ha letto 14 link Scala, 16 Arena, 15 Fenice. **Un link di sezione non costituisce prova che si tratti di opera lirica**, perciò il nuovo triage distingue:

- `already_catalogued`: URL di produzione esattamente presente nel manifesto editoriale verificato, non una nuova scoperta.
- `excluded_nonopera`: URL già identificato come pagina di servizio o programma non lirico dalla prima acquisizione, su allowlist negativa **esatta** per sito (regolamenti, danza, concerti e pagine informative). Nessuna esclusione generalizzata di titoli nuovi.
- `needs_review`: nuovi link potenzialmente pertinenti, che **non diventano automaticamente opere o recite pubbliche**. Occorre verificarne genere, compositore, calendario ufficiale, teatro e descrizione originale breve.

La classificazione del registro persistente viene aggiornata anche per gli elementi storici; rimangono ID stabili, `first_seen` e `last_seen`, senza cancellazioni. Una voce già risolta editorialmente con stato diverso dai tre stati automatici non viene riaperta. Il filtro dei nuovi link impedisce di creare candidate per pagine di servizio note senza sovrastimare la copertura.

Collaudi: `python -m unittest discover -s tests -v` (test dei link esclusi, controllo URL canonici e preservazione delle candidate); verifica successiva di `data/season-index-candidates.json` e `data/season-index-health.json` dal job giornaliero. Le nuove recite e le schede opera complete di sinossi sono un successivo passaggio di acquisizione dopo verifica delle pagine puntuali. Non modificare `jeckodevsite` per questi JSON.


## F2 — estensione scoperta a Regio Parma e Teatro Massimo Palermo

All'individuazione giornaliera di link Scala, Arena e Fenice si aggiungono due indici ufficiali puntuali: `https://teatroregioparma.it/categoria-spettacoli/opera/` (Stagione Opera 2027) e `https://www.teatromassimo.it/la-stagione-2026-27/` (Stagione 2026/27). Sono pagine già individuate come sorgenti ufficiali; i fetch periodici rimangono **sempre subordinati alla verifica robots.txt runtime** con rifiuto di pagina non accessibile, robots negato, redirect e pagina incompleta.

Il parser raccoglie solo URL dell'esatto host e delle sezioni produzione `/spettacolo/` (Parma) e `/event/` (Palermo); esclude collegamenti già identificati come prove, iniziative non liriche e balletto. Poiché gli indici possono includere anche manifestazioni diverse, qualsiasi URL non riconosciuto entra **soltanto in revisione**: non costituisce attestazione di opera, compositore o recita. Per la pubblicazione canonica occorrono lettura consentita e verifica dettagliata della pagina, date/orari, classificazione di genere, deduplicazione e scheda opera con sinossi originale breve.

Controlli: test di estrazione Parma/Palermo, esiti di cinque fonti giornaliere, conservazione dell'ultima versione valida, e `public/catalog/season-index-candidates.json`. Nessun deploy SFTP dei dati. Rossini Opera Festival resta da verificare per accessibilità/policy; non aggirare un eventuale 403. Non dichiarare nessuna stagione completa sulla sola base degli indici.


## F2 — lettura automatica delle pagine di dettaglio candidate

Oltre al monitoraggio quotidiano dei cinque indici, `scripts.collect_candidate_details` approfondisce giornalmente **al massimo 10 candidate** a rotazione deterministica. Seleziona solo URL HTTPS dello stesso dominio e della medesima sezione di produzione censita dall'indice, con `status: needs_review` e fonte approvata. Per ogni singola pagina esegue una nuova verifica robots.txt fail-closed tramite il medesimo `fetch_official_html` con limiti di timeout e dimensione; nessun crawling ricorsivo.

Il parser legge **esclusivamente fatti espliciti** nei blocchi `application/ld+json` di tipo `Event`, `MusicEvent` o `TheaterEvent`: titolo evento, giorno, ora solo se timestamp con timezone, nome della sede eventualmente presente. Ignora ore senza timezone, date non valide, testi di sinossi e contenuti promozionali. Il risultato è una **proposta di evidenza** `needs_editorial_review`, mai un nuovo evento pubblico. Non identifica automaticamente il compositore da titolo omonimo e non scrive la sinossi. Il completamento della scheda opera prima della pubblicazione resta obbligatorio.

I JSON `data/candidate-detail-evidence.json` e `public/catalog/candidate-detail-evidence.json` conservano identificativo candidato, URL fonte, hash della pagina e righe strutturate; `data/candidate-detail-health.json` registra gli esiti della scansione. Le acquisizioni inconcludenti o negate non eliminano evidenze precedenti. Il file pubblico è **diagnostico e di revisione**, non viene unito a `public/catalog/v2`.

Collaudi: test `tests/test_candidate_detail_evidence.py` e suite completa; controllare dopo il merge il numero di pagine con `facts_found` e i casi `unavailable_or_unstructured`, senza dichiarare completamento delle stagioni. L'assenza di JSON-LD su una pagina richiederà un adapter specifico collaudato sul markup reale, non estrazione euristica o date inventate. Il job dati opera solo su `opera-atlas` e non richiede SFTP.


### F2 — confinamento alle sezioni stagionali reali

Dopo il primo controllo live Parma e Palermo sono risultati leggibili, ma gli indici HTML contengono anche collegamenti alla navigazione generale. Il parser dei due siti usa ora una sezione semantica delimitata per evitare falsi positivi: **Parma** solo dopo l'intestazione `h1 Opera` e prima del footer; **Palermo** solo fra `h2 CALENDARIO OPERE E BALLETTI` e la successiva sezione `h2 CALENDARIO CONCERTI`. Gli URL fuori da queste aree non vengono considerati candidate nuove. Rimangono i controlli di dominio HTTPS, path esatto, esclusioni di balletto/prove e soglia minima di completezza; se la struttura cambia, il job non sovrascrive i dati buoni e segnala errore.

La coda storica non viene cancellata solo perché un collegamento non appare più nella nuova estrazione: eventuali variazioni stagionali devono essere valutate prima di marcare un evento cancellato. I test simulano menu, footer e sezione concerti presenti nella stessa pagina.
