# Calendari del Maggio Fiorentino: fonti complete anche per nuove opere

Il calendario ufficiale fiorentino pubblica per ciascuna recita la data, l'ora, la sede, il titolo e il compositore. Il connettore precedente elaborava soltanto le opere già note al registro canonico e soltanto quelle nella Sala Grande del Teatro del Maggio, perdendo le produzioni al **Teatro Goldoni**.

La lettura viene ampliata a entrambe le sedi ufficiali. Per una composizione non ancora catalogata, il titolo deve essere già attestato dalla pagina ufficiale di dettaglio dell'esatto evento (H1, fonte e sede) e il calendario ufficiale deve mostrare immediatamente dopo quel titolo un credito personale unico, non un direttore o altro artista. In caso di ambiguità non si genera alcuna nuova identità.

La nuova evidenza integra i campi già acquisiti nel **medesimo import** quando l'unica informazione mancante è il compositore e **tutte** le altre informazioni coincidono, comprese data, ora e sede; le discrepanze di calendario restano errori di convalida. A seguire il motore unico risolve l'opera, la sinossi, la storia e la copertina prima della pubblicazione del catalogo. Non occorre riconciliazione post-importazione.

Caso di regressione: *Il mondo alla roversa o sia le donne che comandano*, di Baldassarre Galuppi, al Teatro Goldoni, con rappresentazioni fra gennaio e febbraio 2027. Il test verifica titolo, credito, sede, completamento di un evento in precedenza privo di compositore e rifiuto di un falso credito di direttore.

Comandi: `python -m unittest discover -s tests -v`; verificare nel successivo refresh `data/candidate-detail-evidence.json` e `data/candidate-reconciliation-health.json`.
