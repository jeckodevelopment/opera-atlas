# Indicatore recite individuate / pubblicate

Feed: `public/catalog/recite-coverage.json`, rigenerato dai workflow di
pubblicazione del catalogo. La dashboard tecnica `diagnostics/index.html`
legge il feed da GitHub Raw, senza FTP per gli aggiornamenti dati.

**Pubblicate:** recite presenti nel manifesto editoriale approvato
(`data/verified-launch-catalog.json`), deduplicate per sede, giorno e ora.
**Individuate:** unione delle recite pubblicate e delle date/ore riconosciute
nei dettagli delle candidate ufficiali (`data/candidate-detail-evidence.json`).
Non confondere date delle recite, link a produzioni e titoli delle opere.

Lo stesso evento scoperto più volte conta una volta sola. Un dittico con
due opere allo stesso orario in un teatro conta una sola rappresentazione.
Un orario sconosciuto viene accoppiato a un'osservazione dello stesso giorno
solo quando non ci sono ambiguità. I luoghi omonimi non devono essere fusi:
le equivalenze di sede sono deliberate ed esplicite.

**Importante:** un rapporto come `73/73` significa che tutte le date *finora
rilevate nel nostro sistema* sono pubblicate, non che il teatro non abbia
altre rappresentazioni. Un 100% con zero osservazioni indipendenti si basa
soltanto sul catalogo già curato; il feed dichiara il numero di osservazioni
indipendenti, in modo da rendere riconoscibile questo limite. La copertura
assoluta richiede un censimento esaustivo dei calendari ufficiali.

Per rigenerare:
```sh
python -m scripts.recite_coverage
python -m scripts.recite_coverage --check
python -m unittest tests.test_recite_coverage -v
```

Il feed contiene per sede `published`, `found`, `missing`, `percent`,
`independent_observations` e `scope`. Le nuove date mancanti vanno
sottoposte alle normali regole di identificazione e promozione del catalogo,
mai pubblicate automaticamente soltanto perché compaiono in questo rapporto.
