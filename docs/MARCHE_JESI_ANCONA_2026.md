# Connettori Marche – Jesi e Ancona, stagione lirica 2026

## Fonti ufficiali

- **Jesi**, Teatro Giovan Battista Pergolesi: [Fondazione Pergolesi Spontini, programma 2026](https://www.fondazionepergolesispontini.com/lirica/programma-stagione-lirica-2026/). Quattro programmi lirici principali: *Il trittico* di Giacomo Puccini (9 e 11 ottobre; anteprima giovani 7 ottobre esclusa), *Don Pasquale* di Gaetano Donizetti (30 e 31 ottobre; anteprima 28 ottobre esclusa), *L'esecuzione. Sotto lo sguardo di Tosca* di Salvatore Passantino (14 e 15 novembre; anteprima 12 novembre esclusa), *Nabucco* di Giuseppe Verdi (11 e 13 dicembre; anteprima 10 dicembre esclusa). Sono esclusi danza, Opera Lab Edu, concerti educativi e *Li finti filosofi* al Parco Colle Celeste di Maiolati, sede diversa.
- **Ancona**, Teatro delle Muse: [Fondazione Teatro delle Muse, stagione lirica 2026](https://www.fondazionemuse.org/stagione-lirica-2026/). *L'elisir d'amore* di Gaetano Donizetti (2 e 4 ottobre) e il programma misto *A Giacomo Leopardi / Cavalleria rusticana* di Pietro Mascagni (4 e 6 dicembre). Le anteprime giovani del 30 settembre e del 2 dicembre, così come gli incontri *Guida all'opera* al Ridotto, sono esclusi.

Tutte le date citate sono del **2026**; alle date e ore si affianca la verifica del giorno della settimana ufficialmente dichiarato dal produttore. Non vengono attribuite recite senza ora oppure in località differenti.

## Programmi composti, non duplicazioni

Il *Trittico* di Jesi è **un unico biglietto** per le tre opere (*Il tabarro*, *Suor Angelica*, *Gianni Schicchi*), tutte di Puccini. Il programma di Ancona è **un unico biglietto** contenente *A Giacomo Leopardi* (poema sinfonico con soprano, non opera autonoma da catalogare come tale) e *Cavalleria rusticana*. Il connettore passa componenti, autori, sede e orari alla **pipeline unica** `publish_programs.py`; non crea tre o due spettacoli distinti con lo stesso biglietto e la stessa ora.

Le sei source-key sono distinte pur condividendo due pagine ufficiali. Il classificatore considera l'identità dell'opera e, per i programmi composti, il loro `source_key`: pubblicare uno spettacolo non fa considerare già pubblicati gli altri.

Il rilevamento dipende sempre dal rispetto di `robots.txt` e dalla fonte ufficiale. Se un controllo robots fallisce, la fonte non viene acquisita e non si usa una copia non autorizzata. Le produzioni non entrano nel catalogo prima della riconciliazione e della verifica del programma, delle opere e delle recite.

## Test automatici

```sh
python -m unittest tests.test_marche_2026_sources -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

**Dopo il merge:** verificare il primo refresh in `data/season-index-health.json`, le sei candidate, i dettagli `data/candidate-detail-evidence.json`, gli eventuali programmi nella pubblicazione `public/catalog/programs.json` e l'inventario. Le fonti sono inizialmente `configured_not_operational`, non “recite pubblicate”.
