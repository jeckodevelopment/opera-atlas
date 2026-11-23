# Audit retrospettivo delle recite 2026 — baseline non invasiva

Questo intervento avvia la verifica della copertura storica richiesta nella issue #178.
Non modifica connettori, dati pubblicati, riconciliazione o workflow.

## Esecuzione

```bash
python -m scripts.audit_recite_2026 --output /tmp/atlas-recite-2026.json
python -m unittest tests.test_audit_recite_2026 -v
```

Senza `--output` il report va su stdout, senza scrivere file.

## Significato dei dati

- Il perimetro è l'intera `data/venue-directory.json`, non solo le sedi con recite.
- Per ogni sede vengono generati dodici mesi del 2026.
- `published_known` conta date/orari presenti nel manifesto approvato e nei programmi composti.
- `independently_observed` conta osservazioni nelle pagine ufficiali di dettaglio già raccolte.
- `observed_not_published` indica lacune *candidate*: richiedono verifica su opera, sede e titolo prima di una promozione.
- `unassigned_evidence` contiene date con sede non risolvibile senza inferenze.
- `not_verified_complete` **non** significa che non esistano spettacoli o che il mese sia completo.
- `complete_seasons_certified=0`: non è stato verificato il denominatore completo di alcuna stagione.

**Limite importante:** questo report non interroga retroattivamente gli archivi ufficiali. Non misura la completezza storica effettiva del 2026, ma rende visibili le lacune già dimostrabili con le evidenze disponibili.

## Passi per certificare la copertura

1. Inventariare per ogni sede le pagine ufficiali di calendario gennaio–dicembre 2026, inclusi archivi e fonti storiche ufficiali, con URL e data della verifica.
2. Acquisire un denominatore per sede/mese delle recite operistiche aperte al pubblico generale, distinguendo annullamenti e date senza orario.
3. Confrontare titolo/opera canonica, sede, data, ora e fonte; non fondere sedi omonime, né contare due volte programmi composti o eventi promossi da più enti.
4. Solo in presenza di calendario ufficiale esaustivo certificare il mese, e poi l'anno. Altrimenti mantenere `non verificabile`.
5. Collegare gli esiti alla dashboard di governo, separatamente dal portale pubblico; promuovere le lacune confermate tramite l'attuale pipeline editoriale dopo revisione.

Nessun tasso annuale di copertura può essere ricavato dal rapporto pubblicate/individuate senza un denominatore ufficiale indipendente.

## Ricognizione automatica delle fonti già configurate

```bash
python -m scripts.audit_2026_sources --output /tmp/atlas-2026-sources.json
python -m unittest tests.test_audit_2026_sources -v
```

Lo strumento consulta soltanto `venue-directory.json`, `season-index-config.json` e `season-index-health.json` e produce candidati di fonte per sede con corrispondenza **esatta** del dominio ufficiale. Un successo di scansione non certifica il calendario 2026; corrispondenze condivise fra sedi non sono attribuzioni approvate. I domini non corrispondenti restano da esaminare e le fonti storiche non vengono inventate.

Lo scopo è preparare la verifica delle fonti ufficiali senza alterare il processo di acquisizione in produzione. I due report sono indipendenti e non sono ancora collegati alla dashboard pubblicata.
