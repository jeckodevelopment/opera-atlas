# Diagnostica del ciclo di vita delle stagioni

Il feed `public/catalog/season-lifecycle.json` viene ricostruito da
`python -m scripts.season_lifecycle_health` durante la scansione autonoma
delle fonti (ogni tre ore) e il refresh completo del catalogo.

È un report **per indice configurato**, non un conteggio di teatri distinti.
Espone `source_key`, `strategy`, `rollover_implemented`,
`current_scan_status`, `next_season_status`, `next_season_url`,
`next_season_links`, date di verifica ed esito dell'ultimo rollover.
Le categorie sono `verified_rollover`, `evergreen_index` e
`legacy_year_bound`.

Il frontend diagnostico può utilizzare questo feed insieme al già esistente
`source-automation.json` per evidenziare le fonti a rischio di interruzione
dopo il 2026/27. Non mostrare `evergreen_index` come copertura futura
*verificata*: assenza dell'anno nell'URL non significa che il contenuto
includa il prossimo cartellone. `future_season_verified` è vero soltanto
quando l'ultima scansione ha verificato un indice futuro. Nessuna metrica
dell'indice attesta il numero di recite effettivamente pubblicate.

Le righe con `legacy_year_bound` richiedono una strategia di acquisizione
futura specifica. In particolare comunicati e singoli eventi del 2026/27
non possono essere rinominati 2027/28 per semplice sostituzione degli anni,
perché ciò creerebbe nuove produzioni fittizie. Vanno prima individuati
gli indici permanenti o i nuovi documenti ufficiali.

Il feed è pubblicato soltanto dalla pipeline già autorizzata e non abilita
alcuna scansione aggiuntiva. Per la correttezza del report:
`python -m unittest tests.test_season_lifecycle_health -v`.
