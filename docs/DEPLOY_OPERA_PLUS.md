# Pubblicare Opera+ Atlas su opera.plus/atlas

## Architettura e perimetro

**URL canonico:** https://opera.plus/atlas/. Il repository applicativo e il publisher sono entrambi `jeckodevelopment/opera-atlas`. Il repository `jeckodevelopment/jeckodevsite` non è coinvolto nel nuovo deploy; il vecchio sito può restare disponibile durante la migrazione, senza ulteriori modifiche necessarie per la pubblicazione nuova.

- **Interfaccia:** `site/` → `/atlas/` sul nuovo hosting, tramite workflow [deploy-atlas.yml](../.github/workflows/deploy-atlas.yml) e [deploy_atlas_simple_ftp.py](../scripts/deploy_atlas_simple_ftp.py).
- **Catalogo:** `public/catalog/v2/manifest.json`, feed per opere/sedi/allestimenti/repliche e indici editoriali rimangono nel Git pubblico, aggiornati automaticamente da `refresh-catalog.yml`, **senza** un FTP quotidiano.
- **URL:** `<base href="/atlas/">` nei cinque HTML; `RewriteBase /atlas/` nelle rewrite Apache; `catalog-client.js` e `detail.js` ricavano il prefisso da `document.baseURI` e non codificano più il vecchio host. Gli URL assoluti verso GitHub, jsDelivr e le fonti ufficiali sono esterni per scelta e non sono URL della vecchia installazione.

## Configurazione OVH: SFTP su porta 22

Il publisher usa **SFTP via SSH sulla porta 22**, non FTP in chiaro o FTPS. Per il cluster 121, quando il secret storico contiene `ftp.cluster121.hosting.ovh.net`, il codice utilizza automaticamente l'endpoint SSH OVH `ssh.cluster121.hosting.ovh.net`. Il nome del secret non cambia; OVH documenta esplicitamente l'hostname `ssh.clusterXXX.hosting.ovh.net` e la porta 22.

**Riutilizzo dei secret esistenti** nell'environment GitHub `opera-plus-atlas`:

- `ATLAS_SFTP_HOST`: host già configurato (FTP di OVH o endpoint SSH).
- `ATLAS_SFTP_USERNAME`, `ATLAS_SFTP_PASSWORD`: credenziali dell'utente abilitato a SFTP.
- `ATLAS_SFTP_REMOTE_DIR`: destinazione remota assoluta, terminante in `/atlas`.
- `ATLAS_SFTP_PRIVATE_KEY`, `ATLAS_SFTP_KEY_PASSPHRASE`, `ATLAS_SFTP_KNOWN_HOSTS`: opzionali, se già presenti, senza richiederne la creazione.

Non servono nuovi secret né cambi di nome. L'accesso SFTP dell'utente deve essere attivo nel pannello OVH; SSH e SFTP possono condividere le stesse credenziali FTP quando abilitati.

### Percorso remoto e home OVH

La home fisica indicata da OVH è `/homez.2168/operapw`. Il server SFTP può esporre questa come directory iniziale `/` oppure come percorso completo: per questo il publisher legge la directory iniziale effettiva e verifica l'esistenza del **padre** della destinazione configurata, senza dedurre a priori che il sito pubblico sia in `www`. Se il percorso contiene già la home, prova anche il corrispondente percorso relativo al confinamento SFTP; se è relativo alla home, verifica il corrispondente percorso assoluto. In caso di assenza del padre, si ferma **prima di trasferire file**. Verificare nel pannello OVH il percorso document root del dominio `opera.plus` per scegliere il valore definitivo del secret `ATLAS_SFTP_REMOTE_DIR`.

Il publisher copia soltanto i file frontend previsti, crea `/atlas` se il padre esiste e non cancella file estranei; non effettua rename remoti o rollback. Il sito principale e il catalogo JSON GitHub restano separati.

## Prima pubblicazione controllata

1. Unire la PR applicativa dopo il superamento dei test. Il nuovo workflow, in modalità `push`, non esegue la pubblicazione finché la variabile **`ATLAS_DEPLOY_ENABLED` non è `true`**.
2. Dal repository `opera-atlas` aprire *Actions → Publish Opera Atlas to opera.plus/atlas → Run workflow*. Questo primo rilascio manuale usa lo stesso codice del deploy successivo.
3. Il publisher crea una cartella temporanea locale con i soli 19 file statici autorizzati e li carica direttamente via SFTP/22. Non rimuove file estranei sul server. Il controllo funzionale della pubblicazione va eseguito tramite HTTPS dopo il caricamento.
4. Collaudare su **https://opera.plus/atlas/**: Elenco e Calendario; filtri città/raggio/periodo; scheda Opera; scheda Teatro; scheda Produzione; produzione condivisa; manifesto, sinossi e storia; fonti e Privacy; link esterni «Come arrivare».
5. Aprire in una nuova sessione browser e verificare che nessun collegamento rimandi a `/dev/opera-atlas/`, che CSS/JS restino disponibili nei percorsi annidati e che i JSON GitHub continuino ad aggiornarsi senza deploy FTP.
6. Solo dopo collaudo riuscito, impostare la variabile repository **`ATLAS_DEPLOY_ENABLED=true`** per attivare i rilasci UI automatici a ogni push su main che cambia gli asset HTML/CSS/JS/SVG o `.htaccess`, lo script publisher o il workflow. I normali refresh del catalogo JSON non avviano questo publisher.

## Verifica del cutover e dismissione del vecchio flusso

Il rilascio non è concluso finché non sono verificati autenticazione SFTP, URL HTTPS, rewrite e percorsi pubblici. Prima di quel momento il vecchio sito non viene eliminato. Dopo il collaudo, disabilitare il precedente workflow `publish-opera-atlas.yml` su `jeckodevsite` e, se desiderato, impostare un redirect permanente dai vecchi URL alla stessa path relativa su `https://opera.plus/atlas/`, **solo dopo aver verificato gli URL più usati**. Il redirect richiede accesso al vecchio web server, non viene imposto dal codice nuovo. Non spegnere altri servizi presenti su `jeckodevsite`.

## Risoluzione problemi

- **Autenticazione SSH/SFTP negata:** verificare che l'utente OVH abbia il protocollo SFTP abilitato; il workflow usa la porta 22 e l'endpoint SSH del cluster.
- **Directory padre assente:** il processo non carica nulla. Confrontare la home SFTP rilevata con la document root assegnata a `opera.plus` nella scheda Multisito OVH; la home fisica non basta a identificare la directory web.
- **Host key non corrispondente:** aggiornare l'eventuale `ATLAS_SFTP_KNOWN_HOSTS` se contiene l'identità di un server differente. Il publisher non stampa le credenziali.
- **Asset 403/404 o URL annidate:** controllare percorso pubblico e rewrite in `.htaccess`.
- **Catalogo JSON:** continua a essere aggiornato direttamente dal Git pubblico, senza trasferimenti SFTP.

## Confini di sicurezza

Il publisher rifiuta destinazioni come `/` e qualsiasi cartella non terminante in `/atlas` (mentre `/atlas` è consentita per un account SFTP confinato); non segue i symlink locali, non copia file fuori allowlist e non incorpora segreti nell'artefatto. Il deploy è deliberatamente limitato alla sottocartella Atlas, per non sovrascrivere il sito principale opera.plus.
