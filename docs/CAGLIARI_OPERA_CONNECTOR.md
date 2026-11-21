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
- Le rappresentazioni devono avere **data, anno 2027 e ora espliciti**
  nel blocco `Date`. Non si assegna il 2027 soltanto perché compare
  nel menu globale delle stagioni.
- Il contenuto ufficiale attuale di alcune pagine mostra soltanto
  `22/01` senza l'anno nella lista delle date. Quelle candidate
  devono restare **non pubblicabili** dal parser HTML, invece di
  inventare il 2027. L'anno può essere corroborato dalla documentazione
  ufficiale della stagione, ma tale evidenza richiede una fase
  dedicata e verificabile prima di promuovere le recite.
- Non si contano come recite le date di altri spettacoli, dei cast
  alternativi o gli esempi duplicati presenti nel layout.

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
