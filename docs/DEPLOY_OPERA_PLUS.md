# Pubblicare Opera+ Atlas su opera.plus/atlas

## Architettura e perimetro

**URL canonico:** https://opera.plus/atlas/. Il repository applicativo e il publisher sono entrambi `jeckodevelopment/opera-atlas`. Il repository `jeckodevelopment/jeckodevsite` non è coinvolto nel nuovo deploy; il vecchio sito può restare disponibile durante la migrazione, senza ulteriori modifiche necessarie per la pubblicazione nuova.

- **Interfaccia:** `site/` → `/atlas/` sul nuovo hosting, tramite workflow [deploy-atlas.yml](../.github/workflows/deploy-atlas.yml) e [deploy_atlas.py](../scripts/deploy_atlas.py).
- **Catalogo:** `public/catalog/v2/manifest.json`, feed per opere/sedi/allestimenti/repliche e indici editoriali rimangono nel Git pubblico, aggiornati automaticamente da `refresh-catalog.yml`, **senza** un SFTP quotidiano.
- **URL:** `<base href="/atlas/">` nei cinque HTML; `RewriteBase /atlas/` nelle rewrite Apache; `catalog-client.js` e `detail.js` ricavano il prefisso da `document.baseURI` e non codificano più il vecchio host. Gli URL assoluti verso GitHub, jsDelivr e le fonti ufficiali sono esterni per scelta e non sono URL della vecchia installazione.

## Prerequisiti del server

1. Verificare che il dominio **opera.plus** punti all'hosting corretto e disponga di certificato HTTPS valido.
2. Creare una cartella web dedicata `atlas` **sotto la document root pubblica di opera.plus**. Il percorso **SFTP assoluto** esatto dipende dal provider (per esempio `/home/ACCOUNT/public_html/atlas`, solo illustrativo); non copiarlo da jeckodevsite. Il workflow verifica che il percorso termini in `/atlas`.
3. Verificare che la directory padre sia accessibile in lettura/scrittura all'utente SFTP e che Apache gestisca `.htaccess` e `mod_rewrite`. Per Nginx o hosting che ignora `.htaccess`, predisporre manualmente rewrite equivalenti per `/atlas/opere/{slug}/`, `/atlas/produzioni/{id}/`, `/atlas/{città}/{teatro}/` e `/atlas/{città}/{teatro}/{opera}/` verso `/atlas/detail.html` prima del primo deploy.
4. Collegare i seguenti **GitHub Actions Secrets** a `opera-atlas` (preferibilmente nell'environment `opera-plus-atlas`):
   - `ATLAS_SFTP_HOST`: hostname del nuovo server, senza protocollo.
   - `ATLAS_SFTP_PORT`: porta (opzionale, default 22).
   - `ATLAS_SFTP_USERNAME`: account autorizzato a pubblicare esclusivamente `/atlas`.
   - `ATLAS_SFTP_REMOTE_DIR`: percorso SFTP **assoluto della cartella atlas**, non radice web e non radice dell'account.
   - `ATLAS_SFTP_KNOWN_HOSTS`: riga/e OpenSSH `known_hosts` verificate fuori banda con il provider, comprensive dell'eventuale notazione `[host]:port` per porta non standard. **Non** aggiungere host key automaticamente dal server durante il deploy.
   - **Uno solo** tra `ATLAS_SFTP_PRIVATE_KEY` (chiave privata SSH) e `ATLAS_SFTP_PASSWORD` (password).
   - `ATLAS_SFTP_KEY_PASSPHRASE` soltanto se la chiave privata è cifrata.
5. Su GitHub impostare un environment di nome `opera-plus-atlas` con i segreti necessari. Non pubblicare o incollare valori segreti in issue, PR o documentazione. La repository utilizza la chiave host fissata e rifiuta host sconosciuti.

## Prima pubblicazione controllata

1. Unire la PR applicativa dopo il superamento dei test. Il nuovo workflow, in modalità `push`, non esegue la pubblicazione finché la variabile **`ATLAS_DEPLOY_ENABLED` non è `true`**.
2. Dal repository `opera-atlas` aprire *Actions → Publish Opera Atlas to opera.plus/atlas → Run workflow*. Questo primo rilascio manuale usa lo stesso codice del deploy successivo.
3. Il publisher copia solo la allowlist di 19 file statici, aggiunge impronte agli URL CSS/JS, trasferisce tutto in `.atlas-stage-...`, verifica byte-per-byte via SFTP, sposta atomico per quanto consentito dal filesystem la directory esistente in backup, attiva il nuovo contenuto e confronta via HTTPS gli asset con i file locali. Verifica anche i deep link canonici. Un errore prima o dopo l'attivazione tenta di ripristinare la directory precedente.
4. Collaudare su **https://opera.plus/atlas/**: Elenco e Calendario; filtri città/raggio/periodo; scheda Opera; scheda Teatro; scheda Produzione; produzione condivisa; manifesto, sinossi e storia; fonti e Privacy; link esterni «Come arrivare».
5. Aprire in una nuova sessione browser e verificare che nessun collegamento rimandi a `/dev/opera-atlas/`, che CSS/JS restino disponibili nei percorsi annidati e che i JSON GitHub continuino ad aggiornarsi senza deploy SFTP.
6. Solo dopo collaudo riuscito, impostare la variabile repository **`ATLAS_DEPLOY_ENABLED=true`** per attivare i rilasci UI automatici a ogni push su main che cambia `site/**`, lo script publisher o il workflow. I normali refresh del catalogo JSON non avviano questo publisher.

## Verifica del cutover e dismissione del vecchio flusso

Il rilascio non è concluso finché non sono verificati DNS/TLS, configurazione SFTP, rewriting, fingerprint HTTPS e percorsi pubblici. Prima di quel momento il vecchio sito non viene eliminato. Dopo il collaudo, disabilitare il precedente workflow `publish-opera-atlas.yml` su `jeckodevsite` e, se desiderato, impostare un redirect permanente dai vecchi URL alla stessa path relativa su `https://opera.plus/atlas/`, **solo dopo aver verificato gli URL più usati**. Il redirect richiede accesso al vecchio web server, non viene imposto dal codice nuovo. Non spegnere altri servizi presenti su `jeckodevsite`.

## Risoluzione problemi

- **Secret mancante/host sconosciuto:** configurazione o host key da verificare; nessuna connessione insicura alternativa.
- **403 o 404 sugli asset:** controllare directory remota e document root pubblica: SFTP e web server potrebbero vedere percorsi differenti.
- **404 sulle schede annidate:** `.htaccess` o regole rewrite mancanti sul nuovo hosting.
- **JSON non aggiornato:** verificare che il browser possa raggiungere HTTPS `raw.githubusercontent.com` o il mirror jsDelivr, non eseguire SFTP per riparare un feed.
- **Verifica HTTPS fallita:** il job esegue rollback della cartella gestita; controllare il report di Actions e la configurazione del dominio.

## Confini di sicurezza

Il publisher rifiuta destinazioni come `/`, `/atlas` o qualsiasi cartella non terminante in `/atlas`; non segue i symlink locali, non copia file fuori allowlist e non incorpora segreti nell'artefatto. Il deploy è deliberatamente limitato alla sottocartella Atlas, per non sovrascrivere il sito principale opera.plus.
