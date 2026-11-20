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


### F2 — recupero delle date quando manca JSON-LD (Scala e Arena)

Il primo job live delle nuove pagine di dettaglio ha restituito dieci casi senza metadati `Event` strutturati sufficienti, **zero recite nuove**. Il collector tenta ora un secondo parser **soltanto** per Scala e Arena, e **soltanto** quando l'URL corrisponde in modo univoco allo slug di un'opera già presente nel registro canonico con titolo e compositore verificati. In tal caso utilizza i parser Scala/Arena già collaudati: la pagina ufficiale deve contenere davvero il titolo, il compositore e coppie complete data+ora; ora locale Europe/Rome con gestione DST. La nuova evidenza è comunque registrata solo in coda di revisione, non pubblicata come replica.

Per opere non ancora presenti nel registro, slug ambigui, compositor mancante, pagine incomplete, sostituzioni o nuove strutture non viene creato alcun dato fittizio. Fenice, Parma e Palermo richiedono ulteriori parser dedicati ove non espongano JSON-LD Event affidabile. La scheda e la sinossi originale di un'opera nuova restano un requisito obbligatorio prima di promuoverla in catalogo.


## F2 — auto-catalogazione canonica senza riconciliazione manuale

Il requisito di prodotto è **interamente unattended**: scoprire, classificare, identificare e pubblicare automaticamente nuove opere/produzioni/recite quando tutti i dati necessari possono essere verificati senza ambiguità. Gli errori, le fonti inaccessibili e le identità non risolvibili non devono diventare una coda di lavoro umano obbligatoria: rimangono osservazioni diagnostiche, saranno ritentate nelle scansioni successive e il catalogo valido continua a essere servito.

Il primo motore di promozione `scripts.auto_catalogue` usa la coda persistente dei cinque indici nazionali e le evidenze delle pagine di dettaglio. **Nel primo perimetro operativo Scala e Arena**, per una produzione non ancora censita:
- la pagina deve provenire dall'esatto host e sezione autorizzati e superare il controllo robots.txt nel collector;
- la riga deve contenere **opera e compositore già univocamente riconosciuti nel repertorio canonico**, non soltanto un titolo o uno slug somigliante;
- teatro e città devono corrispondere esattamente a una sede canonica; giorno e ora sono verificati con timestamp esplicito e fuso `Europe/Rome`;
- non deve esistere una seconda messa in scena ambigua della stessa opera nello stesso teatro, né un orario contrastante;
- il job attribuisce senza intervento umano ID permanenti a nuova produzione e singole recite, aggiornando il manifesto editoriale, registry, registro degli URL ufficiali approvati per l'import automatico e il feed versionato nella stessa pubblicazione GitHub;
- il record JSON della scheda opera esiste già per i titoli riconosciuti e ha una breve sinossi. Niente SFTP per il refresh dati.

I test verificano import al primo passaggio, ID stabili al secondo, dati di fonte non valida, compositore errato, data/ora dubbie, collisioni, e ripetibilità del feed. Il motore **non** assume che `Event` JSON-LD identifichi sicuramente un'opera lirica. Per opere assenti dal repertorio serve in futuro una fonte autorevole utilizzabile per la coppia titolo/compositore e una sinossi originale **fattualmente affidabile**: non è accettabile inventarne una da un URL o dichiarare automatica la creazione dell'opera quando la descrizione non è supportata dai dati. Tali casi rimangono automaticamente ritentabili, senza chiedere azioni di riconciliazione all'operatore.

Questo percorso sostituisce progressivamente l'onboarding manuale, ma **non dichiara ancora realizzata l'autonomia totale su tutte le fonti**, né garantisce un impossibile aggiornamento corretto quando gli organizzatori bloccano l'accesso. Occorreranno parser affidabili per nuove opere e per Fenice, Parma, Palermo, Regio Torino/OperaLombardia e ROF. Resta la politica last-known-good e nessuna pubblicazione basata su informazioni inconcludenti.


### F2 — autopubblicazione delle nuove produzioni del circuito OperaLombardia

Il motore `scripts.auto_catalogue` supporta anche la nascita autonoma di nuove produzioni nell'indice ufficiale OperaLombardia: dai candidati fattuali raccolti in `data/catalog-source-health.json` (solo indice approvato, con scansione robots-gated conclusa in `review_required`) identifica **titolo univoco** tra le opere già canoniche e **teatro+città esattamente presenti** nel registro delle sedi. Non inventa il compositore: quando esistono più opere dallo stesso titolo (es. le differenti *La bohème*) o la sede è sconosciuta, lascia il record in acquisizione automatica per successive evidenze più complete.

Una coppia titolo/compositore già riconosciuta eredita la sinossi breve editoriale canonica; per la nuova produzione vengono attribuiti automaticamente identificativo permanente, sede, URL ufficiale e date. Se il calendario non riporta l'ora, questa rimane `null` e il frontend indica l'orario da verificare, come già previsto dalle regole del progetto. Nuove date vengono aggiunte senza riutilizzare ID né sovrascrivere date/orari precedenti. In caso di produzione già presente allo stesso teatro con URL differente, il motore evita duplicati e richiede nuove prove **automatiche**, non una riconciliazione manuale.

Per ottimizzare il primo tratto end-to-end Scala/Arena, il collector delle pagine di dettaglio ora visita prima le candidate il cui URL corrisponde già in modo univoco a un'opera canonica e usa il resto delle 10 richieste/giorno a rotazione per le opere totalmente sconosciute. Test: `test_auto_calendar_onboarding.py` e test di priorità in `test_candidate_detail_evidence.py`. Il rinnovo delle scansioni e la pubblicazione dei feed avvengono senza SFTP e senza interventi umani.


## F2 — nuove opere mai censite: ricerca e pubblicazione completamente automatizzate

Il processo non richiede una riconciliazione umana successiva quando i dati sono sufficienti. Per un link di produzione `needs_review` degli indici autorizzati, `scripts.auto_work_research` prova automaticamente a risolvere:
1. Identità **esatta** dell'opera in [Wikidata](https://www.wikidata.org/wiki/Wikidata:Data_access), con classe istanza `opera` (`Q1344`), un **solo** compositore `P86` e pagina italiana collegata dall'entità stessa. Omonimie, assenza di composer o tipi diversi da opera sono scartati.
2. Una fonte fattuale di trama tramite API MediaWiki sull'articolo italiano corrispondente. Nessuna copia di testo Wikipedia, HTML o descrizioni del teatro entra nel repository: l'estratto è usato **solo in memoria** come input per scrivere una descrizione originale molto breve.
3. Una sinossi italiana di 1–2 frasi tramite API linguistica configurabile. Il modello è vincolato alle informazioni fattuali disponibili e deve **rifiutare** se l'estratto non offre sufficienti elementi di trama. Sono controllati lunghezza, formato JSON strutturato e copia di sequenze testuali. Il risultato viene salvato con QID e URL delle fonti in `data/auto-work-intelligence.json`, per provenienza e riuso senza chiamate ripetute.
4. Il collector Scala/Arena, eseguito **dopo** questo arricchimento, riutilizza i parser ufficiali collaudati, richiede che la pagina del teatro mostri sia il nome dell'opera sia il compositore verificato e identifica **date e orari delle singole repliche**. Dati JSON-LD generici e titoli URL non costituiscono conferma.
5. `scripts.auto_catalogue.promote_new_works` esegue un'unica validazione dell'intero grafo. Solo quando tutto concorda crea **opera, ID canonico, messa in scena, recite, sinossi originale e URL fonte**. Il feed `public/catalog/v2` e `public/catalog/work-editorial.json` sono rigenerati e committati in GitHub, senza SFTP. In caso contrario l'ultima versione pubblicata resta intatta, il sistema riprova automaticamente in una successiva scansione.

### Configurazione iniziale facoltativa dell'elaborazione linguistica

Le API Wikimedia di interrogazione dei dati sono pubbliche. La sintesi originale richiede invece un motore linguistico: **GitHub Models è stato ritirato il 30 luglio 2026** e non può essere usato per questo flusso. L'integrazione è predisposta tramite secret GitHub Actions **`ATLAS_OPENAI_API_KEY`** nella sola repository `opera-atlas`, modello economico `gpt-6-luna`. L'accesso API e gli eventuali costi sono indipendenti da ChatGPT. Nessun servizio a pagamento viene chiamato quando il secret è assente. Quando disponibile, sono ammesse al massimo **3 ricerche di nuove opere per esecuzione**, con timeout e risposta limitati. Non inserire mai credenziali in YAML, dati JSON pubblici, log o PR. Dopo la configurazione iniziale il meccanismo è unattended.

**Limiti strutturali:** questo è il primo percorso automatico per **nuove opere presenti negli indici Scala/Arena** con pagine di dettaglio in formato verificabile. Non inventa trame e non promette copertura quando Wikidata non distingue un'opera, Wikipedia non contiene abbastanza fatti o la fonte teatrale blocca l'accesso. Nessuna richiesta di riconciliazione umana: in questi casi la mancata pubblicazione è una protezione automatica, con tentativi futuri e contatori diagnostici. Restano da implementare parser delle altre fonti e la gestione di due opere omonime con slug pubblici differenti. L'obiettivo generale di completare il monitoraggio di otto fonti rimane aperto.

### Collaudi automatici

`python -m unittest discover -s tests -v` include un'identità Wikidata simulata con compositore univoco, rifiuto delle omonimie/classi estranee, mancanza di credenziali, idempotenza della ricerca, creazione in memoria di opera + sinossi + recita, mancata pubblicazione per composer/ora/venue non validi e mantenimento degli URL di provenienza. Il flusso pubblico usa solo le modifiche già validate e genera un commit insieme ai manifest JSON; nessun deploy frontend viene invocato. La generazione reale della sinossi non può essere considerata collaudata senza un secret API valido.


## F2 — acquisizione autonoma di recite Fenice, Parma e Palermo

Il sistema non si limita più ai collegamenti d'indice per queste tre fonti: `opera_atlas.national_detail_parser` estrae **date e ore individuali** dal markup ufficiale delle produzioni, quando titolo e compositore coincidono con un'opera canonica o con un'identità acquisita da fonte autorevole. È richiamato da `scripts.collect_candidate_details` sulle singole pagine dopo il controllo robots.txt già previsto.

- **Teatro La Fenice:** legge la sequenza dei biglietti «Seleziona una data» con giorno, mese, anno e ora espliciti, fermandosi prima dei suggerimenti di altri eventi.
- **Teatro Regio di Parma:** collega l'anno riportato nel programma alle schede giorno/ora, escludendo automaticamente prove aperte e Under30, che non sono recite ordinarie. Se l'anno non è univoco, non pubblica.
- **Teatro Massimo Palermo:** richiede la concordanza completa fra l'elenco dei giorni/orari e il riepilogo della produzione che identifica mese e anno. Rifiuta calendari parziali e date incoerenti.

Le pagine non pertinenti e quelle senza identificazione univoca di titolo e compositore non possono generare recite; il collector conserva sempre l'ultima evidenza valida in caso di assenza dati, errori di rete o pagine modificate. Le evidenze valide passano a `scripts.auto_catalogue`, che ora riconosce anche le sedi canoniche Venezia/Teatro La Fenice, Parma/Teatro Regio di Parma e Palermo/Teatro Massimo. Il relativo motore crea nuovi ID e pubblica i JSON automaticamente solo dopo il controllo dell'intero grafo.

Test: `tests/test_national_detail_parser.py` (date, orari, prove, esclusioni, anno e composer) e `tests/test_candidate_detail_evidence.py`, oltre alla suite Python completa. La riuscita dei test con fixture non equivale al collaudo live: dopo merge occorre verificare `data/candidate-detail-health.json`, `data/autonomous-catalogue-health.json` e i contatori pubblici. Nessun workflow SFTP e nessun aggiornamento manuale dei JSON.


## F2 — scansione equa: nessuna candidata trascurata indefinitamente

La scansione giornaliera delle pagine di produzione e la ricerca automatica delle opere sconosciute utilizzano ora una **rotazione giornaliera di una posizione**, indipendente dalla dimensione della coda. La precedente rotazione con salto pari al budget (10 pagine o 3 ricerche) poteva riesaminare sempre lo stesso sottoinsieme quando il numero dei candidati era multiplo del budget. Si trattava di una fonte di mancato aggiornamento silenzioso incompatibile con l'obiettivo unattended.

Il collector riserva fino a **quattro delle dieci scansioni** per opere non riconosciute, anche quando ci sono più di dieci produzioni già note. Le restanti richieste favoriscono le produzioni verificabili immediatamente, senza mai impedire la scoperta progressiva. Quando una delle due classi è vuota, la capacità passa all'altra. La ricerca di identità Wikidata/sinossi mantiene il limite di tre nuove opere per giorno, visitando a rotazione anche code con 3, 6, 9 o altri multipli. I test simulano 12–30 giorni di lavoro e verificano che tutti gli ID prima o poi siano considerati, senza nuove richieste al singolo sito oltre al budget quotidiano.

Nessuna azione editoriale è richiesta come parte del normale ciclo di acquisizione. I record insufficienti restano protetti dal fail-closed, ma il lavoro di recupero procede autonomamente nelle esecuzioni successive.


## F2 — registro delle otto fonti sincronizzato automaticamente

Per evitare riconciliazioni e discrepanze tra documentazione e operatività, `scripts.sync_source_registry` aggiorna `data/sources.json` durante **ogni** refresh del catalogo, dopo la raccolta e prima della generazione della copertura. Il registro non deve più restare con tutte le otto fonti nello stato `pending` quando i job eseguono già accessi approvati. Due aspetti sono tenuti separati:

- `access_status = approved` significa che **almeno un** URL dettagliato o indice di quella fonte è abilitato nelle configurazioni operativamente approvate; **non** significa che tutto il sito o tutta la stagione siano accessibili.
- `monitoring_status = index_verified` soltanto se la scansione reale dell'indice della fonte ha restituito `success`; `detail_verified` soltanto se almeno una pagina monitorata ha avuto successo; `configured_unverified` se programmata ma la verifica live non riesce; `not_started` se nessuna scansione è abilitata.
- `automated_index` registra la verifica dell'indice. `autonomous_publication_verified` resta `false` finché non esiste un collaudo effettivo, non viene dedotto dalla sola presenza di adapter o test sintetici.

Per il perimetro attualmente configurato, sette fonti risultano approvate per almeno un accesso, mentre **Rossini Opera Festival** resta `pending/not_started` fino all'onboarding tecnico reale. L'indice delle cinque fonti nazionali è subordinato ai controlli robots.txt e ai report di acquisizione; Torino e OperaLombardia mantengono i propri adapter specifici. Il job aggiorna il registro insieme al JSON di copertura in GitHub, senza SFTP. Sono previsti test di fallimento degli indici, approvazioni mancanti, idempotenza e integrità del perimetro di otto fonti.

**Limite:** questo intervento corregge il monitoraggio e la rendicontazione, non attiva da solo nuovi adapter ROF né la ricerca automatica delle stagioni future. Questi interventi rimangono necessari per raggiungere il requisito unattended pluriennale.


## F2 — cambio di stagione senza configurazioni annuali manuali

Il workflow `Refresh public Opera Atlas catalog` esegue `scripts.rollover_season_indexes` **prima** della ricerca quotidiana di nuove produzioni. Per gli indici stagionali con URL annuali — Teatro alla Scala, La Fenice e Teatro Massimo Palermo — dal 1° giugno dell'ultimo anno della stagione l'adapter propone **soltanto** la successiva pagina ufficiale dello stesso host nel formato noto. La nuova URL non viene abilitata perché “sembra plausibile”: prima il fetch deve superare la normale verifica robots.txt, HTTPS, anti-redirect e limiti di dimensione e timeout, poi l'HTML deve contenere almeno il numero minimo di collegamenti attesi alla stagione e alla categoria lirica. Il calendario vecchio resta invariato per 403, robots non disponibili, indice incompleto o errore di rete.

La nuova URL verificata viene salvata automaticamente in `data/season-index-config.json`, insieme al report `data/season-rollover-health.json`. La successiva acquisizione giornaliera utilizza la configurazione aggiornata nello **stesso workflow**, senza lavoro manuale, SFTP o interventi su `jeckodevsite`. I filtri dei link Scala riconoscono solo la struttura esplicita `/it/stagione/YYYY-YYYY/opera/*.html`, con anni consecutivi; i parametri e i domini diversi continuano a essere rifiutati. Le sedi con indice stabile, Arena e Regio Parma, rimangono sui rispettivi percorsi permanenti.

Le nuove produzioni e opere riconosciute ricevono inoltre la stagione derivata dall'URL ufficiale (Scala, Fenice e Palermo), oppure dall'anno della recita verificata quando l'indice non espone una stagione annuale, **non** il valore fisso 2026/2027. Il cambio riguarda l'indice attivo quando la pagina successiva diventa disponibile e passa i controlli; non elimina stagioni passate dal catalogo, non inferisce cancellazioni e non autorizza URL esterni. Ulteriori miglioramenti potranno mantenere **simultaneamente** due indici stagionali se una stagione si sovrappone alla successiva; questo primo meccanismo garantisce il proseguimento automatico senza dover modificare annualmente la configurazione.

Collaudi: `tests/test_season_rollover.py` verifica percorso dei tre indici futuri, test positivo simulato con sorgenti integre, controlli di mancato accesso e contenuto incompleto e rifiuto di anni incoerenti. Il job continua a segnalare le fonti senza accesso affidabile, incluso il Rossini Opera Festival, invece di aggirare limitazioni di rete.
