# Ferrara – opera 2026/27 con doppia verifica ufficiale

**Problema risolto:** il portale diretto del Teatro Comunale Claudio Abbado presenta restrizioni d'accesso. Non le aggiriamo. Usiamo invece due fonti pubbliche istituzionali: la [rassegna della Regione Emilia-Romagna](https://spettacolo.emiliaromagnacultura.it/it/rassegna/teatro-comunale-ferrara-opera-danza-2026-2027/) per confermare che ogni opera sia programmata **a Ferrara** con un intervallo di date esatto, e il [depliant 2026/27 pubblicato dalla Fondazione Teatro Comunale](https://cartellone.emiliaromagnacultura.it/wp-content/uploads/2026/09/Depliant_Opera_Danza_2026.pdf) per identità musicale, giorno e orario di ogni singola recita.

Il file `data/ferrara-opera-2026-27.json` contiene evidenze versionate per **cinque opere e dieci recite**: Macbeth / Giuseppe Verdi (27 e 29 novembre 2026), Il barbiere di Siviglia / Gioachino Rossini (15 e 17 gennaio 2027), Dido and Aeneas / Henry Purcell (20 e 21 febbraio), La clemenza di Tito / Wolfgang Amadeus Mozart (12 e 14 marzo), Simon Boccanegra / Giuseppe Verdi (9 e 11 aprile). La prima rappresentazione è alle ore 20:00, la seconda alle 16:00, come nel depliant.

Gli spettacoli di danza, il concerto *A Christmas Welcome*, lo spettacolo *L’anno che verrà*, l'incontro *Prima della Prima* e le attività scolastiche non sono recite liriche ordinarie. Le date regionali rappresentano talvolta un intervallo; le **ore** non vengono mai ricavate dall'intervallo, ma soltanto dal depliant emesso dal teatro.

## Architettura

Le cinque identità di opera sono cinque source-key indipendenti all'interno del comune `season-index-config.json`. Tutte puntano alla **stessa pagina ufficiale regionale** e condividono il fetcher condizionato ai controlli robots. Per ogni source-key il parser richiede il titolo corretto nella sezione del singolo evento, la sede Ferrara, l'intervallo regionale verificato e le due recite del depliant ufficiale. Soltanto allora produce una candidata.

È fondamentale che una produzione già pubblicata **non chiuda le altre quattro** soltanto perché usano l'identico URL della rassegna; la riconciliazione controlla titolo e compositore, oltre alla sede e all'URL. Ogni opera viene quindi trattata dalla pipeline centrale, senza un catalogo parallelo e senza FTP.

L'indice viene dichiarato `operational` soltanto dopo una scansione ufficiale riuscita. Il successo di una scansione non garantisce l'aggiornamento di una stagione successiva: nuove stagioni richiedono nuove evidenze ufficiali verificate. Nessuna API a pagamento.

## Comportamenti da collaudare

```sh
python -m unittest tests.test_ferrara_official_source -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

Dopo merge verificare in `data/season-index-health.json` cinque sorgenti Ferrara, nella coda candidate cinque osservazioni **distinte** e nel catalogo canonico le recite effettivamente promosse. Non attribuire a Ferrara produzioni del medesimo circuito che si svolgono a Modena, Piacenza o Reggio Emilia.
