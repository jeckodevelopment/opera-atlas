# Reggio Emilia — connettore Opera 2026/27 al Teatro Municipale Valli

Fonte ufficiale: [I Teatri, archivio Opera](https://www.iteatri.re.it/tipo/opera/), con **quattro** produzioni della stagione 2026/27: *Macbeth*, *Death in Venice*, *Simon Boccanegra* e *La clemenza di Tito*. Ogni scheda è un URL `https://www.iteatri.re.it/spettacolo/<slug>/` e pubblica titolo, compositore, teatro, date e orari.

L'indice è estratto soltanto dall'area `Opera Stagione` fino a `In evidenza`, evitando che l'elenco globale di concerti e altre produzioni diventi coda dell'opera. Il parser del dettaglio richiede **Teatro Municipale Valli** e categoria **Opera**, il compositore esplicitamente accreditato e le righe di biglietteria contenenti giorno, mese, anno e ora. Non usa date di cast, banner o eventi correlati.

Le **prove generali riservate** non sono recite ordinarie. Esempio: *Macbeth* presenta prova generale under 28 il 18 novembre 2026, con riga biglietteria gratuita, e due rappresentazioni ordinarie il **20 novembre 2026 alle 20:00** e **22 novembre alle 15:30**. Le righe di prova con importo 0,00 € sono escluse; data duplicata, orari mancanti, modifica di formati, cancellazioni non riconciliate bloccano la proposta.

Il catalogo rimane unico. I dati sono candidati raccolti dalla pipeline nazionale dopo fetch per origine ufficiale, soggetto a controllo robots.txt. Non vengono replicate descrizioni del teatro né avviati deploy FTP per cambiare JSON.

**Verifiche:** `python -m unittest tests.test_reggio_valli_source -v`, suite Python completa e `python -m scripts.source_automation --check`; dopo merge verificare stato del nuovo indice in `data/season-index-health.json`, candidate e successiva pubblicazione autonoma. Reggio passa prima a `configured_not_operational` e poi a `operational` soltanto dopo una scansione riuscita. Il successo dell'indice non è prova di copertura totale delle recite.

Fonte per il titolo di *Macbeth*: https://www.iteatri.re.it/spettacolo/macbeth-2/ ; fonte per il calendario: https://www.iteatri.re.it/tipo/opera/.
