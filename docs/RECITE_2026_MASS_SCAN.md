# Scansione massiva retrospettiva 2026

**Sola diagnostica, mai pubblicazione.** Questo job nazionale analizza tutte le fonti-indice
approvate nella configurazione corrente (88 al checkpoint del 23/11/2026).
Sono esplorati gli URL ufficiali già noti e le pagine di dettaglio scoperte
dalle scansioni: non si inventano archivi o URL per anni precedenti.

## Esecuzione
```bash
python -m unittest tests.test_audit_2026_mass_scan -v
python -m scripts.audit_2026_mass_scan --allow-network \
    --workers 5 --max-detail-pages 750 \
    --output public/diagnostics/atlas-2026-mass-scan.json
```

Il workflow `.github/workflows/audit-2026-mass-scan.yml` svolge i test
sulle PR; al primo push su main che introduce lo scanner esegue la scansione
massiva. È possibile una nuova esecuzione manuale con GitHub Actions.

## Protezioni
- Il fetch riutilizza `opera_atlas.controlled_fetch.fetch_official_html`: policy
  approvata, HTTPS e hostname identico, robots.txt, dimensione/timeout limitati,
  niente redirect automatici.
- Fino a cinque worker tra host differenti, mai contemporanei sullo stesso host,
  almeno un secondo tra richieste consecutive sullo stesso host.
- Massimo 120 indici approvati, 750 dettagli complessivi, 15 per sorgente. Gli
  URL oltre soglia sono contati come differiti nel report, non dimenticati.
- I fallimenti sono registrati `unverified`, non vengono scambiati per stagioni
  vuote. Un sito del 2026/27 non garantisce recupero del primo semestre 2026.
- Il parser iniziale accetta solo metadati evento espliciti (JSON-LD) datati
  2026. Ogni record rimane `needs_independent_validation` e non assume mai
  che l'evento sia opera lirica o aperto al pubblico generale.
- Unicamente `public/diagnostics/atlas-2026-mass-scan.json` può essere scritto
  sul ramo main dal workflow, mediante push non forzato. Il catalogo pubblico,
  i connettori, la coda candidati e le evidenze ufficiali approvate non cambiano.

## Limiti
La scansione massiva non recupera necessariamente fonti storiche eliminate o
non indicizzate: non si può certificare completezza senza denominatore ufficiale.
Le candidate del JSON devono essere riconciliate per opera, sede, data/ora,
pubblico, annullamenti e festival prima di qualunque decisione editoriale.
