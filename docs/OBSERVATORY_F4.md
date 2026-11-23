# Osservatorio Opera+ — F4
Sito autonomo: https://opera.plus/osservatorio (non sotto /atlas). La pubblicazione usa il medesimo accesso SFTP, ma scrive solo nella directory sorella /osservatorio. Non modifica il deploy Atlas.

## Fonte e metodologia
Il frontend carica il manifesto v2 di Opera+ Atlas e verifica SHA-256, schema e conteggi dei quattro canali opere/sedi/allestimenti/recite. Il mirror CDN viene usato esclusivamente in caso di errore del primario; nessuna cifra di esempio compare in produzione. Gli indicatori derivano da recite univoche pubblicate con riferimenti validi a allestimento, opera e sede; recite annullate o rinviate vengono escluse. Sono distinti: recite, sedi attive nel periodo, opere canoniche e allestimenti. Le classifiche contano le recite, non le produzioni. La rarità (massimo tre recite) riguarda il campione acquisito e non costituisce una valutazione nazionale.

Non si pubblicano stime di spettatori, percentuali nazionali né distribuzioni per secolo senza date verificate. La navigazione temporale offre due filtri indipendenti, combinabili per intersezione: **anno solare**, ricavato dal valore verificato `performances.local_date` già pubblicato nel feed canonico (non dalla stagione), e **stagione teatrale**, letta senza alterazioni da `stagings.season`. L'anno solare corrente in Italia è selezionato all'avvio quando presente nei dati; stagione = tutte. Il CSV include entrambi i campi. Etichette annuali (es. `2026`) e pluriennali (es. `2026-2027`) rimangono distinte: non si deduce mai l'appartenenza alla stagione dall'anno della recita. Sono possibili differenze rispetto ai programmi composti finché questi non saranno presenti nel canale canonico v2. Il CSV esporta il campione filtrato.

## Estensioni statistiche e layout
- Il grafico **Distribuzione delle recite per mese** usa le date ufficiali `performances.local_date` delle sole recite filtrate. Mostra sempre i 12 mesi, anche se non risultano recite; zero significa zero recite nel catalogo, non assenza nazionale di spettacoli. Con tutti gli anni selezionati aggrega i mesi di tutte le annualità presenti, dichiarandolo.
- I filtri Anno solare, Stagione e Territorio rimangono nella stessa barra su desktop; a larghezza ridotta vanno a capo per evitare sovrapposizioni. Il pulsante di esportazione CSV è in alto a destra nell'header e usa esattamente gli stessi filtri attivi.
- Analisi future possibili con i dati v2: giorno della settimana, sedi più attive, varietà del repertorio regionale, recite per allestimento. Non si costruiscono KPI di capienza, pubblico, incassi o copertura nazionale senza fonti adeguate.

## Collaudi separati
- Controllare caricamento dati con manifest valido e indisponibilità della sorgente: nessuna statistica fittizia.
- Filtrare per stagione e regione; verificare i quattro indicatori, barre e classifiche.
- Verificare che una recita promossa da più fonti non venga contata più volte; testare annullate/rinviate.
- Controllare la leggibilità mobile, la navigazione da tastiera, l'esportazione CSV, i metatag SEO, gli URL canonici e il routing con e senza slash finale.
- Confermare il marchio grafico ufficiale Opera+ prima del completamento visuale definitivo.

Non chiudere #9 prima dei collaudi funzionali e dei completamenti grafici, territoriali e di metodologia.
