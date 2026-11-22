# Teatro Comunale Mario del Monaco — Treviso, stagione lirica 2026/27

Fonte primaria ufficiale:
https://risorse.teatrostabileveneto.it/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27

Il programma distingue:
- La traviata, Giuseppe Verdi: 21/23/25 ottobre 2026.
- Pagliacci, Ruggero Leoncavallo: 1/4/6 dicembre 2026.
- Il cappello di paglia di Firenze, Nino Rota: 3/5/7 marzo 2027.
- Il pipistrello, Johann Strauss: evento speciale 7 febbraio 2027,
  **senza orario esplicito su questa fonte**, pertanto non pubblicato.

La fonte precisa per la stagione: anteprima per scuole il mercoledì
(martedì per Pagliacci), turno A il venerdì alle 20:00 e turno C
la domenica alle 16:00. Il parser pubblica quindi **solo sei date
candidate con orario comprovabile dei turni pubblici**, escludendo
le tre anteprime scolastiche, i concerti e l'operetta senza orario.
Le recite 2026 già trascorse restano dati storici, non proposte future.

Il programma è un'unica pagina multi-opera, non tre URL indipendenti:
`discover_season_indexes.extract` verifica il contenuto e ritorna
l'URL ufficiale stesso; `collect_candidate_details` scompone
le sei candidate rispettando compositore e identità canonica.
Tutto resta soggetto a robots.txt. La verifica della fonte non prova
la pubblicazione delle recite, che spetta al catalogatore nazionale.

## Comportamenti da testare

- `python -m unittest tests.test_treviso_opera_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Dopo refresh controllare che le sei date siano presenti nelle
  evidence e che le anteprime scolastiche non siano pubblicate.
- Verificare il successivo aggiornamento stagionale senza inferire
  date od orari da fonti incomplete.
