# Catalogo web iniziale — Fase 3

## Ambito consegnato
Il prototipo pubblico statico in `site/` carica `site/performances.json`, contratto `schema_version: 1` generato da `opera_atlas.ingestion.export_public_catalog`. Non sono richiesti server applicativi, servizi di geolocalizzazione o API terze.

Sono disponibili ricerca testuale (opera, compositore, teatro), filtri per città, regione, intervallo di date e orario noto/mancante, ordinamento cronologico, impaginazione di 12 recite e link HTTPS alle fonti ufficiali. I dati di origine sono resi con `textContent`, non con HTML dinamico, e i link sono limitati a HTTPS.

Una recita parziale con **titolo, data, teatro e città** ha una scheda normale con dicitura **Orario da confermare**; il valore `starts_at: null` non viene mai trasformato in mezzanotte. Le recite con ora mostrano l'orario locale già normalizzato dall'export.

L'interfaccia include etichette per i campi, regioni live per il conteggio risultati, focus visibile, link per saltare al contenuto e layout responsivo.

## Avvio locale e pubblicazione
La prima distribuzione non contiene recite dimostrative. Il file `site/performances.json` iniziale è volutamente `{"schema_version":1,"performances":[]}`.

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
