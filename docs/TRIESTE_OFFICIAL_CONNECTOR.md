# Connettore ufficiale Teatro Verdi Trieste — stagione lirica 2026/27

Nuova fonte: `verdi-trieste-season-2026-27`.

- Calendario ufficiale filtrato per lirica: https://www.teatroverdi-trieste.com/it/calendario-spettacoli/?a=0&t=lirica
- Produzioni: URL ufficiali `https://www.teatroverdi-trieste.com/it/spettacoli/<slug>/`.
- Ambito: Teatro Lirico Giuseppe Verdi di Trieste, **non** altri teatri omonimi.
- Accesso: il runner esegue il controllo di `robots.txt` prima di ogni richiesta; fallisce in modo conservativo se non accessibile o contrario alla lettura. Non si aggirano protezioni, credenziali, challenge o restrizioni.
- Il parser registra titolo e compositore dalla pagina ufficiale, e **solo date con anno e ora espliciti** dalla sezione `Altre info`; i numeri di data nel cast non creano recite.
- Le date sono candidate fattuali e confluiscono nella **stessa** pipeline centrale di identità, ricerca editoriale, programmi, immagini, riconciliazione e pubblicazione usata dalle altre fonti.
- Nessuna percentuale di copertura completa viene attribuita automaticamente.
- Non modificare `opera.plus/atlas` o il publisher SFTP per i soli aggiornamenti JSON.

La pagina ufficiale del 21 novembre 2026 elencava almeno sette produzioni liriche per il 2026/27. Il dettaglio di *Lohengrin* presentava date/ore individuali, con un'ultima rappresentazione il 22 novembre 2026. Questi sono riferimenti per i test e non certificano un'esecuzione del nostro crawler.

## Collaudi automatici

```sh
python -m unittest tests.test_trieste_source_connector -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

**Collaudo operativo post-merge:** verificare nel job `Refresh public Opera Atlas catalog` che l'indice `verdi-trieste-season-2026-27` abbia esito `success`, link coerenti con il calendario e date estratte dai dettagli verificati. Soltanto dopo il successo l'inventario passerà Trieste da `configured_not_operational` a `operational`. Eventuali blocchi robots, cambi di HTML o mancanza di crediti ufficiali vanno trattati come sorgente non operativa e non come assenza di spettacoli.

La copertura del prossimo anno resta da gestire con un controllo di cambio stagione, non con URL inventati o rinnovi impliciti.
