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
- Database di lavorazione locale, nessun server pubblico esposto. Migratore baseline idempotente, migrazioni separate v2/v3 in `schema_v2.sql` e `schema_v3.sql`.
- I dati demo rimangono soltanto nei test, mai nel catalogo pubblico.

## Test manuali
1. Eseguire comando unittest e controllare che ogni test termini OK.
2. Eseguire due volte la creazione database, verificando che la migrazione 1 resti unica.
3. Verificare rifiuto di timestamp naive e coordinate parziali.
4. Verificare che import ripetuto della stessa recita non incrementi il conteggio.

## API di riconciliazione
`opera_atlas.reconciliation.reconcile(conn, source_id=..., external_id=..., source_url=..., production_id=..., venue_id=..., starts_at=aware_datetime, payload={...})` restituisce `ReconcileResult(state, performance_id, review_id)`. La chiamata usa una connessione locale SQLite e il chiamante gestisce il commit; tutte le API di scrittura assumono un solo writer. Non usarla per dati pubblici finché non saranno verificati i mapping delle opere, le fonti e l'accessibilità dei calendari.

## Risoluzione manuale dei conflitti
Il codice offre `opera_atlas.review.resolve_review(conn, review_id, action='link', selected_performance_id=...)` oppure `action='create'`. Il revisore deve controllare la fonte prima di chiamare la funzione; una recita già collegata non viene modificata automaticamente. La storia della review e delle osservazioni rimane disponibile. Il chiamante gestisce commit/rollback e single-writer.

## Verifiche manuali aggiuntive
5. Importare la stessa opera/recita da due fonti con diverse produzioni e verificare una sola riga in `performances`, due in `performance_sources`.
6. Ripetere l'import con lo stesso external ID e verificare che i conteggi restino invariati.
7. Cambiare la data di un evento già conosciuto e verificare che compaia una voce in `reconciliation_reviews`, senza spostare la recita.
8. Introdurre due recite già presenti con identico titolo canonico/luogo/istante ma produzioni diverse; la terza fonte deve andare in revisione.

9. Risolvere una review con la scelta esplicita della recita corretta; verificare stato resolved e provenance.
10. Risolvere un rinvio creando una nuova recita; verificare che l'evento storico resti censito e che la fonte punti al nuovo.

## Normalizzazione del repertorio
`opera_atlas.catalog.register_work` registra un titolo con compositore e genere espliciti. `register_alias` aggiunge esclusivamente alias confermati; `find_work(conn,title,composer=...,genre=...)` restituisce ID solo se univoco. Se il compositore manca non effettua match, se più opere corrispondono genera `AmbiguousWorkError`. L'inserimento di un'opera non certifica da solo un programma reale. I generi non operistici devono essere esclusi dai conteggi lirici, secondo la definizione statistica documentata.

### Collaudi aggiuntivi
11. Creare opera e alias e verificare il riconoscimento con case/spazi differenti.
12. Verificare che senza compositore il sistema non deduca l'opera da un titolo omonimo.
13. Verificare che due opere con medesimo titolo e compositore generino ambiguità anziché fusione automatica.
14. Registrare un concerto e verificare che il filtro `genre='opera'` non lo trovi.
