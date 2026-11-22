# Messina — Teatro Vittorio Emanuele, stagione opera 2026/27

Fonte ufficiale: https://www.teatrovittorioemanuele.it/event_listing_type/opera-26-27/

Tre spettacoli nella categoria ufficiale Opera 26/27, tutti con URL e
blocchi Data/Orario precisi:
- Madama Butterfly di Giacomo Puccini: 26 febbraio 2027, 21:00 e 28 febbraio, 17:30.
- La traviata di Giuseppe Verdi: 16 aprile 2027, 21:00 e 18 aprile, 17:30.
- Al cavallino bianco di Ralph Benatzky: 7 e 8 maggio 2027, 21:00.
  Questo spettacolo e' un'operetta, distinta dalle due opere liriche.

Il parser approva soltanto tre URL HTTPS esatti, richiede compositore,
Sala Grande, categoria e due coppie data/ora complete in ogni scheda.
Non trasforma gli intervalli di calendario in recite e non importa
la prosa o gli spettacoli ospitati in sale diverse.

Il sistema nazionale mantiene il controllo di identita' d'opera,
deduplicazione, riconciliazione e pubblicazione. Le sei date
rimangono candidate finche' il refresh live non attesta
acquisizione e pubblicazione.

## Comportamenti da testare

- python -m unittest tests.test_messina_opera_source -v
- python -m unittest discover -s tests -v
- python -m scripts.source_automation --check
- Controllare tre URL ufficiali, sei showtime e la distinta operetta.
- Verificare sul refresh l'esito effettivo e i dati canonici pubblicati.
