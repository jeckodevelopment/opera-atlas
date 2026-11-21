# Inventario verificabile dell'automazione delle fonti

L'indicatore `public/catalog/source-automation.json` associa ogni sede di
`data/venue-directory.json` ai connettori approvati e agli esiti correnti
di `data/catalog-source-health.json` e `data/season-index-health.json`.

Per una sede:
- `operational`: almeno un connettore approvato con ultima scansione riuscita;
- `configured_not_operational`: connettore approvato presente ma senza successo recente;
- `not_automated`: nessun connettore approvato associato esplicitamente.

Gli abbinamenti sono in `scripts/source_automation.py`. I teatri nella stessa
città non vengono fusi automaticamente. I circuiti e le sedi secondarie
vengono elencati esplicitamente; questa scelta evita falsi positivi.
L'indicatore non usa `calendar_status: acquired` della directory come
prova di automazione: è un dato editoriale sul calendario.

Un esito positivo dell'indice stagionale **non** dimostra l'acquisizione di
tutte le date, né l'avvenuta pubblicazione. La copertura delle recite
`pubblicate / individuate` è una metrica distinta.

## Perimetro e divario del censimento

Il registro storico `docs/SOURCE_REGISTRY.md` elenca 66 voci di sede e
territorio, anche multi-sede. La directory strutturata ne contiene 54.
I totali di automazione sono riferiti **solo alle 54 schede strutturate**:
non sottrarre automaticamente 54 da 66 per inventare dodici sedi precise
non catalogate, perché il registro storico include aggregazioni,
varianti editoriali e sedi temporanee. Occorre una riconciliazione esplicita
del registro storico in una fase distinta.

## Aggiornamenti e verifica

L'inventario viene rigenerato dai workflow del catalogo, e la dashboard
`/dev/atlas` legge il feed via GitHub Raw senza deploy dei dati via SFTP.

```sh
python -m scripts.source_automation
python -m scripts.source_automation --check
python -m unittest tests.test_source_automation -v
```

Aggiungere un connettore significa registrarne la fonte e l'associazione
esplicita alle sedi, implementare e testare parser, rispettare robots.txt,
registrare esiti in health e verificare pubblicazione canonica. La sola
inclusione in directory o il conteggio di un link non rende la sede operativa.

## Diagnostica dei connettori non operativi

Il feed espone `source_attention` per ogni sede: `none` (almeno una fonte
verificata), `not_checked` (fonti configurate mai controllate), `scan_failed`
(fonti configurate, ma nessuna verifica recente riuscita) oppure
`not_configured` (nessuna fonte approvata). Ogni fonte espone inoltre
`last_attempt_at` e `failure_reason` quando forniti dal job. Il motivo
`official_robots_unavailable_or_invalid` segnala un blocco **fail closed**:
non abilita automaticamente un URL alternativo né autorizza bypass di
robots.txt. Le date di ultima acquisizione e la copertura delle recite
restano metriche separate.
