# Opera+ Atlas — registro di riconciliazione requisiti 1.0.0

> Audit del backlog: 23 novembre 2026. Documento di gestione, non certificazione di completamento. Roadmap: [PROJECT_PLAN.md](PROJECT_PLAN.md). I dati operativi correnti si leggono dai feed pubblicati e dai workflow, non dagli snapshot contenuti nelle issue.

## Criteri di classificazione

- **Implementazione esistente, non verificata:** una funzione, un parser o una pagina è presente, ma i test/casi di accettazione dell'issue non sono tutti attestati. Non chiudere come `completed`.
- **Da completare:** resta almeno un criterio oggettivamente non soddisfatto.
- **Da verificare per chiusura:** il comportamento risulta costruito; servono verifica test/integrità e link a evidenze prima di chiudere.
- **Tracker aggregato:** issue che coordina sottosistemi e anomalie, da mantenere senza duplicarne il lavoro in issue pilota.
- **Duplicato amministrativo:** possibile chiusura `duplicate` soltanto dopo aver copiato i requisiti residui nel tracker vivo. Non significa funzionalità completata.

## Backlog aperto verificato

| Issue | Fase | Ruolo/stato di audit | Verifica / passo necessario |
| --- | --- | --- | --- |
| [#1](https://github.com/jeckodevelopment/opera-atlas/issues/1) | F1 | Da completare | Censimento e policy fonte/venue/festival per l'intera rete, con timestamp e casi controversi. Coordinare i dati con #178 e #679. |
| [#2](https://github.com/jeckodevelopment/opera-atlas/issues/2) | F1 | Da verificare per chiusura | Schema, migrazioni, vincoli, timezone, source provenance, fixture e test integrità; confronto entità richieste con modello realmente implementato. |
| [#3](https://github.com/jeckodevelopment/opera-atlas/issues/3) | F1 | Da verificare per chiusura | Alias e compositori, stessa recita da fonti differenti, omonimie, venue omonime, variazioni di giorno/ora, programmi composti e coproduzioni. |
| [#4](https://github.com/jeckodevelopment/opera-atlas/issues/4) | F2 | Storica; da verificare per chiusura | Accettazione specifica del primo adapter su fonte verificata, confronto live e idempotenza. Non costituisce priorità di sviluppo del singolo teatro. |
| [#5](https://github.com/jeckodevelopment/opera-atlas/issues/5) | F2 | Storica; da verificare per chiusura | Tour/circuito OperaLombardia, ROF, sedi/edizioni e deduplicazione cross-source; coordinare copertura con #178 e festival con #730. |
| [#6](https://github.com/jeckodevelopment/opera-atlas/issues/6) | F2 | Da verificare / completare | Refresh schedulato, retry, audit, last-known-good, annullamenti, rinvii, guasto di fonte, assenza cancellazioni silenziose; prove end-to-end. |
| [#7](https://github.com/jeckodevelopment/opera-atlas/issues/7) | F3 | Da verificare per chiusura | UX responsive, filtri, dettaglio, URL, fonti/biglietti, tastiera e dati incompleti, prove browser. |
| [#8](https://github.com/jeckodevelopment/opera-atlas/issues/8) | F3 | Da completare | Mappa Leaflet/OSM per coordinate verificate delle venue, marker cluster, filtri, geolocalizzazione opt-in e attribution. Una mappa schematica non basta. |
| [#9](https://github.com/jeckodevelopment/opera-atlas/issues/9) | F4 | Da completare | Osservatorio statistico pubblico: definizioni e denominatori, classifiche, opere rare, filtri, aggregati esportabili e test. |
| [#10](https://github.com/jeckodevelopment/opera-atlas/issues/10) | F4 | Da verificare / completare | Test, release SemVer, quality gates, diritti/licenze, rollback, deployment e collaudi/documentazione. |
| [#178](https://github.com/jeckodevelopment/opera-atlas/issues/178) | F2 | Tracker nazionale | Copertura effettiva per tutte le sedi e stagioni, continuità pluriennale. Include il sottoinsieme storico delle otto fonti di #53. |
| [#679](https://github.com/jeckodevelopment/opera-atlas/issues/679) | F2 | Tracker tecnico | Anomalie scan/index e gestione delle future stagioni: distinguere fetch, parser, policy e assenza di programma. |
| [#685](https://github.com/jeckodevelopment/opera-atlas/issues/685) | F2 | Tracker riconciliazione | Candidati residui, prove, pubblicazione automatica, coverage e differenze per sede; ha assorbito #320. |
| [#730](https://github.com/jeckodevelopment/opera-atlas/issues/730) | F2/F3 | Tracker festival | Copertura edizioni italiane e relazioni festival–produzione–venue; feed automatico e directory senza schede vuote. Parte pubblica in F3, ingestione in F2. |

**Stato al censimento:** 14 issue aperte, a seguito della chiusura amministrativa di #53. Una precedente fotografia a 13 issue è stata superata dalla creazione di #730. Verificare nuovamente il totale al prossimo aggiornamento, non bloccare questo numero come KPI.

## Duplicati amministrativi consolidati

| Issue chiusa | Motivo | Requisiti trasferiti |
| --- | --- | --- |
| [#320](https://github.com/jeckodevelopment/opera-atlas/issues/320) | `duplicate`: vecchia coda di riconciliazione | [#685](https://github.com/jeckodevelopment/opera-atlas/issues/685): checkpoint nazionale, motivazioni, idempotenza, pubblicazione automatica, audit |
| [#53](https://github.com/jeckodevelopment/opera-atlas/issues/53) | `duplicate`: perimetro delle otto fonti pilota oggi contenuto nel nazionale | [#178](https://github.com/jeckodevelopment/opera-atlas/issues/178): otto fonti obbligatorie, confronti cartellone/recite, tour, cancellazioni, tempi ignoti, prove per fonte; ROF anche #730 |

## Sequenza operativa di verifica

1. **F1:** eseguire e documentare verifiche su #2 e #3; risolvere eventuali gap come interventi unitari, con collaudi manuali separati. Completare registro #1 in relazione alla piattaforma nazionale.
2. **F2:** verificare #4/#5 come evidenza storica, non come nuovi progetti di singolo teatro; #6 per l'orchestrazione; monitorare #178/#679/#685 in modo aggregato, con baseline automatica e motivazioni.
3. **F3:** verificare criteri della #7, realizzare i requisiti residui della #8 e completare #730 (ingestione più presentazione festival).
4. **F4:** costruire #9 e completare #10 fino alla release 1.0.0.

## Evidence gate per chiusura

Per chiudere una issue `completed` riportare almeno: commit/PR di implementazione, test pertinenti superati, fonte o fixture di verifica, confronto con ciascun acceptance criterion, stato dei collaudi manuali e aggiornamento documentazione. Non chiudere automaticamente su numero di linee di codice, esistenza della pagina, scansione `success` o generica presenza di un adapter. Per chiusura `duplicate` riportare esplicitamente il tracker che conserva i criteri non ancora soddisfatti.
