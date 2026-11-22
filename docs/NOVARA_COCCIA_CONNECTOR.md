# Teatro Coccia di Novara — connettore lirico 2027

**Fonte ufficiale:** https://www.fondazioneteatrococcia.it/spettacoli.html

Per il primo rilascio sono abilitate tre schede ufficiali con attribuzione
compositore e orario di ciascuna recita verificabili senza inferenze:
- Rigoletto (Verdi): 29, 30, 31 gennaio e 2 febbraio 2027 (4 recite).
- Il barbiere di Siviglia (Rossini): 21, 22, 23 e 25 maggio 2027 (4 recite).
- Le nozze di Figaro (Mozart): 8, 9 e 10 ottobre 2027 (3 recite).

La sorgente contiene anche prosa, concerti, danza, didattica, eventi in foyer
e dittici: sono **esclusi** fino alla presenza di identificazione univoca dei
componenti e delle date. Nessuna opera è dedotta dal solo riepilogo.

Il parser richiede l'URL HTTPS esatto del titolo 2027, la dicitura
`Musica di` con compositore, un blocco circoscritto
`informazioni sull'evento` / `TEATRO COCCIA`, date e orari
completi e coerenza giorno della settimana. Le date di prima storica
e quelle nelle biografie del cast vengono ignorate. Tutti i fetch restano
soggetti a robots.txt e i risultati confluiscono nel catalogatore nazionale,
senza pubblicazione diretta di recite.

## Comportamenti da testare

- `python -m unittest tests.test_novara_coccia_source -v`
- `python -m unittest discover -s tests -v`
- Verificare nell'health `coccia-novara-opera-2027` (3 schede).
- Verificare nelle evidence ufficiali 11 recite con orario prima
  di contarle come pubblicate, escludendo balletti e concerti.
