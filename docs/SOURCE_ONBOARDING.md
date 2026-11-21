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


## F2 — collaudo in due passaggi sul catalogo che cresce realmente

Il workflow reale ha dimostrato che i test sulle PR possono essere verdi ma la pubblicazione fallire **dopo** un'importazione riuscita. Il run `44824586103` ha generato in memoria **3 nuove produzioni e 29 nuove recite**; il secondo passaggio di test, successivo all'ingest, è però fallito. Le cause corrette nella PR di ripristino sono:
- `opera_atlas.source_registry.read_registry` accetta ora i campi diagnostici generati giornalmente e gli stati di accesso realmente approvati, continuando a far nascere qualunque nuova riga SQLite sempre in `pending` (non autorizza da solo nuovi crawl).
- `scripts.build_verified_catalog.build` unisce le sorgenti ufficiali con i **tutti gli URL auto-approvati già persistiti**, più gli URL nuovi della transazione corrente. Una verifica isolata non può invalidare il resto del catalogo dinamico.
- I test di nuove produzioni utilizzano un'opera canonica non ancora rappresentata nella sede del test e una URL fittizia di fixture (mai richiesta alla rete), anziché assumere per sempre che Macbeth alla Scala non sia mai stato importato.
- I test degli indici confrontano la classificazione delle URL con il registro delle produzioni **al momento del test**, senza numeri rigidi che cambiano quando una recita entra davvero nel catalogo.

**Criterio di chiusura:** devono riuscire sia la suite precedente all'acquisizione sia la suite post-ingest del workflow, seguite da generazione di `public/catalog/v2/manifest.json`, `public/catalog/work-editorial.json`, commit dati e verifica dei nuovi contatori. La PR di ripristino non dichiara pubblicate le 29 recite finché non è completata un'esecuzione live su `main`; mantiene fail-closed e non abbassa i controlli dei dati ufficiali.


## F2 — ingresso automatico delle opere già documentate, senza servizio linguistico a pagamento

La catalogazione autonoma distingue ora due casi di **opera nuova per il catalogo**. Se la scheda breve originale è già in `site/work-synopses.json` e l'intero profilo storico documentato è già in `site/work-history.json`, `scripts.auto_work_research` può riutilizzare quei dati senza chiamare un modello linguistico a pagamento. **Non è sufficiente possedere una sinossi:** Wikidata deve identificare in modo univoco opera e compositore, e la singola pagina ufficiale del teatro deve confermare titolo, compositore, recite e orari prima della promozione. In caso di discordanza non viene pubblicata alcuna nuova opera.

È un percorso generale, non una scorciatoia riservata a un titolo: l'insieme di schede già documentate viene derivato dai file esistenti, validando sinossi e storia. Il primo esempio è **Rigoletto**, già dotato di breve sinossi originale e dati storici con fonte Corago, ma non ancora presente nel registro dei 25 titoli pubblicati. L'identità viene risolta tramite l'API pubblica Wikidata e la conferma dei dati sul sito ufficiale di Parma; non si inventa il compositore dallo slug. La nuova opera riceve ID permanente, profilo storico, sinossi e recite nello stesso passaggio di pubblicazione.

Le richieste giornaliere rispettano gli stessi limiti, ma i titoli con scheda già pronta hanno precedenza nella ricerca autorevole (3 al giorno) e nella lettura delle pagine di dettaglio (10 al giorno). La scansione degli altri titoli mantiene rotazione equa. Quando **non** esiste già una sinossi e un profilo storico verificati, resta invece necessario il percorso di sintesi documentata tramite API linguistica: senza `ATLAS_OPENAI_API_KEY` la nuova scheda non viene inventata, e il sistema ritenta autonomamente.

Collaudi: `tests/test_auto_work_research.py` verifica identità con compositore, riuso di sinossi e fonti storiche, nessuna chiamata a pagamento, idempotenza; `tests/test_candidate_detail_evidence.py` verifica la priorità della nuova opera documentata nel budget giornaliero. L'effettiva pubblicazione live va verificata nel manifest prima di incrementare i contatori.


### F2 — correzione verificata del parser della pagina ufficiale Regio Parma

Il primo run reale successivo alla PR #82 ha **risolto automaticamente identità, compositore, sinossi e storia di Rigoletto**, senza API linguistica, ma non ha ancora pubblicato le recite. Sul sito del Teatro Regio di Parma la barra di navigazione `Spettacolo / Cast / Informazioni` precede il calendario: il parser tagliava l'HTML al primo `Cast`, eliminando quindi tutte le date prima di tentare l'estrazione.

Il parser ora legge il blocco **a partire dalla dicitura ufficiale `Musica <compositore>`** e fino all'inizio delle istruzioni per acquistare i biglietti; richiede esattamente titolo/compositore verificati, un unico anno nelle date della testata e coppie giorno/ora nei cartellini. Esclude ancora `Prova Under30` e `Prova Aperta` e rifiuta date contraddittorie. Nessun dato viene forzato in catalogo se l'HTML cambia.

Nuovo test di regressione `test_live_parma_layout_has_cast_navigation_before_ticket_cards`: riproduce il layout reale e verifica quattro recite ordinarie del Rigoletto, escludendo le due prove. Dopo merge il criterio di chiusura è un workflow live riuscito, con **26 opere e almeno quattro nuove recite** nel manifest soltanto se la fonte continua a confermare i dati. Non incrementare i contatori sulla sola base del test unitario.


### F2 — ogni modifica ai connettori avvia il refresh reale

Il merge della PR #83 (correzione del parser Regio Parma) ha prodotto una suite Python verde, ma **non** il workflow di pubblicazione: il filtro `on.push.paths` di `refresh-catalog.yml` non includeva `opera_atlas/national_detail_parser.py`. Da questo intervento, le modifiche ai parser, al codice di acquisizione e ai test sotto `opera_atlas/**`, `scripts/**` e `tests/**` avviano automaticamente anche il refresh canonico completo su `main`. Il percorso programmato giornaliero e `workflow_dispatch` restano attivi. I JSON generati non sono inclusi in un pattern indiscriminato, così il commit automatico dei dati non innesca un ciclo ricorsivo di workflow.

Test automatico `tests/test_refresh_workflow_paths.py`: controlla la presenza dei trigger globali per connettori e script e la continuità della generazione v2. Per considerare risolto il blocco Rigoletto è obbligatorio verificare anche il run live scatenato da questa PR: il numero di opere deve aumentare soltanto se l'estrazione ufficiale delle recite produce evidenze valide e la pipeline pubblica effettivamente il nuovo manifest.


### F2 — chiusura automatica delle candidate nel medesimo refresh e distribuzione equa delle scansioni

Dal primo import reale di Rigoletto abbiamo verificato che la scansione dell'indice avviene prima della catalogazione: in assenza di un controllo successivo, una nuova produzione **appena pubblicata** può restare segnata `needs_review` fino alla giornata successiva. Il workflow ora esegue `scripts.reconcile_published_candidates` **subito dopo `scripts.auto_catalogue`**, usando il manifesto canonico già scritto e aggiornando nello stesso commit `data/season-index-candidates.json` e `public/catalog/season-index-candidates.json`. L'identificazione è tramite **identico URL ufficiale**, mai somiglianza del titolo. I nuovi stati `already_catalogued` e `excluded_nonopera` non cancellano record o dati di audit; `first_seen`, `last_seen` e gli eventuali stati editoriali non automatici restano immutati. Il report `data/candidate-reconciliation-health.json` distingue le transizioni e i contatori per stato. Il giorno successivo il collector non spreca richieste sulle produzioni già riconciliate.

La scansione di dettaglio mantiene un tetto di **10 URL giornalieri complessivi**, ma distribuisce una prima richiesta, quando possibile, a **ogni fonte nazionale attiva con candidate**. La capacità residua continua a favorire opere con identità canonica certa senza sottrarre la quota per le opere nuove (fino a quattro URL); eventuali schede già documentate ricevono un piccolo vantaggio senza impedire indefinitamente l'esplorazione di altri titoli. L'avanzamento giornaliero dei puntatori evita cicli fissi che lascino una fonte senza scansioni.

Test: `test_same_run_candidate_reconciliation.py` verifica promozione allo stato catalogato, idempotenza, storia preservata, esclusioni e stati non automatici; `test_candidate_detail_evidence.py` simula 75 URL su cinque fonti e 80 giornate con budget invariato, verificando che **tutte** le candidate siano progressivamente selezionate. La nuova riconciliazione resta distinta dalla pubblicazione stessa: un URL non viene segnato `already_catalogued` finché la relativa produzione non è scritta nel manifesto validato. Nessun intervento SFTP o modifica a `jeckodevsite`.


### F2 — protezione del comando di commit del refresh

Il primo run reale dopo la PR #86 ha superato **291 test**, comprese la generazione dei feed e la seconda suite post-acquisizione, ma è fallito all'ultimo passo perché il comando shell di staging conteneva accidentalmente `git add ... git add ...`. Git ha quindi interpretato `git` come path inesistente e non ha potuto pubblicare i JSON generati.

Il comando è stato corretto in un'unica invocazione `git add` che include anche `data/candidate-reconciliation-health.json`. Il nuovo test `test_catalog_git_staging_has_no_embedded_duplicate_command` verifica la sintassi di tutte le righe di staging, la presenza del report di riconciliazione, il controllo del diff staged e il push su `main`. La riuscita dei test non equivale ancora a pubblicazione: il job di refresh successivo a questa PR deve concludersi con commit dei dati e manifest leggibile.


### F2 — calendari multi-mese e annullamenti espliciti sulle fonti ufficiali

I calendari delle produzioni operistiche possono attraversare più mesi. La pagina ufficiale **Ernani** del Teatro Massimo riporta un riepilogo documentato `31 ottobre, 2, 3, 4, 5, 6, 7 novembre 2027` e cartellini di data/ora separati: il parser precedente accettava solo un mese, scartando erroneamente tutte le recite. Il nuovo parser ricostruisce l'elenco delle date con i rispettivi mesi **senza interpolazioni** e richiede che ogni giorno del riepilogo abbia il proprio cartellino con orario. Rifiuta giorni mancanti, duplicati incompatibili e intervalli dicembre/gennaio che non dichiarino autonomamente entrambi gli anni. Il controllo di opera e compositore ufficiali resta obbligatorio prima della promozione.

La Fenice pubblica occasionalmente comunicazioni di **annullamento di una singola recita**, anche se il resto della produzione rimane in programma: per Fedora è stato comunicato l'annullamento della prima del **13 novembre 2026**. Il parser ora analizza il testo ufficiale alla ricerca di annullamenti espliciti e relative date complete; **non** include quelle date nelle recite attive da pubblicare. Se un annullamento è citato senza una data identificabile in modo univoco, non pubblica la pagina, mantenendo il last-known-good invece di creare una recita potenzialmente inesistente.

Questa logica protegge **le nuove importazioni**: la gestione delle cancellazioni di recite già pubblicate rimane un controllo distinto da sviluppare, con conservazione dell'identità e aggiornamento dello stato anziché cancellazione indiscriminata. I test riproducono il calendario ufficiale di Ernani con ottobre/novembre, verificano l'anno e ogni ora, un calendario incompleto, il caso Fedora con una sola recita annullata e un avviso ambiguo che deve bloccare la pubblicazione. Non sono inventate date, orari o eventi.


### F2 — pubblicazione robusta quando `main` cambia durante la scansione

Il run reale `44829536477` ha completato scansioni, suite e generazione JSON, ma il push è stato respinto da GitHub (`non-fast-forward`) perché una modifica è stata unita a `main` durante l'esecuzione. L'acquisizione corretta non deve sovrascrivere modifiche recenti né richiedere un intervento manuale per ricostruire il catalogo.

La fase finale usa ora `scripts.safe_push_catalog` con **massimo tre tentativi**, sempre senza `--force`. Se il remote segnala che il commit è già arrivato, considera riuscita la pubblicazione; altrimenti confronta la nuova `main` con il commit base della scansione. Se sono cambiati **soltanto documentazione o asset non canonici**, può applicare un rebase e ripetere la suite e la verifica dei JSON generati prima di un nuovo push. Se sono cambiati **codice, parser, workflow, test, identità, schede o dati canonici**, non applica l'acquisizione potenzialmente obsoleta: registra la pubblicazione come `deferred` e lascia al refresh già innescato dalla modifica più recente o alla scansione programmata il compito di rigenerare i dati. Nessuna forzatura o sovrascrittura silenziosa.

I test `tests/test_safe_push_catalog.py` simulano repository Git locali separati, una modifica concorrente alla documentazione con rebase e commit dei dati riuscito, e una modifica concorrente del parser che **deve impedire** la scrittura del catalogo obsoleto. Sono inoltre verificati i prefissi sensibili e il limite dei tentativi. Il risultato `deferred` non deve essere descritto agli utenti come nuovi dati pubblicati: la conferma si ricava sempre dal manifest e dal commit effettivo.


### F2 — consolidamento della coda completa senza limite arbitrario di dieci pagine

Il precedente `MAX_PAGES=10` **non era un budget economico**, ma una precauzione contro un numero eccessivo di richieste ai siti ufficiali. Con 54 candidate residue, tuttavia, impediva di analizzarle tutte nello stesso ciclo anche quando l'accesso era approvato. Il collector ora legge **fino a 60 pagine di produzione per esecuzione**, con limite aggiuntivo di **24 pagine per singola fonte**. La coda osservata al 20 novembre 2026 (Scala 10, Arena 2, Fenice 7, Parma 12, Palermo 23) può quindi essere interamente affrontata in **un** refresh, salvo nuovi ingressi o errori di accesso. Il workflow ha un timeout adeguato di 75 minuti.

Non è un crawler indiscriminato: la scansione continua a limitarsi alle pagine già individuate in indici ufficiali esplicitamente autorizzati, con verifica fresca di `robots.txt`, URL HTTPS esatto, limiti di dimensione e timeout per ogni fetch. Tra una pagina e la successiva il job **attende 0,75 secondi** per moderare il traffico. Se una fonte impedisce l'accesso, cambia struttura o non presenta dati sufficientemente verificabili, non vengono inventate opera, compositore, sede o recite e il JSON canonico resta valido. Il limite per fonte evita che una stagione molto ampia monopolizzi le richieste; per code superiori, resta la rotazione giornaliera equa e senza starvation.

I test simulano esplicitamente le **54 candidate delle cinque fonti**, verificano che siano tutte selezionabili senza duplicati e che ogni singola fonte resti sotto il proprio tetto. Verificano anche il ritardo di cortesia senza rallentare i test unitari (fetch e pausa iniettati). L'aumento della **copertura di lettura** non costituisce automaticamente un aumento delle **recite pubblicate**: il passo successivo è analizzare gli errori dei parser e l'arricchimento delle opere sconosciute sui risultati reali del job. Il refresh deve essere seguito fino alla pubblicazione del manifest e delle metriche post-acquisizione; nessun SFTP.


### F2 — consolidamento delle produzioni realmente distinte e diagnosi per ciascuna candidata

La prima scansione completa del 20 novembre 2026 ha **tentato tutte le 54 pagine**, ma il report ha restituito `ValueError` generico per ciascuna e nessun nuovo dato; il limite di dieci pagine non era più il blocco. Il collector registra ora, per ogni pagina leggibile ma non promuovibile, **le tre cause di mancata estrazione**: identificazione di un'opera canonica, identificazione di una nuova opera arricchita con fonti autorevoli e assenza di dati evento strutturati. Le diagnostiche derivano dai controlli del parser, sono abbreviate e non archiviano HTML, descrizioni originali, dati personali o credenziali. Rendono misurabile se il blocco è nell'identità musicale, nell'estrazione delle date o nella struttura della pagina. Questo permette di perfezionare i parser senza interventi editoriali sul catalogo né riconciliazioni retroattive.

È stata inoltre individuata una lacuna effettiva all'Arena di Verona: **Aida** viene proposta in **due allestimenti diversi** nella stessa stagione, quello del 1913 diretto da Gianfranco de Bosio (già catalogato) e **Aida ed. Stefano Poda** sul sito ufficiale. Prima il secondo URL non era riconosciuto dall'identità canonica `Aida` e, anche se le date fossero state estratte, il sistema avrebbe rifiutato la seconda produzione per collisione della pagina pubblica. L'adapter ora ammette il suffisso ufficiale `aida-ed-...` **soltanto** quando l'opera e il compositore già canonici sono univoci e la pagina stessa li conferma. Il motore mantiene URL ufficiale e ID propri di ciascuna messa in scena, senza sovrascrivere recite di un allestimento con quelle dell'altro.

La pubblicazione v2 mantiene invariato il percorso del primo allestimento (`/verona/arena-di-verona/aida/`) e attribuisce all'altro un **terzo segmento distinto** (`/verona/arena-di-verona/aida-ed-stefano-poda/`), compatibile con il frontend statico esistente e quindi senza nuovo deploy SFTP. I nuovi slug di edizione devono essere univoci, normalizzati e prefissati dall'opera; ogni altro conflitto resta bloccato. Il test end-to-end verifica che il secondo allestimento riceva un nuovo ID permanente, recite con fonte propria, rotta distinta, e che una seconda scansione non crei duplicazioni. La sola presenza del titolo nell'URL non è una prova di composer o date: i dati nuovi saranno pubblicati **soltanto dopo** il job live con la pagina ufficiale e i controlli canonici superati.


### F2 — test che resta valido quando il catalogo cresce (allestimenti di Aida)

Il primo run effettivo della scansione completa dopo PR #95 ha individuato **1 produzione e 5 recite** di `Aida ed. Stefano Poda`, poi ha superato i controlli del grafo. La suite post-ingest ha però fallito perché il nuovo test sull'omonimia degli allestimenti usava proprio l'URL reale dell'Aida di Stefano Poda e pretendeva la nascita della messa in scena **ancora una volta**, dopo che l'automazione l'aveva già creata. La pubblicazione non è quindi avvenuta: i dati sono rimasti soltanto nel workspace del job fallito.

Il test è ora reso indipendente dal catalogo vivo: la verifica dell'HTML dell'allestimento reale resta sull'URL ufficiale; la simulazione di creazione di una **ulteriore** messa in scena usa esclusivamente un URL di fixture, nello stesso dominio approvato, che non viene mai richiesto alla rete. Così il test resta valido prima **e dopo** l'importazione della produzione reale, senza disattivare i controlli di unicità, ID, provenienza o date. Il criterio di chiusura è il nuovo refresh riuscito su `main` e l'effettivo incremento del manifest, non il solo test verde.


### F2 — recupero delle recite di Carmen al Teatro Massimo

Il report dettagliato post-scansione di tutte le 54 candidate ha mostrato che `Carmen`, già riconosciuta nel registro canonico con **Georges Bizet**, non veniva acquisita perché il parser di Palermo segnalava `Palermo cards incomplete versus dated summary`, nonostante la fonte ufficiale esponga otto recite con orari tra **24 novembre e 2 dicembre 2027**. La causa ricostruita è la presenza possibile della voce di navigazione `Lo spettacolo` prima dei cartellini; il vecchio delimitatore prendeva la prima occorrenza e scartava il calendario.

Ora l'elenco dei cartellini viene estratto dal testo **precedente al riepilogo ufficiale con date e anno già verificati**, invece di affidarsi alla prima etichetta `Lo spettacolo`. Il confronto rimane esatto: la totalità delle date nel riepilogo deve avere un orario individuale, con mese e anno corrispondenti e senza conflitti. La fixture di regressione simula l'ancora preliminare e le otto recite `24, 25, 26, 27, 28, 30 novembre; 1, 2 dicembre 2027`; conferma la distribuzione degli orari pubblicati sul sito ufficiale.

Come per ogni adapter, non si pubblicano numeri presunti: il successivo refresh deve provare che la sorgente reale conferma i dati e che la nuova produzione compare effettivamente nei manifest JSON. Nessun SFTP, nessun cambio alla logica di validazione canonica.


### F2 — classificazione integrale delle 52 candidate (concerti, balletto e opere)

A seguito della scansione completa del 20 novembre 2026 (26 opere, 57 produzioni, 278 rappresentazioni), la coda conteneva **52** URL ancora classificati `needs_review`. Questo numero **non corrisponde a 52 opere liriche**: gli indici ufficiali, specie quello del Teatro Massimo dedicato a «opere e balletti», includono concerti, recital, balletto, proiezioni con orchestra e iniziative collaterali. L'esecuzione precedente tentava ogni giorno anche queste pagine e riportava erroneamente «nessuna identità operistica».

Sono state introdotte **27 esclusioni esatte**, tutte riferite alla chiave della singola fonte e allo slug della pagina ufficiale, così suddivise: 19 al Teatro Massimo, 6 al Teatro Regio di Parma, 1 balletto Arena e 1 anteprima Under30 Scala. Fra gli esempi verificati: `Nuovo cinema Paradiso` (film in concerto), `Biancaneve` e `Lo schiaccianoci` (balletti), `Romeo e Giulietta` Arena (balletto), concerti con titoli Beethoven/Ravel, recital, `Verdi Off Los Angeles` (evento di gala), `Regio in Tour` (estratti di tre opere) e `Otello anteprima Under30` (anteprima distinta dalle recite ordinarie). Nessun filtro per parole generiche come *Beethoven*, *Otello*, *Romeo* o *gala* viene applicato a titoli futuri. Tutti i record restano nello storico con stato `excluded_nonopera` e possono essere riclassificati se la fonte ufficiale modifica il contenuto.

Il resto della coda deve continuare ad alimentare la scoperta delle vere opere liriche: titoli come `Anna Bolena`, `I puritani`, `Boris Godunov`, `La clemenza di Tito`, `Adriana Lecouvreur`, `Falstaff` ed `Ernani` rimangono `needs_review` fino a quando opera/compositore, sinossi originale, storia e date/ore ufficiali risultino comprovati. È stata deliberatamente **mantenuta** come candidata `Piccolo Orso e la montagna di ghiaccio`: il Teatro Regio indica musica originale di Giovanni Sollima e libretto di Giancarlo De Cataldo, per cui non sarebbe prudente escluderla come semplice spettacolo infantile.

L'aggiornamento è automatico: `discover_season_indexes` e `reconcile_published_candidates` ricalcolano le classificazioni nel normale refresh, senza cancellare o alterare gli ID. I test verificano esclusioni puntuali, assenza di falsi positivi sulle opere autentiche e conservazione delle sorgenti già canoniche. Una candidata che manca di elementi necessari **non viene trasformata in opera inventata**: rimane tracciata finché i dati ufficiali e le autorità bibliografiche sono sufficienti.


### F2 — secondo lotto: undici schede d'opera pronte per l'ingresso automatico

La classificazione dei 52 URL ha separato i non-opera dal repertorio lirico ancora non censito. Per evitare attese o l'acquisto obbligatorio di un servizio di scrittura, sono ora disponibili in `site/work-synopses.json` **undici nuove sinossi italiane originali, brevissime** e in `site/work-history.json` le rispettive schede storiche complete con fonti bibliografiche o archivistiche verificabili: **Anna Bolena, I puritani, Il barbiere di Siviglia, Ernani, Falstaff, La clemenza di Tito, Adriana Lecouvreur, Nixon in China, Hänsel und Gretel, Il pipistrello e Die Zauberflöte**. Non sono state duplicate pagine di Wikipedia, libretti o testi dei teatri. Le descrizioni sono sintetiche e finalizzate esclusivamente a presentare gli spettacoli in programma.

Queste schede **non vengono pubblicate anticipatamente** come opere canoniche. Il motore esistente deve ancora trovare una produzione ufficiale, confrontare l'identità della singola opera e il compositore con Wikidata, confermare titolo, sede e date/orari dal teatro e generare identificativi stabili; senza questi riscontri la scheda resta materiale preparatorio. La prima ricerca autorevole per le schede già provviste di trama e storia è stata aumentata a **16 candidate per run**, usando l'API pubblica Wikidata e **senza consumo del modello linguistico**. I titoli senza alcuna documentazione continuano invece nel budget di tre tentativi giornalieri (il modello resta opzionale e non è attivato senza la relativa chiave API).

La separazione fra preparazione editoriale e pubblicazione canonica evita inventari di opere prive di uno spettacolo disponibile, mentre rende possibile l'ingresso immediato quando il teatro fornisce evidenze verificabili. Test automatici convalidano l'intero lotto e il batch gratuito di identificazione. Anche qui un test verde non garantisce nuove opere o recite: verificare `auto-work-intelligence-health.json`, `candidate-detail-health.json` e il manifest v2 dopo il merge.


### F2 — terzo lotto: ulteriori dieci opere documentate e collaudi compatibili con l'auto-pubblicazione

Il primo refresh dopo la preparazione di undici schede d'opera ha **identificato 5 nuove opere e 26 recite con prove di fonte**, ma ha fermato correttamente la pubblicazione prima del commit: due test continuavano a usare `Anna Bolena` come opera necessariamente assente, mentre il motore l'aveva già riconosciuta. Il test di auto-promozione usa ora una **sola opera fittizia di fixture, mai richiesta ad alcun teatro**, verificando creazione integrata, provenienza, sinossi, storia e idempotenza anche quando l'autentica Anna Bolena è entrata nel catalogo. Non vengono allentati i controlli sulle fonti.

Sono state inoltre predisposte **10 schede brevi originali e dieci profili di prima rappresentazione** con fonti archivistiche, editoriali e musicali in `site/work-synopses.json` e `site/work-history.json`: Don Quichotte, The Rake's Progress, Leonora (Paër), Les pêcheurs de perles, Boris Godunov, Nozze istriane, Partenope, Al cavallino bianco, Norma e L'arca di Noè. Restano dati editoriali preparatori, non titoli pubblici senza recite confermate. Non è stato assunto un esito dell'opera storico sulla sola base del nome del file. Sono conservate le fonti e le attribuzioni storiche; in caso di indisponibilità o identità ambigua, il processo ritenta automaticamente senza inventare la rappresentazione.

I titoli ufficiali di Fenice contengono talvolta nomi di direzione/allestimento nello slug, come `normatebar` per **Norma** e `ilbarbieredisivigliapercacciolo` per **Il barbiere di Siviglia**. L'identificazione della ricerca usa **soltanto due alias esatti** e richiede host HTTPS approvato, chiave di fonte riconosciuta, assenza di parametri e struttura ufficiale. La pagina ufficiale e Wikidata devono comunque confermare la coppia opera/compositore, e i cartellini delle recite rimangono validati separatamente.

I test di regressione verificano la disponibilità dei dieci profili completi, l'associazione degli alias esatti, l'esclusione di host non autorizzati e, dopo una importazione reale, la stabilità del test che prima faceva fallire il job. L'obiettivo operativo è ottenere un workflow completo verde e un manifest aumentato **solo** delle nuove opere e delle recite ufficialmente riconosciute. Le candidate incerte o gli spettacoli ibridi non vengono promossi forzatamente.


### F2 — Piccolo Orso è un'opera originale: fonte primaria della prima mondiale

Fra le 25 candidate operistiche risultava `Piccolo Orso e la montagna di ghiaccio` di **Giovanni Sollima**, libretto di **Giancarlo De Cataldo**. La fonte ufficiale di **La Fenice** (<https://www.teatrolafenice.it/event/evento-25-26-piccolo-orso-e-la-montagna-di-ghiaccio/>) conferma esplicitamente la **prima rappresentazione assoluta al Teatro Malibran, Venezia, sabato 31 gennaio 2026**. La successiva pagina ufficiale **Regio Parma** (<https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/>) conferma lo stesso work e il programma dicembre 2026. La scheda originale sintetica e il profilo storico sono ora pronti nei due archivi editoriali; non sono deduzioni da un nome di URL né un testo copiato.

**Limite strutturale rilevato prima di pubblicare:** il Teatro Regio indica **quattro recite in due sole date** (4 dicembre 2026 ore 09:00 e 11:00; 5 dicembre 2026 ore 15:00 e 18:00). Il registro canonico attuale usa una chiave `<staging>|<date>` e consente quindi **solo una recita al giorno per allestimento**. Non va corretta inventando due messe in scena o scegliendo arbitrariamente uno degli orari. La pubblicazione di Piccolo Orso richiede prima un'evoluzione specifica dell'identità delle repliche per coppia data/orario, mantenendo invariati gli ID storici; in assenza, i controlli restano fail-closed. Preparare la scheda non equivale a pubblicare le quattro repliche.


## IMG-01 — locandina/immagine di produzione associata automaticamente alle nuove opere

Un difetto funzionale era emerso con i work ID `oa-w-000027`–`oa-w-000033`: gli ID, i titoli, le recite, le sinossi e gli storici erano aggiornati automaticamente, ma **`site/image-client.js` aveva una tabella `WORKS` statica** con le sole 25 copertine precedenti. La nuova opera riceveva soltanto l'illustrazione astratta creata dal frontend.

Ora `scripts.publish_work_posters` usa i dati **canonici** già validati, cerca la pagina ufficiale di ciascuna produzione soltanto sul dominio approvato, dopo verifica `robots.txt` e dei limiti HTTP, ed esamina **solo** le dichiarazioni dell'immagine principale nei metadati `og:image`/`twitter:image`. Non salva HTML né scarica, copia o ridistribuisce il file di immagine originale. Accetta URL HTTPS dell'host ufficiale o di CDN media strettamente ammessi, rifiuta loghi, tracker, SVG di navigazione, URL con credenziali e banner dichiaratamente orizzontali. Conserva URL della pagina ufficiale, credito e descrizione dell'immagine, distinguendo **immagine promozionale dell'attuale produzione** da un manifesto d'archivio. Non presenta mai un'immagine di un altro teatro o lavoro come la locandina della produzione.

Il risultato è pubblicato automaticamente in `public/catalog/work-posters.json`, separato dal catalogo delle recite. **Ogni opera canonica ha una voce**, e quelle con `kind=official_production_image` forniscono `image_url`, `source_url`, attribuzione e testo alternativo. Dove la fonte non pubblica metadati affidabili, resta `kind=original_editorial_cover`, che il frontend rappresenta con la propria copertina originale, senza inventare o attribuire falsamente un manifesto teatrale. L'acquisizione delle immagini non blocca le recite già verificate. Si leggono massimo 18 pagine di fonte approvata per refresh e si riprova dopo sette giorni una ricerca senza esito, così la manutenzione resta leggera e la nuova opera verrà recuperata anche in caso di temporanea indisponibilità.

Il frontend viene aggiornato **una sola volta**: `site/image-client.js`, `site/app.js`, `site/directory.js` e `site/detail.js` caricano via HTTP il nuovo JSON pubblicato su GitHub **prima** del rendering dei manifesti in homepage, directory opere e pagina di dettaglio. Qualunque opera futura con un'immagine verificabile è quindi associata alla propria immagine **senza dover ripubblicare il frontend via FTPS**. Se il JSON, il CDN o l'immagine non sono disponibili, è comunque visibile la copertina editoriale originale, mai un riquadro rotto. L'hosting statico rimane nel repo `opera-atlas` e il catalogo si aggiorna senza alcuna modifica a `jeckodevsite`.

Collaudi obbligatori: parser dei metadati ufficiali e URL sicuri, rifiuto di loghi/banners/tracker, manifest completo per tutte le opere canoniche, riuso delle immagini reperite per evitare richieste inutili, recupero settimanale dei soli mancanti, caricamento del JSON nel frontend su tutte e tre le viste e suite Python completa. Il controllo reale deve verificare `data/work-poster-health.json`, `public/catalog/work-posters.json`, il feed delle opere e l'esito dell'eventuale workflow di deploy frontend. **Non dichiarare che ogni opera possiede una locandina autentica** quando l'immagine ufficiale non viene resa disponibile.


### IMG-01 — qualità delle locandine: niente immagini errate, sette riferimenti archivistici

La **prima esecuzione reale** del raccoglitore immagini ha creato `public/catalog/work-posters.json` con 35 opere e ha associato sei immagini mediante `og:image`. Il controllo dei risultati ha però mostrato che **cinque di quelle sei erano immagini di persone, direttori o concerti diversi**: per esempio la pagina `Anna Bolena` rimandava a un file `ciampa-2-scaled.jpg`, `I puritani` a `2025-concerto-fabio-luisi...` e `Nixon in China` a `kent-nagano...beethoven.jpg`. Non basta quindi l'origine ufficiale del metadato: l'immagine deve essere **pertinente all'opera**. L'adapter ora confronta tutti i termini significativi del titolo dell'opera con il **nome del file dell'immagine**; rifiuta fotografie ufficiali generiche o afferenti ad altri titoli, e risana automaticamente i record già selezionati erroneamente. Il controllo di integrità ripete questo confronto dopo la pubblicazione.

Per garantire copertine concrete e documentate anche quando i siti ufficiali non pubblicano locandine utilizzabili, `data/archival-work-images.json` contiene **sette immagini storiche verificate su Wikimedia Commons** per le sette opere aggiunte nel primo lotto: *Al cavallino bianco, Il pipistrello, Partenope, Don Quichotte, Norma, Nozze istriane e Adriana Lecouvreur*. Sono state scelte locandine storiche originali dove disponibili (Don Quichotte, Norma), copertine/frontespizi storici (Il pipistrello, Partenope, Nozze istriane) e fotografie storiche documentate (Al cavallino bianco, Adriana Lecouvreur); nessuna fotografia o libretto è falsamente presentato come **manifesto dell'allestimento attualmente in programma**. Il record conserva la pagina Commons, licenza e credito; una delle immagini (Al cavallino bianco) è CC BY 4.0 con attribuzione specifica all'archivio Baden-Württemberg e al fotografo; le altre sono segnate pubblico dominio sulla fonte indicata. `site/credits.html` è stato aggiornato contestualmente con tutti e sette i collegamenti e le condizioni di utilizzo.

Il feed pubblicato usa la priorità **immagine della produzione ufficiale che supera l'identità → immagine storica archivistica con fonte e licenza → copertina editoriale originale**. Tutte le tre viste supportano le prime due categorie, e la pagina dell'opera presenta un piccolo collegamento visibile alla fonte sotto l'immagine. Il motore non ricopia fotografie e non immette immagini senza fonti. Le nuove opere future continueranno ad essere ricercate automaticamente nelle pagine ufficiali; il fondo archivistico è una garanzia specifica per il primo lotto appena censito. Se la fonte ufficiale fornisce finalmente una vera locandina inequivocabilmente pertinente, questa sostituisce automaticamente l'immagine storica, sempre mantenendo provenienza e attributi.


### IMG-02 — immagini indicizzate tramite ID dell'opera, non soltanto titolo

Durante la verifica della pubblicazione delle immagini è emersa una collisione **reale** del catalogo: 36 opere con soltanto 35 slug perché *La bohème* di **Giacomo Puccini** e *La bohème* di **Ruggero Leoncavallo** sono opere autonome e mantengono ID permanenti differenti. Il primo schema delle immagini usava soltanto il titolo normalizzato come chiave; questo poteva produrre un'associazione errata o una voce omessa, perfino con un URL immagine valido e una licenza corretta.

Il nuovo `public/catalog/work-posters.json` ha **schema_version 2** e contiene **esattamente una voce per ciascun `work_id`** del registro canonico. Una nuova opera riceve subito una voce propria; ogni `image_url`, credito e riferimento documentale viene legato alla stessa identità permanente, non al titolo che può essere ambiguo. `data/work-poster-evidence.json` viene migrato automaticamente da chiavi slug (schema 1) alle nuove chiavi ID (schema 2) **solo** quando il record espone già un `work_id` coerente o lo slug identifica un solo lavoro. Non assegna la vecchia copertina per somiglianza a due opere diverse. Anche l'archivio di immagini storiche per slug si applica soltanto in assenza di omonimia; negli altri casi mantiene la copertina editoriale individuale finché non viene reperita un'immagine autorevole.

Il frontend, in homepage, directory e pagina opera, passa ora il `work_id` e consulta prima tale identificativo. Rimane una compatibilità di lettura con il vecchio schema 1 durante il passaggio di versione, ma non si effettua fallback per titolo sui feed v2. Il vecchio fallback statico della copertina della *Bohème* di Puccini è disabilitato esplicitamente quando l'opera è quella di Leoncavallo.

I test coprono la migrazione, la collisione reale fra le due opere, il numero esatto di voci nel manifest, il rifiuto di un `work_id` differente dalla chiave, e il caricamento frontend per ID. Il criterio di successo è che la nuova pubblicazione conti **36 opere e 36 voci immagine**, non 35. Il problema è indipendente dall'autenticazione FTPS, che resta da risolvere prima di poter dichiarare aggiornato il sito live.

## Copertura immagini opere e recupero automatico — 21/11/2026

- **Identità delle opere:** le immagini storiche verificate possono essere registrate tramite `works_by_id` (ID permanente e compositore obbligatori). La precedente banca per slug resta utilizzabile soltanto quando lo slug è univoco, per evitare scambi fra `La bohème` di Puccini e quella di Leoncavallo.
- **Fonti archivistiche iniziali:** frontespizio del libretto del 1830 di *Anna Bolena* di Donizetti (Wikimedia Commons, pubblico dominio) e manifesto del 1897 della *Bohème* di Leoncavallo (Wikimedia Commons; pagina di origine da consultare per le condizioni d'uso territoriali). Sono documenti storici, **non** manifesti della produzione attualmente in calendario.
- **Ricerca ufficiale:** il generatore considera sia `og:image` sia `twitter:image` e seleziona soltanto l'immagine riconducibile al titolo, anziché bloccarsi su una prima immagine estranea. Le regole contro immagini di concerti, loghi e banner rimangono.
- **Riprova automatica:** le precedenti scadenze con policy obsoleta sono rivalutate alla prima esecuzione del nuovo generatore. I risultati senza immagine idonea si ricontrollano ogni due giorni; accessi negati o bloccati ogni sette giorni, nel limite di 18 pagine per esecuzione. Il refresh giornaliero prosegue e non richiede ulteriori deploy dell'interfaccia.
- **Misurazione:** `data/work-poster-health.json` distingue immagini ufficiali, immagini d'archivio e copertine editoriali. Una copertina editoriale non deve essere presentata come manifesto autentico.

## Ricognizione integrale delle copertine — 21/11/2026

L'inventario è stato verificato su **tutte le 36 identità canoniche** con distinzione rigorosa per `work_id` e compositore. Delle 25 copertine editoriali rimaste dopo l'intervento precedente, 23 sono sostituite con documenti storici attinenti alla **specifica opera** (manifesti, copertine di libretti o foto storiche di interpreti nel ruolo). Il catalogo pubblicato comprende quindi 32 immagini archivistiche, 2 immagini di produzione ufficiali e 2 copertine editoriali originali. Le immagini storiche **non** sono rappresentazioni della stagione in corso.

Le due eccezioni sono opere contemporanee: *Death in Venice* di Britten e *Nixon in China* di Adams. Non si è reperito un manifesto/documento fotografico dell'opera con prova sufficiente della riutilizzabilità; sono volutamente mantenute due copertine editoriali chiaramente etichettate, anziché associare una fotografia del film tratto da Mann o un'immagine del viaggio presidenziale del 1972 e presentarla come manifesto dell'opera. Il recupero automatico delle immagini ufficiali di produzione resta attivo sulle relative fonti.

Le opere omonime *La bohème* di Puccini e Leoncavallo conservano immagini distinte per compositore. Per le fonti con licenza CC BY-SA le schede di provenienza contengono il credito nominativo e il link alla licenza. Nessuna risorsa esterna viene copiata o ripubblicata: vengono forniti URL di Wikimedia Commons e attribuzioni, con ripiego a copertina originale se la risorsa non risponde.

La suite di regressione controlla tutte le 36 identità, la tipologia e la provenienza di ogni copertina, il contenuto della banca storica e la non condivisione errata delle opere omonime. Le immagini si aggiornano tramite `public/catalog/work-posters.json`, senza nuovo caricamento SFTP.

## Qualità visiva delle copertine e selezione repertorio homepage — 21/11/2026

- **Un ballo in maschera** (`oa-w-000012`): sostituita la locandina del teatro di Erevan del 1959, con scritte in altra lingua, con il frontespizio Ricordi del 1860 dell'opera di Verdi, in pubblico dominio e con titolo italiano. Fonte: https://commons.wikimedia.org/wiki/File:Giuseppe_Verdi,_Un_Ballo_in_maschera,_Vocal_score_frontispiece_-_restoration.jpg.
- **Jenůfa** (`oa-w-000020`): il manifesto storico della prima del 1904, benché autentico, non era abbastanza leggibile come copertina per l'utente. La scheda utilizza `cover-jenufa.svg`, copertina editoriale originale con titolo «JENŮFA» ben visibile. Non è pubblicizzata come locandina storica o attuale.
- **Nixon in China** (`oa-w-000034`): usa la nuova `cover-nixon-in-china.svg` (originale, auto-ospitata), con titolo e compositore leggibili; evita link esterni a fotografie promozionali senza riutilizzo verificato. Entrambe le copertine editoriali sono incluse nella allowlist SFTP e sono dotate di fallback SVG generato dal client.
- Il JSON `public/catalog/work-posters.json` contiene le provenienze e per le due opere originali il nome del file `cover_file`; il generatore rigenera queste scelte e non ripristina l'immagine storica di Jenůfa.
- Nella striscia **Esplora le opere** della homepage la selezione editoriale è fissa, per **ID permanente** e nell'ordine: **Rigoletto, Aida, Don Giovanni, Norma, Tosca, Lucia di Lammermoor**. Non dipende dall'ordine alfabetico né dalle nuove acquisizioni.
- **Collaudi**: controllare le tre copertine nel catalogo, le relative pagine opera e le sei schede della homepage nell'ordine richiesto; verificare che ciascuna porti alla scheda corretta e che il frontend sia stato pubblicato con il workflow SFTP di `opera-atlas`. La pubblicazione dei soli JSON non trasferisce le due nuove SVG sull'hosting OVH.

## Connettore indice Carlo Felice Genova — 21/11/2026

Il registro degli indici include `https://www.carlofelice.it/rassegna-stagione-opera-danza-musical-2026-27/`, con acquisizione condizionata a controllo `robots.txt` fresco e fail-closed. I collegamenti candidati sono esclusivamente URL HTTPS dello stesso host sotto `/spettacolo/`. La soglia minima di completezza è sette. Sono esclusi esplicitamente gli spettacoli di danza e musical identificati nell’indice ufficiale: Lo schiaccianoci, Giselle, Il lago dei cigni, Deledda, Sergio Bernal Dance Company e The Phantom of the Opera. Ogni nuovo link non ancora verificato resta candidato; non si inventano date, orari o compositori e la scheda opera richiede identità canonica univoca anche in caso di omonimie.

Collaudo: suite `python -m unittest discover -s tests -v`; esecuzione del job `Refresh public Opera Atlas catalog` con verifica dello stato robots e delle candidate in `data/season-index-candidates.json`; confermare assenza dei sei titoli non operistici e nessuna pubblicazione di recite senza prova della pagina di dettaglio. L’acquisizione dei dati del catalogo rimane indipendente dal deploy SFTP.

## Connettori indici Bergamo e Brescia — 21/11/2026

Due nuovi indici ufficiali per il job `discover_season_indexes`: Donizetti Opera (`https://www.donizettiopera.org/it/opere-2026/`, sezione “Opere 2026”, almeno tre link evento) e Teatro Grande Brescia (`https://teatrogrande.it/it`, sezione “Opera e Balletto”, almeno due link stagione). Entrambi soggetti a fresh robots.txt check prima di ogni richiesta e policy fail-closed. Il parser limita i percorsi e gli host, rifiuta link di menu/footer, concerti, brunch e link esterni, e non inventa date, ore o compositori. Il dittico Cavalleria/Pagliacci è un solo link di produzione fino a classificazione delle due opere.

Verifica post-merge: `python -m unittest discover -s tests -v`, esiti in `data/season-index-health.json`, link in `data/season-index-candidates.json`. Una scansione live riuscita non dimostra copertura completa di stagione o delle singole recite: servono parser di dettaglio specifici per pubblicare date e orari con evidenza ufficiale; nessun SFTP richiesto per il feed JSON.

## Adapter dettaglio Genova/Bergamo — 21/11/2026

La fase `collect_candidate_details` riconosce ora la struttura ufficiale delle schede `/spettacolo/<slug>/` del Teatro Carlo Felice e `/it/evento/<slug>/` del Donizetti Opera. Non deriviamo date dagli intervalli pubblicitari di stagione. Per Genova si leggono esclusivamente righe giornaliere con data completa `gg/mm/aaaa` e ora esplicita nella sezione di biglietteria precedente a “Dove”; per Bergamo solo le righe `gg mese aaaa | hh:mm` nella sezione “Info” prima di “Luogo”. In entrambi i casi è obbligatoria la corrispondenza del titolo nella prima intestazione H1 e del compositore nel testo della pagina ufficiale. Annullamenti, rinvii, doppie recite nello stesso giorno non distinguibili o assenza di un orario fanno fallire la prova invece di generare dati presunti.

La sede è presa dal dettaglio: `Teatro Donizetti` e `Teatro Sociale` restano distinti. Le righe complete e conformi producono *evidenze candidate*, ma **non** una promozione pubblica indiscriminata: per quest'ultima servono opera/compositore canonici, riconciliazione con l'identità della sede e intera validazione della pipeline. Il Teatro Carlo Felice non è ancora censito come sede canonica nel registro degli ID; non dichiararne l'autopubblicazione prima di completare tale onboarding. Per il Donizetti Opera, le opere ancora assenti dal registro devono prima ottenere un'identità verificata. Le scansioni restano subordinante al controllo `robots.txt` e al budget di richieste del job.

Collaudo: `python -m unittest discover -s tests -v` e `python -m scripts.collect_candidate_details --allow-network` nel workflow ordinario; verificare su un esempio consentito Carlo Felice che le singole date differiscano dal generico intervallo di stagione, su Donizetti che l'evento conservi il teatro indicato nella scheda. Accertare che le prove senza autore, orario, sede o con date annullate siano respinte. Nessun trasferimento SFTP per le modifiche JSON.

## Promozione autonoma Genova/Bergamo — 21/11/2026

Le sedi `Teatro Carlo Felice` (Genova, Liguria) e `Teatro Sociale` (Bergamo, Lombardia) vengono riconosciute come possibili sedi ufficiali, distinte dal già registrato `Teatro Donizetti`. Il loro ID permanente viene assegnato **soltanto contestualmente alla prima produzione con recite verificate**, e committato atomicamente con il catalogo; non si aggiungono sedi vuote al registro. Le evidenze strutturate di dettaglio sono ora riconciliate tramite **nome della sede esplicito, identico per tutte le recite**, città e registrazione canonica. È vietato attribuire automaticamente un evento a un teatro predefinito se il testo della fonte non lo identifica, se i record hanno sedi discordanti o se la sede non è tra quelle ammesse per la fonte.

L’auto-catalogazione di nuove repliche di opere note si applica a Genova e Bergamo, quando titolo e compositore corrispondono a un’identità canonica già confermata e tutte le recite hanno data, ora e fuso validi. Le opere nuove seguono il percorso esistente di ricerca autorevole, sinossi originale e profilo storico validato, con lo stesso vincolo sulla sede: non si crea un’opera dal solo titolo di un indice. Restano necessari collaudi HTTP live dei parser di dettaglio, con `robots.txt` permissivo; l’assenza di un esito di scansione riuscita non equivale a copertura della stagione. Brescia ha per ora il connettore indice, ma non il parser specifico di dettaglio certificato.

Collaudi: suite completa, prova di pubblicazione idempotente di recite con evidenza del Carlo Felice o del Teatro Sociale, prova che sede assente/non corrispondente blocchi ogni aggiunta, prova di confusione tra teatri di Bergamo e tra le due Bohème. I JSON rimangono aggiornabili senza SFTP.

## Brescia — estrazione recite e seconda fonte d'orario (21/11/2026)

L'indice ufficiale del Teatro Grande è già monitorato con controllo robots runtime. L'adapter di dettaglio delle schede `/it/stagioni/2026/<slug>` usa soltanto le righe di biglietteria “Turno A/B” precedenti all'intestazione dell'opera: richiede data completa, ora puntuale, “Sala Grande”, nome esatto dell'opera e compositore esplicitati nell'H1. Ignora prezzi, prove e attività di accessibilità con date successive nel documento. La grafia dell'apostrofo tipografico/non tipografico viene normalizzata **solo** durante il confronto con l'identità canonica. Il dittico *Cavalleria rusticana/Pagliacci* non è trattato come una singola opera; la pagina deve essere suddivisa in due identità distinte solo tramite un successivo adapter di doppia produzione verificata.

Per *L'italiana in Algeri* il calendario OperaLombardia contiene già le date del 26 e 28 novembre 2026 al Teatro Grande ma senza orari. Invece di creare due repliche duplicate da una seconda pagina del teatro, il runner confronta l'insieme completo delle date, l'identità (opera e compositore), il teatro e le ore; quando tutto coincide, scrive in `data/verified-time-evidence.json` la prova ufficiale della durata e ora **preservando gli ID permanenti e la fonte originaria**. L'URL ammissibile è esplicitamente ristretto alla pagina Teatro Grande e alla produzione già canonica `lombardia-italiana-brescia`. La prova può essere aggiornata solo se non confligge con il dato esistente, viene validata con `validate_time_evidence` e pubblicata nei JSON v2 nel workflow automatico senza SFTP. Controlli su duplicazioni di rappresentazioni fra circuito e teatro impediscono schede alternative per lo stesso giorno.

**Collaudi**: suite `python -m unittest discover -s tests -v`; verificare i due orari 20:00/15:30, nessun nuovo ID né staging, correttezza DST, idempotenza del refresh, conflitti rifiutati; verificare l'esito live di `candidate-detail-health.json` e `autonomous-catalogue-health.json` prima di dichiarare la fonte pienamente operativa. 

## Dittico verista Teatro Grande: due opere, un calendario (21/11/2026)

La scheda ufficiale del Teatro Grande di Brescia `https://teatrogrande.it/it/stagioni/2026/cavalleria-rusticana-pagliacci` pubblica due repliche del programma condiviso (11 dicembre 2026, 20:00; 13 dicembre 2026, 15:30) con due crediti di opera e compositore indipendenti. Il parser `parse_brescia_double_bill` non crea una terza identità di repertorio: richiede l'esatta intestazione del dittico, i crediti testuali di *Cavalleria rusticana* / Pietro Mascagni e *Pagliacci* / Ruggero Leoncavallo, e due date/orari completi in Sala Grande. L'evidenza viene emessa come quattro righe (due per opera), con gli stessi orari verificati e riferimenti al medesimo URL ufficiale.

La funzione `enrich_double_bill_times` aggiorna le quattro recite già censite da OperaLombardia (**lombardia-cavalleria-brescia** e **lombardia-pagliacci-brescia**) aggiungendo l'orario come prova secondaria, **senza cambiare staging, opera o ID della recita**. L'operazione fallisce integralmente se una delle identità, il numero delle righe, le date o le ore delle due opere differiscono, se un credito manca, se un'ora confligge con evidenze già approvate o se l'URL ufficiale è alterato. La fonte originaria del calendario rimane invariata. Un secondo ciclo è idempotente. Il dato viene pubblicato nel feed JSON dal workflow ordinario, non attraverso SFTP.

Collaudi automatizzati: `python -m unittest discover -s tests -v`, inclusi `test_brescia_double_bill`, `test_brescia_official_details`, test di identità delle due opere, di modifica dell'ora e di annullamento. Collaudo della fonte: controllare `season-index-health.json`, `candidate-detail-health.json` e `autonomous-catalogue-health.json` dopo una nuova esecuzione con rispetto del `robots.txt`. Una pagina irraggiungibile o incompleta non giustifica pubblicazioni.

## Donizetti Opera 2026 — URL evento datata e validazione (21/11/2026)

Il festival collega *Alahor in Granata* da `opere-2026` a un URL ufficiale `/it/evento/alahor-in-granata/2026-11-14/`, mentre gli altri due titoli usano il percorso senza suffisso data. Il vecchio parser richiedeva solo `/it/evento/<slug>/` e rigettava l’indice per mancato raggiungimento di tre link validi. Ora l’indice 2026 ammette esclusivamente i tre titoli operistici verificati, con eventuale data ISO completa e valida nel 2026. Non ammette brunch, anteprime, URL esterni, query o date inventate. La ricerca d’identità usa il titolo dell’opera, mai la componente data del percorso. Il parser del dettaglio applica la stessa allowlist e controlla sempre H1, compositore, date/ore e sede effettiva. I collegamenti scansionati restano soggetti a `robots.txt` aggiornato. Un errore non cancella l’ultimo catalogo valido.

Collaudo: test Python; il link datato di Alahor deve essere scoperto con gli altri due, senza collegamenti non operistici; la scheda di dettaglio datata deve restare validabile con tre recite e Teatro Sociale; nessuna pubblicazione senza identificazione canonica del compositore e senza prova ufficiale degli orari.

## Ricerca autoritativa dei titoli del Donizetti Opera 2026

I tre URL del programma 2026 hanno adesso un nome d’opera esplicito e verificato per la ricerca delle autorità esterne: *L’esule di Roma*, *Alahor in Granata* e *Le convenienze ed inconvenienze teatrali*. La normalizzazione dal solo slug URL non è affidabile per articoli apostrofati (ad esempio `l-esule` non corrisponde a `L’esule` nella funzione slugify). Le alias qui configurate correggono **esclusivamente la stringa di ricerca**; non autorizzano l’identificazione automatica di un’opera o l’attribuzione del compositore senza validazione indipendente della fonte autoritativa, del dettaglio ufficiale e della corretta sede.

## Diagnostica attendibilità dell'indice di stagione (21/11/2026)

Il job `discover_season_indexes` registra ora per ogni connettore:
`last_attempt_at`, `last_success_at`, `last_successful_links`,
`required_links` e `current_scan_verified`. Una fonte che ha funzionato
ieri ma fallisce oggi **non** risulta verificata: l'ultimo esito positivo
resta distinto dall'attuale tentativo. Il report non deduce mai una prima
scansione riuscita quando non esistono prove precedenti.

In caso di errore i codici deterministici `access_denied_or_robots_disallowed`,
`official_source_unavailable`, `index_incomplete_or_markup_changed` e
`invalid_index_or_source_config` permettono di distinguere divieti di
accesso, problemi del sito e cambi di struttura dell'indice; non vengono
esposti messaggi arbitrari ricevuti dai server. In particolare il connettore
Donizetti 2026 non deve più limitarsi alla generica etichetta `ValueError`.
Un errore non elimina i candidati scoperti in precedenza e non attesta
la copertura dell'intera stagione.

Collaudo: suite Python, poi workflow `Refresh public Opera Atlas catalog`.
Controllare in `data/season-index-health.json` che Bergamo, Brescia e Genova
abbiano `current_scan_verified: true` solo dopo una lettura riuscita con
`robots.txt` consentito; controllare separatamente la raccolta di evidenze
e la pubblicazione delle repliche. Nessun deploy SFTP è richiesto.


## Risoluzione autonoma delle opere omonime — 21/11/2026

La ricerca quotidiana **non esclude più** dal controllo di autorità i titoli che sono già presenti nel registro: un titolo noto può riferirsi a una composizione nuova. `scripts.auto_work_research.resolve_identity` valuta tutte le opere valide restituite da Wikidata per quel titolo e raccoglie il compositore associato a ciascuna; se più opere rimangono compatibili, utilizza **solo** un compositore documentato dalla medesima scheda ufficiale di produzione e conservato nella coda delle evidenze. Le attribuzioni a direttori, interpreti o altri ruoli non sono accettate come compositore.

Per i contenuti ufficiali che espongono `MusicEvent.workPerformed.composer` come dati strutturati, `scripts.collect_candidate_details` conserva questa informazione a fianco della data e della sede. Poiché la lettura delle pagine dettagliate segue la ricerca autorevole nel workflow giornaliero, una nuova evidenza può essere utilizzata nel **ciclo successivo** senza interventi manuali o richieste ulteriori alle stesse pagine nello stesso giorno.

Le opere con titolo già presente **non riutilizzano** le sinossi e i profili storici preparati per un'altra composizione: devono ottenere la propria ricerca e il proprio profilo, e vengono pubblicate con ID e URL autonomi. Titoli senza prove sufficienti, crediti in conflitto e candidati Wikidata multipli non risolti restano in retry automatico; non vengono mai attribuiti per somiglianza a un'opera esistente. La pubblicazione di nuove omonime con identità verificata non richiede più alcun secret: in assenza di un testo specifico verificato, Atlas produce una brevissima introduzione fattuale senza inventare dati storici. Le verifiche `robots.txt` sulle pagine ufficiali restano obbligatorie.

I test includono il caso *Il barbiere di Siviglia* (Rossini/Paisiello), la conservazione del compositore nei JSON-LD ufficiali e la ricerca di un titolo già noto con compositore differente. Questo meccanismo non garantisce che ogni teatro renda disponibili prove adeguate: la pubblicazione è intenzionalmente bloccata quando l'identità non è verificabile.

## Carlo Felice — correzione credito compositore Evgenij Onegin

Il compositore registrato come `Pëtr Il\u0027ič Čajkovskij` è presentato dalla fonte ufficiale come `Pëtr Il’ič Čajkovskij`. Il confronto del credito normalizza esclusivamente questa differenza di apostrofo, preservando nome, diacritici e cognome. Il compositore di un’altra opera rimane escluso. La modifica abilita la lettura delle date della scheda ufficiale senza alterare l’identità permanente. Verificare il refresh live e il feed dopo il merge.


## Schede autonome senza chiavi API — 21/11/2026

Il ciclo ordinario di ricerca e pubblicazione **non usa alcuna API di modelli linguistici e non richiede secret a pagamento**. La verifica dell'identità continua a interrogare Wikidata, come servizio pubblico, e a confrontare l'opera con il titolo e il compositore rilevati sulla fonte ufficiale del teatro. Per un'opera non ancora descritta editorialmente, Atlas genera automaticamente una **brevissima introduzione originale e fattuale** esclusivamente da titolo e compositore verificati; non inventa trama, personaggi o ambientazione. Questa introduzione è sufficiente a presentare gli spettacoli disponibili.

Una scheda con Wikidata ID verificato può essere pubblicata anche quando mancano librettista, anno e luogo della prima: in quel caso la parte storica è assente, non segnalata come errore e non compilata con supposizioni. La pubblicazione rimane vincolata a evidenze ufficiali delle singole recite, all'unicità del compositore e agli invarianti di catalogo, anche nei casi di omonimia. Le sinossi e le storie già censite e verificate restano immutate. Il job `refresh-catalog.yml` non carica `ATLAS_OPENAI_API_KEY`.

**Limite esplicito:** una breve introduzione basata su titolo e compositore non è una sinossi narrativa della trama. Per le opere nuove prive di una trama riassumibile in modo affidabile, questa scelta è intenzionale: Atlas è un catalogo di spettacoli, non un'enciclopedia.

## Refresh automatico dopo una pubblicazione rinviata

Il processo `safe_push_catalog` protegge i dati: se nel frattempo un nuovo
commit applicativo ha modificato `main`, non sovrascrive il catalogo aggiornato.
Il risultato `deferred` viene ora esportato come output del job GitHub Actions.
Quando accade, un evento `repository_dispatch: catalog-refresh-retry`
richiede autonomamente un'altra acquisizione usando il codice più recente.
Un push riuscito non genera il retry. La concorrenza privilegia il commit
`main` più recente e interrompe le scansioni obsolete, senza force push.
Il token GitHub Actions già disponibile (`contents: write`) viene usato per
l'evento di dispatch; non servono token personali aggiuntivi né SFTP.

Verificare `data/verified-launch-catalog.json`, `public/catalog/v2/` e
`data/autonomous-catalogue-health.json` dopo il refresh reale. La scoperta
delle sette schede del Teatro Carlo Felice è distinta dalla pubblicazione
delle singole recite: almeno quattro schede con 24 recite hanno già
evidenze ufficiali in coda, le altre tre richiedono la raccolta dei dettagli.

## Pubblicazione rapida delle recite già verificate (21/11/2026)

Il refresh esegue adesso **prima delle letture di rete** una promozione
solo offline delle produzioni con opera e compositore già canonici, sede
verificata e orari espliciti precedentemente acquisiti da pagine ufficiali
(`scripts.publish_cached_known`). L'algoritmo riusa le stesse verifiche di
`scripts.auto_catalogue.promote`; non genera opere inedite, dati editoriali
o manifesti da uno slug, e non aggira `robots.txt`: usa solo evidenze
registrate da precedenti scansioni robots-gated. La pubblicazione valida il
grafo ID e le schede editoriali, rigenera i JSON pubblici e tenta subito
il push in sicurezza. Solo dopo iniziano le scansioni più lente di nuove
opere e fonti. La scansione completa mantiene il proprio secondo passaggio
di riconciliazione e pubblicazione di nuove scoperte.

Se un commit concorrente rende obsoleto il push rapido, non si forzano
sovrascritture: si richiede il refresh sulla nuova `main`. La procedura
è idempotente e resta interamente in `opera-atlas`; non richiede SFTP.
Per Genova, le quattro schede già dotate di date/ore ufficiali
(*Turandot*, *Pagliacci*, *Nabucco*, *L’italiana in Algeri*) possono quindi
diventare visibili senza attendere il download di tutte le altre fonti.
Le altre tre produzioni richiedono prove ancora da acquisire.

## Composer verificato sulle nuove opere del Carlo Felice

Le schede ufficiali prive di un'identità già censita possono ora produrre
**evidenze candidate**, ma soltanto quando H1, slug del percorso HTTPS
ufficiale, credito esplicito `Musica di [autore] Direttore`, sede e
data/orario di ciascuna recita sono tutti verificati sulla stessa pagina.
Non si deducono compositori dai titoli, dai direttori o dalle biografie.
L'attribuzione viene successivamente confrontata con un'identità Wikidata
autonoma, preservando le eventuali omonimie. Gli orari privi di prove,
i crediti discordanti e gli avvisi di annullamento non sono pubblicati.

Il refresh ora esegue le letture dei dettagli *prima* del passaggio
autoritativo, così il compositore rilevato sul sito del teatro è disponibile
alla ricerca della corretta identità nello stesso ciclo. Non aumenta il
budget giornaliero di ricerche o richieste AI, e il controllo `robots.txt`
rimane obbligatorio.

Verifica: `python -m unittest discover -s tests -v`, con test di
*Le nozze di Figaro* (Mozart) e *I Capuleti e i Montecchi* (Bellini);
controllare la riconciliazione autoritativa, la successiva promozione e i
manifesti nel workflow. Le evidenze candidate non equivalgono ancora a
recite pubblicate sul sito.

## Canale indipendente di pubblicazione rapida verificata

`.github/workflows/publish-cached-catalog.yml` pubblica autonomamente i dati
già acquisiti e verificati, **senza attendere** la scansione nazionale completa.
Il workflow ha una coda GitHub Actions separata
(`opera-atlas-cached-feed`, `cancel-in-progress: false`): i merge frequenti
di PR che modificano `main` non possono interrompere il lavoro rapido a
metà. Usa i JSON persistiti di evidenze candidate (che sono già passate per
`robots.txt` e per le verifiche ufficiali) e applica esclusivamente
`scripts.publish_cached_known`, che non crea nuove identità di opere,
non inventa calendari e non fa chiamate a servizi esterni.

Prima del push rigenera e verifica i feed pubblici, le identità canoniche,
la vista sedi e le schede editoriali. Un conflitto di `main` non autorizza
un push forzato: `safe_push_catalog` segnala `deferred` e il job richiede
un retry sulla HEAD corrente tramite evento `cached-catalog-retry`. Un
catalogo già aggiornato non produce un nuovo commit, un refresh riuscito
non si riattiva da sé, e i commit dei dati portano `[skip ci]` per evitare
cicli. Il normale refresh completo continua separatamente a scoprire opere
inedite, verificare nuove recite, immagini e schede, e aggiorna le evidenze
per il passaggio rapido successivo. Niente SFTP.

**Controllo funzionale:** la produzione del Carlo Felice ha quattro schede
con almeno 24 repliche documentate in `data/candidate-detail-evidence.json`,
pubblicabili nella prima fase rapida. Verificare dopo l'esecuzione che le
relative produzioni e repliche risultino sia in
`data/verified-launch-catalog.json` sia in `public/catalog/v2/`;
la sola presenza delle URL candidate non costituisce pubblicazione.

## Concorrenza del refresh nazionale

Le scansioni ufficiali sono abbastanza lunghe da poter essere interrotte dai numerosi merge concorrenti. Il workflow nazionale ora usa `cancel-in-progress: false` per completare un'acquisizione già avviata; una nuova rimane in coda. Il push finale non sovrascrive mai codice o dati arrivati nel frattempo: `safe_push_catalog` rinvia i dati obsoleti e richiede un refresh sulla `main` aggiornata. Il pubblicatore rapido dei dati già verificati utilizza una coda indipendente. Nessun SFTP è coinvolto. Collaudo: eseguire suite Python e seguire il workflow completo fino alla pubblicazione dei JSON e dei manifesti di nuove opere, distinguendo candidati, evidenze e recite pubblicate.

## Checkpoint autonomo delle fonti ufficiali prima della ricerca autoritativa

Il workflow `Refresh public Opera Atlas catalog` adotta una pubblicazione
intermedia degli **indici e delle evidenze candidate ufficiali** subito
dopo `discover_season_indexes` e `collect_candidate_details`:
`data/season-index-{candidates,health}.json`,
`data/candidate-detail-{evidence,health}.json` e i corrispondenti
file pubblici di sola revisione, insieme al report di rollover.
Prima il processo scriveva questi dati su GitHub solo dopo l'intera
ricerca Wikidata, l'arricchimento dei manifesti, la generazione di tutti
i feed e i collaudi finali. Un errore tardivo impediva quindi anche di
leggere le diagnosi delle fonti già verificate, dando l'impressione di un
catalogo non aggiornato.

Il checkpoint **non** inserisce produzioni, recite, opere o identità
nuove nel catalogo canonico; le evidenze restano in stato di revisione
fino a titolo/compositore e orari convalidati. Pubblica in sicurezza
tramite `safe_push_catalog`, senza forzare mai commit concorrenti.
Se `main` avanza nel frattempo, un evento di retry richiede una nuova
esecuzione sulla versione corrente. Le fasi successive continuano
normalmente a riconciliare e pubblicare il catalogo definitivo. I
commit di dati utilizzano `[skip ci]` per non creare loop. Nessun
SFTP o servizio di generazione a pagamento è necessario.

**Collaudi:** suite Python, verifica che il checkpoint preceda
`auto_work_research` e `publish_work_posters`, conferma del suo
commit review-only e poi controllo separato di
`data/verified-launch-catalog.json` e
`public/catalog/v2/manifest.json`. Un checkpoint riuscito non
significa che tutte le recite siano pubblicate.

## Maggio Musicale Fiorentino — calendario mensile verificato (21/11/2026)

La nona fonte d'indice ufficiale è il calendario Opera del Maggio Musicale Fiorentino
(`https://www.maggiofiorentino.com/calendario/2027/01/opera`).
Il nuovo connettore `scripts.collect_maggio_calendar` legge, **con autorizzazione
robots.txt aggiornata a ogni accesso**, al massimo otto pagine mensili a
partire dal mese corrente. Non usa IA generativa né servizi a pagamento.
Ogni card è valida solo se contiene giorno, mese, giorno della settimana,
ora HH:MM, sala precisa `Teatro del Maggio - Sala Grande`, titolo e compositore
di una singola opera già canonica, adiacenti in uno dei due ordinamenti
pubblicati dal teatro. Il collegamento deve puntare a un dettaglio
`https://www.maggiofiorentino.com/events/<slug>`; vengono ignorati altre
sedi, spettacoli didattici e lavori ignoti/non ancora riconciliati. I
collegamenti a servizi terzi, URL manipolati e orari assenti non sono ammessi.

Il connettore crea candidati e prove di data/orario per la promozione standard
`auto_catalogue.promote`: **non pubblica direttamente dati non verificati**.
In caso di successo, `Firenze|Teatro del Maggio Musicale Fiorentino`
riceve l'ID permanente `oa-v-*` solo insieme alla prima opera effettivamente
validata, senza alterare la scheda nazionale esistente. Le recite di una
produzione con un URL ufficiale identico sono idempotenti fra i mesi e fra
le scansioni: quelle nuove si aggiungono dopo controllo delle collisioni.
La funzione permette di estendere la copertura a nuove opere già conosciute
senza nuovi sviluppi per ciascun cartellone.

La pagina ufficiale di gennaio 2027 elenca almeno quattro recite de
*La traviata* (Verdi) il 15/01 alle 20:00, il 17/01 alle 15:30,
il 20/01 alle 20:00 e il 22/01 alle 20:00. Queste date sono usate
come regressione di parsing, **non considerate pubblicate** fino
alla loro effettiva presenza nel manifest v2. Gli spettacoli di
`Teatro Goldoni` non vengono attribuiti al Teatro del Maggio.

**Collaudi:** `python -m unittest discover -s tests -v`;
`test_maggio_calendar` verifica date/ore, composer, sito, sede, idempotenza,
costruzione del catalogo e rifiuto dei casi incongruenti. Nel workflow,
controllare `data/maggio-calendar-health.json`, il checkpoint delle
evidenze, la promozione e il manifest pubblico. Nessun deploy SFTP.

## Prima acquisizione verificata del calendario di Firenze

Per non lasciare il nuovo connettore in attesa del successivo refresh live,
sono state registrate come **evidenze candidate, non ancora come recite
pubblicate**, quattro occorrenze de *La traviata* (Giuseppe Verdi) tratte
dal calendario Opera ufficiale del Maggio Musicale Fiorentino, gennaio 2027:
15/01 20:00, 17/01 15:30, 20/01 20:00, 22/01 20:00. Sono registrate
con URL del dettaglio `/events/la-traviata-2027`, sede `Teatro del
Maggio Musicale Fiorentino`, data/ora Europe/Rome e la stessa identità
permanente di candidata che il nuovo estrattore genererà nei refresh futuri.
La documentazione del calendario è
`https://www.maggiofiorentino.com/calendario/2027/01/opera`, che
specifica singole date, ore e sala; la scheda di dettaglio conferma Verdi.
Un connettore che non può leggere una pagina per `robots.txt` non
sovrascrive queste evidenze verificate già persistite.

Questi fatti sono destinati alla promozione con la procedura ordinaria,
che convalida ID, titolo/compositore, sede e URL approvato prima di
pubblicare i JSON. La loro mera presenza nelle prove candidate **non**
garantisce che il feed v2 sia aggiornato; verificarlo sul manifest e sul
registro delle produzioni dopo l'esecuzione di GitHub Actions. Il job
`Publish cached verified Opera Atlas recite` può pubblicare questi
fatti senza richieste esterne, lasciando il mantenimento successivo al
connettore mensile. Nessun deploy SFTP.

## Firenze — promozione autonoma della prima opera nuova del Maggio

Il calendario Opera ufficiale del Maggio Musicale Fiorentino ha pubblicato
quattro recite di *Les contes d’Hoffmann* di Jacques Offenbach: 20 dicembre
2026 alle 17:00, 27 dicembre alle 15:30, 30 dicembre alle 20:00 e 2 gennaio
2027 alle 17:00. Le stesse informazioni compaiono nelle schede delle
rappresentazioni di dicembre 2026 e gennaio 2027 sul sito ufficiale:
`https://www.maggiofiorentino.com/calendario/2026/12/opera` e
`https://www.maggiofiorentino.com/calendario/2027/01/opera`.

La scheda dell'opera è stata confrontata con l'identità Wikidata **Q335012**
(opera di Jacques Offenbach, non il film omonimo), e con la scheda
bibliografica BnF, che conferma il librettista Jules Barbier e la prima
rappresentazione all'Opéra-Comique di Parigi nel 1881. La breve sinossi è
originale e limitata alla presentazione dell'opera. Le quattro righe di
evidenza contengono ora titolo, compositore, sede esatta e orario locale
Europe/Rome: il dato del direttore non viene confuso con il compositore.

Il pubblicatore offline `publish_cached_known` può adesso promuovere
anche nuove opere del Maggio **solo quando** dispone di evidenza ufficiale
completa, identità Wikidata, una sinossi originale e un profilo storico
verificato. Riusa `promote_new_works` e convalida grafo canonico, URL
approvati e schede editoriali **prima** di scrivere su disco. Non esegue
richieste esterne, non bypassa robots.txt e non genera un'identità
basata solo sul titolo. Scrive il nuovo `site/work-synopses.json` e
`site/work-history.json` soltanto quando la nuova opera è accettata;
un secondo refresh non crea duplicati. I passaggi di poster e immagini
restano affidati al workflow dedicato.

**Collaudi**: suite completa Python, inclusi
`test_offenbach_cached_promotion.py` e i controlli di regressione,
verifica del workflow indipendente dopo il merge e presenza della
nuova opera con **quattro recite** nel manifest pubblico v2.
La sola aggiunta delle evidenze o l'approvazione della PR non viene
conteggiata come pubblicazione effettiva.

## Commit atomico dei dati editoriali in pubblicazione rapida

Le nuove opere possono essere promosse da `publish_cached_known` solo con
Wikidata, credito del compositore sulla fonte ufficiale, sinossi originale e
dati storici verificati. Il workflow rapido e il primo passaggio del workflow
nazionale aggiungono ora **anche** `site/work-synopses.json` e
`site/work-history.json` nello stesso commit che aggiorna il manifest,
le identità canoniche e il feed editoriale pubblico. Questa transazione evita
che la scheda di una nuova opera sia pubblicata senza le relative fonti
dell'editoriale; non modifica i controlli degli URL o gli ID permanenti.
La suite Python contiene un controllo statico esplicito dei due workflow.

## Roma — Teatro dell'Opera, Teatro Costanzi (21/11/2026)

La decima fonte di indice approvata è la sezione ufficiale
`https://www.operaroma.it/opere/`, con pagine dettaglio
`https://www.operaroma.it/spettacoli/<slug>/`, che vengono
lette soltanto dopo una verifica positiva del `robots.txt` corrente.
L'estrattore `opera_atlas.roma_detail_parser` accetta **esclusivamente**
pagine ufficiali HTTPS senza query, frammenti o redirect, con H1
dell'opera già canonica, compositore espresso come `Musica di ...`,
stagione dichiarata **2026/2027**, luogo effettivo **Teatro Costanzi**
e singole date/orari `ORE HH:MM` verificati anche contro il giorno
della settimana. La scansione si interrompe prima delle anteprime
giovani, dei link a spettacoli correlati e di eventuali pagine
di altre stagioni. Un annullamento, una data impossibile o
un credito divergente blocca la promozione.

Ai fini delle schede nazionali, il Teatro Costanzi è la sala
della Fondazione **Teatro dell'Opera di Roma** già censita,
che mantiene il suo URL pubblico; la nuova identità canonica
`Roma|Teatro dell'Opera di Roma` è creata soltanto insieme
alla prima recita verificata, con regione Lazio. Le singole
recite non sono attribuite alle altre sale della fondazione,
come Teatro Nazionale o Terme di Caracalla.

La prima produzione verificata è *Lucia di Lammermoor*
(Gaetano Donizetti) con sette recite il **21, 23, 24, 25, 26,
27 e 28 febbraio 2027**. Gli orari sono, rispettivamente,
19:00, 20:00, 20:00, 20:00, 20:00, 18:00 e 16:30.
Sono letti dalla pagina ufficiale
`https://www.operaroma.it/spettacoli/lucia-di-lammermoor-2/`,
che specifica il compositore, la sala e le singole rappresentazioni.
L'anteprima del 20 febbraio non viene inserita come replica
ordinaria. Le stesse informazioni sono documentate dal programma
ufficiale della stagione. Il primo set entra nelle evidenze
candidate per la promozione del pubblicatore rapido: il suo
inserimento non equivale da solo alla pubblicazione nel catalogo.

**Collaudo:** suite Python con `test_opera_roma_calendar.py`,
controllo nel workflow delle sette date con ore, dell'ID stabile,
dell'assenza di anteprime, dell'attribuzione alla corretta sala,
dell'idempotenza e del manifesto pubblico v2. Nessun SFTP;
la raccolta di ulteriori opere segue il normale refresh nazionale.

## Bari — Teatro Petruzzelli: stagione 2027 e Nabucco

La fonte ufficiale di Bari è
`https://www.fondazionepetruzzelli.it/opera-e-balletto-2027/`,
con dettagli operistici `https://www.fondazionepetruzzelli.it/eventi/<slug>/`.
È un indice approvato con scansione controllata da `robots.txt` a ogni
accesso; le candidate non sono automaticamente equiparate a opere liriche:
un titolo di balletto o un concerto è escluso dalla pubblicazione se
non supera le verifiche sul compositore, l'opera canonica e il calendario.

Il primo dettaglio verificato è
`https://www.fondazionepetruzzelli.it/eventi/nabucco-di-giuseppe-verdi-12-19-marzo/`.
Il teatro presenta il compositore **Giuseppe Verdi** e sette recite di
*Nabucco* il 12, 13, 14, 16, 17, 18 e 19 marzo 2027, con orari
20:30, 18:00, 18:00, 20:30, 20:30, 20:30, 18:00. Il parser
`opera_atlas.petruzzelli_detail_parser` richiede l'esatto dominio
ufficiale, il credito dell'opera nel titolo della scheda, la sezione
`Orari Spettacoli`, giorni della settimana compatibili con le date,
orari HH:MM per **tutte** le recite e nessun annullamento.

La conferenza di presentazione del 4 marzo non viene scambiata
per una replica operistica. Sedi o festival terzi non vengono assegnati
automaticamente al Petruzzelli. La prima promozione assegna il nuovo
ID canonico `Bari|Teatro Petruzzelli` (regione Puglia) solo insieme
alla prima produzione valida. Le identità dei compositori e dei
titoli sono quelle già verificate nel registro del repertorio;
non vengono create nuove opere sulla base dei soli URL.

Le sette recite sono registrate come **evidenze di prima acquisizione**
per la pipeline rapida di promozione e pubblicazione, che provvede agli
ID permanenti e alla rigenerazione del JSON v2 in un commit controllato.
Né la PR né le evidenze costituiscono prova di pubblicazione:
questa è verificata solo quando il manifest e il feed contengono le
sette rappresentazioni. Non è richiesto un deploy SFTP.

**Collaudi:** `python -m unittest discover -s tests -v`, in particolare
`tests/test_petruzzelli_calendar.py`, poi lettura del JSON canonico
e del report del workflow sul sito del teatro e sul repository.

## Teatro Comunale di Bologna — opera 2027 (21/11/2026)

Fonte ufficiale: https://www.tcbo.it/stagione-futura/?_tipo=opera. La pagina distingue 9 produzioni operistiche, 38 rappresentazioni annunciate nel 2027, di cui due produzioni al Teatro Auditorium Manzoni. Gli orari non vengono mai inferiti dalla pagina di stagione: il parser `opera_atlas/bologna_detail_parser.py` legge esclusivamente le singole schede `/evento/opera/<slug>-<anno>/` e richiede titolo H1, compositore esplicitamente dichiarato, data, orario e sede nel blocco «Date e turni». I concerti, la danza e le attività dell'Accademia non sono assunti come opera.

La nuova fonte `bologna-comunale-opera-2027` entra nella scansione giornaliera robot-gated e genera prima candidati e prove. Solo le identità canoniche univoche sono promosse automaticamente; le nuove composizioni richiedono riconciliazione d'autorità automatica, e i casi irrisolti restano fuori dalle recite pubbliche. Le recite al Manzoni non vengono mai attribuite alla sala storica di Largo Respighi. La pagina del Comunale storico è già censita; la sede provvisoria Nouveau non viene ripristinata. Dopo il merge la scansione completa può iniziare automaticamente dal workflow `refresh-catalog` senza deploy SFTP.
