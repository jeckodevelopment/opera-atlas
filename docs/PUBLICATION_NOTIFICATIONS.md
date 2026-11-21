# Notifiche diagnostiche di pubblicazione (Resend)

Il workflow `.github/workflows/refresh-catalog.yml` invia una notifica per **ogni nuova opera** e **ogni nuova produzione** solo dopo un push del catalogo accettato da GitHub. Il controllo usa gli ID immutabili nei feed pubblici v2 prima e dopo il checkpoint. Nuove recite, variazioni di data, sinossi e poster non provocano una nuova email. Il checkpoint rapido e quello finale hanno baseline indipendenti; non occorre deploy SFTP.

## Configurazione GitHub Actions

Configurare nella repository `jeckodevelopment/opera-atlas`:

- **Secret** `RESEND_API_KEY`: chiave API Resend con permesso invio.
- **Variable** `ATLAS_NOTIFICATION_FROM`: mittente verificato in Resend, esempio `Opera Atlas <notifiche@dominio-verificato.example>`.
- **Variable** `ATLAS_NOTIFICATION_TO`: email destinataria diagnostica.

La chiave non deve comparire nei file del progetto. Il dominio mittente deve essere verificato presso Resend. Se manca una delle tre configurazioni, il catalogo continua a pubblicarsi e il workflow registra un warning; non viene effettuato alcun invio di prova verso indirizzi inventati.

Ogni email include tipo dell'evento, titolo, ID permanente, teatro/città o compositore e URL pubblico. L'header `Idempotency-Key` è basato sull'ID immutabile dell'entità per mitigare ripetizioni. Un errore della API Resend viene segnalato nei log senza interrompere il catalogo. Non viene garantita la consegna finale nella casella: una risposta positiva dell'API equivale ad accettazione di invio.

## Verifiche

`python -m unittest tests.test_publication_notifications -v`

Collaudi di integrazione: configurare le tre credenziali, pubblicare in staging una nuova opera con relativa produzione, verificare due email; ripetere il refresh senza cambiamenti e verificare zero email; aggiungere una diversa produzione della stessa opera e verificare una sola email; simulare un errore Resend e verificare che il push resti valido. Le nuove recite non devono generare email. I messaggi vengono inviati nel workflow di produzione, non nei test.
