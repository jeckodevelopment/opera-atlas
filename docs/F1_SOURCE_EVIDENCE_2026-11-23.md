# F1 — Verifica delle fonti ancora senza mapping esplicito

**Checkpoint:** 23 novembre 2026, repository `main` esaminata durante l'audit. Questi dati cambiano con i refresh e le nuove sedi: rileggere sempre le configurazioni prima di intervenire.

## Stato nazionale aggiornato

- **72 venue censite**, **19 organizzazioni correlate**.
- **88 indici di stagione** configurati; **13** senza voce esplicita in `INDEX_VENUES`.
- Feed `public/catalog/source-automation.json`: **70 venue operative**, **2 non operative** al checkpoint. Non confondere operatività con completezza delle stagioni.
- **Teatro M° Tonino Pardo (Trapani)**: la mappa `INDEX_VENUES` ora associa esplicitamente `trapani-luglio-musicale-2026` anche a questa venue; il feed riporta l'ultima scansione riuscita. **Il precedente rapporto che la segnalava priva di connettore è superato.** Non modificare questa associazione.
- **Teatro Nuovo Gian Carlo Menotti (Spoleto)**: configurato, ma scansione segnalata `access_denied_or_robots_disallowed`. Questo non è un difetto del mapping; verifica tecnica in #679.
- **Villa Pisani Bonetti (Lonigo)**: non configurata nel feed. Non assegnare il connettore di un altro teatro; verificare prima se esistono un calendario lirico ufficiale e una reale relazione operativa con l'organizzatore.

## I 13 indici non mappati sono classificati, non corretti per supposizione

| Stato del checkpoint | Indici | Azione sicura |
| --- | --- | --- |
| Scansione riuscita | `macerata-festival-rolling`, `filarmonico-verona-rolling-opera` | Verificare quali venue fisiche siano effettivamente servite; nessuna assegnazione per semplice città/festival |
| Stagione futura non verificata | `chieti-marrucino-season-2027`, `salerno-verdi-rolling-opera`, `padova-verdi-season-2027`, `rovigo-sociale-season-2027-28`, `lecce-provincia-season-2027` | Conservare l'incertezza; non inferire né assenza di stagione né divieto robots |
| Recupero HTML non riuscito | `modena-municipal-opera-2027-28`, `ferrara-season-opera-2027-28`, `jesi-opera-season-2027`, `ancona-opera-season-2027`, `treviso-del-monaco-season-2027-28` | Diagnostica tecnica in #679, preservando eventuali altri canali attivi |
| Validazione fonte/indice non riuscita | `donizetti-opera-2027` | Verificare cartellone e struttura della fonte; conservare eventuale edizione esistente |

`python -m scripts.audit_source_registry` ora produce anche `unmapped_index_evidence` per ogni sorgente non mappata: URL configurato, stato e diagnosi dell'ultima scansione, timestamp e vincolo di verifica della venue. **Il programma non prova via rete che un URL sia ufficiale, non assegna venue e non scrive file.** Le nuove prove automatiche sono isolate e non bloccano i connettori per la presenza di nuove stagioni non ancora verificabili.

## Gate di chiusura #1

La verifica strutturale in repository è avanzata, ma i requisiti originali impongono ancora un controllo esaustivo di **URL ufficiali, calendario, rapporti organizzatore/venue, stato e policy robots/termini**, più un campione manuale per ogni regione e tutti i casi controversi. Quest'ultimo rimane un collaudo separato del proprietario; **non può essere dichiarato eseguito** da un audit di JSON in sola lettura.

La #1 resta aperta finché l'evidenza mancante non è acquisita. Non riaprire il refactoring dei 70+ collegamenti solo per ottenere una percentuale di avanzamento. Per le stagioni future usare #178, per errori sorgente #679.
