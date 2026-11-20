# Catalogo web iniziale — Fase 3

## Ambito consegnato
Il prototipo pubblico statico in `site/` carica `site/performances.json`, contratto `schema_version: 1` generato da `opera_atlas.ingestion.export_public_catalog`. Non sono richiesti server applicativi, servizi di geolocalizzazione o API terze.

Sono disponibili ricerca testuale (opera, compositore, teatro), filtri per città, regione, intervallo di date e orario noto/mancante, ordinamento cronologico, impaginazione di 12 recite e link HTTPS alle fonti ufficiali. I dati di origine sono resi con `textContent`, non con HTML dinamico, e i link sono limitati a HTTPS.

Una recita parziale con **titolo, data, teatro e città** ha una scheda normale con dicitura **Orario da confermare**; il valore `starts_at: null` non viene mai trasformato in mezzanotte. Le recite con ora mostrano l'orario locale già normalizzato dall'export.

L'interfaccia include etichette per i campi, regioni live per il conteggio risultati, focus visibile, link per saltare al contenuto e layout responsivo.

## Avvio locale e pubblicazione
La prima distribuzione era intenzionalmente vuota. L’aggiornamento editoriale del 20/11/2026 include **19 recite verificate sulle pagine ufficiali** (11 La traviata Torino, 8 L’italiana in Algeri OperaLombardia). Nessuna recita dimostrativa è pubblicata.

Dopo una importazione **autorizzata** e una verifica editoriale, esportare soltanto dati effettivamente presenti nel DB:

```sh
python -m unittest discover -s tests -v
python -m opera_atlas.ingest_cli --db atlas.sqlite3 export --output site/performances.json
python -m http.server 8000 --directory site
```

Aprire `http://localhost:8000/`. Non aprire il file HTML come `file://`, perché `fetch` può essere bloccato dal browser.

La pubblicazione del JSON è una decisione esplicita dell'operatore: non committare dati di prova come se fossero risultati ufficiali. Il frontend non acquisisce dati dai siti teatrali e non aggira alcuna policy.

## Comportamenti da collaudare manualmente
1. Avviare il catalogo vuoto: messaggio **Nessuna recita pubblicata**, nessuna recita di fantasia.
2. Esportare un DB di prova con una recita completa e una senza ora: entrambe visibili; la seconda mostra **Orario da confermare** senza `00:00`.
3. Filtrare per città, regione, opera, date e stato dell'orario; conteggi e schede coerenti.
4. Azzerare i filtri; verificare che l'elenco ritorni completo.
5. Eseguire la prova da tastiera e su viewport mobile: label, focus, link e pulsanti raggiungibili.
6. Verificare che i link puntino a URL HTTPS effettivamente presenti nel JSON, senza riferimenti a terze parti aggiunti dal frontend.
7. Rimuovere o corrompere il JSON: compare un messaggio di errore senza creare recite.
8. Con più di 12 recite, verificare paginazione e ordine cronologico.

## Limiti reali
È il **primo catalogo navigabile**, non la Fase 3 completa: mancano pagine dettaglio dedicate, filtri per festival, mappa, geolocalizzazione e dashboard KPI. Non è stato eseguito un test browser visuale in CI. L'export data-only non inventa regione, compositore o coordinate: tali campi rimangono null o vuoti e non sono selezionabili tramite il filtro regione finché non vengono verificati.

## Schede di opera, recita e teatro
Da ciascuna scheda del catalogo sono disponibili link a `detail.html?type=work&key=…`, `detail.html?type=venue&key=…` e `detail.html?type=performance&key=…`. La pagina legge lo stesso `performances.json` e risolve le associazioni attraverso i dati pubblicati, senza una chiamata server o un database pubblico. Titoli, compositori, date, orari, sedi e fonti ufficiali vengono mostrati solo quando presenti. Se `starts_at` è null, compare **Orario da confermare**. Il dettaglio di una recita ha collegamenti all'opera e al teatro; quello di un'opera o teatro elenca le recite abbinate.

Gli URL non validi o senza corrispondenza hanno uno stato vuoto comprensibile. È vietato inserire markup HTML proveniente dal JSON: i contenuti sono visualizzati solo come testo e i link alle fonti accettano esclusivamente HTTPS. I parametri in query non autorizzano a leggere file o URL di terze parti.

## Distribuzione tramite jeckodevsite
Publisher di riferimento: `jeckodevelopment/jeckodevsite`, script `scripts/deploy_opera_atlas.py`, workflow `.github/workflows/publish-opera-atlas.yml`. Destinazione: **https://jeckodevelopment.com/dev/opera-atlas/**. Il workflow usa la stessa configurazione SFTP/host key e rollback delle altre applicazioni `/dev/`, verificando byte-per-byte i sei asset via HTTPS. Non è previsto un nuovo secret né la pubblicazione dell'intero sito. Un cambiamento del frontend in questa repository richiede un trigger al publisher (`deploy-requests/opera-atlas.txt`) o il relativo avvio manuale; le due repository non condividono segreti.

L'interfaccia può essere pubblicata con JSON iniziale vuoto, ma non è prova della disponibilità di recite reali: l'autorizzazione delle fonti e i collaudi di acquisizione restano requisiti separati.

### Ulteriori collaudi
- Dalla home aprire le schede opera, recita e teatro usando un JSON di test locale autorizzato; verificare titoli/luogo/fonti e link di ritorno.
- Confermare che una recita senza orario conservi la dicitura anche nel dettaglio.
- Verificare link errati o di eventi rimossi: messaggio `Scheda non disponibile`, nessun errore JavaScript.
- Controllare la risposta HTTPS di `index.html`, `detail.html`, CSS/JS e JSON dopo la pubblicazione; il deploy deve essere isolato dai percorsi degli altri progetti.

## Primo catalogo editoriale verificato — 20/11/2026

**Fonti:** [Teatro Regio Torino – La traviata](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata), con 11 recite tra il 26 febbraio e il 10 marzo 2027, ed [OperaLombardia – L’italiana in Algeri](https://www.operalombardia.it/l-italiana-in-algeri/), con 8 recite in Como, Pavia, Brescia e Cremona tra il 13 novembre e il 12 dicembre 2026. I dati minimi sono titolo/compositore, data, teatro, città, regione e URL ufficiale. **Non** sono copiate fotografie, cast, descrizioni, testi di programma o pagine HTML.

La procedura `python -m scripts.build_verified_catalog --check` confronta `site/performances.json` con il manifesto `data/verified-launch-catalog.json`, rifiutando fonti non previste, duplicati, date o orari malformati. Il catalogo è un **seed editoriale manuale** e non disattiva le condizioni di approvazione dei crawler: nessun job di fetch o polling viene abilitato. Gli orari OperaLombardia rimangono sconosciuti (null e dicitura “Orario da confermare”). Queste date potrebbero cambiare; il visitatore è invitato a controllare la fonte ufficiale.

## Identità grafica iniziale
Design ispirato alla grammatica visiva di Opera+ Funding: base avorio, schede bianche leggere, grigi caldi, accenti oro, titoli serif, metriche riassuntive, filtri compatti e recite in righe orizzontali con mini-calendario. **Non** è stato utilizzato il logo di Opera+ Funding: Opera Atlas conserva una testata testuale in attesa del logo definitivo. Non sono incorporati asset o fotografie di terzi.

### Collaudi aggiuntivi
- Controllare 19 recite, 2 opere, 5 teatri, 8 orari ignoti e collegamenti alle due pagine ufficiali.
- Verificare che tutte le 11 recite torinesi riportino ora locale, che le altre 8 presentino “Orario da confermare” e che due date già passate restino correttamente nello storico.
- Verificare schede, riepiloghi, filtri, paginazione, pagine di dettaglio, accessibilità su smartphone e coerenza grafica con Funding.
- Confermare la nuova pubblicazione con `jeckodevsite` e l'esito HTTPS di tutti gli asset.

## Nuovo feed canonico separato dal deploy (catalogo v2)
Il frontend consulta `raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/manifest.json` e quattro canali JSON: opere, teatri, messe in scena e repliche. Verifica SHA-256 e integrità referenziale, presenta le schede con dati verificati e, se non può leggere il feed remoto, usa il JSON locale dell'ultimo deploy come **fallback dichiaratamente non aggiornato**. Non pubblica falsi dati correnti o variazioni non riconciliate.

Gli ID `oa-w-...`, `oa-v-...`, `oa-s-...`, `oa-r-...` sono registrati una volta in `data/identity-registry.json`. Gli slug `/opere/la-traviata/`, `/torino/teatro-regio/`, `/torino/teatro-regio/la-traviata/` sono identità editoriali separabili e richiedono la futura configurazione delle rewrite per il supporto HTTP diretto. La corrente interfaccia mantiene ancora `detail.html?type=...`, perciò non si dichiarano già pubblicati gli URL SEO.

**Regola di pubblicazione:** modifiche a catalogo e schedule agiscono esclusivamente in `opera-atlas`. Un aggiornamento del feed non deve invocare SFTP; solo nuove versioni HTML/CSS/JS transitano da `jeckodevsite`. Il workflow quotidiano non esegue ancora fetch di siti con permessi non verificati. Prima di aggiungere nuovi eventi, occorre registrare ID permanenti e provenienza nell'archivio editoriale, verificare e pubblicare, senza sovrascrivere arbitrariamente i record precedenti.

### Collaudi da eseguire
1. Validare `python -m scripts.publish_catalog_v2 --check` dopo generazione; controllare 2 opere, 5 teatri, 5 messe in scena, 19 repliche.
2. Ripetere generazione senza dati cambiati: nessun cambiamento di hash, nessun commit di pubblicazione.
3. Cambiare una data senza risolverne identità: il generatore deve interrompersi e preservare il feed precedente.
4. Verificare che il frontend prelevi manifesto e quattro canali via HTTPS direttamente da GitHub, senza SFTP; interrompere la rete e verificare avviso di fallback.
5. Un file JSON danneggiato o senza relazione canonica deve provocare fallback/errore esplicito, non un catalogo parziale.
6. Controllare la schedulazione, i permessi `contents:write` limitati al workflow e l'assenza di job di scansione non approvata.

## URL leggibili e pagine per messa in scena
La home offre **Per data** (ogni replica) e **Per messa in scena** (produzione in un teatro, con calendario delle repliche). I link sono generati da ID e slug canonici del feed, **mai dal titolo preso dalla query**. La pagina `/opere/<opera>/` aggrega tutte le messe in scena nazionali censite, con le date raggruppate per teatro; `/<citta>/<teatro>/` raccoglie le programmazioni del teatro; `/<citta>/<teatro>/<opera>/` mostra un'unica messa in scena, con tutte le sue repliche e orari noti/sconosciuti.

Le riscritture Apache sono in `site/.htaccess` e inviano soltanto i percorsi whitelist a `detail.html`, senza invocare un backend. Il tag `<base href="/dev/opera-atlas/">` rende CSS, JavaScript e fallback JSON raggiungibili anche dai percorsi annidati. Gli URL legacy `detail.html?type=work|venue|performance&key=...` continuano a essere risolti tramite il catalogo e canonizzati nel browser. Il vecchio identificatore `curated:...` viene trasportato in `legacy_id` accanto all'ID `oa-r-...` per la compatibilità.

**Nota di hosting:** per gli URL deep link serve un server Apache con `mod_rewrite` e `AllowOverride` abilitati. Il collaudo post-deploy deve richiedere direttamente le tre tipologie di URL, verificare 200 e contenuto HTML corretto, oltre al JSON GitHub via CORS; in caso contrario il publisher deve interrompersi/ripristinare i file.

### Test manuali
1. Dalla home selezionare **Per messa in scena**: 5 schede corrispondenti a 5 programmazioni, a fronte delle 19 repliche in modalità **Per data**.
2. Aprire `/dev/opera-atlas/opere/la-traviata/`: raggruppamenti per teatro, 11 recite al Teatro Regio.
3. Aprire `/dev/opera-atlas/torino/teatro-regio/`: La traviata, 11 repliche.
4. Aprire `/dev/opera-atlas/torino/teatro-regio/la-traviata/`: una sola scheda con undici giorni e orari, senza undici pagine distinte.
5. Aprire `/dev/opera-atlas/opere/italiana-in-algeri/`: quattro teatri e otto recite senza ora; nessun `00:00`.
6. Verificare i vecchi link parametrizzati, le richieste dirette e il refresh del browser su URL profondi, su desktop e smartphone.
7. Controllare che il deploy del frontend non sia rieseguito per le modifiche dei soli JSON.

## Freschezza dei dati e controllo giornaliero
Il catalogo mostra la data di verifica editoriale proveniente dal manifesto GitHub; è distinta dalla data di esecuzione del workflow. Il job quotidiano può leggere pagine soltanto quando il file `data/daily-source-config.json` segnala approvazione documentata. Un errore di robots o pagina incompleta non rimuove eventi e non pubblica dati fittizi. I risultati di scansione autorizzata sono registrati separatamente in `data/catalog-source-health.json` e non causano mai un deploy SFTP. Il dettaglio dei controlli e le regole di onboarding sono in [SOURCE_ONBOARDING](SOURCE_ONBOARDING.md).

## Arricchimento degli orari da più fonti ufficiali

La fonte aggregatrice OperaLombardia documenta **opera, teatro e data** ma non l'ora. Il registro `data/verified-time-evidence.json` conserva ulteriori prove ufficiali relative a **specifici ID di replica**. Il frontend mantiene il collegamento al circuito e mostra anche la fonte che prova l'ora; non crea una seconda recita. La regola di pubblicazione è: orari solo da evidenza esplicita collegata a produzione e data; altrimenti `starts_at: null` e «Orario da confermare».

Evidenze del 20 novembre 2026: Teatro Sociale di Como (13/11 20:00, 15/11 15:30), Teatro Fraschini di Pavia (20/11 20:00, 22/11 15:30), Comune di Cremona (Teatro Ponchielli 10/12 20:00, 12/12 16:00). Brescia 26 e 28 novembre rimane senza orario. Il catalogo resta a 19 repliche: **17 orari noti, 2 sconosciuti**. L'arricchimento avviene con JSON in `opera-atlas`, senza nuova pubblicazione SFTP per i dati; se occorre modificare il renderer web, solo quella modifica passa nel workflow SFTP.

Test: `python -m unittest discover -s tests -v`, `python -m scripts.build_verified_catalog --check`, `python -m scripts.publish_catalog_v2 --check` (quest'ultimo dopo la rigenerazione dei canali). Verificare con browser le 6 repliche, i due URL ufficiali per ciascuna e la permanenza degli ID nel link canonico.

## Ampliamento Regio verificato — 20/11/2026
Due produzioni del Teatro Regio Torino aggiunte a partire dai calendari di dettaglio ufficiali, con timestamp locali `Europe/Rome`: [Edgar](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/edgar), 7 recite (22, 26, 28, 30 gennaio; 2, 4, 6 febbraio 2027), e [Salome](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/salome), 6 recite (2, 6, 9, 11, 14, 17 aprile 2027). Il giorno 22 gennaio e il 2 aprile sono anteprime giovani effettivamente riportate nelle rispettive pagine, non duplicati di altre repliche.

**Catalogo dopo la rigenerazione:** 32 recite, 4 opere, 5 teatri, 7 messe in scena; 30 con orario esplicito, 2 senza (Brescia). URL stabili `/torino/teatro-regio/edgar/`, `/torino/teatro-regio/salome/`, `/opere/edgar/` e `/opere/salome/`. Ogni replica della stessa produzione rimanda a un'unica scheda. I dati transitano esclusivamente via feed JSON GitHub e non richiedono SFTP.

## Repertorio principale Teatro Regio Torino completo — 20/11/2026
Censite tutte le nove opere della stagione 2026/27 sul palcoscenico principale attraverso le rispettive pagine di dettaglio ufficiali. Aggiunte 49 nuove repliche: [Cavalleria rusticana](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/cavalleria-rusticana) 9, [Pagliacci](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/pagliacci) 9, [La bohème di Leoncavallo](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-boheme) 6, [Iris](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/iris) 7, [Carmen](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/carmen) 11, [Evgenij Onegin](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/evgenij-onegin) 7. Preesistenti Edgar 7, La traviata 11, Salome 6. **73 recite del Regio + 8 del circuito OperaLombardia = 81**, 10 opere distinte, 5 teatri, 13 messe in scena; 79 orari noti e 2 null. Il doppio cartellone Cavalleria/Pagliacci ha **due ID opera separati** ma le stesse date ufficiali: non si tratta di un duplicato di record. *Juditha triumphans* è oratorio e rimane fuori dal perimetro opera; esclusi balletto e concerti. La stagione Regio considerata è limitata alle produzioni sul palcoscenico principale e non afferma di aver censito gli eventi educativi nel Piccolo Regio.

Collaudo manuale: cercare La bohème di Leoncavallo, tutte le date del dittico, i calendari di maggio/giugno, il corretto offset +02:00 prima del 25 ottobre 2026, la conservazione di tutti gli ID precedenti, le fonti HTTPS e il mancato invio SFTP su variazioni dei soli JSON.

### OperaLombardia — partner Teatro Fraschini, programma 2026/27
Le prime dieci nuove recite presso il partner territoriale Teatro Fraschini Pavia sono fondate sulle quattro pagine ufficiali: [Turandot](https://www.teatrofraschini.it/programma/turandot/) 9/11 ottobre 2026 ore 20/15:30; [Cavalleria rusticana / Pagliacci](https://www.teatrofraschini.it/programma/cavalleria-rusticana-pagliacci/) 30/31 ottobre ore 20 (due opere distinte, stessa serata); [Un ballo in maschera](https://www.teatrofraschini.it/programma/un-ballo-in-maschera/) 3/5 dicembre ore 20; [Death in Venice](https://www.teatrofraschini.it/programma/death-in-venice/) 15/17 gennaio 2027 ore 20/15:30. Il perimetro è **Pavia**: non attribuire le medesime date a Como/Brescia/Cremona. Totale dopo l'export: 91 recite, 13 opere, 5 teatri, 18 messe in scena, 89 orari noti e 2 ignoti. Fonte collegata per ogni recita, ID permanente, URL dinamico `/pavia/teatro-fraschini/<opera>/`. JSON canonico su GitHub senza SFTP. Il circuito nazionale rimane da ampliare sui singoli teatri.

## Primo catalogo da cinque nuovi teatri — 20/11/2026
Dati verificati e pubblicabili da sei specifiche pagine ufficiali, **non scansioni automatiche attive**: Otello Scala 9 recite, Aida ed. 1913 Arena di Verona 9, Fedora La Fenice 7 (escluso il **13 novembre 2026 annullato**), Samson et Dalila Teatro Massimo 6, Macbeth Teatro Massimo 5, Madama Butterfly Regio Parma 4 (escluse le prove del 12 e 14 aprile). Nessun dato inferito da intervalli di programmazione; ogni record ha giorno/ora, teatro, città, titolo, compositore, fonte HTTPS e nuovo ID canonico. Totalizzazione prevista: **131 recite, 19 opere, 10 teatri, 24 messe in scena; 129 ore note, 2 sconosciute**. I dati aggiornati vengono distribuiti da `opera-atlas/public/catalog/v2/` senza SFTP. Per i limiti della copertura nazionale e le fonti primarie, vedi [INITIAL_SOURCE_COVERAGE_2026-11-20](INITIAL_SOURCE_COVERAGE_2026-11-20.md).
