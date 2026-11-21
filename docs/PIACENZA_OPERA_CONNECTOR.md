# Piacenza — connettore Opera 2026/27

Fonte primaria: [Fondazione Teatri Piacenza, stagione 26/27](https://teatripiacenza.it/stagioni/stagione-26-27/). La pagina distingue esplicitamente **Opera** (sei produzioni) da Concerti, Danza, Young, Rassegne e altri eventi. La scoperta automatica legge **solo la sezione Opera**, seguendo collegamenti ufficiali `https://teatripiacenza.it/event/<slug>/`, senza crawling ricorsivo.

Ogni acquisizione resta soggetta alla verifica di `robots.txt` sul dominio esatto, timeout, assenza di redirect non autorizzati e limiti dimensionali già previsti dal runner.

## Perimetro delle recite

- Il parser legge il titolo `h1`, il compositore accreditato dal teatro e le date **singole con anno e ora** prima della sezione `INTERPRETI`. Il successivo footer, con l'intera stagione e le schede di altri spettacoli, è escluso.
- Le giornate riservate alle scuole, prove aperte e anteprime speciali riservate a minorenni o studenti sono registrazioni **non ordinarie** e non diventano recite pubbliche.
- Esempio di fonte: [Siberia](https://teatripiacenza.it/event/siberia/). Il 14 dicembre 2026 è riservato alle scuole, il 16 dicembre è una speciale anteprima; le recite ordinarie verificabili sono **18 dicembre 2026 alle 20:00** e **20 dicembre 2026 alle 15:30**.
- Schede prive di date complete (o con dati di calendario incompatibili) non sono promosse con giorni o orari indovinati: rimangono disponibili nella coda dei candidati, preservando il catalogo pubblicato.
- Le opere omonime sono distinte nella **pipeline nazionale unica** usando compositore e autorità, mai soltanto l'identità dello slug.

La scheda del teatro e la diagnostica passano a **configurato, da verificare**; la classificazione «operativo» dipende dal primo esito di scansione riuscita. Questo stato non attesta ancora copertura integrale o recite pubblicate. Nessun deploy FTP per ogni aggiornamento del catalogo.

## Test

```sh
python -m unittest tests.test_piacenza_opera_source -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

Nel job `Refresh public Opera Atlas catalog` verificare `piacenza-opera-2026-27` in `data/season-index-health.json`, le candidate individuate in `data/season-index-candidates.json`, la lettura dei singoli dettagli e l'esito della riconciliazione, senza attribuire pubblicazione per il solo successo dell'indice.
