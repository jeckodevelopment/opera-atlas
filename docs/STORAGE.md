# Fase 1: schema SQLite e sviluppo locale

## Stato
Implementazione del modello dati SQLite di base e suite unittest. Nessuna acquisizione automatica o dato di spettacolo è ancora pubblicato. Questo lavoro copre solo la parte di schema e validazione dell'issue #2.

## Avvio
Richiede Python 3.12+ con SQLite compilato con JSON1.

```sh
python -m unittest discover -s tests -v
python -c "from opera_atlas.db import connect, migrate; c=connect('atlas.sqlite3'); migrate(c); c.close()"
```

## Relazioni
- `works`, `work_aliases`, `organizations`, `venues`, `seasons`
- `productions`, `production_organizations`, `performances`
- `sources`, `observations`, `performance_sources`
- `schema_migrations`

## Invarianti e limitazioni attuali
- Le recite richiedono un timestamp con offset e si memorizzano in ora locale italiana con offset (ora legale inclusa). I timestamp senza timezone vengono rifiutati.
- Un duplicato con stessa produzione, sede e data/ora è idempotente; riconciliazione tra produzioni e fonti differenti non ancora realizzata (issue #3).
- Opera omonima o titolo normalizzato non identificano da soli un'unica opera; l'aliasing richiede revisione.
- Venue senza coordinate è legittima; un solo valore lat/lon non è ammesso.
- Database di lavorazione locale, nessun server pubblico esposto. Migratore baseline idempotente, migrazioni future da versionare.
- I dati demo rimangono soltanto nei test, mai nel catalogo pubblico.

## Test manuali
1. Eseguire comando unittest e controllare che ogni test termini OK.
2. Eseguire due volte la creazione database, verificando che la migrazione 1 resti unica.
3. Verificare rifiuto di timestamp naive e coordinate parziali.
4. Verificare che import ripetuto della stessa recita non incrementi il conteggio.
