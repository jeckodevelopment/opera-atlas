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
