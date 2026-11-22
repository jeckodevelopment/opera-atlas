# Revisione delle schede opere — processo gratuito

## Finalità
Il catalogo automatico continua a funzionare senza API OpenAI o altri servizi
a pagamento. Le schede delle nuove opere vengono pubblicate **soltanto dopo** che
la sinossi specifica e i fatti storici richiesti sono verificati. La
sola identificazione con titolo e compositore non soddisfa questa regola.
Un'opera incompleta resta in coda senza interrompere l'acquisizione e
la pubblicazione di tutte le altre rappresentazioni verificabili.
Le informazioni editoriali già approvate vengono riutilizzate nello
stesso refresh, senza servizi a pagamento.

## Preparazione prima della pubblicazione

Il generatore consulta le sinossi originali e i profili storici già verificati,
corroborandoli con l'identità Wikidata e con la fonte ufficiale. Ogni
opera non ancora completa viene rivalutata nei refresh successivi: una
vecchia presentazione generica non viene mai considerata un successo
editoriale definitivo. I candidati con date imminenti hanno priorità,
indipendentemente dal teatro; il budget di ricerca per le opere sconosciute
è di dodici candidati per ciclo, con rotazione equa per quelle senza data.

Quando non esistono ancora fatti sufficienti per formulare una trama
originale affidabile, il sistema registra `verified_plot_unavailable`.
Quando la trama esiste ma non si riescono a documentare i dati storici,
registra `verified_premiere_history_unavailable`. La ricerca
**non inventa né la sinossi né i dati di prima rappresentazione**.
Gli elementi già verificati vengono conservati e completati nei refresh
successivi, senza fermare il resto del calendario.

## Sintesi originale da fonti enciclopediche verificate

Per una nuova composizione risolta univocamente in Wikidata, la ricerca
può consultare la sezione *Trama* della sua voce Wikipedia italiana. Il
generatore gratuito e deterministico `scripts/work_plot_generator.py`
produce una frase originale **solo se** individua almeno due azioni
narrative esplicite relative a personaggi in comune. Evita di riprodurre
un paragrafo sorgente o di dedurre personaggi, intenzioni e finali non
documentati. La fonte rimane associata alla candidate.

La copertura è intenzionalmente conservativa: i testi che non seguono
queste costruzioni grammaticali, gli articoli senza trama e quelli con
identità incerta non producono una sinossi. Una sinossi così preparata
non abilita da sola la pubblicazione: sono richiesti anche fatti storici
documentati e tutti i controlli del catalogo. Quando mancano, il testo
viene conservato per i cicli successivi senza fermare le altre opere.
Nessuna chiave API o servizio a pagamento è necessario.

## Completamento integrato della scheda prima della pubblicazione

Il medesimo ciclo di refresh esegue questi controlli prima della promozione
nel catalogo: (1) identità Wikidata univoca coerente con il compositore
della fonte ufficiale; (2) riuso della sinossi specifica già verificata,
altrimenti ricerca della sezione `Trama` italiana e costruzione prudente
di un nuovo testo originale; (3) riuso del profilo di prima rappresentazione,
altrimenti recupero da **Wikidata P87** (librettista), **P1191**
(data della prima), **P4647** (luogo della prima) e **P131**
(località in cui si trova il teatro). Il recupero storico fallisce
esplicitamente se un dato è assente, contraddittorio o non univoco.

`scripts/work_history_research.py` ricostruisce il profilo storico
solo dal QID **della stessa composizione** che ha superato la disambiguazione,
registrando l'URL della fonte. L'anno della prima non viene dedotto
dall'anno di composizione; non si confondono opere omonime.
Una scheda editoriale completa viene promossa nello stesso ciclo, previa
verifica delle date e delle immagini richiesta dal catalogo. Per una
scheda parziale rimangono in coda esclusivamente i dati mancanti, senza
pubblicazioni provvisorie e senza blocco globale.

Il generatore grammaticale rimane conservativo: non è un LLM e non può
scrivere trame per ogni opera. La mancanza di una fonte non è un motivo
per riportare una presentazione generica come se fosse una sinossi.

## Riuso sicuro dei contenuti già verificati

Il refresh riutilizza le sinossi e i dati di prima rappresentazione pubblicati
per un'unica composizione riconosciuta con titolo e compositore coincidenti.
Quando esiste un riferimento editoriale specifico con QID Wikidata, il riuso
richiede **anche** la corrispondenza del QID: gli alias e le opere omonime
non autorizzano accorpamenti per titolo. Se il registro contiene più
composizioni dello stesso titolo, si usano esclusivamente i campi riferiti
al work ID immutabile. Un secondo teatro può riutilizzare un
arricchimento completo già raccolto da un'altra fonte soltanto con
Wikidata QID e compositore identici.

I nuovi report distinguono `authority_not_unique`,
`invalid_authority_data`, `verified_plot_unavailable` e
`verified_premiere_history_unavailable`; non aggregano più tutti
gli errori in un generico `ValueError`. Le candidate non risolte
continuano a essere monitorate, senza impedire nuove pubblicazioni
che superano i controlli.

## Titoli tradotti e diagnostica operativa

Quando lo stesso QID Wikidata documentato identifica una composizione
già pubblicata, il riuso dei contenuti validati è consentito anche se
la denominazione ufficiale del teatro è un titolo alternativo in un'altra
lingua. Il compositore deve coincidere; un titolo diverso senza QID
documentato non è sufficiente. La regola impedisce di trasferire
trame tra opere omonime o composizioni distinte.

Ogni esito di ricerca riporta inoltre `source_key`, `official_url`
e `title_hint`, oltre a codice di errore e candidate ID: è così
possibile classificare gli ostacoli per fonte e per opera dal report
generato dallo stesso refresh, senza dedurli a posteriori dagli URL.
I report più vecchi non possiedono questi nuovi campi.

## Promozione delle recite con titoli alternativi

Il riconoscimento editoriale e la pubblicazione delle recite applicano la
stessa identità canonica. Quando il titolo dell'evento ufficiale differisce
dal titolo dell'opera già pubblicata, il promotore accetta l'abbinamento
**solo** se la candidate possiede un arricchimento Wikidata associato
all'esatto URL e fonte dell'evento e se lo stesso QID è registrato per
la composizione canonica (o nella sua attribuzione editoriale).
Il compositore deve corrispondere in entrambi i record.

La scheda dell'opera conserva titolo e identificativo originali, evitando
copie o composizioni omonime fuse; le date e la sede seguono gli stessi
controlli delle altre recite. Un QID assente o contraddittorio lascia
in attesa soltanto la candidate interessata.

## Ricerca affidabile con limiti di dimensione

La ricerca Wikidata resta **gratuita** e mantiene i limiti di risposta
contro payload sproporzionati. Se un'opera molto documentata supera
il limite della lettura aggregata, il sistema recupera le sole
proprietà indispensabili per l'identità (`P31`, `P7937`, `P86`)
e, per la prima rappresentazione, `P87`, `P1191`, `P4647`.
Nessun dato è ricavato dalla risposta troncata.

Se la ricerca per titolo non fornisce un riscontro esatto, il
compositore **già documentato nella fonte ufficiale** viene usato per
una seconda ricerca; la validazione continua a richiedere etichetta
o alias esatto, tipologia opera e compositore concordante.

La sinossi viene cercata direttamente nella sezione *Trama*,
*Argomento* o *Soggetto* della voce Wikipedia italiana associata
all'esatto QID. In questo modo gli articoli lunghi non bloccano
la ricerca e le sezioni poste oltre l'introduzione restano raggiungibili.
L'assenza di una sezione identificabile univocamente o di due
relazioni narrative esplicite comporta un retry, mai una trama
inventata.

## Candidate già canoniche e candidate prive di credito ufficiale

Il research budget è dedicato alle **composizioni non ancora censite**
che hanno un titolo e un compositore esplicitamente attribuiti dalla
pagina ufficiale della produzione. Una candidata che corrisponde in modo
univoco a un'opera già censita, con identici titolo e compositore
nell'evidenza strutturata del teatro, assume lo stato
`existing_canonical_work`: le sue eventuali nuove rappresentazioni
sono esaminate autonomamente da `scripts.auto_catalogue`, senza nuovi
download enciclopedici o duplicazione della scheda opera.

Una candidata per la quale il connettore non ha acquisito titolo e
compositore verificati resta `awaiting_official_identity_evidence`.
Questo **non equivale a opera completata né a recita pubblicata**.
Il connettore continuerà a essere monitorato e l'opera potrà entrare
nella ricerca quando l'evidenza ufficiale sarà sufficiente.
Una semplice parola nell'URL non è prova di un'opera: il sistema non
deve trasformare programmi didattici, adattamenti o opere omonime
in schede inventate.

Le due categorie non consumano il budget destinato alle opere davvero
nuove. Il report mantiene il legame a candidate, fonte e URL ufficiali
per verificare l'esito in un refresh successivo.

## Generazione automatica
Dopo la pubblicazione del feed editoriale il workflow
`.github/workflows/refresh-catalog.yml` esegue
`python -m scripts.editorial_review_queue` e salva
`data/editorial-review-queue.json` con il resto dei dati canonici.
Il file è rigenerato e controllato con `--check` ad ogni scansione, senza
commit se non è cambiato.

La coda segnala, per ciascun **work_id immutabile**:
- `identity_only_introduction`: testo generato da titolo e compositore,
  prioritario per una sinossi narrativa;
- `historical_facts_missing`: storia d'archivio non ancora verificata,
  meno urgente (Atlas non è un'enciclopedia).

I record riportano titolo, compositore, route, testo corrente e fonti storiche
già disponibili. Non si deduce lo stato dal solo titolo, così omonimi e
composizioni differenti non vengono fusi.

## Collaborazione periodica in ChatGPT e GitHub
Una revisione periodica può leggere questo JSON, scegliere un piccolo numero
di schede ad alta priorità, cercare materiale utilizzabile in fonti verificabili
e proporre una **sinossi originale in italiano di 1–2 frasi (45–220 caratteri)**,
senza copiare testi teatrali né inventare dettagli. Quando i fatti sono
verificabili, aggiornare `site/work-synopses.json` per `work_id` nelle
omonimie, con test, documentazione e PR. Per trame incerte, annotare i
blocchi nel report anziché modificare schede in modo arbitrario. I dati
storici richiedono fonti esplicite; non ricavare la data di composizione
dall'anno della prima.

**La coda non è una lista di errori di pubblicazione** e non obbliga a
intervenire. La scansione e la pubblicazione rimangono autonome. Non creare
issue per ogni opera a ogni esecuzione, né notificare se non ci sono novità
o miglioramenti concreti.

## Verifiche
`python -m unittest discover -s tests -v`; generazione e controllo
`python -m scripts.editorial_review_queue && python -m scripts.editorial_review_queue --check`.
Il codice del catalogo rimane in `opera-atlas`; nessuna pubblicazione SFTP
o modifica a `jeckodevsite` è richiesta per questa coda.

## Schede recuperate da fonti specialistiche verificate (21 novembre 2026)

Le schede di *La clemenza di Tito* (Mozart, Parma), *L'arca di Noè* / `Noye's Fludde` (Britten, La Fenice) e *La rondine* (Puccini, Opera di Roma) non devono attendere indefinitamente che Wikipedia produca automaticamente una trama o che il record Wikidata completo resti sotto i limiti dell'API. I riferimenti editoriali sono conservati in `data/verified-work-authority-seeds.json`; restano legati all'**esatto URL dell'evento ufficiale** e al compositore verificato nella sua evidenza, non al solo titolo o allo slug.

Fonti: Corago, Università di Bologna e Opéra national de Paris per *La clemenza di Tito*; Britten Pears Arts e Boosey & Hawkes per *Noye's Fludde*; Puccini Museum e Opéra de Monte-Carlo per *La rondine*. Il poster originale del libretto (1791) e la locandina storica (1917) sono associati tramite Wikimedia Commons e identificati in `data/archival-work-images.json`. Per Britten, in mancanza di un manifesto storico liberamente verificato, si usa soltanto l'immagine già documentata dalla pagina ufficiale della produzione, senza spacciare immagini di scena per un manifesto del 1958.

La pubblicazione richiede comunque compositore, sede, date e orari esatti dalla fonte ufficiale, sinossi narrativa originale, storia della prima verificata e immagine con provenienza. `tests/test_verified_blocked_opera_editorials.py` esercita la transazione e la sua idempotenza. Le altre candidate prive di prove ufficiali sufficienti **non vengono promosse**.

## Esiti della promozione nella stessa esecuzione

L'algoritmo pubblica prima le recite di opere già canoniche e poi le
opere nuove con schede editoriali e immagini validate. Nel primo
passaggio una nuova composizione può risultare temporaneamente
`unknown_work_needs_authority_data`; se il secondo passaggio la
pubblica realmente, questo errore viene eliminato dal report finale.
La riconciliazione controlla il nuovo URL di produzione nel catalogo
canonico: non elimina i retry delle altre candidate, i problemi di
orario o le candidate soltanto arricchite ma non pubblicate.
Questo mantiene la diagnostica coerente con le opere e le recite effettivamente
aggiunte nello stesso ciclo, senza manipolare i record delle fonti.

## Roma: crediti ufficiali su righe separate

Per le produzioni del Teatro dell'Opera di Roma, `Musica di` e il nome
del compositore possono essere in due blocchi HTML consecutivi, anziché
nella stessa riga. L'estrattore accetta questa variante soltanto quando
l'etichetta `Musica di` è esatta, il blocco seguente contiene un nome
personale verificabile e la pagina mostra stagione 2026/2027, sede
Teatro Costanzi e recite con giorno e ora. Un direttore d'orchestra o
un campo generico non vengono mai scambiati per il compositore.

Per *Una Lady Macbeth del distretto di Mzensk* è disponibile nel registro
di fonti specialistiche una breve sinossi narrativa originale e la storia
della prima del 1934 a Leningrado, con riferimenti a Boosey & Hawkes e
Mariinsky. La scheda verrà pubblicata soltanto quando anche l'evidenza
della recita, la fonte e un'immagine con provenienza soddisferanno i
controlli canonici; un testo editoriale già pronto non autorizza date
ipotetiche o pubblicazione senza manifesto verificato.

## Pubblicazione automatica dei nuovi record editoriali verificati

Un aggiornamento a `data/verified-work-authority-seeds.json` o
`data/verified-work-editorial-attribution.json` su `main` attiva
il workflow `refresh-catalog`, anche se nella stessa modifica non
cambiano script o test. In questo modo una nuova scheda già documentata
può completare l'intero ciclo di acquisizione, verifica, pubblicazione
degli indici JSON e diagnostica senza deploy FTP o interventi manuali.
Il workflow conserva il controllo sulla provenienza dell'immagine e
l'obbligo di date, sede e compositore ufficiali; l'attivazione non
costituisce un bypass della validazione né garantisce che una pagina
incompleta venga pubblicata.

## Chiusura immediata delle candidate già pubblicate

Le candidate che hanno un URL ufficiale **identico** a una produzione
nel manifesto canonico non sono più una revisione aperta: passano a
`already_catalogued` e conservano ID, URL e storico delle scansioni.
La correzione del 21 novembre ha riclassificato in questo modo le
fonti ufficiali de *La rondine*, *L'arca di Noè* e *La clemenza di Tito*,
già pubblicate con nove recite complessive.

Il workflow esegue ora `reconcile_published_candidates` anche nella
fase iniziale di pubblicazione dai dati verificati in cache e salva la
coda riconciliata nello stesso checkpoint. La riconciliazione continua
dopo l'acquisizione delle nuove fonti, proteggendo i casi in cui una
produzione diventi pubblicabile solo durante il refresh corrente.
La coda non viene azzerata artificialmente: le candidate senza opera,
compositore o orari verificati restano aperte finché non c'è evidenza
sufficiente o una classificazione ufficiale di esclusione.

## Donizetti Opera 2026: prima attribuzione di un'opera nuova

L'evento *Le convenienze ed inconvenienze teatrali* espone nella pagina
ufficiale il titolo, il credito esplicito «Musica di Gaetano Donizetti»,
la sede Teatro Donizetti e gli orari delle recite del 15, 20 e 28
novembre 2026. Il nuovo adattatore `donizetti_credited_detail`
acquisisce questi fatti senza dedurre il compositore da cast, URL o
biografia; tratta gli orari individualmente e non pubblica spettacoli
con data o sede ambigue.

La scheda breve e la storia della prima versione riveduta del 1831
(Napoli, Teatro del Fondo) sono legate all'esatto evento ufficiale
nel registro delle fonti. L'opera originaria del 1827 è distinta dalla
versione riveduta del 1831 nella documentazione storica. Come immagine
stabile si utilizza una pagina autografa di Donizetti, digitalizzata
dalla Bibliothèque nationale de France, resa disponibile in pubblico
dominio su Wikimedia Commons; è descritta come *manoscritto storico*,
non come manifesto di una produzione recente.

Riferimenti: pagina ufficiale Donizetti Opera 2026,
`https://corago.unibo.it/opera/Z000002027` e
`https://commons.wikimedia.org/wiki/File:Le_Convenienze_teatrali_(manuscrit_autographe)_-_btv1b108620224_(052_of_254).jpg`.

## Completamento editoriale Cagliari, Trieste e Roma (21 novembre 2026)

Cinque opere con **26 rappresentazioni** già descritte da fonti teatrali
accreditate risultavano in retry a causa di sinossi non estratte da
Wikipedia: *Lohengrin* (Trieste, 6 recite), *Don Carlos*, *Alcina*,
*Maria Stuarda* (Cagliari, 5 recite ciascuna) e *La Cenerentola*
(Roma, 5 recite). Si usano sinossi originali molto brevi, storie della
prima documentate e materiale d'epoca autentico: nessuna scheda
enciclopedica estesa, nessuna fotografia promozionale sostituita a un
manifesto storico.

Le fonti editoriali specialistiche sono Mariinsky (Lohengrin), Corago
Università di Bologna e Metropolitan Opera (Don Carlos), Händel Society
e Bayerische Staatsoper (Alcina), Corago e Bayerische Staatsoper
(Maria Stuarda), Archivio Storico Opera di Roma e Rossini Opera Festival
(La Cenerentola). I riferimenti restano nei record
`data/verified-work-authority-seeds.json`, esattamente associati
all'URL ufficiale di ciascuno spettacolo e al suo compositore.

Le immagini pubbliche appartengono al registro
`data/archival-work-images.json`: spartito/riduzione d'epoca per
*Lohengrin*, locandina del 1867 di *Don Carlos*, frontespizi originali
dei libretti di *Alcina* (1735), *Maria Stuarda* (1835) e *La
Cenerentola* (1817, già censito). Ogni descrizione distingue il
materiale storico dalla produzione teatrale futura.

Il controllo `tests/test_five_new_opera_editorials.py` verifica
corrispondenza dei crediti, 26 date/ore già acquisite, provenienza
Commons, validità storica e idempotenza della transazione. La
pubblicazione deve comunque validare integralmente i medesimi fatti,
senza eccezioni rispetto alle altre opere.

## Due ulteriori candidate documentate: Alahor ed Elisir

*Alahor in Granata* è documentata direttamente dal programma ufficiale
Donizetti Opera 2026: opera di Gaetano Donizetti, libretto attribuito
alla sigla M.A. (non espansa arbitrariamente), prima Palermo al Teatro
Carolino nel 1826; rappresentazioni con ore precise al Teatro Sociale
il 14, 22 e 27 novembre 2026. Copertina stabile: frontespizio del libretto
1826 digitalizzato dalla Library of Congress, tramite Wikimedia Commons.

*L’elisir d’amore* ha sei recite triestine già registrate con ore complete.
Il vecchio parser includeva erroneamente `Melodramma` nel campo
compositore. Per questa composizione non ancora canonica, il promotore
rimuove quella parola esclusivamente a fronte di un seed editoriale
verificato, collegato allo stesso URL ufficiale, con titolo, compositore,
sinossi e prima documentati; per gli altri titoli rimangono i controlli
canonici normali. La prima è confermata al Teatro della Canobbiana di
Milano, 1832, da Rai Cultura e Corago; il frontespizio originale del
libretto del 1832 proviene da Wikimedia Commons.

Entrambe le schede sono brevi e orientate agli spettacoli, non
all'enciclopedia. Nessuna data può essere pubblicata sulla base di un
manifesto o di una sinossi: il sistema richiede sempre evidenza oraria
della rappresentazione specifica. I test `test_donizetti_alahor_and_elisir.py`
verificano sorgente, identità, immagini e promozione idempotente.

## Riconciliazione dei crediti del compositore (22/11/2026)

Il risolutore condiviso `opera_atlas.work_identity.resolve_work` riconosce, oltre al credito esatto, soltanto quattro tipologie strettamente delimitate di metadati che possono seguire un compositore **già presente nel registro canonico**: `Opera`, `Tragedia`, `Melodramma` e anni di nascita/morte tra parentesi (`AAAA–AAAA` oppure `AAAA-AAAA`). Non vengono modificati il nome del compositore in ingresso, il titolo originale o gli ID delle opere; la risoluzione avviene contro un'unica corrispondenza verificata nel registro.

I crediti arbitrari, i compositori diversi e i titoli omonimi non sono mai risolti automaticamente. Gli alias multilingua rimangono vincolati al compositore canonico. Le candidate prive di sufficiente evidenza restano in revisione, senza creazione di duplicati e senza promozione forzata. I test coprono i sei casi di metadati emersi nella diagnostica (Carmen, La bohème, L’elisir d’amore, Madama Butterfly, Norma e Aida) e le regressioni sui casi ambigui.

## Classificazione delle identità ancora sconosciute (22/11/2026)

La diagnostica di riconciliazione classifica come `composer_credit_to_review` **soltanto** un credito contaminato per il quale è disponibile un suggerimento di corrispondenza a una specifica opera canonica. Se la coppia titolo/compositore non trova corrispondenza e non è disponibile quel suggerimento, il caso è `new_work_candidate`, indipendentemente dal fatto che il compositore abbia già altre opere nel registro. L'assenza di compositore resta `missing_composer`.

Questa classificazione non promuove opere né attribuisce nuovi ID: serve a distinguere le vere opere non catalogate (come le tre componenti del *Trittico* e *Don Pasquale*) dai problemi di parsing dei crediti. La pubblicazione rimane subordinata ai controlli editoriali e alle evidenze storiche. Le schede delle produzioni multiopera mantengono distinte le componenti anche quando condividono data e sede.

## Identità canoniche riservate per programmi verificati (22/11/2026)

Il registro `data/identity-registry.json` mantiene una sezione `reserved_works` per identità editorialmente verificate, ma ancora prive di una produzione autonoma nel catalogo v2. Il 22/11 sono stati assegnati in modo permanente gli ID `oa-w-000090` (*Don Pasquale*, Donizetti), `oa-w-000091` (*Il tabarro*, Puccini), `oa-w-000092` (*Suor Angelica*, Puccini) e `oa-w-000093` (*Gianni Schicchi*, Puccini). Gli ID sono unici rispetto agli altri canali e non devono essere riassegnati. Le schede editoriali corrispondenti sono verificate in `data/reviewed-program-work-editorials.json`.

Il risolutore centralizzato e il generatore dei programmi considerano le identità riservate per associare correttamente i componenti del *Trittico* alla singola programmazione di Jesi, senza creare tre produzioni e senza moltiplicare i due biglietti per data. L'integrità degli ID e delle schede viene controllata nella compilazione del catalogo v2, **ma le opere riservate non vengono ancora esposte nel canale v2 `works`**, che richiede una produzione canonica collegata. La futura promozione di una voce riservata a `works` deve preservarne l'ID e completare tutti gli altri canali, non crearne uno nuovo. Le candidate storiche non diventano automaticamente nuove recite pubblicate.

## Pubblicazione di opere verificate senza messa in scena autonoma (22/11/2026)

Il canale canonico v2 `works` include anche le quattro opere con identità permanente in `reserved_works` (ID da `oa-w-000090` a `oa-w-000093`), classificate `catalog_status: program_component`. Le loro sinossi e prime rappresentazioni provengono dal registro editoriale verificato `data/reviewed-program-work-editorials.json` e sono pubblicate in `work-editorial.json`. Non viene creato alcun nuovo staging o biglietto fittizio in v2; le due date del *Trittico* restano nel feed `programs.json` come singolo programma multiopera. La directory delle opere consulta il canale canonico `works`, non soltanto le rappresentazioni. Una scheda opera senza recite autonome rimane apribile e mostra la sua storia, anche quando non vi sono date future. Il frontend carica i dati GitHub senza richiedere un nuovo deploy FTP per ogni aggiornamento.

Quando una di queste opere sarà promossa a una messa in scena autonoma, l'ID viene trasferito da `reserved_works` a `works` senza modifica dell'URL canonico e senza collisioni di ID. Il refresh deve pubblicare e validare insieme feed v2, editoriale e programmi.
