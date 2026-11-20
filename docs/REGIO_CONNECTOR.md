# Primo connettore offline — Teatro Regio Torino (Fase 2)

## Perché due livelli
Il calendario ufficiale `/calendario/opera` comprende **opera e balletto**, oltre a intervalli di programmazione che non corrispondono a singole recite. Le pagine di dettaglio delle produzioni espongono un calendario di recite con data, ora e fuso orario; il primo adapter accetta solo questi dettagli. Un intervallo (es. 27 febbraio–13 marzo) **non** genera recite.

## Stato e limiti
- Parser conservativo per snapshot HTML salvati localmente, senza HTTP, senza scansioni automatizzate e senza immagini/cast/testi descrittivi.
- Riconosce soltanto timestamp espliciti nel formato `YYYY-MM-DD HH:MM:SS Europe/Rome`; se il markup cambia, non genera eventi ipotetici.
- Validazione della fonte, ID canonici, venue Torino e stato `approved` prima di qualunque importazione.
- Gli snapshot di test sono **sintetici** e modellano i campi tecnici riscontrati nella pagina di dettaglio ufficiale. Non sono dati pubblicati.
- Non è stato verificato permesso di crawling in produzione: l'operatore deve controllare condizioni, robots e traffico prima di attivare fetch automatici. Nessun fetch automatico è introdotto.
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
