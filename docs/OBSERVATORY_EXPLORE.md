# Osservatorio Opera+ — Esplora i dati

Specifiche approvate il 26 novembre 2026.

## Confine non regressivo
Nuova pagina pubblica /osservatorio/esplora/ con asset, script e test isolati. Non modificare observatory/index.html, styles.css, app.js, report-pdf.js, logo, grafici, filtri o report attuali. L'accesso dalla pagina esistente sarà valutato separatamente; la nuova pagina deve collegare la panoramica. Il rilascio deve scrivere esclusivamente nella sottodirectory esplora e non sovrascrivere file esistenti. Nessun nuovo database, login o servizio esterno.

## Lotti
1. Motore puro di interrogazione (integrato con PR #901), unit test, regole statistiche.
2. Interfaccia responsive, filtri combinabili, indicatori, dettaglio, caricamento feed verificato.
3. Raggruppamenti, confronti, grafici, ricerche predefinite.
4. CSV, PDF istituzionale, URL condivisibile, deploy isolato e collaudo.

## Modello e regole
Il motore accetta gli eventi normalizzati dal client Atlas (catalogo v2 e programmi composti) e l'indice festival permanente. Il successivo loader deve usare il feed remoto verificato, non uno snapshot locale non verificato, e gestire l'indice festival mancante senza mostrare conteggi apparentemente completi. I programmi composti non devono essere scartati: una recita/biglietto e una produzione per programma, una presenza per ciascun componente canonico. Componenti senza ID non concorrono al conteggio delle opere; non attribuire loro identità ipotetiche. Stagione mancante resta ignota, non inferita dall'anno. Filtri opera e compositore si applicano allo stesso componente.
 
Produzioni = staging ID distinti (o ID programma), per sede, non gruppi di coproduzione; recite = ID recita distinti. Teatro = ID sede. Città = coppia regione/città. Festival = ID permanente, non edizione; un evento collegato a teatro e festival non viene duplicato. Raggruppamenti per opera/compositore/festival non sono necessariamente additivi. Escludere cancellate e rinviate. Le date passate sono recite rilevate, non certificazione di effettivo svolgimento. Oggi è incluso nelle date in programma (fuso Europe/Rome); il loader fornisce la data locale. Anno solare da local_date; stagione originale, indipendente. Un intervallo è inclusivo. I filtri multipli sono OR nella stessa dimensione e AND tra dimensioni. Le produzioni a cavallo d'anno contano una volta nel periodo complessivo, e una volta in ogni periodo in cui hanno recite. Nessun dato non significa nessuna attività.

## UI e output
Opera e compositore ricercabili e multiselezione; anno, stagione, periodo, regione, città, teatro, festival, tipologia (festival/non associato a festival), stato temporale. KPI, dettaglio produzioni e singole recite, raggruppamento per opera/compositore/teatro/città/regione/festival/mese/anno/stagione. Link Atlas e fonti; aggiornamento del feed e avviso di copertura. PDF, CSV sintesi e dettaglio, query URL riproducibile. Esportazioni con gli stessi filtri e conteggi visibili.

## Test
node tests/observatory_explore_engine.cjs
python -m unittest discover -s tests -v

Il motore è indipendente dal DOM; il test include programmi composti, date a cavallo d'anno, filtri incrociati, festival multipli, duplicati e annullamenti. Nessuna pagina viene pubblicata dal lotto 1.

## Lotto 2 — interfaccia e caricamento

La nuova interfaccia in `observatory-explore/` riutilizza in sola lettura la grafica, il logo e il client pubblico Atlas già esistenti (`/atlas/catalog-client.js`). Il client valida digest e conteggi dei quattro canali; l'adattatore rifiuta il fallback locale non verificato e richiede anche programmi composti e festival allineati, con tentativo sul mirror. I canali complementari sono verificati per schema e riferimenti, non firmati dal manifesto v2. Una mancata verifica impedisce l'esposizione di statistiche incomplete.

Filtri a caselle ricercabili (OR interno, AND fra categorie); città e sede dipendono dalla regione, con rimozione delle scelte non compatibili. Anno corrente in Italia se presente; Azzera filtri seleziona l'intero catalogo. Risultati ordinabili e paginati (30 righe), con due viste, link canonici e fonti delle singole recite. La prima e ultima data della produzione sono quelle comprese nei filtri, non dell'intero allestimento. Copertura temporale e data di aggiornamento sono esplicite. Nessuna modifica al sito pubblico né al workflow di pubblicazione in questo lotto.

Test: `node tests/observatory_explore_ui.cjs` verifica anche il client Atlas sui file canonici effettivi versionati nel repository, senza accesso di rete. Restano da collaudare graficamente desktop/mobile e l'interazione nel browser durante il rilascio.

## Lotto 3 — grafici e analisi comparative

Il modulo puro `analysis.js` elabora gli stessi eventi filtrati dei KPI e del dettaglio. Grafici mensili (mese e anno, senza aggregare gennaio di anni differenti) e regionali, confronto per tutte le nove dimensioni, scelta di uno degli otto indicatori, ordinamento, confronto opzionale con le produzioni e tabella aggregata completa. I grafici limitano il numero di gruppi visibili per leggibilità e dichiarano il limite; le tabelle non perdono righe. Le barre hanno scala comune e valori numerici accessibili. I mesi senza osservazioni sono a zero esclusivamente come conteggio del campione selezionato, non come prova di inattività.

Sei ricerche predefinite: opere, compositori, regioni, repertorio delle sedi, evoluzione annuale e opere rare. I preset mantengono i filtri scelti; l'evoluzione annuale suggerisce di selezionare più anni. Il repertorio delle sedi confronta il numero di opere distinte. Il preset opere rare restringe anche i KPI e il dettaglio alle recite contenenti almeno un'opera con 1–3 presenze nel campione filtrato, limitando le identità canoniche ai soli titoli rari. Un dittico può contribuire a più gruppi; i totali restano deduplicati. La tabella aggregata dichiara che la somma dei gruppi non coincide necessariamente con il totale.

Test: `node tests/observatory_explore_analysis.cjs`, integrato nella suite Python. La pagina non viene ancora pubblicata. Il lotto 4 dovrà serializzare anche preset, raggruppamento, indicatore e ordinamento negli URL e mantenere l'allineamento tra risultati, grafici, CSV e PDF.

## Lotto 4 — esportazioni e pubblicazione

- PDF A4 generato localmente nel browser, con intestazione Opera+, versione dati, filtri, KPI, grafico comparativo, tabelle mensili, territoriali, aggregate e dettaglio della vista scelta. Il renderer è isolato e conserva gli accenti italiani tramite WinAnsi; nessun servizio PDF esterno.
- CSV di sintesi con tutti i gruppi e gli otto indicatori; CSV di dettaglio con tutte le produzioni o recite della vista scelta, ID canonici, schede Atlas e fonti delle recite. UTF-8 BOM, separatore punto e virgola, escaping e protezione formula injection. I file non sono limitati alla paginazione visibile.
- URL versione 1 con tutti i filtri applicati e impostazioni di analisi, preset e vista. Le identità non più disponibili causano un errore esplicito invece di ampliare la query. Il link riproduce la ricerca sul catalogo corrente, non congela uno snapshot storico: filtri relativi a oggi vengono ricalcolati.
- Workflow autonomo `deploy-observatory-explore.yml` su main e manuale. Usa gli stessi segreti SFTP esistenti e pubblica esclusivamente gli otto file allowlist nella sottodirectory `/osservatorio/esplora/`, dopo aver verificato directory, assenza di symlink sui file, byte SFTP e poi risposta HTTPS. Il workflow esistente dell'Osservatorio resta immutato. Non si aggiunge un link alla panoramica senza autorizzazione: accesso diretto alla nuova URL e collegamento di ritorno già disponibile.

### Collaudo finale

Test automatici: `node tests/observatory_explore_export.cjs`; suite Python, incluso confine SFTP. Dopo il merge, verificare il workflow di pubblicazione e il sito reale. Collaudo browser desktop/mobile: selezionare Rigoletto e 2026, confrontare due opere/anni/regioni, verificare dittici, cambiare vista, scaricare PDF e CSV, ripristinare link in nuova scheda, azzerare filtri, verificare leggibilità e assenza di regressioni sulla panoramica. Verificare anche che i file esportati riflettano la ricerca elaborata, non modifiche ancora non applicate. Il superamento della CI non sostituisce il collaudo visivo nel browser.
