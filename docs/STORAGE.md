# Fase 1: schema SQLite e sviluppo locale

## Stato
Implementazione del modello dati SQLite di base e suite unittest. Nessuna acquisizione automatica o dato di spettacolo è ancora pubblicato. Include lo schema iniziale dell'issue #2 e la riconciliazione deterministica dell'issue #3; restano aperte connettori e risoluzione manuale dei conflitti.

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
- Un duplicato con stessa produzione, sede e data/ora è idempotente; riconciliazione cross-source deterministica disponibile: stesso ID opera canonica, sede e istante UTC; conflitti salvati in revisione, senza merge silenziosi.
- Opera omonima o titolo normalizzato non identificano da soli un'unica opera; l'aliasing richiede revisione.
- Venue senza coordinate è legittima; un solo valore lat/lon non è ammesso.
- Database di lavorazione locale, nessun server pubblico esposto. Migratore baseline idempotente, migrazione v2 separata versionata in `schema_v2.sql`.
- I dati demo rimangono soltanto nei test, mai nel catalogo pubblico.

## Test manuali
1. Eseguire comando unittest e controllare che ogni test termini OK.
2. Eseguire due volte la creazione database, verificando che la migrazione 1 resti unica.
3. Verificare rifiuto di timestamp naive e coordinate parziali.
4. Verificare che import ripetuto della stessa recita non incrementi il conteggio.

## API di riconciliazione
`opera_atlas.reconciliation.reconcile(conn, source_id=..., external_id=..., source_url=..., production_id=..., venue_id=..., starts_at=aware_datetime, payload={...})` restituisce `ReconcileResult(state, performance_id, review_id)`. La chiamata usa una connessione locale SQLite e il chiamante gestisce il commit; tutte le API di scrittura assumono un solo writer. Non usarla per dati pubblici finché non saranno verificati i mapping delle opere, le fonti e l'accessibilità dei calendari.

## Verifiche manuali aggiuntive
5. Importare la stessa opera/recita da due fonti con diverse produzioni e verificare una sola riga in `performances`, due in `performance_sources`.
6. Ripetere l'import con lo stesso external ID e verificare che i conteggi restino invariati.
7. Cambiare la data di un evento già conosciuto e verificare che compaia una voce in `reconciliation_reviews`, senza spostare la recita.
8. Introdurre due recite già presenti con identico titolo canonico/luogo/istante ma produzioni diverse; la terza fonte deve andare in revisione.
