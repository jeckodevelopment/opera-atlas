# Immagini di copertina per tre opere appena completate

Le nuove schede di *L'esule di Roma* (Donizetti), *I Capuleti e i Montecchi* (Bellini) e *Falstaff* (Verdi) vengono abbinate a documenti d'archivio effettivamente relativi alle composizioni, ospitati su Wikimedia Commons. Nessuna fotografia di scena moderna è utilizzata come illustrazione della scheda canonica.

- **L'esule di Roma:** frontespizio del libretto napoletano del 1828, conservato su Wikimedia Commons.
- **I Capuleti e i Montecchi:** frontespizio del libretto originale veneziano del 1830, Wikimedia Commons.
- **Falstaff:** manifesto di Adolfo Hohenstein per la produzione francese del Falstaff di Giuseppe Verdi (1894), Wikimedia Commons.

I crediti e le condizioni di riutilizzo sono conservati in `data/archival-work-images.json`. La pipeline di pubblicazione costruisce gli URL attraverso l'infrastruttura Wikimedia e preferisce queste immagini rispetto a miniature di produzione potenzialmente temporanee.

Questi materiali, insieme alle sinossi e alla storia esattamente attribuite nella PR #227, soddisfano il criterio di immagine storica verificata che blocca la promozione delle nuove opere quando non risulta un manifesto adatto.

## Verifiche automatiche

`python -m unittest discover -s tests -v`; test specifico in `tests/test_work_posters.py`. Dopo il workflow, verificare che le opere complete siano promosse con una copertina autentica, senza confondere opere omonime o attribuire un'immagine di produzione a una scheda canonica.
