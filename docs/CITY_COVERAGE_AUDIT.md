# Verifica della copertura per città

Il job `Opera Atlas city coverage audit` produce ogni giorno un artefatto
JSON scaricabile dalle GitHub Actions. Il confronto usa la stessa finestra di
30 giorni per Torino, Milano, Roma, Genova, Bari e Palermo. È un audit in sola
lettura: non pubblica, modifica o elimina recite.

**Definizioni:** `published_recite_in_window` conta le recite canoniche
pubblicate nel manifesto v2, deduplicate per ID e non cancellate. La finestra
include entrambe le date. `official_production_links_seen` proviene dagli
esiti di scansione degli indici ufficiali: sono link a produzioni, **non recite**.
`official_total_recite` e `coverage_percent` rimangono `null` finché
un audit indipendente non abbia enumerato tutte le singole date ufficiali
della finestra e riconciliato sede, opera e recita. Nessuno zero nel catalogo
dimostra automaticamente l'assenza di programmazione del teatro.

`attention: high` significa soltanto che l'indice riporta link ma Atlas
non ha recite nella finestra; non significa che i link abbiano date in quella
finestra. Le anomalie del dettaglio sono riepilogate separatamente e non
attribuite a una città senza prova.

Per rigenerare:
```sh
python -m unittest tests.test_city_coverage_audit -v
python -m scripts.city_coverage_audit --start 2026-11-22 --days 30 --output city-coverage-audit.json
```

Priorità operativa: Roma, dove l'indice 2026/27 risultava accessibile e
l'acquisizione di date/identità era ancora incompleta al 21/11/2026.
Per ottenere percentuali reali bisogna estendere i connettori con un
inventario completo delle singole recite ufficiali per intervallo, non
confrontare i numeri con aggregatori terzi o trasformare i link in date.
