# Livorno — stagione lirica 2026/27 del Teatro Goldoni

**Fonte ufficiale:** [Fondazione Teatro Goldoni, programma lirico 2026/27](https://www.goldoniteatro.it/notizie/la-stagione-lirica/). L'articolo elenca quattro titoli della stagione lirica, di cui *Cavalleria rusticana* viene rappresentata in **Piazza Goldoni** e non all'interno del Teatro Goldoni. Il programma **Opera Oggi** indica invece la sede **Goldonetta**, e non può essere attribuito al teatro principale.

Sono quindi monitorati come recite del **Teatro Goldoni** i tre titoli con date esatte:

| Opera | Compositore | Recite pubblicate dalla fonte |
| --- | --- | --- |
| Dido and Aeneas | Henry Purcell | 6 novembre 2026 20:00; 8 novembre 2026 16:00 |
| Otello | Giuseppe Verdi | 29 gennaio 2027 20:00; 31 gennaio 2027 16:00 |
| L'elisir d'amore | Gaetano Donizetti | 16 aprile 2027 20:00; 18 aprile 2027 16:00 |

La fonte ufficiale indica mese/giorno/ora e giorni della settimana, ma non l'anno accanto a ogni recita. L'anno può essere assegnato soltanto se coerente con **la stagione 2026/27 e il giorno della settimana**. In caso di divergenze il parser interrompe l'acquisizione e non pubblica date inventate.

## Riconciliazione

Le tre produzioni sono tre identità distinte nella **stessa pagina**. Ciascuna ha una source-key dedicata, ma il fetch HTML è soggetto all'ordinario controllo `robots.txt` e alle limitazioni di origine. L'estrattore controlla i titoli ufficiali e le attribuzioni del compositore dopo il titolo; evita che un titolo diventi una produzione già catalogata solo perché condivide l'URL con un'altra opera.

L'integrazione utilizza il catalogatore centralizzato: confronta opera, compositore, sede, data e orario, senza creare un catalogo locale. Non duplica produzioni provenienti da coproduzioni di altri teatri e non richiede nuovi deploy FTP.

La diagnostica distingue **configurata** da **operativa**, che sarà confermata solo dall'esito reale del refresh. Le sei recite del programma sono evidenza ufficiale, non prova che siano già pubblicate su Opera Atlas.

### Test

```sh
python -m unittest tests.test_livorno_opera_source -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

Verificare dopo il merge le tre source-key `goldoni-livorno-*` in `data/season-index-health.json`, la coda candidate e i singoli esiti di promozione.
