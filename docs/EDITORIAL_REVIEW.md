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
originale affidabile, il sistema registra
`verified_plot_and_history_unavailable` e **non inventa una sinossi**.
Questo è un limite esplicito: la ricerca automatica attuale non scrive
una trama nuova usando un modello linguistico. La pubblicazione delle
altre opere e dei calendari verificati prosegue normalmente.

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
