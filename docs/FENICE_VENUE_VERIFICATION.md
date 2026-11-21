# Fenice: riconoscimento di sede e opere non ancora censite

Le pagine delle produzioni del Teatro La Fenice possono riguardare **Teatro La Fenice** oppure **Teatro Malibran**. Il nome della fondazione o il dominio ufficiale NON è una prova che la recita si svolga nel teatro principale.

Il parser usa la sezione primaria dell'evento: H1 ufficiale, compositore dichiarato immediatamente dopo il titolo e sede effettiva prima della scelta della data. L'identificazione dell'opera mediante Wikidata resta distinta e precede la pubblicazione. La sede viene verificata tramite una lista di luoghi autorizzati della fonte. Se in seguito viene trovata un'opera nuova verificata al Malibran, l'identità della sede viene creata automaticamente con regione Veneto, anziché attribuirla erroneamente al Teatro La Fenice.

Le rappresentazioni espressamente **riservate alle scuole** non devono comparire come eventi acquistabili dal pubblico; solo gli orari verificati non riservati confluiscono nel catalogo eventi. Le altre date restano verificabili dalla fonte.

## Verifiche
- `python -m unittest discover -s tests -v`.
- In fase di refresh, *Hänsel und Gretel* e *L'arca di Noè* devono acquisire compositore, date valide e sede Teatro Malibran, se la fonte ufficiale mantiene la struttura verificata.
- Le recite riservate alle scuole non vanno presentate tra le rappresentazioni aperte al pubblico.
- Qualsiasi fonte con titolo, compositore o sede assente/contraddittoria deve restare sospesa, senza inventare orari.

La correzione è compatibile con la pipeline centrale pre-pubblicazione; non sono previsti deploy FTP per i nuovi JSON.
