# Teatro Filarmonico di Verona — stagione lirica 2027

Fonte ufficiale: https://www.arena.it/teatro-filarmonico-verona/spettacoli-prossima-stagione/

Cinque opere con quattro recite ciascuna sono annunciate dal Teatro
Filarmonico: Il ratto dal serraglio (Mozart), Alzira (Verdi), Fidelio
(Beethoven), Il signor Bruschino (Rossini), Cristoforo Colombo (Franchetti).
Si tratta di **20 recite identificabili**, ancora da acquisire e pubblicare
dal workflow live. Il balletto e i concerti non sono opere da catalogare.

La allowlist accetta soltanto cinque path della stagione 2027 sotto
`/teatro-filarmonico-verona/2027/`. Il parser di dettaglio richiede la
classificazione Opera, la sede Teatro Filarmonico, il credito Musica, quattro
date con orari puntuali e giorno della settimana compatibile con il 2027.
Gli orari si leggono nella sezione Prossimi spettacoli di ciascuna opera,
non dalle biografie dei cast o dal calendario dell'Arena di Verona.
Il titolo omonimo Il signor Bruschino può essere in cartellone presso
altri teatri: il confronto richiede URL, sede e compositore.

Il fetch passa obbligatoriamente dai controlli robots.txt.
Le candidate vengono lavorate solo dal catalogatore centrale; nessun
FTP né pubblicazione diretta del connettore. Una scansione verificata
non equivale a 20 recite pubblicate. Il passaggio alla stagione successiva
richiede nuova evidenza ufficiale e revisione della allowlist.

## Comportamenti da testare

- `python -m unittest tests.test_verona_filarmonico_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Nel primo refresh live verificare cinque URL, 20 recite in evidence,
  eventuali stati fail-closed, e quanti spettacoli sono realmente
  promossi nei JSON canonici; non confondere Arena e Filarmonico.
