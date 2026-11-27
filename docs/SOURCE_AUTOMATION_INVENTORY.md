# Inventario verificabile dell'automazione delle fonti

L'indicatore `public/catalog/source-automation.json` associa ogni sede di
`data/venue-directory.json` ai connettori approvati e agli esiti correnti
di `data/catalog-source-health.json` e `data/season-index-health.json`.

Per una sede:
- `operational`: almeno un connettore approvato con ultima scansione riuscita;
- `configured_not_operational`: connettore approvato presente ma senza successo recente;
- `not_automated`: nessun connettore approvato associato esplicitamente.

Gli abbinamenti sono in `scripts/source_automation.py`. I teatri nella stessa
città non vengono fusi automaticamente. I circuiti e le sedi secondarie
vengono elencati esplicitamente; questa scelta evita falsi positivi.
L'indicatore non usa `calendar_status: acquired` della directory come
prova di automazione: è un dato editoriale sul calendario.

Un esito positivo dell'indice stagionale **non** dimostra l'acquisizione di
tutte le date, né l'avvenuta pubblicazione. La copertura delle recite
`pubblicate / individuate` è una metrica distinta.

## Perimetro e divario del censimento

Il registro storico `docs/SOURCE_REGISTRY.md` elenca 66 voci di sede e
territorio, anche multi-sede. La directory strutturata ne contiene 54.
I totali di automazione sono riferiti **solo alle 54 schede strutturate**:
non sottrarre automaticamente 54 da 66 per inventare dodici sedi precise
non catalogate, perché il registro storico include aggregazioni,
varianti editoriali e sedi temporanee. Occorre una riconciliazione esplicita
del registro storico in una fase distinta.

## Aggiornamenti e verifica

L'inventario viene rigenerato dai workflow del catalogo, e la dashboard
`/dev/atlas` legge il feed via GitHub Raw senza deploy dei dati via SFTP.

```sh
python -m scripts.source_automation
python -m scripts.source_automation --check
python -m unittest tests.test_source_automation -v
```

Aggiungere un connettore significa registrarne la fonte e l'associazione
esplicita alle sedi, implementare e testare parser, rispettare robots.txt,
registrare esiti in health e verificare pubblicazione canonica. La sola
inclusione in directory o il conteggio di un link non rende la sede operativa.

## Diagnostica dei connettori non operativi

Il feed espone `source_attention` per ogni sede: `none` (almeno una fonte
verificata), `not_checked` (fonti configurate mai controllate), `scan_failed`
(fonti configurate, ma nessuna verifica recente riuscita) oppure
`not_configured` (nessuna fonte approvata). Ogni fonte espone inoltre
`last_attempt_at` e `failure_reason` quando forniti dal job. Il motivo
`official_robots_unavailable_or_invalid` segnala un blocco **fail closed**:
non abilita automaticamente un URL alternativo né autorizza bypass di
robots.txt. Le date di ultima acquisizione e la copertura delle recite
restano metriche separate.

## Invarianti di test e ampliamento continuo

La completezza dell'insieme degli indici stagionali è verificata da
`tests/test_national_season_indexes.py` tramite l'insieme esplicito delle
source-key. I test dei singoli teatri verificano invece solo URL, mapping,
parser, date e sicurezza della fonte pertinente; non ripetono il numero
totale nazionale, che cambia legittimamente quando si integra una nuova sede.
Il test nazionale va aggiornato per ogni nuova source-key, preservando così
il controllo contro cancellazioni accidentali e duplicati, senza modificare
una dozzina di test indipendenti per ogni onboarding.

## Checkpoint anticipato per gli indici stagionali

Il refresh del catalogo deve effettuare una prima scansione delle fonti
stagionali **prima** della coda nazionale dei dettagli. Il job salva subito
`data/season-index-health.json`, le candidate URL e
`public/catalog/source-automation.json`: il feed diagnostico quindi non
rimane bloccato sul precedente successo se i passi di arricchimento
successivi risultano lenti. Le URL di discovery non pubblicano recite.

Il checkpoint usa il push non forzato di `scripts.safe_push_catalog`; se
`main` avanza durante l'acquisizione, viene richiesto automaticamente un
nuovo refresh anziché sovrascrivere dati più recenti. La seconda scansione
stagionale **dopo** il rollover rimane necessaria per le nuove edizioni
ufficialmente adottate. L'indicatore `operational` richiede una scansione
completata con successo; non certifica copertura delle recite né
pubblicazione sul sito.

## Refresh autonomo delle fonti ufficiali

Il workflow `.github/workflows/refresh-source-health.yml` esegue il
controllo degli indici stagionali in modo **indipendente** dal refresh
nazionale più lento: su richiesta manuale, ogni tre ore e quando vengono
modificati i connettori o la relativa configurazione. Usa un gruppo di
concorrenza proprio, così l'analisi di candidate e arricchimenti editoriali
non può impedire di osservare il tentativo di verifica delle fonti.

Controlla tutte le source-key configurate con i medesimi controlli
robots.txt e le allowlist del catalogatore. Pubblica esclusivamente
`data/season-index-health.json`, le URL di candidate in revisione e
`public/catalog/source-automation.json`, senza promuovere opere o recite.
I dati vengono condivisi su GitHub mediante `safe_push_catalog`, mai con
FTP, force push o sovrascritture di dati più recenti.

Se un altro job modifica `main`, il checkpoint viene differito senza
sovrascrivere i cambiamenti; la prossima scansione autonoma lo ricalcola.
`operational` richiede una scansione recente conclusa con successo,
non equivale a copertura esaustiva o pubblicazione di recite.


## Tolleranza operativa dei guasti temporanei

Un tentativo fallito non equivale a un disservizio persistente. I registri
dei connettori stagionali e giornalieri conservano `first_failure_at`,
`consecutive_failures` e `last_attempt_at`. L'allarme tecnico scatta
soltanto dopo almeno due esecuzioni distinte consecutive fallite, separate
da almeno 24 ore tra il primo e l'ultimo errore osservati. Il semplice
trascorrere del tempo senza una nuova esecuzione non genera un allarme.
Una scansione riuscita azzera la sequenza. I programmi futuri esplicitamente
non verificati e le revisioni editoriali non costituiscono guasti tecnici.

Il feed conserva gli esiti effettivi (`status`, `scan_classification`)
e aggiunge `failure_state`, `failure_hours`,
`requires_technical_attention` e i contatori delle anomalie temporanee e
persistenti. Una sede con una fonte alternativa riuscita rimane operativa;
gli errori della singola fonte restano consultabili. La dashboard utilizza
gli indicatori di persistenza per gli allarmi, mostrando gli errori recenti
come osservazioni non bloccanti. Nessun filtro modifica le regole di
verifica o di pubblicazione delle recite. Per i checkpoint precedenti
privi di storico si parte dall'ultimo errore effettivamente registrato,
non dall'ultima scansione riuscita.
