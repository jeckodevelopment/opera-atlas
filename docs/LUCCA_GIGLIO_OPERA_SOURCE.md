# Teatro del Giglio Giacomo Puccini (Lucca) — connettore Lirica 2026/27

Il [cartellone ufficiale della stagione lirica 2026/27](https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/lirica/stagione-2026-2027/) pubblica i singoli spettacoli e le recite con data **completa** e orario. Il parser acquisisce solo le pagine esatte nell'albero `/it/cartellone/lirica/stagione-2026-2027/<opera>/`, dopo controllo di `robots.txt` sull'host ufficiale, senza navigazione esterna o aggiramento di restrizioni.

Il calendario della stagione presenta quattro produzioni: *Il barbiere di Siviglia* (22 e 24 gennaio 2027), *Otello* (12 e 14 febbraio), *L'anno che verrà* (12 marzo) e *Aida* (21 marzo). Gli orari vengono estratti dai dettagli di ogni produzione; un titolo senza attribuzione ufficiale del compositore non viene pubblicato automaticamente.

### Regole

- Distinguere il **Teatro del Giglio Giacomo Puccini** (sede canonica di Lucca) da eventuali spettacoli al Teatro San Girolamo o da altre sedi presenti nel sito.
- Estrarre la sola sezione riferita alla produzione, dopo `MENU / TEATRO DEL GIGLIO`, ignorando le card globali “I prossimi spettacoli” e footer.
- Verificare esplicitamente `Lirica`, titolo della singola scheda, `Musica di <compositore>`, date, anno e orari.
- Bloccare date incomplete, duplicazioni, annullamenti e orari mancanti. Nessuna data derivata da finestre stagionali.
- Inviare l'evidenza alla pipeline nazionale unica di identificazione delle opere, completamento editoriale e pubblicazione; non esiste un catalogo Lucca parallelo.
- Il rinnovo della stagione 2027/28 richiederà un URL ufficiale verificato: non riutilizzare automaticamente un cartellone scaduto.

### Test da verificare dopo il merge

```sh
python -m unittest tests.test_lucca_opera_source -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

Il feed diagnostico mantiene inizialmente la sede `configured_not_operational`. Solo il refresh GitHub Actions può certificare il successo della scansione, che è distinto dalla pubblicazione delle singole recite.
