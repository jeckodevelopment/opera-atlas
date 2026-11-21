# Stato riconciliazione candidate — 21 novembre 2026

Questa nota distingue le candidate rilevate dagli indici dalle recite pubblicate. La coda del catalogo viene riconciliata dopo ciascuna esecuzione; le esclusioni sono verificabili e conservano il record di audit.

## Intervento

Due candidate Petruzzelli erano classificate `needs_review` benché i titoli ufficiali identifichino balletti: *Le lac des cygnes / Il lago dei cigni* (2026) e *Lo schiaccianoci* (2027). Sono escluse **solo mediante URL ufficiale esatto e source_key**, senza inferire che altri spettacoli della stessa fonte non siano opere. Il test di regressione protegge questa regola. Lo stato pubblicato della coda viene aggiornato dal consueto ciclo di riconciliazione, non alterando manualmente i dati derivati.

## Coda precedente all'intervento

- 133 candidate, 61 già catalogate, 41 escluse non operistiche, 31 in revisione.
- 5 delle 31 presentano `facts_found` in `candidate-detail-health.json`, ma questo non implica pubblicabilità. Tra queste vi sono l'opera nuova *L'esule di Roma*, *Il mondo alla roversa* senza attribuzione del compositore nella riga acquisita, il dittico *Cavalleria rusticana / Pagliacci* che richiede due identità, la duplicazione della *Italiana in Algeri* del circuito lombardo e *I Capuleti e i Montecchi* che richiede identità verificata.
- Altre 26 risultano `unavailable_or_unstructured`/`no_verified_showtimes` nel checkpoint del 21 novembre: occorrono parser della struttura ufficiale, attribuzione certa dell'opera e recite esplicite. Non è ammissibile sintetizzare date, orari o compositori a partire da slug.

## Risultato atteso dopo riconciliazione

A parità di altre evidenze: 61 già catalogate; 43 escluse non operistiche; **29 ancora da risolvere**. I numeri possono cambiare al prossimo refresh live. La riduzione della coda da sola non indica maggiore copertura pubblicata.

## Prossimo sviluppo necessario

Implementare e testare gli adapter per i casi `no_verified_showtimes` su base di HTML ufficiale accessibile e robots-gated; gestire i programmi misti come più opere collegate alla medesima recita senza attribuzioni fittizie; separare i duplicati tra fonte teatrale e circuito; costruire identificazione autorevole delle nuove opere. Tutti gli adapter devono confluire nel motore centralizzato e nella stessa pipeline di pubblicazione.
