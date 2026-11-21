# Finalizzazione delle candidate prima della pubblicazione

## Contratto di importazione

Ogni fonte scopre URL ufficiali. Nello stesso refresh le evidenze vengono acquisite, verificate e associate a un'opera canonica oppure a un programma con più opere. Dopo aver generato i feed in memoria/su disco di lavoro e aver superato le verifiche, la coda delle candidate viene **finalizzata prima del push pubblico**. Non serve un secondo job di riconciliazione editoriale.

- **`already_catalogued`**: esiste una produzione canonica effettivamente presente nel manifest verificato **oppure** un programma ufficiale già generato in `public/catalog/programs.json` con URL eleggibile, almeno due componenti e almeno una recita. La sola presenza nella coda delle evidenze non basta.
- **`excluded_nonopera`**: esclusione deterministica per una fonte e un percorso già classificati.
- **`needs_review`**: nessuna produzione o programma pubblicato. Non viene inventata una data, un compositore, una sinossi o un'attribuzione.

La finalizzazione mantiene `id`, `first_seen` e `last_seen`, aggiorna insieme registri pubblico/interno e health, e precede il commit/push del catalogo. Il generatore dei programmi continua a ricalcolare e convalidare quelli con candidate `already_catalogued`: non devono sparire al refresh successivo o alternare continuamente stato.

## Test di regressione

`tests/test_same_run_candidate_reconciliation.py` verifica il passaggio atomico alla categoria catalogata e l'idempotenza. `tests/test_multi_work_publication.py` verifica che un programma già catalogato sia rigenerato identico. La suite generale si esegue con `python -m unittest discover -s tests -v`.

## Limiti e prossimi interventi

Questa modifica elimina una falsa coda di riconciliazione per i programmi verificati, **non** prova automaticamente la pubblicabilità delle altre candidate senza evidenze. Restano da migliorare i parser della fonte ufficiale per le produzioni prive di recite complete e la ricerca di nuove opere con breve sinossi, provenienza e manifesto storico verificato. Una fonte irraggiungibile deve comparire nella diagnostica senza impedire la pubblicazione delle altre.
