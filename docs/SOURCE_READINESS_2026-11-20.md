# Verifica readiness connettori – 20 novembre 2026

## Esito operativo

| Sorgente | Pagina produzione | robots.txt | Stato scansione quotidiana |
| --- | --- | --- | --- |
| Teatro Regio Torino | https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata | Non verificabile dal controllo esterno in questa sessione | **pending** |
| OperaLombardia | https://www.operalombardia.it/l-italiana-in-algeri/ | Non verificabile dal controllo esterno in questa sessione | **pending** |

Entrambe le pagine ufficiali sono consultabili e confermano la struttura dei dati già censiti: Regio presenta date e orari espliciti per *La traviata*, OperaLombardia conferma date e teatri per *L’italiana in Algeri* senza gli orari. **La consultabilità della pagina non è prova che una scansione automatica sia consentita**. Non sono state cambiate le autorizzazioni del registro `data/daily-source-config.json`, né impostate prove fittizie in `approval_evidence`.

Il sito del Regio pubblica una pagina di copyright con licenza CC BY-NC-ND 3.0 per i contenuti; Opera Atlas non riutilizza testi, immagini o descrizioni ma solo dati fattuali, con link alla pagina ufficiale. Queste condizioni, da sole, **non costituiscono autorizzazione per crawler**.

## Controlli implementati nel blocco

- Nessuna acquisizione automatica da fonti `pending`; blocco anche se il flag approvato non è accompagnato da evidenza documentata.
- Il fetch HTTP effettivo richiede HTTPS, dominio esatto, `robots.txt` disponibile e compatibile, timeout, limiti dimensioni e assenza di redirect.
- Una singola pagina con dati contraddittori o possibili spostamenti ora blocca **tutte** le nuove recite proposte dalla stessa pagina; prima era possibile una pubblicazione parziale.
- Tutte le ore vengono normalizzate rispetto a `Europe/Rome` con offset stagionale, rifiutando ore inesistenti e ambigue nel cambio ora legale.
- Il catalogo precedente e gli ID già assegnati restano invariati se la verifica non è concludente.

## Cosa manca per abilitare realmente

1. Verifica documentata delle regole di accesso su ciascun dominio, inclusi robots e condizioni di utilizzo, eseguita dall'ambiente che farà le scansioni.
2. Test di parsing su HTML reale autorizzato e confronto integrale delle recite con il catalogo ufficiale, senza duplicati o presunzioni.
3. PR specifica per passare da `pending` a `approved` con evidenza dettagliata, quindi primo run controllato di GitHub Actions e verifica delle tracce.
4. Estensione a nuove opere e teatri con mappature canoniche e ID assegnati dal catalogo.

La schedulazione quotidiana dei JSON è già attiva nella repository di Opera Atlas; **non** significa che i due connettori siano già attivi. Non è necessario SFTP per questi controlli.

## Autorizzazione condizionata dell'operatore — 20/11/2026
L'operatore del catalogo ha autorizzato espressamente l'avvio di controlli quotidiani sulle pagine pubbliche di Teatro Regio Torino e OperaLombardia **soltanto in assenza di regole ostative in robots.txt**. La consultazione manuale precedente non aveva consentito di verificare robots.txt: il nuovo stato `approved` in `data/daily-source-config.json` rappresenta **il consenso a tentare la verifica e l'acquisizione condizionata**, non la certificazione che i siti permettano lo scraping.

La funzione `fetch_official_html` verifica **ogni volta** `robots.txt` prima della pagina di produzione. Se il file è irraggiungibile, malformato, contiene un divieto per il nostro user agent o l'URL reindirizza ad altro host, il fetch della pagina non avviene. Le risposte HTML fasulle su `robots.txt` sono trattate come errore. Nessun aggiramento, autenticazione, copia di descrizioni, immagini o HTML integrale; vengono esportati solo titolo, teatro, città, data, ora eventualmente presente e collegamento alla fonte. La frequenza rimane una volta al giorno per pagina, con timeout e limiti esistenti.

**Interpretazione degli stati:** `approved` indica l'autorizzazione dell'operatore a *provare* una scansione sotto controllo, non un permesso attribuito dal teatro; `robots_blocked` o `robots_unavailable` nell'esito operativo prevale sempre e impedisce l'acquisizione. Gli esiti tecnici sono da controllare dopo il primo workflow live, poiché la consultazione esterna non ha potuto accedere a robots.txt.
