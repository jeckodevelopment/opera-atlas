# Teatro Verdi di Padova — Stagione lirica 2026

Fonte ufficiale comunale:
https://padovacultura.padovanet.it/it/attivita-culturali/stagione-lirica-di-padova-2026

La pagina riporta:
- Pagliacci di Ruggero Leoncavallo — 20 novembre 2026, 20:45;
  22 novembre 2026, 16:00.
- La traviata di Giuseppe Verdi — 28 e 29 dicembre 2026, 20:45;
  31 dicembre 2026, 21:00.

Il parser applica controlli fail-closed sul programma delimitato,
compositore, sede, anno e cinque date/orari esatti. Esclude il
Concerto di Capodanno del 1 gennaio 2027 e la Cavalleria rusticana
estiva in Piazza Eremitani, che non si è svolta al Teatro Verdi.
La prima data dei Pagliacci è già trascorsa alla data di
integrazione e non va proposta come spettacolo futuro.

La fonte è una singola pagina multi-opera: il primo passaggio di
scoperta registra l'URL dopo verifica del programma, mentre la
pipeline dei dettagli estrae le cinque candidate con le rispettive
identità canoniche. Robots.txt resta obbligatorio. L'inclusione
nel registro e il superamento dei test non attestano né l'esito
della scansione live né l'effettiva pubblicazione delle recite.

## Comportamenti da testare

- `python -m unittest tests.test_padova_opera_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Al primo refresh verificare la classificazione delle cinque recite,
  l'esclusione del concerto e della rappresentazione in altra sede.
- Verificare separatamente le recite effettivamente pubblicate.
