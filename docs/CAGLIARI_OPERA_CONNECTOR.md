# Teatro Lirico di Cagliari — connettore candidato 2027

**Fonte ufficiale:** [Categoria Opera](https://www.liricocagliari.it/categoria-evento/opera/).
L'indice comprende più annate ed eventi di approfondimento; i collegamenti
`/evento/<slug>/` vengono trattati **soltanto come candidate**, mai come
prove automatiche di una rappresentazione.

Il connettore usa la normale pipeline `discover_season_indexes` →
`collect_candidate_details` → `auto_catalogue` →
`reconcile_published_candidates` → pubblicazione canonica JSON v2.

- Accesso HTTP: solo dominio esatto e verifica runtime di robots.txt,
  nessun redirect, challenge o restrizione aggirati.
- Esclusione delle voci *Parliamo d'opera*, non liriche.
- Titolo e compositore devono corrispondere ai titoli principali della
  pagina della produzione, non ai suggerimenti nel footer.
- Le rappresentazioni devono avere **giorno e ora espliciti** nel blocco `Date`, e l'anno 2027 deve provenire dalla data completa della scheda oppure da corrispondenza esatta con il pieghevole **ufficiale** 2027 del teatro.
- Il contenuto attuale di alcune pagine mostra `22/01` senza anno. Il file `data/cagliari-season-2027.json` registra **39 recite ordinarie** delle sette opere, con date, compositori e orari verificati sul pieghevole ufficiale 2027 di due pagine: https://www.liricocagliari.it/wp-content/uploads/2026/11/Pieghevole-Stagione-Opera-2027-21x15-4-ante.pdf. Il parser ammette queste date senza anno **solo** quando ogni data e ora della scheda coincidono con la fonte PDF. Scontri o calendari parziali bloccano la proposta, senza pubblicazione parziale.
- Non si contano come recite i cast alternativi, gli eventi suggeriti nel footer, gli esempi `24/06` duplicati presenti nel layout, né le matinée scolastiche `Opera NextGen` (escluse anche dal registro ordinario).

La configurazione è **approved** soltanto nel senso di tentativo
condizionato al controllo robots, non di certificazione di permessi del
teatro. La dashboard segnala inizialmente Cagliari come
`configured_not_operational`; soltanto un indice letto con successo
può portare `operational`. Questo stato non dimostra comunque che
tutte le recite siano già state pubblicate.

## Comandi di verifica

```sh
python -m unittest tests.test_cagliari_source_connector -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

**Verifiche dopo il merge:** leggere
`data/season-index-health.json` per `lirico-cagliari-opera-2027`,
controllare candidate prodotte e la coda di dettagli; verificare che
il numero di rappresentazioni realmente pubblicate su Opera Atlas
aumenti soltanto dopo la riconciliazione centrale. Gli aggiornamenti
del catalogo continuano via GitHub senza SFTP.

## Limite del cambio stagione

Il pieghevole 2027 è una prova **versionata e verificabile**, non un catalogo che si ricrea automaticamente per stagioni future. Il sistema continua a scoprire nuovi link, ma una nuova annata richiede un nuovo documento ufficiale o una pagina con date/anni completi. Non riciclare mai l'anno 2027 su nuove candidate di altre stagioni.
