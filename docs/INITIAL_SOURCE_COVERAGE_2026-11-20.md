# Copertura delle otto fonti iniziali — 20/11/2026

## Regola di veridicità
Una fonte nell'inventario non equivale a un teatro pienamente catalogato. Questo report distingue l'avvio con **almeno una produzione verificata** dal completamento della stagione e dall'automazione live. Nessun nuovo adapter è approvato soltanto perché è possibile leggere una pagina in un browser. `robots.txt` e parser devono essere verificati nei runner che acquisiranno i dati. Le copie dei contenuti editoriali, foto e programmi non vengono archiviate.

| Fonte iniziale | Produzioni già documentate | Stato copertura | Acquisizione giornaliera |
|---|---|---|---|
| Teatro Regio Torino | 9 opere del cartellone principale 2026/27, 73 recite | Cartellone principale censito; altri programmi separati | **Attiva**, robots-gated |
| OperaLombardia | 5 titoli presso Teatro Fraschini Pavia (10 recite) + L'italiana in Algeri in 4 teatri (8 recite) | **Parziale**: tournée delle altre opere in Como, Brescia, Cremona e altre sedi da verificare | **Attiva** per 1 pagina circuito + 4 pagine partner; robots-gated |
| Teatro alla Scala Milano | Otello di Verdi, 9 recite tra dicembre 2026 e gennaio 2027 | Parziale: ulteriori opere e stagioni da censire | **Non attiva**: adattatore e robots da testare |
| Fondazione Arena di Verona | Aida, allestimento Gianfranco de Bosio, 9 recite estate 2027 | Parziale: Aida Stefano Poda e altre opere del festival, distinguere allestimenti e Teatro Filarmonico | **Non attiva** |
| Teatro La Fenice Venezia | Fedora, 7 recite novembre 2026 | Parziale: altre opere e sede Teatro Malibran da verificare. **13/11 annullata**, non pubblicata come recita attiva | **Non attiva** |
| Teatro Massimo Palermo | Samson et Dalila 6 recite novembre 2026 e Macbeth 5 febbraio 2027 | Parziale: ulteriori opere della lunga stagione da censire, Sala Grande verificata | **Non attiva** |
| Teatro Regio di Parma | Madama Butterfly, 4 recite ordinarie aprile 2027 | Parziale: altri spettacoli della stagione e Festival Verdi, prove aperte/Under30 non confuse con recite ordinarie | **Non attiva** |
| Rossini Opera Festival Pesaro | Il programma 2027 e le prime date sono stati annunciati, ma la pagina calendario è bloccata HTTP 403 nell'ambiente di ricerca | **Non censito nel JSON**: non attribuire sede/orario a date non individualmente corroborate | **Non attiva**, non aggirare il 403 |

## Dettagli di provenienza per primo ampliamento nazionale
- [Otello, Teatro alla Scala](https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello.html): serata inaugurale 7/12 ore 18 e otto recite pubblicate fino al 5/1 2027. L'anteprima Under30 del 4 dicembre non è inserita senza verifica separata dell'orario.
- [Aida 1913, Arena di Verona](https://www.arena.it/arena-opera-festival/aida-ed-gianfranco-de-bosio/): 9 recite fra giugno e agosto 2027, con orari 21:30/21:15/21:00, sede Arena. Non unificare con l'altra produzione *Aida* di Stefano Poda della stessa stagione, che necessita un URL qualificato.
- [Fedora, La Fenice](https://www.teatrolafenice.it/event/fedora/): il teatro dichiara espressamente cancellata la prima del **13 novembre 2026**, pur presente tra le date acquistabili nell'HTML. Restano 7 repliche non annullate, 14–22 novembre 2026.
- [Samson et Dalila](https://www.teatromassimo.it/event/samson-et-dalila/) e [Macbeth](https://www.teatromassimo.it/event/macbeth/), Teatro Massimo Palermo: 6 + 5 recite con orari individuali e sede Sala Grande.
- [Madama Butterfly, Teatro Regio di Parma](https://teatroregioparma.it/spettacolo/madama-butterfly/): 4 recite ordinarie il 16, 18, 22 e 24 aprile 2027, esclusi la prova Under30 del 12 e la prova aperta del 14 aprile.

## Architettura e prossime attività
L'import di questa tranche è **editoriale e verificato**, non una nuova scansione live; i sei URL sono nell'allowlist del generatore e sono collegati a ciascun evento. Non sono stati aggiunti a `daily-source-config.json` con `approved` perché gli adapter dei nuovi host non sono stati collaudati. Il catalogo v2 resta servito da GitHub in maniera automatica senza SFTP.

Per completare davvero il mandato: (1) continuare OperaLombardia nei singoli teatri e riconciliare le coproduzioni; (2) censire le ulteriori produzioni e orari delle cinque fonti con primo campione; (3) affrontare ROF tramite pagine ufficiali singole liberamente raggiungibili, senza aggirare il calendario bloccato; (4) sviluppare test parser e controlli robots per ogni dominio, solo dopo verifiche reali; (5) mantenere ID e percorsi permanenti, distinguendo produzioni diverse della stessa opera e stesso teatro per stagione/allestimento.
