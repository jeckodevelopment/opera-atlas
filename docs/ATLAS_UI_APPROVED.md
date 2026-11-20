# Opera+ Atlas — interfaccia approvata (20/11/2026)

## Finalità
Guida nazionale agli spettacoli operistici: identificare una rappresentazione, scegliere teatro e data, aprire la fonte/biglietteria ufficiale. Non è un'enciclopedia, un corso o una piattaforma di streaming. Le schede opera prevedono solo un'introduzione/sinossi brevissima.

## Decisioni di prodotto approvate
- Homepage: ricerca spettacoli → produzioni vicino a te → prossimi festival → esplora opere → teatri.
- Menu: Spettacoli, Opere, Teatri, Festival; su mobile barra inferiore persistente e intestazione compatta.
- Ricerca di riferimento: Torino, entro 100 km, prossimi 30 giorni, vista elenco raggruppata per produzione, ordinamento per prima data utile.
- Modalità alternative: calendario per singola replica e mappa delle sedi.
- Identità visiva: logo ufficiale Opera+ Atlas, nero/bianco/oro, avorio discreto.
- Modello: opera → produzione/allestimento → rappresentazioni; sede fisica distinta da soggetto organizzatore. Gestire festival, coproduzioni, circuiti e tournée senza duplicare l'opera o l'allestimento.
- Link alle fonti ufficiali e biglietterie solo quando verificati. Se l'orario manca, visualizzare «Orario da confermare».

## Stato di questa iterazione
Implementati nella UI statica: navigazione a quattro voci desktop/mobile, struttura della homepage con sezioni di scoperta, raggruppamento per produzione predefinito, periodo iniziale di 30 giorni e link a opere e teatri realmente presenti nel feed. Il calendario e la mappa non sono ancora realizzati.

**Limitazione esplicita:** il filtro «Torino» in questa iterazione è una ricerca per città esatta, **non** per raggio di 100 km. Non visualizzare distanze inesistenti né pretendere copertura geografica verificata. Il raggio richiede coordinate validate per i luoghi e un filtro geospaziale, così come l'eventuale localizzazione autorizzata. L'assenza di eventi nei risultati non prova l'assenza di programmazione nell'area.

Le sezioni festival sono attualmente vuote senza manifestazioni/edizioni validate nel feed. Le immagini e il logo grafico vanno incorporati solo da asset autorizzati; il marchio attuale resta testuale finché il logo approvato non sia integrato negli asset pubblicabili.

## Collaudi da effettuare prima del merge/deploy
1. Con dataset reale: vista iniziale raggruppata per produzione, Torino, 30 giorni e ordine cronologico; non duplicare le repliche.
2. Svuotare la città e vedere risultati nazionali; modificare città e periodo; «Azzera filtri» ripristina Torino e 30 giorni.
3. I link di «Opere» e «Teatri» risolvono gli URL canonici derivati dal feed, non titoli inventati.
4. Desktop: quattro collegamenti nella testata. Mobile: quattro voci nella barra inferiore, nessun contenuto coperto, supporto tastiera/screen reader.
5. Conservare «Orario da confermare» quando starts_at è null; link esterni esclusivamente HTTPS.
6. Fallback del catalogo remoto esplicitamente segnalato; assenza rete o feed non valido non crea rappresentazioni.
7. Nessuna azione GitHub Actions sul repository jeckodevsite per test; soltanto workflow di deploy SFTP dopo il merge.

## Interventi successivi (non dichiarati completati)
Geocodifica affidabile delle sedi e ricerca entro 100 km; viste calendario e mappa; feed festival con edizioni; effettivo logo approvato; controllo accessibilità e screenshot mobile/desktop; eventuale gestione preferenze locale e sinossi editoriali brevi validate.

## Iterazione di interfaccia completa — 20 novembre 2026

Implementati nel frontend statico:
- Homepage conforme all'ordine approvato: ricerca, produzioni vicino a te, prossimi festival, opere, teatri.
- Ricerca iniziale Torino, raggio 100 km, 30 giorni, ordinamento cronologico, schede raggruppate per produzione. Filtri avanzati richiudibili e possibilità di visualizzare tutta Italia.
- Vista calendario mensile con repliche individuali e vista mappa geografica **schematica** delle città con produzioni verificate. Nessun servizio di mappe a pagamento, nessun dato o contatore inventato.
- Distanze calcolate in linea d'aria su coordinate indicative dei **centri delle quattordici città attualmente censite**; non sono distanze teatro-teatro né stradali. Se una città futura è priva di coordinate, non viene inclusa nei risultati entro un raggio finché non viene registrata la sua posizione. L'opzione «Tutta Italia» include tutti gli eventi.
- Localizzazione solo su richiesta esplicita: la posizione dell'utente viene convertita nella città censita più vicina, solo entro 80 km, e non è memorizzata.
- Directory dedicate Opere, Teatri, Festival; una breve sinossi originale per le opere note; schede produzione con date future e link alle fonti ufficiali per ogni replica.
- Indice festival editoriale in \`public/catalog/v2/festival-index.json\`, letto da GitHub indipendentemente dal deploy SFTP. Una manifestazione con programmazione futura viene mostrata solo se associata a ID di produzioni già presenti nel feed verificato. Le fonti censite senza date non diventano eventi.
- Barra inferiore mobile, quattro destinazioni principali e test di compatibilità statica più verifica della sintassi JavaScript.

**Limitazioni ancora presenti:** la vista mappa è una rappresentazione schematica per località e non un servizio cartografico stradale; i punti non sono coordinate geocodificate delle singole sedi. Il catalogo nazionale e il programma dei festival non sono ancora completi. La pagina Teatro non può mostrare indirizzo o accessibilità finché non sono presenti nell'export. Non è stata verificata visivamente la resa in un browser reale o su dispositivo mobile. Il logo raster fornito dall'utente resta da includere come asset effettivo; il marchio nell'header è testuale, coerente nella palette ma non sostituisce il logo originale.

### Comportamenti da collaudare
1. Torino, 100 km, 30 giorni e vista elenco di default; nessuna recita fuori intervallo.
2. Raggio 25/50/100/200 km, oppure tutta Italia; etichetta distanza solo quando calcolabile per i centri cittadini.
3. Cambio intervallo, ricerca testuale e filtri avanzati; reset della ricerca.
4. Calendario: singole date corrette, navigazione mesi e link produzione; mappa: pin e link corrispondenti alle città del filtro.
5. Geolocalizzazione negata e accettata (solo dopo azione utente); nessuna necessità di permesso per la ricerca manuale.
6. Festival con/senza staging verificati, assenza di recite inventate, feed disponibile senza nuovo SFTP.
7. Opera → produzione → teatro e link alle fonti con orari sconosciuti conservati.
8. Mobile: bottom navigation senza sovrapposizioni, focus/tastiera e layout di filtri e calendario.
9. Sintassi dei JS, test Python, integrità della build JSON e verifica statica delle sorgenti.

### Pubblicazione e responsabilità
Test, script, controlli e feed esclusivamente nel repository \`opera-atlas\`. L'unico ruolo di \`jeckodevsite\` è il workflow SFTP per HTML, CSS, JS e asset quando necessario. Nessuna modifica ai JSON richiede rilascio del frontend.

### Coproduzioni OperaLombardia 2026/27
Il registro di gruppo unisce, senza confondere le diverse opere, le sei produzioni condivise di L'italiana in Algeri, Turandot, Death in Venice, Cavalleria rusticana, Pagliacci e Un ballo in maschera. Il teatro di Torino rimane distinto dalle coproduzioni del circuito. Il feed canonico attuale comprende 208 recite e 14 teatri; le date senza ora restano esplicitamente non confermate.

## Rifinitura editoriale e fotografica — 20 novembre 2026

Le card non sono più elenchi tecnici privi di immagini: i cataloghi mostrano fotografie illustrative con attribuzione documentata in `site/credits.html` e componenti visivi condivisi da `site/image-client.js`. Per le immagini le fonti e le licenze sono verificate su Wikimedia Commons; foto storiche e documentarie **non** sono spacciate per immagini delle produzioni attualmente in vendita. Non vengono copiate le immagini temporanee delle demo senza autorizzazione.

Layout approvato: 3 colonne per la vista elenco delle produzioni, 4 per le directory su desktop; riduzione responsiva fino a 2 colonne su mobile, con fallback a 1 solo su schermi molto stretti. Homepage con fotografia editoriale e cataloghi di scoperta illustrati.

Copy destinato ai visitatori e non agli operatori: eliminati ripetitivi avvisi di audit e disponibilità dai cataloghi, rimossi i collegamenti «Fonte ufficiale» dalle card, conservate le verifiche nel backend e i link dell'organizzatore soltanto in fondo alle **schede di dettaglio** sotto «Programma e biglietti». Festival con etichette semplici, non tecniche. Permangono messaggi di errore essenziali se il catalogo non viene caricato e l'avvertenza sulle distanze stimate.

Verificare: il correttissimo comportamento delle card a 3/4/2 colonne, il caricamento delle immagini (con fallback cromatico), l'accessibilità delle fotografie, i link dei crediti e l'effettiva assenza di collegamenti esterni ufficiali nelle viste catalogo. Il publisher SFTP di jeckodevsite deve includere i nuovi asset `credits.html` e `image-client.js`, senza aggiungere logica o test applicativi.

## Recupero catalogo, presentazione dei teatri e link — 20 novembre 2026

Il catalogo principale continua a essere aggiornato dal repository GitHub, con manifest v2 verificato tramite SHA-256. Il client ora verifica nell'ordine l'endpoint raw GitHub, il mirror del repository su jsDelivr e, in caso di mancata raggiungibilità di entrambi, la copia locale statica (esplicitamente identificata come copia di riserva). Sono presenti test funzionali Node senza rete che simulano tutti e tre gli scenari. Le immagini editoriali sono facoltative: l'assenza di `image-client.js` o un errore fotografico non deve più far fallire la lista né essere interpretato come errore del feed.

Le 14 schede Teatro riportano un breve testo introduttivo e indirizzo verificato in `site/theatre-profiles.json`, accompagnato da «Come arrivare» e programma futuro dal feed. I siti dei teatri vengono elencati soltanto alla fine della scheda, in una sezione dedicata e con etichette pertinenti. Le pagine generali delle opere rimandano alle produzioni interne senza elencare decine di link esterni ripetitivi; quelle delle produzioni riportano link deduplicati e contestualizzati alla rappresentazione. Le schede restano prive di contenuti didattici.

Fonti per gli indirizzi: pagine contatti/biglietteria dei teatri e siti istituzionali comunali (Torino, Como, Pavia, Brescia, Cremona, Milano, Verona, Venezia, Palermo, Parma, Novara, Bergamo, Reggio Emilia e Ravenna). Le coordinate dei luoghi non sono confuse con i centri cittadini usati dal filtro geografico. Il profilo viene caricato indipendentemente dal feed, e un suo errore non impedisce la consultazione del calendario.

Da collaudare: tab Opere/Teatri/Festival anche con blocco del server immagini, scena con 30+ date che mostra il solo link pertinente, «Come arrivare», area di biglietteria al fondo, confronto con il feed GitHub e con fallback locale.
