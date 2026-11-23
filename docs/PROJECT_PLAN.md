# Opera+ Atlas — piano di sviluppo 1.0.0

> **Piano operativo riallineato il 23 novembre 2026.** Questo documento sostituisce le precedenti fotografie incrementali della fase pilota. Il dettaglio storico resta nella cronologia Git e nelle PR; le diagnosi correnti sono nei feed machine-readable, non nei numeri statici di questa pagina.
>
> **Stato release:** 1.0.0 in sviluppo, non dichiarata completa. Le percentuali non sono assegnate senza matrice verificata dei requisiti.

## Missione e confini

Opera+ Atlas è il **catalogo nazionale delle rappresentazioni operistiche in Italia**, con ricerca, luoghi, festival e osservatorio statistico; si alimenta da programmi ufficiali, conserva la provenienza e non inventa date, orari, immagini o attribuzioni. Il prodotto serve gli utenti su **https://opera.plus/atlas/**. Il **centro di governo e diagnostica**, su `jeckodevelopment.com/dev/atlas`, è un'interfaccia amministrativa distinta: non sostituisce l'osservatorio pubblico.

Sono esclusi dalla prima release: account personali, vendita diretta di biglietti, social, streaming, raccolta di coordinate personali, motore proprietario di percorsi stradali e riutilizzo non autorizzato di fotografie o testi. Sono ammessi i generi lirici concordati, inclusi operetta e oratorio drammatico quando classificati correttamente; spettacoli pop, crossover, concerti, prosa, balletti e produzioni didattiche/non aperte al pubblico generale non diventano automaticamente opere pubblicabili. Un programma composto ha una sola recita/biglietto con collegamenti alle opere eseguite.

## Principi del riallineamento

1. **Non siamo più nella fase di un singolo teatro pilota.** Il progetto copre circa 70 teatri con connettori realizzati o censiti; il numero operativo e la completezza effettiva vanno **misurati** nei feed aggiornati. Le issue #4 e #5 sono requisiti storici di accettazione dei primi adapter, non la roadmap corrente della piattaforma.
2. **Connettore operativo ≠ cartellone completo.** Un fetch riuscito, un fallback o la presenza del teatro nel catalogo non dimostrano che tutte le recite ufficiali siano presenti. Separare copertura tecnica, contenuti ed effettiva pubblicazione.
3. **Acquisizione, riconciliazione e pubblicazione devono essere autonome e idempotenti.** Non ricorrere a riconciliazione manuale per i casi ordinari e non inventare la soluzione per quelli privi di prove.
4. **Non aprire una nuova fase senza chiudere i suoi requisiti fondamentali.** Un'anomalia editoriale non bloccante va nel backlog di qualità, non deve far dimenticare F3 e F4.
5. **Unica fonte di verità sul progresso:** requisiti e criteri di accettazione tracciati a issue, PR, test e collaudi. Le fotografie nei testi sono datate; i feed aggiornati hanno priorità per lo stato operativo.
6. **Separare implementazione da collaudo manuale**: il proprietario del prodotto svolge i collaudi funzionali separatamente. Una PR implementativa può essere unita con test automatici verdi e istruzioni di collaudo; la chiusura definitiva del criterio conserva evidenza di verifica e distingue l'eventuale collaudo ancora pendente.

## Fasi della 1.0.0, nell'ordine di completamento

### F1 — Fondamenta, identità e integrità

**Scopo:** consolidare l'architettura già costruita, non ripetere la fase pilota.

- [ ] Convalidare modello dati completo: opere canoniche, alias, compositori, produzioni/allestimenti, recite, venue, organizzatori, festival/edizioni, stagioni, fonti e osservazioni; vincoli, migrazioni, fixture e provenienza.
- [ ] Verificare identità immutabili e deduplicazione cross-source: stessa recita pubblicizzata da teatro, festival e circuito = singola recita con più evidenze; composizioni omonime restano distinte; titoli tradotti ricondotti alla stessa opera quando dimostrato.
- [ ] Validare programmi composti e co-produzioni, sedi fisiche separate dagli organizzatori, cambi data, annullamenti e casi ambigui.
- [ ] Consolidare tassonomia dei generi, policy editoriale, regole sui dati incompleti e test di regressione.
- [x] Issue storiche #2 e #3 chiuse dopo audit e test di regressione; collaudi manuali restano separati.\n- [ ] Completare #1: confrontare le 70 sedi e i relativi canali con le fonti ufficiali, date/policy e casi controversi; vedere [audit F1 delle fonti del 23/11](F1_SOURCE_REGISTRY_AUDIT_2026-11-23.md).

**Criterio di uscita:** modello e identificazione canonica stabili, import ripetibili senza duplicati né fusioni improprie; test positivi su casi reali multi-fonte, omonimi, stagioni e programmi composti. Eventuali collaudi manuali pendenti identificati separatamente.

### F2 — Piattaforma nazionale di acquisizione e pubblicazione

**Scopo:** rendere affidabile e misurabile la rete già realizzata di circa 70 teatri, non aggiungere uno alla volta i primi adapter.

- [ ] Censire nel registro tutti i teatri/organizzatori/festival, tutti i loro canali di acquisizione, stato sorgente, fallback, ultima verifica, stagioni correnti e future, e associare ciascuna fonte alla venue corretta.
- [ ] Per ogni teatro distinguere: **connettore configurato**, **scansione riuscita**, **fonte ufficiale/fallback**, **programma trovato**, **produzioni canonizzate**, **recite pubblicate**, **copertura provata**, **lacune e cause**.
- [ ] Verificare tutti i connettori esistenti su esecuzioni reali della pipeline, con gestione conservativa dei blocchi, robots espliciti, limiti di accesso, timestamp, retry, last-known-good, guasti e fallback documentati.
- [ ] Supportare simultaneamente la stagione in corso e quella successiva, con rollover pluriennale senza perdere le ultime recite del vecchio periodo e senza dichiarare complete future stagioni indisponibili.
- [ ] Acquisire dettagli (opera/compositore, produzione, data, sede, ora ove nota), arricchire le prove incrociate, riconciliare e pubblicare nello **stesso refresh** i casi sicuri; motivare e conservare solo le eccezioni non risolvibili automaticamente.
- [ ] Gestire variazioni, rinvii, annullamenti, aggiornamenti immagine e provenienza senza cancellazioni silenziose; testare idempotenza e riconciliazione inter-fonte.
- [ ] Misurare copertura per sede/stagione confrontando tutte le date ufficiali reperibili con le date pubblicate; indicare esplicitamente gli indici non verificabili e le stagioni non ancora pubblicate.
- [ ] Completare audit automatico della pubblicazione **live** separato dalla scansione GitHub e dalla dashboard di governo.
- [ ] Trattare #53 (otto fonti iniziali) e #4/#5 (pilota) come sottoinsiemi storici, #178 come riferimento nazionale su stagioni/copertura, #679 per anomalie sorgenti e #685 per riconciliazioni residue. Nessun duplicato di tracker.

**Criterio di uscita:** matrice nazionale completa con stato reale di ogni connettore, pipeline autonoma e idempotente, KPI di copertura supportati da prove ufficiali; backlog residuo di fonti o evidenze non disponibili esplicito, non occultato. Non serve dimostrare accessibilità di future stagioni non pubblicate, ma il sistema deve saperle scoprire quando compaiono.

### F3 — Portale pubblico e qualità dell'esperienza

**Scopo:** completare l'esperienza approvata, senza confonderla con la diagnostica amministrativa.

- [ ] Verificare homepage e menu Spettacoli/Opere/Teatri/Festival, ricerca nazionale e locale, filtri data/compositore/teatro/area, ordinamenti e assenza risultati.
- [ ] Validare schede opera, allestimento/produzione, recita, teatro e festival, inclusi legami produzione–festival–venue, tournée, programmi composti e link a fonte/biglietteria ufficiale.
- [ ] Validare viste elenco e calendario; completare mappa cartografica Leaflet/OSM con coordinate delle **sedi** verificate, raggruppamenti, filtri, attribuzioni, link esterni indicazioni, consenso opt-in e fallback senza geolocalizzazione. La mappa schematica delle città non soddisfa di per sé la #8.
- [ ] Rivedere immagini, crediti/diritti, schede prive di immagine, descrizioni rivolte al pubblico, accessibilità WCAG applicabile, mobile/tastiera, SEO/deep link e dati incompleti.
- [ ] Conservare un'unica pagina canonica per entità omonime/alias verificati e disambiguazione di opere con lo stesso titolo.
- [ ] Chiudere #7 e #8 quando i criteri specifici sono verificati, non solo perché esiste una pagina pubblica.

**Criterio di uscita:** percorsi principali e tutti i casi limite collaudabili con dati reali; audit accessibilità/SEO e correttezza editoriale; nessuna funzionalità originaria F3 data per completata solo per equivalenza approssimativa.

### F4 — Osservatorio pubblico, governance del rilascio e 1.0.0

**Scopo:** completare il prodotto che il piano originario prevedeva, non soltanto il catalogo.

- [ ] KPI distinti di opere canoniche, produzioni/allestimenti, recite, teatri attivi e distribuzione regionale per periodo/stagione, senza usare come denominatore i soli record acquisiti.
- [ ] Classifiche, opere rare, distribuzione geografica/temporale, filtri e aggregati esportabili; metodologia, periodo e limiti di completezza pubblici.
- [ ] Dashboard **statistica pubblica** distinta dal centro di governo interno; verifica dei conteggi contro fixture note e casi di doppia fonte/annullamenti.
- [ ] CI e test unitari/integrati end-to-end; prova di recupero da errore di fonte, rollback, pubblicazione statica e deep link HTTPS; verifica delle policy di immagini/robots/licenze.
- [ ] Documentazione d'installazione, runbook, dizionario KPI, changelog SemVer, note di rilascio e pacchetto di evidenze per la 1.0.0.
- [ ] Chiusura #9 e #10 al soddisfacimento dei rispettivi criteri.

**Criterio di uscita:** osservatorio pubblico utilizzabile e metodologicamente corretto; rilascio riproducibile, tracciato e collaudabile.

## Baseline verificata al 23/11/2026 (non una percentuale di completamento)

- Il progetto è già nazionale, non più un esperimento Regio/OperaLombardia. Nel tracker #679 (diagnostica di riferimento) risultavano **64/64 teatri operativi**, e **69/87 scansioni-indice riuscite**; il dato riguarda quel checkpoint e **non** conferma l'inventario complessivo dei circa 70 teatri né cartelloni completi. Ricalcolare dai feed prima di ogni dichiarazione di progresso.
- `data/candidate-reconciliation-health.json`, 2026-11-23 15:46 UTC: **440** candidati, **256** già catalogati, **17** `needs_review`, **149** esclusi non-opera, **18** fuori stagione. La diagnostica dei dettagli nazionale successiva riporta **17 tentati / 17 esiti**. Questi sono candidati, non 440 opere o recite.
- `public/catalog/recite-coverage.json` misura le **recite ufficiali finora individuate** vs pubblicate, **non** la percentuale di stagione completa.
- Il backlog è dinamico: dopo la bonifica di #320 e #53 e l'apertura di #730, la successiva verifica ha contato **14** issue aperte. I numeri storici non sono KPI permanenti. #320 e #53 sono chiuse come duplicati amministrativi, non come requisiti implementativi completati.
- Documenti da leggere insieme: `docs/DATA_MODEL.md`, `docs/SOURCE_REGISTRY.md`, `docs/ATLAS_UI_APPROVED.md`; feed `data/season-index-health.json`, `data/candidate-reconciliation-health.json`, `data/candidate-detail-health.json`, `public/catalog/source-automation.json` e `public/catalog/recite-coverage.json`.

## Registro dei requisiti e issue aperte

Il censimento datato delle issue, i casi di chiusura amministrativa, le evidenze richieste e la sequenza di audit sono nel [registro dei requisiti 1.0.0](REQUIREMENTS_STATUS.md). Il tracker festival [#730](https://github.com/jeckodevelopment/opera-atlas/issues/730) integra **F2** per acquisizione/relazioni canoniche e **F3** per directory/edizioni; non sostituisce le issue nazionali #178/#685.

## Backlog di riallineamento e precedenze

| Ordine | Gruppo | Issue di riferimento | Uscita richiesta |
| --- | --- | --- | --- |
| 0 | Bonifica backlog e baseline | #1–#10, #53, #178, #679, #685 | Issue senza duplicazioni, tracciate per fase; chiudere quelle provate risolte |
| 1 | F1 modello e identità | #1, #2, #3 | Test e invarianti consolidati |
| 2 | F2 piattaforma nazionale | #4, #5, #6, #53, #178, #679, #685 | Matrice copertura, pipeline affidabile, casi residui motivati |
| 3 | F3 UX pubblica | #7, #8 | Portale completo rispetto alla UX approvata |
| 4 | F4 osservatorio e rilascio | #9, #10 | KPI pubblici, CI, qualità e 1.0.0 |

I numeri delle issue pilota restano come tracciabilità storica e **non stabiliscono l'ordine dei lavori**. La priorità non è incrementare indefinitamente il numero di connettori; nuovi teatri/nuove stagioni entrano nel normale ciclo di gestione della copertura.

## Matrice requisiti e misurazione

Ogni requisito deve avere: `ID`, fase, descrizione/criteri di accettazione, priorità, issue/PR, test automatici, stato implementativo, stato collaudo manuale, evidenze e data dell'ultima verifica.

Stati ammessi: `not_started`, `in_progress`, `implemented`, `verified`, `manual_qa_pending`, `closed`, `blocked`. `implemented` non è sinonimo di `closed`; `manual_qa_pending` non cancella l'evidenza di implementazione. Percentuali globali e per fase derivano solo dal totale dei criteri valutati e dalla matrice pubblicata; non inferirle da commit, PR, numero di connettori, conteggi di recite o 100% relativi a un sottoinsieme.

## Definition of Done e disciplina PR

1. Ogni PR specifica fase, issue, cambi funzionali, comportamenti da testare, risultati test, rischi, aggiornamenti documentali, impatto SemVer e regressioni.
2. CI verde, test pertinenti, verifica di integrità e prove replicabili. Per cambi di acquisizione, verificare anche feed e risultato di un refresh; per frontend, verificare sito pubblico separatamente dai dati.
3. PR seguite sino al merge. I collaudi manuali richiesti dal proprietario del prodotto rimangono separati e dichiarati pendenti finché svolti.
4. Chiudere l'issue solo se i suoi criteri sono soddisfatti; in caso di duplicato usare `duplicate` e trasferire i requisiti aperti. Non inventare percentuali né attestazioni di test.
5. Per ogni aggiornamento della roadmap, usare baseline datata e riferimenti ai feed, senza accumulare diari cronologici permanenti nel piano.

## Documentazione storica

Le precedenti sequenze di attività dedicate ai singoli connettori, con snapshot del 20/11 e checklist incrementali, rimangono consultabili nella cronologia di `docs/PROJECT_PLAN.md` e nelle PR/issue corrispondenti. Non costituiscono più la definizione aggiornata della roadmap 1.0.0.
