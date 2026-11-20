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
