# Opera Atlas — architettura economica e durevole

**Decisione confermata 2026-11-20:** il catalogo vive su GitHub, il frontend su un hosting statico esistente. Il dataset si aggiorna senza trasferire nuovamente il frontend con SFTP.

## Ruoli e responsabilità

| Livello | Repository / hosting | Funzione | Costo infrastrutturale incrementale |
| --- | --- | --- | --- |
| Fonti ufficiali | Siti teatri/festival | Pubblicazione delle programmazioni | Nessun servizio nostro |
| Input editoriale | `opera-atlas/data` | Fonti approvate, ID e provenienza persistente | Repository Git |
| Elaborazione | `opera-atlas/scripts` e Python stdlib | Validazioni, catalogo versionato e controlli | Quota GitHub Actions |
| Archivio canonico | SQLite locale/operator + registro ID JSON Git | Riconciliazione, audit e identità | Nessun DBaaS |
| Pubblicazione JSON | `opera-atlas/public/catalog/v2/` | Feed pubblico tramite GitHub Raw | Nessun server dedicato |
| UI | `opera.plus/atlas/` | HTML/CSS/JS statici, caricamento feed CORS | Hosting esistente |
| Deploy frontend | Workflow SFTP nativo `opera-atlas` | Trasferimento sui cambi UI, credenziali proprie e rollback | Segreti del nuovo hosting |

### Identità (catalogo v2)

La produzione artistica in un luogo in una stagione è una **messa in scena pubblica**, con ID `oa-s-xxxxxx`. Le sue repliche hanno ID `oa-r-xxxxxx`, anche quando l'orario manca. Le opere hanno `oa-w-xxxxxx`, i teatri `oa-v-xxxxxx`. Gli slug di città/teatro/opera sono attributi distinti; il generatore rifiuta duplicazioni dei percorsi. Il registry committato è la fonte di verità delle identità: **mai riassegnare un ID**.

L'URL editoriale desiderato è `/opere/<slug>/`, `/<citta>/<teatro>/`, `/<citta>/<teatro>/<opera>/`. Il supporto HTTP tramite rewrite e la UI per raggruppare le recite sono ancora da sviluppare: il solo campo `staging.url` nel feed non li rende immediatamente accessibili. Le stagioni con lo stesso teatro e opera richiedono una scelta esplicita dello slug qualificato.

### Pubblicazione consistente dei dati

L'insieme è suddiviso in `works`, `venues`, `stagings`, `performances`. Ogni canale è serializzato ordinatamente e salvato con SHA-256 nel nome. Il workflow scrive prima le parti immutabili, poi aggiorna `manifest.json`, un unico puntatore piccolo, nello **stesso commit**. Il client verifica i SHA-256 degli asset. Una cache che consegna un manifesto vecchio rimanda comunque ai file della versione corrispondente; non c'è rischio di leggere metà release.

I file immutabili rimangono nella repository: questo semplifica rollback e riproducibilità, ma richiederà nel tempo una politica di pulizia dei file non più referenziati dopo un periodo prudenziale (non immediata, per mantenere valide le cache). Nessuna chiave, password o dato personale va pubblicato.

### Schedulazione e sicurezza della raccolta

`refresh-catalog.yml`: ogni giorno alle **07:17 UTC**, e su variazione delle fonti editoriali committate. Oggi il job valida e materializza dati già verificati; il numero di recite **non cresce automaticamente** finché non vengono aggiunti connettori live approvati e provati. Un errore di build impedisce il commit; se non cambia alcun dato, non si crea un commit inutile.

Le future acquisizioni devono poter operare esclusivamente su sorgenti con `access_status=approved` e robots/policy verificate. Ogni fetch deve avere timeout, limiti di frequenza, errori isolati, riconciliazione e audit. La perdita temporanea di una fonte **non** è una cancellazione. Lo stato SQLite tra job dovrà essere reso persistente/versionabile o ricostruibile dai record normalizzati, prima di schedulare davvero la raccolta. L'accesso delle fonti ancora pending non viene autorizzato dall'esecuzione quotidiana del workflow.

### Pubblicazione della UI e verifiche

Frontend SFTP indipendente: solo il repository `opera-atlas` contiene `.github/workflows/deploy-atlas.yml`, il publisher `scripts/deploy_atlas.py` e i test applicativi. Il deploy usa credenziali del nuovo hosting, trasferisce file frontend statici nella cartella `/atlas`, verifica via HTTPS anche i deep link e, in caso di esito negativo, ripristina la versione precedente. Il workflow dati rimane distinto: `site/catalog-client.js` carica il catalogo JSON su GitHub tramite HTTPS/CORS con digest e fallback locale. `jeckodevsite` non è coinvolto nel nuovo processo.

La configurazione dell'hosting, la compatibilità delle rewrite, la gestione offline e il comportamento su browser mobili richiedono collaudo end-to-end. Per versioni future, valutare uno snapshot di riserva periodico solo se necessario, senza introdurre SFTP quotidiano né un backend dedicato.

## Routing statico e costi
Gli URL canonici sono risolti dal browser dalla path, con rewrite Apache **solo** verso `detail.html`. Non occorre rigenerare HTML per ogni messa in scena, quindi nuove schede e nuovi teatri diventano navigabili subito dopo l'aggiornamento del feed, senza SFTP. L'unica configurazione server consiste nel file `site/.htaccess`, da pubblicare e collaudare con la prima modifica del frontend. I vecchi URL query rimangono compatibili; mantenere `legacy_id` finché serviranno le migrazioni dei vecchi link.

## Schedulazione incrementale autorizzata
La pipeline di `refresh-catalog.yml` contiene `scripts.daily_ingest`, che usa uno SQLite **in memoria e temporaneo** soltanto per imporre le regole del fetch ufficiale. I dati persistenti sono due JSON nel Git: osservazioni curate e registry ID, aggiornati solo per nuove date non ambigue. Un'integrazione GitHub Actions pubblica stato e JSON in uno stesso commit, senza SFTP. I connettori iniziali restano disabilitati finché accesso e parser non sono verificati: il sistema fallisce in modo sicuro senza scartare recite già pubblicate. Vedi [SOURCE_ONBOARDING](SOURCE_ONBOARDING.md).

## Migrazione hosting Opera+ — 20/11/2026

Destinazione pubblica `https://opera.plus/atlas/`, con `<base href="/atlas/">` su tutte le pagine, `RewriteBase /atlas/` e prefisso delle route ricavato da `document.baseURI`, senza riferimenti al dominio o alla directory del vecchio hosting nel codice. I feed GitHub canonici sono volutamente URL assoluti esterni, perché i loro aggiornamenti sono indipendenti da SFTP. La riscrittura richiede Apache con `.htaccess`/mod_rewrite o regole equivalenti configurate sull'hosting. **Pubblicazione non attiva finché mancano le credenziali SFTP del nuovo spazio e la verifica DNS/TLS:** per configurazione e collaudi vedere [DEPLOY_OPERA_PLUS](DEPLOY_OPERA_PLUS.md).
