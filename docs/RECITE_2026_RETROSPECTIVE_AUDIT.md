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

## Pipeline diagnostica indipendente

La workflow `.github/workflows/audit-recite-2026.yml` esegue i test e genera due file distinti:

- `public/diagnostics/atlas-recite-2026.json` (matrice sedi × mesi).
- `public/diagnostics/atlas-2026-sources.json` (fonti-indice candidate da verificare).

Ogni PR che modifica i file pertinenti esegue la sola generazione e carica un artefatto Actions, **senza modificare il repository**. Dopo il merge in `main`, l'esecuzione manuale o il job del lunedì pubblicano esclusivamente questi due JSON con una commit separata. Il job non effettua chiamate di rete a siti teatrali né pubblica recite; in caso di push non fast-forward interrompe senza forzare o fare rebase. Non sono garantiti i dati live finché la workflow non sarà stata eseguita con successo.

**Attenzione all'integrazione:** l'attuale workflow generale `refresh-catalog.yml` intercetta anche modifiche a `scripts/**`. Valutare separatamente il suo trigger prima di un merge, per evitare un refresh nazionale non necessario; non alterare la pipeline in questa PR. I JSON diagnostici non devono essere caricati dal frontend pubblico né trattati come un nuovo manifesto editoriale.

L'integrazione visiva nella dashboard di controllo va verificata dopo che i due feed risultano pubblicati. La sola presenza dei report non conferma alcuna copertura storica.

## Prima evidenza storica ufficiale recuperata

Il nuovo archivio `data/historical-2026-official-evidence.json` conserva **soltanto dati verificati** dalle pagine evento ufficiali, separato dal manifesto editoriale. Il primo caso è **La Cenerentola**, Teatro Regio di Torino (stagione 2025/26): 20, 21, 22, 23 gennaio alle 20:00; 24, 25 e 27 gennaio alle 15:00. La pagina ufficiale è:
https://www.teatroregio.torino.it/opera-e-balletto-2025-2026/la-cenerentola

La recita del 17 gennaio, esplicitamente qualificata come *Anteprima Giovani*, non viene inserita nel campione pubblico ordinario. L'archivio richiede `venue_id`, nome e città coerenti, HTTPS della fonte ufficiale, titolo, compositore, data e ora precise, e classificazione di pubblico generale. Errori di identità o fatti fuori periodo bloccano il report.

Il report mensile `atlas-recite-2026.json` espone `historical_official_candidates`, senza aggiungere alcuna recita al catalogo; lo stato rimane **lacuna candidata** e non costituisce automaticamente un requisito di pubblicazione. La certificazione dell'anno resta zero: la verifica di un singolo allestimento non dimostra il calendario completo di una sede.
