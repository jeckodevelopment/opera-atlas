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

## Fonte istituzionale indipendente (22/11/2026)

Per non bloccare la raccolta quando il sito ASP del teatro restituisce HTML
non disponibile al runner, è stato aggiunto il connettore
`lecce-provincia-politeama-2026` sulla [comunicazione ufficiale della Provincia di Lecce](https://www.provincia.le.it/https-www-provincia-le-it-al-via-la-51-stagione-lirica-della-provincia-di-lecce-lunedi-9-novembre-la-conferenza-stampa-di-presentazione-del-cartellone-2026/).
La Provincia è l'ente promotore della stagione 2026 e pubblica i tre titoli,
i compositori e tutte le sei date. La pagina viene acquisita con il normale
robots gate e con URL HTTPS esatto, senza proxy, redirect alternativi o bypass.
Il parser verifica unicamente il blocco della stagione e ignora conferenze,
prove per le scuole e l'opera separata al Teatro Apollo. Il vecchio connettore
del teatro rimane indipendente e diagnostica i propri fallimenti; la sede è
operativa quando almeno una delle due fonti supera una scansione live.
L'esito dell'indice non certifica da solo la pubblicazione delle recite.
