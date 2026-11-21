# Pubblicare Opera+ Atlas su opera.plus/atlas

## Architettura e perimetro

**URL canonico:** https://opera.plus/atlas/. Il repository applicativo e il publisher sono entrambi `jeckodevelopment/opera-atlas`. Il repository `jeckodevelopment/jeckodevsite` non è coinvolto nel nuovo deploy; il vecchio sito può restare disponibile durante la migrazione, senza ulteriori modifiche necessarie per la pubblicazione nuova.

- **Interfaccia:** `site/` → `/atlas/` sul nuovo hosting, tramite workflow [deploy-atlas.yml](../.github/workflows/deploy-atlas.yml) e [deploy_atlas_simple_ftp.py](../scripts/deploy_atlas_simple_ftp.py).
- **Catalogo:** `public/catalog/v2/manifest.json`, feed per opere/sedi/allestimenti/repliche e indici editoriali rimangono nel Git pubblico, aggiornati automaticamente da `refresh-catalog.yml`, **senza** un FTP quotidiano.
- **URL:** `<base href="/atlas/">` nei cinque HTML; `RewriteBase /atlas/` nelle rewrite Apache; `catalog-client.js` e `detail.js` ricavano il prefisso da `document.baseURI` e non codificano più il vecchio host. Gli URL assoluti verso GitHub, jsDelivr e le fonti ufficiali sono esterni per scelta e non sono URL della vecchia installazione.

## Prerequisiti del server

1. L'hosting deve rendere disponibile `/atlas/` via HTTPS e consentire le rewrite Apache per le schede.
2. Il publisher usa **FTP semplice in chiaro (non FTPS e non SFTP)**, modalità passiva sulla **porta 21**, perché il server indicato non implementa `AUTH TLS`.
3. I **secret esistenti conservano i loro nomi**, senza alcuna reinstallazione nell'environment `opera-plus-atlas`:
   - `ATLAS_SFTP_HOST`: hostname FTP del server;
   - `ATLAS_SFTP_USERNAME`: nome utente FTP;
   - `ATLAS_SFTP_PASSWORD`: password FTP;
   - `ATLAS_SFTP_REMOTE_DIR`: directory remota che termina con `/atlas`.
   I nomi storici `SFTP` sono usati per compatibilità; non indicano il protocollo effettivo. Porta 21 fissata nel workflow, il secret storico `ATLAS_SFTP_PORT` non viene utilizzato.
4. Non esistono override dell'hostname: il workflow legge direttamente `ATLAS_SFTP_HOST`. Evitare duplicati o override di configurazione.
5. **Avvertenza di sicurezza:** FTP semplice **non cifra credenziali, comandi né file trasferiti**; il traffico può essere intercettato sulla rete. Usare un account dedicato con privilegi circoscritti a `/atlas`; restringere gli IP sorgenti presso il provider se disponibile e preferire il ripristino di un trasporto cifrato appena possibile. Nessuna credenziale deve apparire nel repository o nei log.
6. Il deploy usa `lftp` con FTP passivo senza TLS: crea/aggiorna i file statici previsti sotto `/atlas` e non cancella gli altri file. Non esegue rinomine atomiche o rollback: è un caricamento diretto e semplificato. Il controllo dei file sorgente avviene prima della connessione. Non considerare una pubblicazione riuscita prima del collaudo della pagina HTTPS.
7. Le chiavi SSH/known_hosts storiche non sono usate.

## Prima pubblicazione controllata

1. Unire la PR applicativa dopo il superamento dei test. Il nuovo workflow, in modalità `push`, non esegue la pubblicazione finché la variabile **`ATLAS_DEPLOY_ENABLED` non è `true`**.
2. Dal repository `opera-atlas` aprire *Actions → Publish Opera Atlas to opera.plus/atlas → Run workflow*. Questo primo rilascio manuale usa lo stesso codice del deploy successivo.
3. Il publisher crea una cartella temporanea locale con i soli 19 file statici autorizzati e li carica direttamente via FTP in modalità passiva. Non rimuove file estranei sul server. Il controllo funzionale della pubblicazione va eseguito tramite HTTPS dopo il caricamento.
4. Collaudare su **https://opera.plus/atlas/**: Elenco e Calendario; filtri città/raggio/periodo; scheda Opera; scheda Teatro; scheda Produzione; produzione condivisa; manifesto, sinossi e storia; fonti e Privacy; link esterni «Come arrivare».
5. Aprire in una nuova sessione browser e verificare che nessun collegamento rimandi a `/dev/opera-atlas/`, che CSS/JS restino disponibili nei percorsi annidati e che i JSON GitHub continuino ad aggiornarsi senza deploy FTP.
6. Solo dopo collaudo riuscito, impostare la variabile repository **`ATLAS_DEPLOY_ENABLED=true`** per attivare i rilasci UI automatici a ogni push su main che cambia gli asset HTML/CSS/JS/SVG o `.htaccess`, lo script publisher o il workflow. I normali refresh del catalogo JSON non avviano questo publisher.

## Verifica del cutover e dismissione del vecchio flusso

Il rilascio non è concluso finché non sono verificati configurazione FTP, URL HTTPS, rewrite e percorsi pubblici. Prima di quel momento il vecchio sito non viene eliminato. Dopo il collaudo, disabilitare il precedente workflow `publish-opera-atlas.yml` su `jeckodevsite` e, se desiderato, impostare un redirect permanente dai vecchi URL alla stessa path relativa su `https://opera.plus/atlas/`, **solo dopo aver verificato gli URL più usati**. Il redirect richiede accesso al vecchio web server, non viene imposto dal codice nuovo. Non spegnere altri servizi presenti su `jeckodevsite`.

## Risoluzione problemi

- **Login FTP rifiutato:** confrontare host e utente realmente usati in FileZilla (senza pubblicare la password) con quelli nell'environment GitHub, verificare che l'account FTP non limiti gli IP sorgenti o le connessioni da servizi cloud. Un codice `530` può anche indicare host/account/ACL non corrispondenti.
- **Directory FTP non valida:** controllare la document root vista dall'account FTP e la directory padre di `/atlas`.
- **403/404 asset o rewrite:** controllare pubblicazione web, `.htaccess` e riscritture delle URL annidate.
- **Verifica HTTPS fallita:** controllare gli asset pubblicati e ripetere il deploy dopo la correzione; il caricamento diretto non prevede rollback.
- **Aggiornamenti JSON:** continuano dal catalogo Git pubblico, senza deploy FTP.

## Confini di sicurezza

Il publisher rifiuta destinazioni come `/` e qualsiasi cartella non terminante in `/atlas` (mentre `/atlas` è consentita per un account FTP confinato); non segue i symlink locali, non copia file fuori allowlist e non incorpora segreti nell'artefatto. Il deploy è deliberatamente limitato alla sottocartella Atlas, per non sovrascrivere il sito principale opera.plus.
