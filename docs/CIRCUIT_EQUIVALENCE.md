# Identificazione automatica delle recite già presenti in un circuito

Una stessa rappresentazione può essere riportata dal circuito e dal teatro (es. OperaLombardia e Teatro Grande). Non sono due produzioni da pubblicare, né una candidata che debba richiedere revisione editoriale ogni volta.

Al termine dell'acquisizione, **prima della pubblicazione**, `scripts.reconcile_published_candidates` verifica la prova della seconda fonte: deve riferirsi a una produzione esistente e tutte le sue date devono avere un orario indipendentemente confermato tramite la **medesima URL ufficiale approvata**, presente nel registro `TIME_EVIDENCE_URLS` e validata da `validate_time_evidence`. Solo così la candidata viene marcata `already_catalogued`.

Se anche una sola data manca, una fonte cambia o gli orari sono discordanti, l'equivalenza non è presunta. Il lavoro di catalogazione del circuito, gli ID canonici e la URL del teatro rimangono tracciabili: non viene creata alcuna recita duplicata.

Caso di regressione: *L'italiana in Algeri* al Teatro Grande, il 26 e 28 novembre 2026, con due orari verificati indipendentemente. Il nuovo test assicura che rimuovere una delle due prove impedisca di riconciliare la candidata.

La logica resta trasversale: non si confrontano soltanto slug o titoli. Questa è una finalizzazione dello **stesso import**, non un audit periodico post-pubblicazione.
