# Primo connettore controllato — Teatro Regio Torino (Fase 2)

## Perché due livelli
Il calendario ufficiale `/calendario/opera` comprende **opera e balletto**, oltre a intervalli di programmazione che non corrispondono a singole recite. Le pagine di dettaglio delle produzioni espongono un calendario di recite con data, ora e fuso orario; il primo adapter accetta solo questi dettagli. Un intervallo (es. 27 febbraio–13 marzo) **non** genera recite.

## Stato e limiti
- Parser conservativo per snapshot HTML salvati localmente; recupero HTTP su singola pagina **solo** tramite comando esplicito con verifica robots, fonte già approvata, host HTTPS invariato, timeout e limite dimensioni. Nessuna scansione schedulata e nessuna copia di immagini/cast/testi descrittivi.
- Riconosce soltanto timestamp espliciti nel formato `YYYY-MM-DD HH:MM:SS Europe/Rome`; se il markup cambia, non genera eventi ipotetici.
- Validazione della fonte, ID canonici, venue Torino e stato `approved` prima di qualunque importazione.
- Gli snapshot di test sono **sintetici** e modellano i campi tecnici riscontrati nella pagina di dettaglio ufficiale. Non sono dati pubblicati.
- Non è stato verificato permesso di crawling in produzione: l'operatore deve controllare condizioni, robots e traffico prima di attivare fetch automatici. Il nuovo fetch opt-in fallisce se robots.txt è indisponibile o nega l'accesso; nessuna scansione periodica è introdotta.
- La mappatura delle singole produzioni/opere, la verifica degli orari effettivi sul markup HTML, gli annullamenti e l'acquisizione automatica sono ancora da fare.

## Comandi
```sh
python -m unittest discover -s tests -v
python -m opera_atlas.ingest_cli --db atlas.sqlite3 import-regio --html path/to/saved-detail.html --url https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata --source-id 1 --venue-id 1 --production-id 1 --title "La traviata" --composer "Giuseppe Verdi"
# Solo dopo verifica del risultato, ripetere aggiungendo --apply
python -m opera_atlas.ingest_cli --db atlas.sqlite3 export --output public/performances.json
```
Il comando senza `--apply` non persiste le recite. Gli ID di esempio sono **illustrativi**: devono esistere nel DB ed essere quelli verificati dall'operatore.

## Collaudi manuali
1. Verificare gli URL di dettaglio e che il sito ufficiale esponga effettivamente timestamp completi nel markup ottenuto.
2. Confrontare il totale delle recite estratte con la tabella ufficiale; nessuna data ricavata da un intervallo.
3. Ripetere importazione con `--apply`: conteggio invariato.
4. Disabilitare la fonte: import rifiutato e nessuna recita esportata.
5. Provare produzione/compositore non coerenti: import rifiutato.
6. Verificare il JSON pubblico e le sole informazioni fattuali, senza contenuti editoriali o fotografie.

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

## Importazioni multiple in una sola esecuzione (Fase 2)
Il modulo `opera_atlas.batch` introduce una pipeline limitata a 20 pagine di dettaglio, con mapping opera/compositore/produzione/venue/sorgente già verificati dall'operatore. Il manifesto segue il formato di `tests/fixtures/regio-manifest.json` (esempio *sintetico*: gli ID non sono dati pre-caricati e i timestamp delle fixture non sono dati di catalogo).

```sh
python -m unittest discover -s tests -v
python -m opera_atlas.batch_cli --db atlas.sqlite3 --manifest path/to/verified-productions.json --allow-network
# Dopo esame degli esiti, usare --apply soltanto su un database già popolato e verificato.
```

**Garanzie:** controllo di tutti gli ID e delle fonti approvate prima della prima richiesta; nessuna auto-discovery; una pagina per voce e nessun retry; validazione HTTPS e della path della stagione; rollback per singola pagina in caso di errore di import, con log `import_error`; report riepilogativo complessivo. Lo script non automatizza approvazioni, non esegue scansioni periodiche e per impostazione predefinita annulla la transazione. Una pagina senza date esplicite restituisce zero recite: il caso va verificato manualmente, non convertito in un calendario presunto.

### Collaudi del batch
1. Preparare un database con opere, produzioni, sedi e fonti approvate, usando ID reali e verificati.
2. Eseguire un manifesto di più pagine con `--allow-network` (senza `--apply`), previa conferma di policy e robots.
3. Controllare risultati aggregati e righe `source_checks` soltanto dopo importazione con `--apply`.
4. Ripetere lo stesso batch e confermare che il numero delle recite non aumenta.
5. Simulare errore di mapping su una sola produzione e verificare che le altre siano importate integralmente e l'errore sia isolato.
6. Confermare che un manifesto con ID sconosciuti o fonte non approvata sia rifiutato prima di qualsiasi HTTP.

**Limite esplicito:** il batch è un passo operativo, non ancora un crawler automatico per scoprire autonomamente opere e date dalle stagioni. Il sito deve permettere fetch nel contesto di esecuzione e il parser deve essere collaudato con HTML reale prima dell'uso in produzione.
