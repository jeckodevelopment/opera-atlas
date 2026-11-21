# Teatro Massimo Bellini di Catania — connettore ufficiale

**Fonte:** [Lirica e Balletto](https://www.teatromassimobellini.it/opere-e-balletto/). Il calendario ufficiale include opere, balletti e sedi diverse (Teatro Metropolitan, Sangiorgi). Il connettore conserva soltanto candidati `/eventi/<slug>/` del dominio ufficiale, e la successiva lettura con `robots.txt` verifica ogni dettaglio prima di estrarre fatti.

Nel dettaglio, l'automazione richiede:
- sede effettiva **Teatro Massimo Bellini**: non attribuire produzioni al Bellini quando sono programmate al Metropolitan o Sangiorgi;
- categoria ufficiale e intestazione univoca dell'opera, con compositore esplicito;
- singole recite datate con anno e orario nel programma (non il mero intervallo, né turni senza orario), controllo di duplicazioni/annullamenti;
- passaggio al catalogatore nazionale unico per identità, locandine, sinossi brevi e pubblicazione, senza SFTP dei dati.

**Esempio verificato sulla fonte ufficiale:** [Carmen](https://www.teatromassimobellini.it/eventi/carmen-2026/), con sette date dal 14 al 21 febbraio 2027; la pagina dettaglia ogni turno e il relativo orario. Il nome nell'URL conserva `2026` ma non determina l'anno: contano le date **2027** espressamente dichiarate nella pagina. Altre voci nel calendario includono balletto e produzioni presso altre sedi, che non devono essere inventariate come rappresentazioni al Teatro Massimo Bellini.

Dopo la PR l'inventario mostra Catania `configured_not_operational` fino alla prima scansione riuscita nel feed `data/season-index-health.json`. Anche il successo dell'indice non garantisce che tutte le recite risultino pubblicate.

Test:
```sh
python -m unittest tests.test_catania_source_connector -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```
