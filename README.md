# Opera Atlas

Catalogo nazionale delle rappresentazioni di opera lirica in Italia e osservatorio statistico collegato al progetto culturale Opera+.

> Stato: fase 1 — schema SQLite, riconciliazione delle recite cross-source e test disponibili. Nessuna programmazione pubblicata finché le fonti e le recite non saranno state verificate.

## Obiettivi

- Catalogo di opere, produzioni, recite, teatri, festival e organizzatori, senza duplicati.
- Mappa interattiva dei luoghi e geolocalizzazione facoltativa.
- Raccolta automatica e tracciabile da fonti ufficiali, con controlli di qualità.
- Statistiche sul repertorio e sulla distribuzione geografica e temporale.

## Sviluppo locale

Richiede Python 3.12+ e SQLite con JSON1 (nessuna dipendenza Python esterna per lo storage).

```bash
python -m unittest discover -s tests -v
python -c "from opera_atlas.db import connect, migrate; c=connect('atlas.sqlite3'); migrate(c); c.close()"
```

Il file `atlas.sqlite3` è un artefatto locale di lavorazione, non un dataset pubblico di spettacoli. Vedi [schema, riconciliazione e limitazioni](docs/STORAGE.md), [piano 1.0.0](docs/PROJECT_PLAN.md) e [registro delle fonti](docs/SOURCE_REGISTRY.md).

## Processo

Tutte le modifiche funzionali tramite pull request con test, documentazione nella stessa PR e Semantic Versioning. Licenze e policy di raccolta dati, mappe e materiali di terze parti saranno verificate prima della pubblicazione.

## Registro sorgenti
I primi ingressi ufficiali verificati sono in [data/sources.json](data/sources.json). Per validarli e importarli nel database di lavorazione, dopo la migrazione:
```bash
python -c "from opera_atlas.db import connect,migrate; from opera_atlas.source_registry import seed_sources; c=connect('atlas.sqlite3'); migrate(c); print(seed_sources(c)); c.commit(); c.close()"
```
Le sorgenti sono inizialmente `pending`: nessuna scansione automatica è attivata da questa operazione.
