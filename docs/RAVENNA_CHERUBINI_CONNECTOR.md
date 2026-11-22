# Ravenna — Teatro Dante Alighieri, Opera 2027

Fonte primaria dell'orchestra che esegue le produzioni:
https://www.orchestracherubini.it/eventi/tpl/list/

Prima integrazione prudenziale con **due** schede esplicite per Ravenna:
- `/eventi/pagliacci-2/` — *Pagliacci* di Ruggero Leoncavallo:
  venerdì 15 gennaio 2027 alle 20:00 e domenica 17 gennaio alle 15:30.
- `/eventi/la-cenerentola-4/` — *La Cenerentola* di Gioachino Rossini:
  venerdì 2 aprile 2027 alle 20:00 e domenica 4 aprile alle 15:30.

La fonte è il sito ufficiale dell'Orchestra Giovanile Luigi Cherubini,
che figura come esecutrice nei due allestimenti del Teatro Alighieri.
Non è un calendario generico della città, né un sito di terze parti.

La stagione 2026/27 comprende anche *Death in Venice* e altri eventi,
ma non sono abilitati da questo adattatore: manca ancora una fonte
primaria con date/orari equivalenti per tali spettacoli. Le opere
della Trilogia d'autunno 2026 non sono assimilate alle quattro recite
2027. Il parser lega i due orari alla sezione `Date` della singola
scheda e verifica compositore, orchestra, categoria `Opera`, luogo
`Teatro Alighieri, Ravenna`, compatibilità del giorno e URL esatto.

Il catalogatore centrale gestisce il riconoscimento delle opere,
la deduplicazione delle produzioni e la pubblicazione delle recite.
Il connettore non pubblica direttamente né aggira robots.txt.
Le quattro recite restano candidate finché la scansione live e
la promozione canonica non le attestano.

## Comportamenti da testare

- `python -m unittest tests.test_ravenna_cherubini_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Nel refresh verificare 2 pagine, 4 date e il luogo Ravenna,
  senza importare Macbeth di Modena o concerti dal medesimo indice.
