# Osservatorio Opera+ — F4
Sito autonomo: https://opera.plus/osservatorio (non sotto /atlas). La pubblicazione usa il medesimo accesso SFTP, ma scrive solo nella directory sorella /osservatorio. Non modifica il deploy Atlas.

## Fonte e metodologia
Il frontend carica il manifesto v2 di Opera+ Atlas e verifica SHA-256, schema e conteggi dei quattro canali opere/sedi/allestimenti/recite. Il mirror CDN viene usato esclusivamente in caso di errore del primario; nessuna cifra di esempio compare in produzione. Gli indicatori derivano da recite univoche pubblicate con riferimenti validi a allestimento, opera e sede; recite annullate o rinviate vengono escluse. Sono distinti: recite, sedi attive nel periodo, opere canoniche e allestimenti. Le classifiche contano le recite, non le produzioni. La rarità (massimo tre recite) riguarda il campione acquisito e non costituisce una valutazione nazionale.

Non si pubblicano stime di spettatori, percentuali nazionali né distribuzioni per secolo senza date verificate. La navigazione temporale offre due filtri indipendenti, combinabili per intersezione: **anno solare**, ricavato dal valore verificato `performances.local_date` già pubblicato nel feed canonico (non dalla stagione), e **stagione teatrale**, letta senza alterazioni da `stagings.season`. L'anno solare corrente in Italia è selezionato all'avvio quando presente nei dati; stagione = tutte. Il CSV include entrambi i campi. Etichette annuali (es. `2026`) e pluriennali (es. `2026-2027`) rimangono distinte: non si deduce mai l'appartenenza alla stagione dall'anno della recita. Sono possibili differenze rispetto ai programmi composti finché questi non saranno presenti nel canale canonico v2. Il CSV esporta il campione filtrato.

## Estensioni statistiche e layout
- Il grafico **Distribuzione delle recite per mese** usa le date ufficiali `performances.local_date` delle sole recite filtrate. Mostra sempre i 12 mesi, anche se non risultano recite; zero significa zero recite nel catalogo, non assenza nazionale di spettacoli. Con tutti gli anni selezionati aggrega i mesi di tutte le annualità presenti, dichiarandolo.
- I filtri Anno solare, Stagione e Territorio rimangono nella stessa barra su desktop; a larghezza ridotta vanno a capo per evitare sovrapposizioni. Il pulsante di esportazione CSV è in alto a destra nell'header e usa esattamente gli stessi filtri attivi.
- Analisi future possibili con i dati v2: giorno della settimana, sedi più attive, varietà del repertorio regionale, recite per allestimento. Non si costruiscono KPI di capienza, pubblico, incassi o copertura nazionale senza fonti adeguate.

## Analisi dettagliate (stessi tre filtri globali)
Sei pannelli aggiuntivi sono calcolati esclusivamente sulle recite filtrate presenti nel catalogo canonico:
- Giorno della settimana: dalla `performances.local_date` in calendario civile, lunedì–domenica, senza conversioni timezone.
- Sedi più attive: numero di recite per `venues.id` (non ricavi o pubblico). La dicitura in pagina precisa che sono **recite rilevate**.
- Diversità regionale del repertorio: cardinalità dei `works.id` distinti per `venues.region`, non numero di repliche.
- Opere per regione: quantità di recite per coppia `(works.id, venues.region)`; titoli identici ma opere canoniche diverse rimangono distinti.
- Compositori per regione: quantità di recite per coppia `(composer, venues.region)`; autori non indicati esclusi dalla graduatoria.
- Recite per allestimento: quantità di recite per `stagings.id`; più fonti sulla stessa recita non aumentano il conteggio.

Tutti i pannelli usano la stessa intersezione Anno solare / Stagione / Territorio dei KPI e del CSV. Non si inseriscono date di inizio/fine rilevate come ulteriori KPI. I limiti di copertura e gli eventi non ancora acquisiti valgono anche per queste classifiche.

## Intestazione e immagini
Il banner usa il dettaglio **effettivo del teatro nel mockup originale approvato** per Opera+ Osservatorio, ritagliato dall'immagine generata per il progetto, non una fotografia di un teatro identificato. L'asset locale `observatory/mockup-theatre-banner.svg` incorpora l'estratto compresso; non necessita di collegamenti esterni né attribuzioni fotografiche improprie. La testata mantiene proporzioni, sfumatura blu notte e scena dorata a destra. Il comando «Esporta CSV» rimane discreto nell'header.

## Opere in circolazione e prime assolute
- «La circolazione delle opere» conta, per ogni `works.id` con recite nel campione temporale, i distinti `venues.id`, le coppie città-regione e le regioni. La stessa recita o il medesimo titolo replicato non aumenta artificialmente il numero di sedi. Le opere omonime rimangono separate per ID.
- Il box «Prime assolute» usa **esclusivamente** `public/catalog/work-editorial.json`, già prodotto dall'editoria verificata di Atlas: per ogni `work_id` e `history.premiere_year` validi con fonti presenti, mostra l'anno storico di debutto. Non tenta di inferire una prima assoluta dalla prima recita registrata in Atlas, né confonde un nuovo allestimento con una nuova composizione.
- **Anno solare** seleziona l'anno della prima assoluta. Il box usa **stagione** e **territorio** come filtro di presenza dell'opera nel catalogo, anche se le recite italiane di quell'opera si svolgono in anni differenti; non dichiara che la prima sia avvenuta in quel territorio.
- Poiché molte schede hanno solo l'anno e non la data precisa, il box distingue date documentate già trascorse, date future e date non specificate. **L'anno di prima registrato non costituisce da solo prova che un evento futuro sia già avvenuto.** Se il feed editoriale non è disponibile, il box non mostra numeri fittizi. Se non è selezionato un singolo anno civile, propone di selezionarne uno per il conteggio.
- Il box è inserito accanto alla tabella sulla circolazione per preservare una composizione grafica equilibrata; nessun nuovo dato di affluenza o copertura nazionale.

## Rapporto PDF istituzionale
Il frontend genera interamente nel browser un rapporto **A4 multipagina** (11 pagine, carta vettoriale), scaricabile dal comando discreto «Report PDF» nell'intestazione, adiacente all'esportazione CSV. Non utilizza servizi remoti PDF, server, credenziali, librerie di terzi o dati inventati.

Il documento presenta copertina Opera+, perimetro dei filtri Anno/Stagione/Territorio, quattro KPI, recite per mese e giorno, geografia regionale, città e sedi, repertorio per opera e compositore, circolazione canonica, prime assolute con anno storico verificato, allestimenti, titoli meno rappresentati, metodologia e data di versione dei dati. I grafici sono disegnati come vettori nel PDF e le cifre derivano dal medesimo insieme di recite filtrate già usato dalla dashboard. Le prime assolute usano il feed editoriale separato e non confondono anno storico di debutto con anno delle repliche. Il comando resta disabilitato finché il catalogo non è caricato correttamente. Se il feed editoriale è assente, il PDF non inventa alcun numero per le prime assolute.

I PDF, una volta generati, non si aggiornano automaticamente quando cambia Atlas: la data di versione e i filtri sono riportati per garantire citabilità.

## Collaudi separati
- Controllare caricamento dati con manifest valido e indisponibilità della sorgente: nessuna statistica fittizia.
- Filtrare per stagione e regione; verificare i quattro indicatori, barre e classifiche.
- Verificare che una recita promossa da più fonti non venga contata più volte; testare annullate/rinviate.
- Controllare la leggibilità mobile, la navigazione da tastiera, l'esportazione CSV, i metatag SEO, gli URL canonici e il routing con e senza slash finale.
- Confermare il marchio grafico ufficiale Opera+ prima del completamento visuale definitivo.

Non chiudere #9 prima dei collaudi funzionali e dei completamenti grafici, territoriali e di metodologia.
