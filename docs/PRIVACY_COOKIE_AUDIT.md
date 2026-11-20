# Opera+ Atlas — verifica privacy e cookie
**Data:** 20 novembre 2026 — verifica statica del codice pubblicato su GitHub.

## Funzionamento rilevato
- Sito HTML/CSS/JavaScript statico: nessun login, form contatti, pagamenti o profili utente.
- Nessun sistema di marketing, pubblicità, analytics o pixel inserito negli script Atlas. Ricerca e filtri rimangono nel browser; non risultano scritture a `document.cookie`, `localStorage` o `sessionStorage`.
- Catalogo da `raw.githubusercontent.com`; mirror di continuità `cdn.jsdelivr.net`; fallback locale.
- Immagini editoriali da `commons.wikimedia.org`, che possono trasferire l'indirizzo IP all'host esterno. Alcuni loghi e fallback SVG sono interni al sito.
- L'utente avvia la geolocalizzazione cliccando il pulsante, che attiva il permesso nativo del browser. Le coordinate del dispositivo vengono usate solo localmente per associare la città censita più vicina. Non è attiva la geolocalizzazione automatica.
- Collegamenti esterni a teatri/biglietterie/festival e OpenStreetMap sono aperti a seguito di selezione.
- Header Apache, quando `mod_headers` è disponibile: Referrer-Policy `no-referrer`, Permissions-Policy `geolocation=(self)`, X-Content-Type-Options `nosniff`.

## Scelta cookie: nessun banner non necessario
In base alle [Linee guida cookie del Garante del 10 giugno 2021](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9677876), un banner di consenso non è richiesto se sono usati esclusivamente cookie tecnici e non vengono installati altri strumenti di profilazione/tracciamento. Nella versione di Atlas esaminata non vi sono tali funzionalità introdotte dal codice applicativo: pertanto è prevista **un'unica pagina Privacy e cookie** e non viene aggiunto un banner decorativo. L'assenza nel codice non dimostra, da sola, l'assenza assoluta di cookie installati dall'hosting, dal CDN e da fornitori esterni.

## Informativa pubblicata
`site/privacy.html` espone titolare Associazione Opera+, sede legale, C.F., email istituzionale, tipi di dati tecnici, finalità e basi giuridiche, geolocalizzazione facoltativa, richieste ai fornitori, trattamento dei cookie, diritti GDPR e reclami al Garante. Il footer di **tutte** le pagine riporta il collegamento all'informativa e il C.F. dell'Associazione.

## Verifiche ancora necessarie prima di dichiarare la conformità completa
- [ ] **Browser e rete pubblicata**: registrare una sessione HAR pulita in finestra anonima, verificando `Cookies`, `Set-Cookie`, `localStorage`, `sessionStorage`, third-party requests e redirect di Wikimedia, GitHub e jsDelivr. Testare prima di qualsiasi interazione e dopo geolocalizzazione volontaria. L'ambiente automatico di sviluppo non certifica il comportamento del server di produzione.
- [ ] **Hosting e responsabili del trattamento:** acquisire condizioni contrattuali del provider, eventuale DPA art. 28, policy e tempi di conservazione dei log e Paesi di trattamento; documentarli internamente e specificare, se possibile, il periodo o criteri più precisi in informativa.
- [ ] **Email privacy e sede:** verificare che `info@opera.plus` riceva le richieste e che la sede pubblicata sia aggiornata.
- [ ] **Fornitori esterni:** controllare eventuali cookie di terzi, identificatori o tracciamenti non necessari. Se presenti, rimuoverli oppure bloccarli fino a idoneo consenso preventivo, con preferenze revocabili e rifiuto semplice.
- [ ] **Revisione legale finale** dell'informativa (in particolare ruoli, trasferimenti extra-SEE, legittimo interesse e retention) dopo la conferma dei servizi effettivamente in produzione.
- [ ] **Rilasci futuri:** una regressione automatica deve intercettare nuove API di tracking, cookie e domini esterni prima del merge.

## Metodo di pubblicazione
Sviluppo, test e documentazione solamente nel repository `opera-atlas`. L'aggiornamento HTML/CSS/SVG e della nuova pagina informativa avviene mediante **solo** workflow SFTP in `jeckodevsite`. Il feed JSON resta indipendente.
