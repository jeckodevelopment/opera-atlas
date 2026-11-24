# Festival permanenti

## Modello approvato

Il festival è un'entità editoriale permanente identificata da `festival_id` (esposto come `id` nella directory). L'edizione è subordinata al festival, conserva il proprio ID e collega staging canonici già verificati. Le recite restano associate agli staging e alle sedi effettive; nessuna produzione o recita viene creata dall'aggregazione. Le fonti dei teatri e dei festival possono riferirsi allo stesso evento.

## Contratto dati

- `data/festival-identities.json`: anagrafica stabile revisionata, indipendente dall'anno.
- `public/catalog/v2/festival-index.json`: indice delle edizioni compatibile con connettori e audit esistenti.
- `public/catalog/v2/festival-directory.json`: una voce per festival, con edizioni e unione deduplicata degli ID staging. Include anche anagrafiche senza edizioni.
- Il publisher verifica riferimenti canonici, unicità delle identità e delle edizioni. Non altera i feed di opere, sedi, staging o recite.

## Migrazione frontend

La directory e la scheda devono usare l'identità permanente e un URL canonico senza anno. Gli URL delle edizioni precedenti devono continuare a risolvere verso il festival. La programmazione mostra solo produzioni con recite ancora in programma, utilizzando la stessa regola temporale dei teatri. Una scheda senza recite future rimane accessibile. Lo storico resta nei dati, disponibile per l'Osservatorio, senza duplicazioni statistiche.

Aggiornare routing, sitemap, metadati SEO e API di integrazione; verificare il comportamento delle vecchie URL e la continuità dei collegamenti con teatri e opere. Non rigenerare inutilmente i feed canonici.

Il frontend usa `festival-directory.json`. URL canonico: `/atlas/directory.html?section=festival&id=<festival-id>`. Gli ID delle edizioni sono risolti tramite `location.replace` (redirect client-side, non HTTP 301). La sitemap include tutte le identità permanenti, anche senza recite future.


## Continuità delle edizioni

| Festival | Strategia di acquisizione configurata |
| --- | --- |
| Donizetti Opera | Rollover verificato |
| Arena Opera Festival | Indice permanente |
| Rossini Opera Festival | Rollover verificato |
| Macerata Opera Festival | Rollover verificato |
| Festival Puccini | Rollover, parser per calendari futuri con repertorio riconosciuto e orario esplicito |
| Festival della Valle d'Itria | Rollover verificato |
| Luglio Musicale Trapanese | Rollover, associazione con anno della fonte coerente |
| Festival Verdi | Rollover e appartenenza verificata |
| Vicenza in Lirica | Homepage permanente, parser dinamico per il Teatro Olimpico |

Il riconoscimento delle edizioni future di Puccini e Trapani non dipende più dall'anno iniziale del registro. Il calendario Puccini 2027 mantiene i controlli storici, comprese le quarantene; per gli anni successivi il parser accetta variazioni nei titoli riconosciuti, nelle date e nell'orario comune esplicitamente pubblicato. Formati sconosciuti o composizioni ambigue restano soggetti a revisione. Per Vicenza il parser ordinario richiede ancora il Teatro Olimpico: altre sedi non sono automaticamente garantite. La configurazione e i test sintetici non costituiscono prova che una futura pagina non ancora annunciata sarà acquisita correttamente.
