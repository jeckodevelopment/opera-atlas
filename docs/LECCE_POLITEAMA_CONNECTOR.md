# Lecce — Teatro Politeama Greco, stagione lirica 2026

Fonte ufficiale: https://www.politeamagreco.it/programmazione.asp

L'indice ufficiale pubblica schede individuali con parametri ASP.
Il connettore approva **solo** i tre URL esatti con query
`id=1147`, `id=1148`, `id=1149`: altri valori, query aggiuntive,
conferenze (`id=1150`), stagione composita (`id=1146`),
spettacoli di prosa e link esterni sono esclusi.

Programma verificato sulle pagine del teatro:
- *Turandot* di Giacomo Puccini: 13 novembre 2026 ore 20:45,
  15 novembre ore 18:00.
- *L'elisir d'amore* di Gaetano Donizetti: 27 novembre ore 20:45,
  29 novembre ore 18:00.
- *Nabucco* di Giuseppe Verdi: 11 dicembre ore 20:45,
  13 dicembre ore 18:00.

Il parser attribuisce le sei recite a singoli titoli e compositori
sulla base delle date e degli orari nella rispettiva scheda.
Non confonde il riepilogo del cartellone con un evento, né le
conferenze di introduzione alle opere con spettacoli.
Le due recite di Turandot sono già trascorse al momento
dell'integrazione e non vanno presentate come eventi futuri.

Tutti i fetch rispettano il controllo obbligatorio robots.txt
e i divieti di redirect. Le candidate passano dal catalogatore
nazionale prima della pubblicazione canonica. Nessuna pubblicazione
di recite è attestata fino alla scansione live e alla riconciliazione.

## Comportamenti da testare

- `python -m unittest tests.test_lecce_politeama_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Controllare tre candidate esatte, sei showtime attribuite,
  nessuna conferenza, prosa o URL di altra sede.
- Controllare separatamente quante recite sono pubblicate
  nel catalogo canonico dopo il refresh.
