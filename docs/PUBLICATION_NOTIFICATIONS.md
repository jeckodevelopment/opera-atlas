# Notifiche diagnostiche di pubblicazione (Resend)

Il workflow `.github/workflows/refresh-catalog.yml` invia una notifica per **ogni nuova opera** e **ogni nuova produzione** solo dopo un push del catalogo accettato da GitHub. Il controllo usa gli ID immutabili nei feed pubblici v2 prima e dopo il checkpoint. Nuove recite, variazioni di data, sinossi e poster non provocano una nuova email. Il checkpoint rapido e quello finale hanno baseline indipendenti; non occorre deploy SFTP.

## Configurazione GitHub Actions

Configurare nella repository `jeckodevelopment/opera-atlas`:

- **Secret** `RESEND_API_KEY`: chiave API Resend con permesso invio.
- **Secret** `ATLAS_NOTIFICATION_FROM`: mittente verificato in Resend, esempio `Opera Atlas <notifiche@dominio-verificato.example>`.
- **Secret** `ATLAS_NOTIFICATION_TO`: elenco di indirizzi destinatari separati da virgola (o a capo), ad esempio `primo@example.org,secondo@example.org`. Un'unica richiesta Resend consegna l'avviso a tutti gli indirizzi configurati.

La chiave non deve comparire nei file del progetto. Il dominio mittente deve essere verificato presso Resend. Se manca una delle tre configurazioni, il catalogo continua a pubblicarsi e il workflow registra un warning; non viene effettuato alcun invio di prova verso indirizzi inventati.

Ogni email include tipo dell'evento, titolo, ID permanente, teatro/città o compositore e URL pubblico. Il template HTML usa una intestazione testuale OPERA+ ATLAS nero/oro, un pulsante oro verso la scheda, etichette diagnostiche leggibili e layout a tabelle compatibile con client email anche mobili. È inclusa una versione `text/plain` per l'accessibilità e i client che non renderizzano HTML. Tutti i campi provenienti dal catalogo sono escapati; non sono necessari asset remoti, immagini o tracking pixel. L'header `Idempotency-Key` è basato sull'ID immutabile dell'entità per mitigare ripetizioni. Un errore della API Resend viene segnalato nei log senza interrompere il catalogo. Non viene garantita la consegna finale nella casella: una risposta positiva dell'API equivale ad accettazione di invio.

## Verifiche

`python -m unittest tests.test_publication_notifications -v`

Collaudi di integrazione: configurare le tre credenziali, pubblicare in staging una nuova opera con relativa produzione, verificare due email; ripetere il refresh senza cambiamenti e verificare zero email; aggiungere una diversa produzione della stessa opera e verificare una sola email; simulare un errore Resend e verificare che il push resti valido. Verificare che entrambi i destinatari ricevano la notifica senza che gli indirizzi compaiano nel repository o nei log. Le nuove recite non devono generare email. I messaggi vengono inviati nel workflow di produzione, non nei test.

## Pubblicazioni dirette tramite Pull Request

Anche il workflow `.github/workflows/notify-catalog-publications.yml` intercetta le modifiche al manifesto pubblico v2 effettuate da una PR unita a `main` (o da un push manuale). Confronta la versione pubblicata prima del push (`github.event.before`) e il nuovo commit (`github.sha`), utilizzando gli stessi ID canonici e lo stesso servizio Resend. Questo risolve il caso delle opere già inserite nel feed dalla PR prima dell'esecuzione del refresh.

I commit catalogo prodotti dal workflow `refresh-catalog` mediante `GITHUB_TOKEN` non attivano un secondo workflow `push` ricorsivo; le rispettive notifiche restano gestite nel workflow originario. La stessa chiave d'idempotenza basata sull'ID permanente protegge da reinvii involontari. Il job aggiuntivo non esegue scansioni né pubblica JSON.

### Ripetizione controllata di una notifica saltata

Il workflow aggiuntivo espone `workflow_dispatch` con `base_sha` (revisione precedente alla pubblicazione) e `entity_ids` (elenco facoltativo di ID separati da virgola). La ripetizione notifica **soltanto** entità presenti nel feed pubblico corrente e assenti nel feed della baseline. Per recuperare esattamente le due notifiche delle opere del Petruzzelli, inserire:

- `base_sha`: `b0804e1c3772602b8eef550f1e1cb2121ea374a8`
- `entity_ids`: `oa-w-000077,oa-w-000078`

Il replay invia email reali a tutti i destinatari configurati: eseguirlo una sola volta dopo aver verificato il mittente Resend. Non usare `entity_ids` vuoto nel replay storico se non si intende notificare tutte le opere e produzioni nuove dall'epoca della baseline. Nessun valore dei secret è inserito nel repository o nei log.

## Diagnosi degli HTTP 403 di Resend

Quando Resend rifiuta una notifica, nei log GitHub Actions viene registrato lo stato HTTP e, se disponibile, soltanto il campo strutturato `name`/`code` della risposta API (ammessi caratteri alfanumerici, `_` e `-`). Il messaggio completo e il body JSON non sono mai stampati, per non divulgare indirizzi o token. I campi `ATLAS_NOTIFICATION_FROM` e `RESEND_API_KEY` restano secret GitHub.

Se un HTTP 403 non appare nei log della dashboard Resend, verificare che si stia visualizzando la **stessa organizzazione/team** a cui appartiene la chiave API e controllare le **restrizioni di dominio** della chiave stessa. L'assenza di log nella dashboard non dimostra che l'API non sia stata contattata: il codice HTTP viene restituito dalla richiesta HTTPS del workflow.

Un errore nella consegna non compromette la pubblicazione del catalogo. Per recuperare notifiche saltate, usare il replay con filtro `entity_ids` documentato sopra, dopo aver corretto la causa del rifiuto.
