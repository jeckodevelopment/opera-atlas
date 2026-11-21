# Parma: riconoscimento di nuove opere dalle fonti ufficiali

Il dettaglio del Teatro Regio di Parma espone l'opera nell'H1, il credito **Musica [compositore]** e le date della stagione nella stessa pagina. Il parser ora può produrre evidenze verificabili anche quando l'opera non è ancora registrata nel catalogo. I dati passano al motore unico di identità, ricerca autorevole, sinossi, storia, immagini, deduplicazione e pubblicazione.

Il parser usa soltanto l'host ufficiale e il percorso di spettacolo autorizzato; richiede il credito completo del compositore con un'etichetta artistica che ne delimita il nome e una sede ufficiale coerente. Il parser delle date verifica l'anno riportato nella pagina, date esplicite, orari e segnali di cancellazione. Non considera le prove Under30, le prove aperte e gli spettacoli indicati come riservati alle **Scuole** rappresentazioni pubbliche ordinarie.

Fonti-esempio: *Boris Godunov*, *La clemenza di Tito* e *Piccolo Orso e la montagna di ghiaccio*. Nessun titolo o compositore è dedotto dal solo slug.

## Collaudi
- `python -m unittest discover -s tests -v`.
- Verificare che l'acquisizione produca `facts_found` con la fonte ufficiale verificata e che non pubblichi orari di prove o turni scolastici.
- Verificare dopo il refresh l'esito delle candidate e la presenza di schede complete (non segnaposto) dove l'autorità e l'immagine sono disponibili.
