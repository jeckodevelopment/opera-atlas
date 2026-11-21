# Nuove opere: materiali verificati prima della pubblicazione

Le candidate *Die Zauberflöte* di Wolfgang Amadeus Mozart (Q5064), *Hänsel und Gretel* di Engelbert Humperdinck (Q1099668), *Ernani* di Giuseppe Verdi (Q211279) dispongono di recite con orario e compositore verificati dai teatri, sinossi brevi e storia dell'opera già presenti nel catalogo editoriale.

Per renderle pubblicabili in un'unica transazione, il registro `verified-work-editorial-attribution.json` lega i testi al compositore e al QID **esatti**, mentre il registro `archival-work-images.json` aggiunge tre file Wikimedia Commons controllati:

- *Die Zauberflöte*: programma della prima di Vienna, 1791, `Zauberflöte-Theaterzettel1791.jpg` (pubblico dominio).
- *Hänsel und Gretel*: manifesto del Federal Theatre Project americano, 1936–1941, `Hansel and Gretel by Engelbert Humperdinck (theatre adaptation).jpg` (pubblico dominio negli Stati Uniti).
- *Ernani*: manifesto originale del Teatro Sociale di Trento del 1857 comprendente *Ernani*, `Verdi - Ernani + Giovanni Battista Ferrari - Ultimi giorni di Suli - Trento Teatro sociale per la fiera di s. Vigilio primavera 1857.jpg` (documento storico).

Le immagini non devono essere presentate come fotografia dell'allestimento corrente. Il generatore già richiede la concordanza fra fonte ufficiale, compositore, titolo e QID prima di usare i contenuti; il file Commons non sostituisce nessuna di queste verifiche.

Il test in `tests/test_new_opera_autopromotion.py` controlla che i tre record del cache siano pronti per la promozione con sinossi e storia. La pubblicazione resta subordinata a controllo automatico del catalogo e validazione del feed.
