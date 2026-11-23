# F1 — Eccezioni di mapping degli indici di stagione (23/11/2026)

Questo documento integra [l'audit nazionale F1](F1_SOURCE_REGISTRY_AUDIT_2026-11-23.md). Le configurazioni sono analizzate **senza richieste di rete e senza modifiche ai connettori** tramite:

```sh
python -m scripts.audit_source_registry
python -m unittest tests.test_f1_source_registry_audit -v
```

Il report macchina distingue i 70 profili di sede, gli 87 indici configurati, i 19 dettagli configurati, gli ID/mapping duplicati, gli URL non interpretabili, le associazioni a venue inesistenti e l'assenza di esito health.

## Tredici indici senza mapping `INDEX_VENUES` esplicito

I seguenti indici sono configurati in `data/season-index-config.json`, ma **non** compaiono nella tabella di assegnazione per venue usata dalla diagnostica `scripts/source_automation.py`:

| Gruppo | Source key |
| --- | --- |
| Bergamo / festival futuro | `donizetti-opera-2027` |
| Chieti / stagione futura | `chieti-marrucino-season-2027` |
| Modena / stagione futura | `modena-municipal-opera-2027-28` |
| Ferrara / stagione futura | `ferrara-season-opera-2027-28` |
| Jesi / stagione futura | `jesi-opera-season-2027` |
| Ancona / stagione futura | `ancona-opera-season-2027` |
| Macerata / festival continuativo | `macerata-festival-rolling` |
| Salerno / stagione continuativa | `salerno-verdi-rolling-opera` |
| Verona / Filarmonico | `filarmonico-verona-rolling-opera` |
| Treviso / stagione futura | `treviso-del-monaco-season-2027-28` |
| Padova / stagione futura | `padova-verdi-season-2027` |
| Rovigo / stagione futura | `rovigo-sociale-season-2027-28` |
| Lecce / stagione futura | `lecce-provincia-season-2027` |

**Non sono 13 teatri senza connettore.** Sono sorgenti non collegate in questa specifica mappa diagnostica, talvolta affiancate da indici precedenti funzionanti. Il sistema può inoltre avere altre evidenze editoriali o di pubblicazione.

La mancanza del mapping non prova un difetto del parser, e non autorizza ad associare automaticamente una fonte a un teatro solo perché condividono città, nome o organizzatore. Ogni associazione va provata con la sede fisica e il cartellone ufficiale; le stagioni future possono non essere ancora verificabili.

## Protezioni introdotte

- Audit in sola lettura, con output su stdout; nessun file del catalogo modificato.
- Test automatici su unicità di ID/profili delle venue, chiavi delle fonti, validità degli URL, target mapping e riconciliazione con esiti delle scansioni.
- Il test **non esige che il numero di sorgenti senza mapping sia zero**; le elenca per audit invece di bloccare la pipeline nazionale.
- Nessuna modifica a `INDEX_VENUES`, `DAILY_VENUES`, schema, ID canonici, fixture del catalogo o workflow di pubblicazione.
- Chiudere la #1 soltanto dopo aver verificato attribuzioni, URL/policy e i collaudi manuali per regioni/casi controversi. Le anomalie tecniche delle fonti restano in #679.

## Criterio di avanzamento

Il report deve permettere di **distinguere** un nuovo indice senza mapping, un target inesistente, una stagione non verificata e una venue realmente senza connettore. Il caso Tonino Pardo rimane separato perché privo di associazione configurata nel feed `source-automation.json`.
