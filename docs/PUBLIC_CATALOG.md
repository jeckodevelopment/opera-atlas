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
