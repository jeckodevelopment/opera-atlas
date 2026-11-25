# Modello dati e integrità — proposta iniziale

## Entità
- **work**: identificatore canonico, titolo, varianti/alias, compositore, genere, anno (se affidabile).
- **production**: work_id, soggetto produttore, edizione, regia e altri crediti opzionali, intervallo di validità. Una coproduzione può avere più organizzatori.
- **performance**: production_id, venue_id, inizio con timezone Europe/Rome, stato (annunciata/confermata/rinviata/annullata), URL programma/biglietti, note fattuali verificate. Ogni recita è distinta.
- **venue**: nome, alias, indirizzo verificato, comune, provincia, regione, coordinate, stato di verifica; sedi temporanee e alternative rappresentabili.
- **organizer**: fondazione, teatro operatore, festival o circuito; URL canonico e alias. Organizzatori e luoghi sono distinti.
- **festival/season**: edizione, organizzatore, periodo, relazione many-to-many con produzione/recita.
- **source**: URL ufficiale, tipologia pagina e metodo di acquisizione, frequenza, restrizioni, stato, ultima verifica.
- **observation**: snapshot di fatti estratti, timestamp, URL e fingerprint contenuto; storia delle correzioni.

## Invarianti
1. La stessa recita pubblicizzata da festival, circuito e teatro deve essere una sola entità, con più provenance/source.
2. Un titolo identico senza compositore o contesto non autorizza la fusione automatica di opere.
3. Gli spettacoli senza data precisa sono annunci di produzione, non recite inventate.
4. La deduplicazione incrocia opera canonica, venue, timestamp locale, organizzazione/produzione e URL, con revisione delle collisioni.
5. Nessuna interpretazione di 'attivo' da un semplice censimento: teatro attivo = almeno una recita nel periodo scelto, non venue presente in elenco.
6. Metriche distinte per opere, produzioni e recite; 'opera rara' significa una sola produzione nel periodo selezionato fino a definizione statistica più sofisticata.
7. Coordinate e URL non verificati rimangono null, senza sostituti ipotetici.
8. Rinvii e annullamenti conservano storicità e riferimenti; rappresentazioni future di default escludono annullate.
9. Copertura dichiarata per fonte e periodo: dati parziali non sono una fotografia esaustiva dell'Italia.

## Contratto di acquisizione
Per ogni connettore: input URL, policy e limiti, parser versionato, confidence dei campi, data estrazione, osservazioni, warnings, mapping canonical, test con fixture e log degli esiti.

## Riconciliazione implementata (F1 / #3)
- `source_events` assegna una identità stabile alla coppia (source_id, external_id), con puntatore alla recita canonica.
- Nuova osservazione con **opera canonica già identificata**, stessa sede e medesimo istante UTC: un solo candidato -> collegamento a una recita esistente e provenienza aggiuntiva. Nessun candidato -> crea recita; più candidati -> `reconciliation_reviews`.
- La ripetizione della stessa fonte è idempotente e conserva fingerprint e JSON delle osservazioni.
- Un evento già collegato che cambia identità geografica/temporale/editoriale resta sul riferimento precedente e produce una revisione umana, senza sovrascrittura silenziosa.
- La corrispondenza tra titoli e compositori **non è ancora automatica**: gli ID delle opere devono essere canonici e verificati. Non sono ancora disponibili connettori reali, interfaccia di risoluzione dei conflitti né gestione automatica di rinvii/annullamenti.

## Risoluzione controllata delle revisioni (F1)
La funzione `resolve_review` consente di scegliere esplicitamente una recita già esistente (verificando opera, sede e istante) oppure creare una nuova recita usando la proposta registrata. Il record di review passa a `resolved`; le osservazioni storiche rimangono, mentre la provenienza attiva viene collegata alla recita confermata. Non esiste auto-risoluzione basata sul titolo. Il sistema non include ancora un'interfaccia web di moderazione.

## Registro canonico del repertorio (Fase 1, issue #2)
`opera_atlas.catalog` introduce `register_work`, `register_alias` e `find_work`, con corrispondenze esplicite basate su titolo canonico o alias approvato e compositore fornito. Titolo senza compositore: risultato ignoto (`None`); più opere compatibili: eccezione `AmbiguousWorkError`, quindi richiesta revisione. Nessuna fusione implicita. La classificazione controllata include `opera`, `operetta`, `music_theatre`, `concert`, `ballet`, `prose`, `other` per distinguere i contenuti nelle future metriche. La classificazione dei singoli programmi rimane responsabilità dei connettori verificati.

## Opere omonime e nuovi adattamenti — 21/11/2026

- L'identità canonica è l'ID immutabile di **una specifica composizione**. Titolo e compositore verificati sono necessari per riconoscerla; un titolo da solo non dimostra la paternità di una produzione.
- Il registro può contenere più opere con il medesimo titolo e con compositori differenti. `slug` rappresenta il titolo normalizzato; `route_slug` è un percorso pubblico univoco. Quando il titolo esiste già, le nuove opere ricevono `<slug>-<compositore>` senza cambiare gli URL delle opere già pubblicate.
- Le schede editoriali, i dati storici e le immagini di opere omonime vengono associati all'**ID dell'opera**, evitando che dati di una composizione finiscano nella scheda dell'altra.
- Le pagine di dettaglio mostrano collegamenti alle altre opere *effettivamente censite* con lo stesso titolo. Sono collegamenti al repertorio, non una sezione didattica.
- L'acquisizione di calendari senza compositore verificato lascia la candidata non pubblicata (`identity_requires_more_evidence`), anche quando il registro conosce una sola opera con quel titolo: una futura omonima non deve diventare un errore storico.
- Le composizioni basate sullo stesso soggetto ma con titoli differenti (per esempio *Manon* e *Manon Lescaut*) rimangono distinte. Una relazione editoriale per soggetto richiederà evidenza esplicita e non può essere dedotta per somiglianza testuale.
- Regressioni da coprire: *La bohème* (Puccini/Leoncavallo), *Il barbiere di Siviglia* (Paisiello/Rossini), *Manon Lescaut* (Auber/Puccini) e, per titoli differenti, *Manon* (Massenet). Gli ultimi casi non vanno inseriti nel catalogo pubblico in assenza di spettacoli e fonti verificati.


## Identità delle produzioni e repliche Haydn — 25/11/2026

L'URL di biglietteria non identifica necessariamente un allestimento. Le due pagine di *La clemenza di Tito* (Teatro Sociale, Trento, 27/29 novembre 2026) condividono il [gruppo ufficiale Repliche](https://www.haydn.it/eventi/area/opera?repliche=la-clemenza-di-tito). Conserviamo la produzione `oa-s-000245` e le recite `oa-r-000962`, `oa-r-000963`, con i rispettivi URL di acquisto. La produzione duplicata `oa-s-000246` è registrata come ritirata; il precedente percorso web reindirizza al canonico.

Il connettore acquisisce il collegamento esplicito Repliche; il riconciliatore richiede due evidenze ufficiali indipendenti, stesso gruppo, composizione, sede e orari verificati, con date ravvicinate. Un gruppo ambiguo rimane in revisione, non genera una seconda produzione. Titolo identico, suffisso numerico nell'URL o prossimità temporale da soli non bastano. Le edizioni distinte restano separate.

Audit sul catalogo di partenza: 343 produzioni, 10 gruppi con titolo/compositore/sede coincidenti. Il caso Tito è riconciliato. Götterdämmerung alla Scala (febbraio e cicli Ring di marzo 2026) merita una verifica dedicata della semantica di produzione e biglietteria; non è accorpato in questo intervento. Gli altri gruppi includono edizioni annuali o allestimenti distinti. Nessuna recita è rimossa.
