# Contratto pluriennale obbligatorio per ogni nuovo connettore

Ogni nuovo indice in `data/season-index-config.json` **deve** avere un record in `data/season-lifecycle-policy.json`, verificato da `tests/test_season_lifecycle_contract.py`. Non è più accettabile introdurre un connettore limitato per costruzione a 2026/27 (o qualunque stagione fissa) e rinviare il passaggio agli anni successivi.

## Strategie ammesse

- `evergreen_index`: pagina ufficiale indipendente dall'anno, con test che verificano che il sito esponga anche le produzioni della stagione successiva. Il successo HTTP non basta a dimostrare la completezza.
- `verified_rollover`: regola registrata in `scripts/rollover_season_indexes.py`, con test 2026/27 → 2027/28 → 2028/29, controllo sull'indice ufficiale e fallback all'ultimo valido.
- `legacy_year_bound`: **solo** per l'inventario storico cristallizzato il 22/11/2026. Non è una strategia ammessa per nuovi connettori.

I nuovi connettori richiedono `verification: test_verified` oppure `live_verified` e test specifici sulla loro strategia. La CI controlla la presenza della dichiarazione e impedisce nuove eccezioni storiche, ma un'etichetta da sola non certifica il comportamento: la PR deve allegare i test e i risultati delle scansioni reali.

## Requisiti per il collaudo e il merge

1. Scoperta di una nuova stagione senza modificare manualmente gli URL e senza presumere che il teatro mantenga il medesimo schema.
2. Sovrapposizione del monitoraggio di stagione corrente e successiva, senza perdita delle ultime recite, prima di dismettere l'indice precedente.
3. Nessuna cancellazione delle produzioni e delle recite storiche; riconciliazione canonica e deduplicazione.
4. Eventuale indice futuro verificato come pagina del teatro corretta, con contenuti operistici attendibili; conservazione del last-known-good in caso di errore.
5. Distinzione tra fonte operativa, copertura delle recite e capacità di scoperta pluriennale nella diagnostica.
6. Se la fonte è un PDF, un comunicato stampa o una scheda singola legata a una stagione, occorre aggiungere **anche** una strategia permanente per trovare il documento/calendario della stagione successiva.

Non segnare un connettore come `verified_rollover` se il codice non lo supporta. Le 24 fonti `legacy_year_bound` richiedono una migrazione separata nell'ambito dell'issue #447; le 24 `evergreen_index` richiedono comunque prova di copertura futura e non vanno interpretate come garanzia automatica.

Test: `python -m unittest tests.test_season_lifecycle_contract -v`.
