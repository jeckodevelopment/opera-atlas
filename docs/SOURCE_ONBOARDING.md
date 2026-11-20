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
