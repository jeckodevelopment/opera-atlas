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

## Distribuzione autonoma su opera.plus/atlas/

La destinazione canonica del frontend è **https://opera.plus/atlas/**. Il publisher risiede esclusivamente in `jeckodevelopment/opera-atlas`: `.github/workflows/deploy-atlas.yml` e `scripts/deploy_atlas.py`. Nessuna richiesta di pubblicazione è più necessaria in `jeckodevsite`. Si usa un account FTPS esplicito del nuovo hosting, con verifica TLS del certificato, una allowlist di file statici, upload verificato su area temporanea, cambio di directory, collaudo HTTPS degli asset e delle rewrite e ripristino del rilascio precedente in caso di errore. Il percorso remoto è sempre una **cartella specifica terminante in /atlas**, non la document root dell'intero dominio.

Per il primo rilascio utilizzare l'avvio manuale: l'automazione dopo merge resta sospesa finché non si configura `ATLAS_DEPLOY_ENABLED=true`. Vedere [DEPLOY_OPERA_PLUS](DEPLOY_OPERA_PLUS.md) per credenziali, preparazione webroot, controllo DNS/TLS, eventuale server senza mod_rewrite e strategia di taglio dal vecchio sito.

Le date, le opere e le nuove schede continuano ad aggiornarsi direttamente tramite il JSON canonico GitHub; i rilasci SFTP riguardano solo nuove versioni dell'interfaccia. Il fallback JSON locale viene aggiornato solo quando cambia il contenuto del frontend. L'assenza di credenziali o di un server web compatibile impedisce il deploy, senza alterare il sito corrente.

### Ulteriori collaudi
- Dalla homepage aprire schede opera, produzione e teatro con il nuovo prefisso `/atlas/`.
- Confermare il corretto caricamento dei feed GitHub, compresi nuovi titoli e repliche, e il fallback.
- Verificare che le repliche senza orario rimangano senza orario inventato.
- Controllare HTTPS e impronte SHA-256 di ogni asset, la navigazione alle pagine profonde e la risoluzione di `.htaccess`.

## Primo catalogo editoriale verificato — 20/11/2026

**Fonti:** [Teatro Regio Torino – La traviata](https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata), con 11 recite tra il 26 febbraio e il 10 marzo 2027, ed [OperaLombardia – L’italiana in Algeri](https://www.operalombardia.it/l-italiana-in-algeri/), con 8 recite in Como, Pavia, Brescia e Cremona tra il 13 novembre e il 12 dicembre 2026. I dati minimi sono titolo/compositore, data, teatro, città, regione e URL ufficiale. **Non** sono copiate fotografie, cast, descrizioni, testi di programma o pagine HTML.

La procedura `python -m scripts.build_verified_catalog --check` confronta `site/performances.json` con il manifesto `data/verified-launch-catalog.json`, rifiutando fonti non previste, duplicati, date o orari malformati. Il catalogo è un **seed editoriale manuale** e non disattiva le condizioni di approvazione dei crawler: nessun job di fetch o polling viene abilitato. Gli orari OperaLombardia rimangono sconosciuti (null e dicitura “Orario da confermare”). Queste date potrebbero cambiare; il visitatore è invitato a controllare la fonte ufficiale.

## Identità grafica iniziale
Design ispirato alla grammatica visiva di Opera+ Funding: base avorio, schede bianche leggere, grigi caldi, accenti oro, titoli serif, metriche riassuntive, filtri compatti e recite in righe orizzontali con mini-calendario. **Non** è stato utilizzato il logo di Opera+ Funding: Opera Atlas conserva una testata testuale in attesa del logo definitivo. Non sono incorporati asset o fotografie di terzi.

### Collaudi aggiuntivi
- Controllare 19 recite, 2 opere, 5 teatri, 8 orari ignoti e collegamenti alle due pagine ufficiali.
- Verificare che tutte le 11 recite torinesi riportino ora locale, che le altre 8 presentino “Orario da confermare” e che due date già passate restino correttamente nello storico.
- Verificare schede, riepiloghi, filtri, paginazione, pagine di dettaglio, accessibilità su smartphone e coerenza grafica con Funding.
- Confermare la nuova pubblicazione con il workflow `opera-atlas` e l'esito HTTPS di tutti gli asset.

## Nuovo feed canonico separato dal deploy (catalogo v2)
Il frontend consulta `raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/public/catalog/v2/manifest.json` e quattro canali JSON: opere, teatri, messe in scena e repliche. Verifica SHA-256 e integrità referenziale, presenta le schede con dati verificati e, se non può leggere il feed remoto, usa il JSON locale dell'ultimo deploy come **fallback dichiaratamente non aggiornato**. Non pubblica falsi dati correnti o variazioni non riconciliate.

Gli ID `oa-w-...`, `oa-v-...`, `oa-s-...`, `oa-r-...` sono registrati una volta in `data/identity-registry.json`. Gli slug `/opere/la-traviata/`, `/torino/teatro-regio/`, `/torino/teatro-regio/la-traviata/` sono identità editoriali separabili e richiedono la futura configurazione delle rewrite per il supporto HTTP diretto. La corrente interfaccia mantiene ancora `detail.html?type=...`, perciò non si dichiarano già pubblicati gli URL SEO.

**Regola di pubblicazione:** modifiche a catalogo e schedule agiscono esclusivamente in `opera-atlas`. Un aggiornamento del feed non deve invocare SFTP; solo nuove versioni HTML/CSS/JS transitano dal workflow FTPS nativo `opera-atlas`. Il workflow quotidiano non esegue ancora fetch di siti con permessi non verificati. Prima di aggiungere nuovi eventi, occorre registrare ID permanenti e provenienza nell'archivio editoriale, verificare e pubblicare, senza sovrascrivere arbitrariamente i record precedenti.

### Collaudi da eseguire
1. Validare `python -m scripts.publish_catalog_v2 --check` dopo generazione; controllare 2 opere, 5 teatri, 5 messe in scena, 19 repliche.
2. Ripetere generazione senza dati cambiati: nessun cambiamento di hash, nessun commit di pubblicazione.
3. Cambiare una data senza risolverne identità: il generatore deve interrompersi e preservare il feed precedente.
4. Verificare che il frontend prelevi manifesto e quattro canali via HTTPS direttamente da GitHub, senza SFTP; interrompere la rete e verificare avviso di fallback.
5. Un file JSON danneggiato o senza relazione canonica deve provocare fallback/errore esplicito, non un catalogo parziale.
6. Controllare la schedulazione, i permessi `contents:write` limitati al workflow e l'assenza di job di scansione non approvata.

## URL leggibili e pagine per messa in scena
La home offre **Per data** (ogni replica) e **Per messa in scena** (produzione in un teatro, con calendario delle repliche). I link sono generati da ID e slug canonici del feed, **mai dal titolo preso dalla query**. La pagina `/opere/<opera>/` aggrega tutte le messe in scena nazionali censite, con le date raggruppate per teatro; `/<citta>/<teatro>/` raccoglie le programmazioni del teatro; `/<citta>/<teatro>/<opera>/` mostra un'unica messa in scena, con tutte le sue repliche e orari noti/sconosciuti.

Le riscritture Apache sono in `site/.htaccess` e inviano soltanto i percorsi whitelist a `detail.html`, senza invocare un backend. Il tag `<base href="/atlas/">` rende CSS, JavaScript e fallback JSON raggiungibili anche dai percorsi annidati. Gli URL legacy `detail.html?type=work|venue|performance&key=...` continuano a essere risolti tramite il catalogo e canonizzati nel browser. Il vecchio identificatore `curated:...` viene trasportato in `legacy_id` accanto all'ID `oa-r-...` per la compatibilità.

**Nota di hosting:** per gli URL deep link serve un server Apache con `mod_rewrite` e `AllowOverride` abilitati. Il collaudo post-deploy deve richiedere direttamente le tre tipologie di URL, verificare 200 e contenuto HTML corretto, oltre al JSON GitHub via CORS; in caso contrario il publisher deve interrompersi/ripristinare i file.

### Test manuali
1. Dalla home selezionare **Per messa in scena**: 5 schede corrispondenti a 5 programmazioni, a fronte delle 19 repliche in modalità **Per data**.
2. Aprire `/atlas/opere/la-traviata/`: raggruppamenti per teatro, 11 recite al Teatro Regio.
3. Aprire `/atlas/torino/teatro-regio/`: La traviata, 11 repliche.
4. Aprire `/atlas/torino/teatro-regio/la-traviata/`: una sola scheda con undici giorni e orari, senza undici pagine distinte.
5. Aprire `/atlas/opere/italiana-in-algeri/`: quattro teatri e otto recite senza ora; nessun `00:00`.
6. Verificare i vecchi link parametrizzati, le richieste dirette e il refresh del browser su URL profondi, su desktop e smartphone.
7. Controllare che il deploy del frontend non sia rieseguito per le modifiche dei soli JSON.

## Freschezza dei dati e controllo giornaliero
Il catalogo mostra la data di verifica editoriale proveniente dal manifesto GitHub; è distinta dalla data di esecuzione del workflow. Il job quotidiano può leggere pagine soltanto quando il file `data/daily-source-config.json` segnala approvazione documentata. Un errore di robots o pagina incompleta non rimuove eventi e non pubblica dati fittizi. I risultati di scansione autorizzata sono registrati separatamente in `data/catalog-source-health.json` e non causano mai un deploy SFTP. Il dettaglio dei controlli e le regole di onboarding sono in [SOURCE_ONBOARDING](SOURCE_ONBOARDING.md).

## Arricchimento degli orari da più fonti ufficiali

La fonte aggregatrice OperaLombardia documenta **opera, teatro e data** ma non l'ora. Il registro `data/verified-time-evidence.json` conserva ulteriori prove ufficiali relative a **specifici ID di replica**. Il frontend mantiene il collegamento al circuito e mostra anche la fonte che prova l'ora; non crea una seconda recita. La regola di pubblicazione è: orari solo da evidenza esplicita collegata a produzione e data; altrimenti `starts_at: null` e «Orario da confermare».

Evidenze del 20 novembre 2026: Teatro Sociale di Como (13/11 20:00, 15/11 15:30), Teatro Fraschini di Pavia (20/11 20:00, 22/11 15:30), Comune di Cremona (Teatro Ponchielli 10/12 20:00, 12/12 16:00). Brescia 26 e 28 novembre rimane senza orario. Il catalogo resta a 19 repliche: **17 orari noti, 2 sconosciuti**. L'arricchimento avviene con JSON in `opera-atlas`, senza nuova pubblicazione SFTP per i dati; se occorre modificare il renderer web, solo quella modifica passa nel workflow SFTP nativo.

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


## Estensione del catalogo ufficiale — 20 novembre 2026
Sono state verificate 39 repliche su cinque schede di produzione ufficiali (nessun dato copiato salvo fatti di calendario):
- [Jenůfa](https://www.teatrolafenice.it/event/jenufa/) — Teatro La Fenice, Venezia: 12, 14, 16, 18, 20 marzo 2027 (5).
- [Madama Butterfly](https://www.teatrolafenice.it/event/madamabutterflycallegari/) — Teatro La Fenice, Venezia: 30 e 31 gennaio; 2, 3, 4, 5, 6, 7, 9 febbraio 2027 (9).
- [Carmen](https://www.teatrolafenice.it/event/carmenaxelrod/) — Teatro La Fenice, Venezia: 23, 24, 27, 28, 29, 30 aprile; 2 e 4 maggio 2027 (8).
- [Lucia di Lammermoor](https://www.teatromassimo.it/event/lucia-di-lammermoor-2/) — Teatro Massimo Palermo: 5, 6, 7, 9, 10, 11, 12, 13 marzo 2027 (8).
- [Tosca](https://www.teatromassimo.it/event/tosca-2/) — Teatro Massimo Palermo: 18, 20, 21, 22, 23, 24, 27, 28, 29 aprile 2027 (9).

Orari conformi alle fonti individuali e offset italiano calcolato con `Europe/Rome`. Le nuove rappresentazioni ricevono ID immutabili, con ID opera preesistenti riusati quando appropriato. Non vengono inventati teatri, biglietti, orari, cast o coordinate. **Totale del catalogo dopo la build: 170 recite, 22 opere, 29 messe in scena e 10 teatri**, con 2 orari ancora da confermare.

**Nota operativa:** le cinque pagine sono fonti editoriali manualmente verificate; non sono state automaticamente aggiunte a `daily-source-config.json`, poiché i parser Fenice e Massimo devono ancora essere sottoposti a test di estrazione e controllo robots in un job GitHub Actions. L'aggiunta di dati pubblici avviene solo via JSON GitHub, senza nuove pubblicazioni SFTP.


## Calendario OperaLombardia 2026/27 — copertura data/teatro
L'indice ufficiale https://www.operalombardia.it/calendario/ pubblica i giorni delle recite per cinque titoli della stagione, distinti per città e sede. Sono state aggiunte 38 repliche non ancora presenti: **Turandot** (Como, Cremona, Brescia, Novara, Bergamo); **Death in Venice** (Brescia, Como, Reggio Emilia, Cremona, Ravenna); **Cavalleria rusticana** e **Pagliacci** (ciascuno Como, Brescia, Cremona; le due opere dello stesso dittico mantengono schede opera distinte); **Un ballo in maschera** (Cremona, Como, Bergamo). Sono state conservate le recite già censite e gli ID attribuiti a Pavia e alle repliche de L'italiana in Algeri.

La pagina del circuito non espone l'ora delle singole rappresentazioni: le nuove 38 recite vengono pubblicate con `starts_at: null`, `time_known: false` e «Orario da confermare». Un orario futuro potrà essere aggiunto solo con prova ufficiale specifica, mantenendo l'ID. Gli spettacoli hanno pagine con URL descrittivo e riferimenti alla fonte. Totale del catalogo dopo la rigenerazione: **208 recite, 48 messe in scena, 22 opere, 14 teatri**, con 40 orari da confermare. L'acquisizione periodica non copre ancora l'indice generale: la completezza del *seed* 2026/27 non equivale a una copertura continua nel tempo.

## Controllo continuo dell'indice OperaLombardia
Un'unica scansione quotidiana del calendario ufficiale OperaLombardia controlla titoli, città, teatri e giorni (dopo robots.txt). Il parser suddivide Cavalleria e Pagliacci come due opere, senza indovinare orari. Gli ID restano invariati, e gli orari presenti su pagine partner non sono sovrascritti da un indice privo di ore. Eventi nuovi non riconosciuti, rimozioni, cambi formato o rinvii non causano aggiornamenti parziali: gli esiti e le anomalie sono registrati in `data/catalog-source-health.json`. Nessun nuovo deploy SFTP necessario.

## Esperienza visitatore e coproduzioni condivise (20/11/2026)

La UI usa di default la ricerca Torino/100 km/30 giorni e produce un elenco per produzione, vista calendario mensile e mappa schematica delle città. I chilometri sono distanze indicative fra centri città. L'utente può rifiutare la geolocalizzazione e scegliere manualmente una località. Opere, Teatri e Festival hanno directory e collegamenti propri.

Per evitare che una produzione condivisa su più teatri venga duplicata, il file pubblico `public/catalog/v2/production-groups.json` conserva un **ID di produzione condivisa** e gli ID delle messe in scena territoriali. Il client verifica che tutte le messe in scena dello stesso gruppo si riferiscano alla medesima opera, che gli ID siano noti e che non vi siano assegnazioni multiple. Nel catalogo si visualizza una sola scheda condivisa; la pagina `/produzioni/<id>/` aggrega le rappresentazioni per teatro, preservando i link specifici a ogni sede. Un errore di caricamento delle relazioni è segnalato e non inventa gruppi.

L'indice indipendente `public/catalog/v2/festival-index.json` collega esclusivamente festival e ID di staging verificati, mostrando in homepage solo quelli con date future. Le fonti monitorate senza programmazione verificata non sono annunciate come festival in arrivo. I due indici possono essere aggiornati nel repository `opera-atlas` senza deploy SFTP, mentre l'interfaccia richiede una pubblicazione isolata tramite il publisher nativo di `opera-atlas`.

Collaudi aggiuntivi: `python -m unittest discover -s tests -v`, sintassi JS, ricerca per raggio, opt-in geolocalizzazione, gruppi condivisi nella homepage e pagina gruppo, calendario, mappa, link delle singole sedi, festival senza date e modalità mobile. Il logo ufficiale binario e il collaudo visuale restano attività non eseguite in questo intervento.

### Scala e Arena: nuove schede 2026/27
**Fonti ufficiali consultate:**
- [Don Giovanni](https://www.teatroallascala.org/it/stagione/2026-2027/opera/don-giovanni.html) — 3, 6, 9, 11, 13, 18, 20, 23, 25 e 28 febbraio 2027; ultima recita ore 14:30, le altre ore 20:00.
- [La bohème, Puccini](https://www.teatroallascala.org/it/stagione/2026-2027/opera/la-boheme.html) — 16, 17, 19, 21, 24, 26 febbraio; 4 e 7 marzo 2027. Le due domeniche ore 14:30, le altre ore 20:00. Distinguere dall'opera omonima di Leoncavallo.
- [Nabucco](https://www.arena.it/arena-opera-festival/nabucco/) — 29 luglio ore 21:15, 5/15/21 agosto ore 21:00, 3/9 settembre ore 21:00. Il 27 agosto **non** è una recita attiva di Nabucco, perché è stata sostituita da Carmen.

Dati pubblicabili solo dopo validazione: **232 recite, 25 opere, 14 teatri, 51 messe in scena**. Gli orari già sconosciuti restano `null`; nessun testo editoriale o immagine di terzi viene copiato. URL canonici: `/milano/teatro-alla-scala/don-giovanni/`, `/milano/teatro-alla-scala/la-boheme/`, `/verona/arena-di-verona/nabucco/`. Nuovi record nel feed GitHub, senza deploy SFTP.

## Identità delle opere omonime — La bohème (21/11/2026)

Le due opere di Henri Murger sono composizioni **distinte** e non possono condividere l'URL, la sinossi, la storia o le immagini.

| Opera | ID canonico | Scheda opera | Allestimento 2026/27 |
|---|---|---|---|
| Ruggero Leoncavallo | `oa-w-000007` | `/atlas/opere/la-boheme-leoncavallo/` | Teatro Regio Torino, `/atlas/torino/teatro-regio/la-boheme/` |
| Giacomo Puccini | `oa-w-000024` | `/atlas/opere/la-boheme-puccini/` | Teatro alla Scala Milano, `/atlas/milano/teatro-alla-scala/la-boheme/` |

- La prima di Puccini ebbe luogo al Teatro Regio di Torino il **1 febbraio 1896**, su libretto di Luigi Illica e Giuseppe Giacosa; fonte: https://puccini.it/opera/la-boheme/.
- La prima di Leoncavallo ebbe luogo al Teatro La Fenice di Venezia il **6 maggio 1897**, su libretto dello stesso Leoncavallo; fonti: https://www.ruggeroleoncavallo-epistolario.ch/index.php/it/leoncavallo/prime-rappresentazioni e https://www.librettidopera.it/boheme_l/boheme_l.html.
- Il registro conserva lo slug normalizzato `la-boheme` per compatibilità nella risoluzione delle produzioni, ma assegna un `route_slug` pubblico diverso per opera. Il feed canonico e il client usano `work_id` per sinossi e storia; le immagini sono già associate ai due ID separati.
- Il generatore rifiuta in modo esplicito i duplicati di URL opera e la pubblicazione di contenuti editoriali ambigui per due opere omonime. Non vengono spostate o reidentificate le repliche originarie.
- **Collaudo**: verificare le due URL pubbliche, elenco opere (due voci), link dalla homepage e da ciascuna produzione, sinossi e storia specifiche, relativi manifesti, e assenza di repliche della Scala nella scheda Leoncavallo e viceversa. Le modifiche JavaScript richiedono una pubblicazione del frontend con il workflow SFTP di `opera-atlas`; gli aggiornamenti del catalogo JSON continuano senza FTP/SFTP.

## Denominazione pubblica del Teatro Regio di Torino — 21/11/2026

Il nome mostrato al pubblico per la sede di Torino è **Teatro Regio di Torino**, per distinguere chiaramente il teatro dal **Teatro Regio di Parma**. La correzione è un alias di presentazione nel registro delle sedi canoniche:

- ID immutabile `oa-v-000001`; chiave originale `Torino|Teatro Regio`; `name: Teatro Regio` conservato come identità sorgente.
- `display_name: Teatro Regio di Torino` esposto dal feed v2 e dal frontend; `site/theatre-profiles.json` allineato.
- URL esistenti invariati: `/atlas/torino/teatro-regio/` e `/atlas/torino/teatro-regio/<opera>/`. Nessuna modifica alle repliche o al titolo del Teatro Regio di Parma.
- Anche il fallback al catalogo locale `site/performances.json` presenta il nome esteso senza riscrivere le chiavi sorgenti o gli slug. Le ricerche e i dettagli mostrano il nome approvato.
- Collaudi: pagina teatro, elenco teatri, schede spettacolo, homepage e ricerca; verificare che i link profondi precedenti continuino a funzionare, che il profilo della sede venga caricato e che Parma resti distinto. La modifica al codice frontend richiede la consueta pubblicazione SFTP di `opera-atlas` e non tocca credenziali né workflow.

## Preflight di pubblicazione SFTP resiliente ai feed in rigenerazione (21/11/2026)

Il workflow `deploy-atlas.yml` deve consentire una pubblicazione manuale del solo frontend anche immediatamente dopo modifiche a nomi, opere o sedi: la generazione dei feed JSON pubblici avviene nel processo indipendente `refresh-catalog.yml`, potenzialmente ancora in corso. Il checkout della pubblicazione può quindi contenere temporaneamente un manifest content-addressed obsoleto, senza che questo indichi un difetto applicativo o un problema SFTP.

Per evitare falsi blocchi, il preflight del deploy genera **in locale** e senza rete i file derivati da `data/verified-launch-catalog.json` e `data/identity-registry.json` tramite `build_verified_catalog`, `publish_catalog_v2` e `publish_work_editorial`, quindi verifica la corrispondenza con `--check` e con la suite. Questa rigenerazione non committa, non fa push e **non trasferisce feed JSON dinamici via SFTP**. La pubblicazione dei dati continua esclusivamente nel workflow apposito. Non cambia secret, ID o URL canonici.

Collaudo: avviare `Publish Opera Atlas` su `main` con un feed v2 obsoleto rispetto al registro canonico; il preflight non deve fallire con `missing or changed content-addressed feed`. Il job prosegue all'upload SFTP e alla verifica HTTPS; i test devono ancora bloccare dati o URL realmente inconsistenti.

## Censimento nazionale autonomo dei teatri — 21/11/2026

La sezione **Teatri** non è più derivata esclusivamente dalle rappresentazioni. La fonte di verità editoriale per le sedi fisiche è `data/venue-directory.json`, pubblicata separatamente nel feed `public/catalog/venue-directory.json` attraverso `python -m scripts.publish_venue_directory`. All'adozione iniziale censisce **50 sedi in 16 regioni**, incluse tutte le 14 già presenti nel catalogo degli spettacoli e 36 nuove sedi con URL individuali, fonte, nome, città, regione, testo sintetico e stato di acquisizione.

Le sedi senza repliche mantengono una **scheda individuale navigabile** sul percorso stabile `/atlas/<citta>/<teatro>/`. Vi compaiono nome, città/regione, breve introduzione, collegamento alla fonte e indicazione esplicita che il programma non è ancora stato acquisito; non viene inventata alcuna rappresentazione né una biografia storica non verificata. Le 14 schede con storia documentata conservano la precedente presentazione storica e l'indirizzo. Le immagini sconosciute utilizzano la copertina editoriale di ripiego; in particolare il Teatro Filarmonico non eredita per errore la fotografia dell'Arena di Verona.

L'anagrafica delle **sedi** è distinta dal registro di **circuiti, festival e organizzatori** (`related_organizations` nello stesso file). OperaLombardia, il Circuito Lirico Piemontese, il Teatro dell'Opera Giocosa, Fondazione Haydn, Festival Verdi, Rossini Opera Festival, Festival Puccini, Festival della Valle d'Itria, Ravenna Festival, Monteverdi Festival, Macerata Opera Festival e Luglio Musicale Trapanese non diventano per errore edifici teatrali. Le loro sedi fisiche vengono censite separatamente quando documentate. Alcune sedi di spettacoli all'aperto sono stagionali e altre richiedono verifiche di continuità, esplicitamente distinte dal programma.

Gli ID `oa-v-*` delle 14 sedi già collegate agli spettacoli **non cambiano**. I nuovi record dell'anagrafica usano lo spazio riservato `oa-vd-*`, che non può entrare in collisione con l'assegnazione dei nuovi ID del catalogo delle recite. Il generatore blocca slug di percorso duplicati, fonti HTTP non sicure, campi incompleti e alterazioni degli ID canonici. Le future promozioni nel catalogo eventi dovranno ricondurre esplicitamente la sede alla sua identità esistente, non creare schede duplicate.

Il feed è aggiornabile via GitHub **senza nuovo deploy SFTP per ciascun teatro**. Il frontend richiede una sola pubblicazione SFTP per leggere l'anagrafica autonoma; il workflow di refresh comprende validazione, generazione e commit del feed `venue-directory.json` separatamente dai JSON delle recite.

### Comportamenti da collaudare

1. Pagina `directory.html?section=teatri`: 50 schede, ricerca per nome/città e sedi senza rappresentazioni visibili.
2. Pagine singole: Carlo Felice Genova, Alfieri Asti, Filarmonico Verona, Verdi Trieste, Teatro delle Muse Ancona, San Carlo Napoli, Petruzzelli Bari, Teatro Lirico Cagliari. Link a fonte e testo prudente sul calendario in acquisizione.
3. Collegamenti preesistenti `/atlas/torino/teatro-regio/`, `/atlas/milano/teatro-alla-scala/` e relative repliche invariati; Stabile Veneto e più teatri nello stesso comune non devono fondersi.
4. Controllo delle 13 entità non-sede: nessuna viene impropriamente mostrata come teatro.
5. Suite `python -m unittest discover -s tests -v`, `python -m scripts.publish_venue_directory --check`, verifica finale del deploy SFTP e lettura HTTPS del feed.

## Schede complete dei 50 teatri — 21/11/2026

Le 36 nuove schede vengono ora alimentate da profili editoriali in `site/theatre-profiles.json` con **indirizzo fisico**, **storia originale breve**, **link a fonte pubblica** e, dove disponibile con provenienza chiaramente riconoscibile, **fotografia della specifica sede**; lo stesso contenuto è incluso nell'anagrafica versionata `data/venue-directory.json` e nel feed pubblico `public/catalog/venue-directory.json`. Le 14 schede preesistenti mantengono storie e indirizzi. Per **49/50 sedi** il feed indica la fonte fotografica Commons; per l'ex sede temporanea Teatro Comunale Nouveau (chiusa a giugno 2026) non si attribuiscono immagini di altri edifici, e si mantiene un'illustrazione editoriale di ripiego sino a verifica di una fotografia legalmente riutilizzabile.

Il dettaglio pubblico rende foto del teatro con collegamento di attribuzione, breve storia e indirizzo con azione **Come arrivare** tramite OpenStreetMap. La selezione di immagini è per venue, non soltanto per città (es. Arena di Verona e Filarmonico). La pagina non usa più la stringa «La sede è censita. Il programma degli spettacoli non è ancora stato acquisito.» e non mostra intestazioni/sezioni vuote di programma per teatri senza recite. La directory non mostra avvisi di calendario non ancora acquisito. Il feed pubblico è rigenerato automaticamente; gli aggiornamenti del frontend richiedono un deploy SFTP, attivabile su push con variabile GitHub repository `ATLAS_DEPLOY_ENABLED=true`.

Collaudi: visitare nuove schede di Asti, Genova, Trieste, Firenze, Napoli, Bari e Cagliari, verificando immagine pertinente, storia, indirizzo e link mappa; verificare separazione dei due teatri di Verona e di Bologna; controllare il comportamento dell'ex Nouveau senza fotografia; confermare assenza di testi segnaposto; eseguire test Python e Node, publish-venue-directory --check, deploy e verifica HTTPS.

## Censimento Lecce, testi editoriali e stati calendario (21/11/2026)

- Aggiunte al registro nazionale le schede distinte del **Teatro Politeama Greco** (`oa-vd-000051`, via XXV Luglio 30) e del **Teatro Apollo** (`oa-vd-000052`, via Salvatore Trinchese 13/A), entrambe a Lecce, portando il totale a **52 sedi**. Storia e indirizzi provengono rispettivamente dai siti del Politeama Greco e dal portale cittadino Visit Lecce. La foto Commons dell'Apollo è `File:Teatro Apollo, Lecce.jpg` (Alfonso Piccarreta, CC BY-SA 4.0); per il Politeama Greco la verifica dei diritti su una fotografia pertinente non è ancora conclusa, quindi nessuna foto di altro teatro deve essere attribuita alla sede.
- Ripuliti gli incipit generici delle 36 schede precedentemente aggiunte: le **card descrivono peculiarità concrete** (architettura, storia o programmazione) anziché usare «è una sede teatrale censita a…». La pagina Teatri non mostra alcun avviso di acquisizione incompleta.
- Il campo `calendar_status` del feed è indipendente dalle date future e distingue `not_acquired` da `acquired`. La scheda teatro, se il calendario **non è stato acquisito** e non contiene rappresentazioni, mostra esclusivamente nel dettaglio «**Calendario non ancora acquisito · consulta il sito del teatro**», con link al sito ufficiale. Quando il calendario è stato acquisito ma non risultano spettacoli futuri mostra «**Non risultano prossimi spettacoli in programma.**». Se ci sono recite future mostra le date senza alcun avviso.
- I due teatri sono censiti separatamente in `data/venue-source-candidates.json` come candidati a futuri connettori (stato `pending`, `automated=false`), senza alterare le otto fonti primarie sincronizzate in `data/sources.json`: non si dichiara attivo un connettore finché non è stato verificato. Il Politeama possiede già un calendario lirico ufficiale 2026; il Comune di Lecce pubblica un cartellone congiunto Apollo/Paisiello 2026–27, ma eventi non operistici non vanno pubblicati come rappresentazioni liriche.
- Test e generatore impongono descrizioni non generiche e stato di acquisizione esplicito, conservando ID/slug delle 50 sedi esistenti. La pubblicazione delle modifiche al frontend segue il normale deploy SFTP su main, l'aggiornamento del feed resta nel repository.

Collaudi: elenco 52 teatri con ricerca per Lecce e card corrette; detail di Politeama e Apollo con storia, indirizzo e link alla mappa; avviso di acquisizione **solo nel dettaglio**; confronto tra teatro senza dati e teatro già monitorato ma senza eventi futuri; nessuna regressione sulle altre schede.

## Adozione automatica delle nuove sedi nelle rappresentazioni (21/11/2026)

Il workflow di refresh può acquisire nuove rappresentazioni verificate di un teatro già censito nell’anagrafica editoriale ma non ancora presente fra le sedi con recite (per esempio Teatro Carlo Felice di Genova). La sede ottiene a quel punto un nuovo ID tecnico `oa-v-*` nel catalogo degli spettacoli, mentre la sua pagina nazionale esiste già con un ID `oa-vd-*` e uno slug stabile. Il generatore nazionale riconcilia queste identità **automaticamente per percorso città/teatro verificato**: mantiene una sola scheda e l’URL invariato, associa `canonical_venue_id` nel feed e imposta `calendar_status=acquired`. La fonte editoriale `data/venue-directory.json` resta immutata, così non occorre alcun intervento manuale a posteriori.

Se un teatro completamente nuovo non ha ancora una scheda editoriale verificata, non si blocca la pubblicazione delle sue rappresentazioni ufficiali: continua a essere consultabile nel catalogo eventi senza creare automaticamente una storia, una foto o un indirizzo fittizi. Non è consentito unire due teatri omonimi soltanto per titolo: la riconciliazione usa anche città e slug, e blocca le associazioni conflittuali. Questo risolve l’errore nel refresh che fermava la pubblicazione dopo il passaggio da 14 a 15 sedi canoniche.

Test regressione: promuovere automaticamente Carlo Felice (ID canonico aggiuntivo) senza duplicare la scheda nazionale; verificare `calendar_status=acquired`, ID pubblico/URL stabili e feed generato riproducibile; nessun blocco del refresh per nuove sedi non ancora documentate.

## Test di regressione resistenti alla crescita autonoma del catalogo (21/11/2026)

I test del catalogo non devono considerare fissi **14 teatri** o **330 recite**: le fonti verificate possono aggiungere nuove sedi canoniche e nuove date senza PR manuali. Gli invarianti corretti sono: identificativi già assegnati immutabili, percorso pubblico della sede stabile, città e sede collegate alla produzione verificata, nessuna data/orario inventato, conteggi coerenti con la fonte di verità attuale. In particolare, `oa-vd-000016` per il Carlo Felice resta la stessa scheda editoriale dopo l’assegnazione dell’ID canonico `oa-v-000015` per le nuove recite.

La pagina di copertura delle **otto fonti primarie** non deve affermare di coprire le recite dei nuovi connettori nazionali: il relativo test confronta soltanto le recite provenienti dai domini primari autorizzati, lasciando separate le altre fonti. I test di acquisizione utilizzano date di prova non ancora presenti nel manifest, perché l’acquisizione idempotente deve ignorare le date già pubblicate. La ricerca geografica conosce anche il centro municipale indicativo di Genova e non inventa coordinate per nuove città sconosciute.

Collaudo: nuova recita già verificata al Teatro Carlo Felice, seconda acquisizione idempotente, nessuna collisione o ridenominazione nel catalogo dei 52 teatri, controlli dei domini primari invariati, test Python e release automatizzata del feed senza fallimenti per conteggi rigidi.

## Fotografia del Teatro Carlo Felice nella homepage (21/11/2026)

Le card «Scopri i teatri» della homepage nascono dalle rappresentazioni verificate: questi record non trasportano automaticamente `photo_file`. Dopo il primo rendering, il frontend carica l'anagrafica nazionale separata e associa il profilo fotografico tramite `city_slug/venue_slug` alla stessa identità usata per il link alla scheda. La card viene ridisegnata quando la fonte è disponibile: non si usa il nome della città come prova di identità fotografica.

Per evitare che il caricamento asincrono iniziale lasci visibile una copertina editoriale sul **Teatro Carlo Felice di Genova**, il client immagini conserva anche un riferimento statico specifico alla fotografia Commons [Genova - Teatro Carlo Felice.jpg](https://commons.wikimedia.org/wiki/File:Genova_-_Teatro_Carlo_Felice.jpg), autore Marek Śliwecki, licenza CC BY-SA 4.0; non è un fallback generico di Genova e non viene applicato ad altre sedi. Fonte/diritti restano nella scheda del teatro.

**Collaudi:** homepage «Scopri i teatri»: Carlo Felice deve avere l'immagine reale sia prima sia dopo il caricamento del feed nazionale; nessun'altra sede a Genova deve ereditare la sua foto; le schede e il dettaglio delle sedi continuano a usare foto pertinenti; verificare anche la connessione con il catalogo aggiornato e la visualizzazione durante un eventuale errore di rete.

## Selezione editoriale dei sei teatri della homepage (21/11/2026)

La sezione «Scopri i teatri» utilizza ora una **selezione esplicita di sei sedi**, senza dipendere dall'ordinamento alfabetico delle sedi con rappresentazioni. Le sei card, in ordine, sono: Teatro Regio di Torino, Arena di Verona, Teatro alla Scala, Teatro Carlo Felice, Teatro La Fenice di Venezia e Teatro di San Carlo di Napoli. La Fenice e il San Carlo **sostituiscono** rispettivamente Teatro Coccia di Novara e Teatro Dante Alighieri di Ravenna nella sola homepage; questi ultimi restano naturalmente nel catalogo nazionale e mantengono le loro schede.

I percorsi sono identificati da `city_slug/venue_slug`, non dal nome ambiguo. Le foto vengono ricavate dall'anagrafica nazionale dei teatri. La card del San Carlo deve essere visibile anche se nel catalogo delle rappresentazioni non sono ancora presenti sue recite: viene costruita dal profilo della sede, con URL e immagine pertinenti, senza inventare alcuno spettacolo. La selezione esatta delle sei sedi, i link e le fonti fotografiche sono soggetti a test automatico.

Collaudo: homepage con le sei card nell'ordine sopra, senza Coccia e Dante nella selezione; presenza di La Fenice (Venezia) e San Carlo (Napoli) con foto corretta, URL canonico e scheda di dettaglio raggiungibile; verifica che Coccia e Dante siano ancora presenti nella directory Teatri.


## Protezione delle immagini di sede (21/11/2026)

La selezione delle foto nella homepage e nelle schede del catalogo usa solo una fotografia associata esplicitamente alla singola sede (oppure una deroga nominativa verificata), mai un'immagine scelta in base alla sola città. In mancanza di un'immagine verificata, compare una copertina editoriale dichiarata come tale: evita di mostrare il Teatro Comunale storico come se fosse il Comunale Nouveau, o un altro teatro leccese al posto del Politeama Greco.

Per **Comunale Nouveau** e **Politeama Greco** esistono fotografie autentiche nelle fonti istituzionali e nelle gallerie ufficiali, ma il riuso delle immagini non è ancora autorizzato o documentato con licenza compatibile. Non si inseriscono URL di fotografie di terzi prima di averne attestato provenienza, licenza e attribuzione. Le anteprime non equivalgono a pubblicazione: le modifiche frontend vanno distribuite separatamente dal feed dati GitHub.


## Fotografia autentica del Politeama Greco (21/11/2026)

La scheda di Lecce ora riferisce una fotografia dell'interno del Teatro Politeama Greco pubblicata da Salento Sagre Eventi, con attribuzione espressa a **Regione Puglia / viaggiareinpuglia.it** e licenza dichiarata **CC BY 4.0** sulla pagina di provenienza. Il credito è conservato nei dati e nella scheda teatro. La fonte fotografica ripubblicata è https://salentosagreeventi.it/places/teatro-politeama-greco-lecce; la scheda originale della Regione è https://www.viaggiareinpuglia.it/at/teatro-politeama-greco. Le fotografie extra-Commons non si inferiscono dalla città, e richiedono URL HTTPS, provenienza, credito e licenza dichiarata.

Per il Comunale Nouveau di Bologna non è ancora stata identificata una fotografia della sede con licenza riutilizzabile verificabile. L'illustrazione di ripiego resta intenzionale per non attribuire la Sala Bibiena storica alla sede temporanea. Il deploy dei file statici resta distinto dall'aggiornamento del feed GitHub.
