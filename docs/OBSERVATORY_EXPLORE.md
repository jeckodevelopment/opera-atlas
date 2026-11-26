# Osservatorio Opera+ — Esplora i dati

Specifiche approvate il 26 novembre 2026.

## Confine non regressivo
Nuova pagina pubblica /osservatorio/esplora/ con asset, script e test isolati. Non modificare observatory/index.html, styles.css, app.js, report-pdf.js, logo, grafici, filtri o report attuali. L'accesso dalla pagina esistente sarà valutato separatamente; la nuova pagina deve collegare la panoramica. Il rilascio deve scrivere esclusivamente nella sottodirectory esplora e non sovrascrivere file esistenti. Nessun nuovo database, login o servizio esterno.

## Lotti
1. Motore puro di interrogazione (questa PR), unit test, regole statistiche.
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
