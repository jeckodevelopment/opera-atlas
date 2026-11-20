# Opera Atlas

Catalogo nazionale delle rappresentazioni di opera lirica in Italia e osservatorio statistico collegato al progetto culturale Opera+.

> Stato: fase 1 — schema SQLite, riconciliazione delle recite cross-source e test disponibili. Nessuna programmazione pubblicata finché le fonti e le recite non saranno state verificate.

## Obiettivi

- Catalogo di opere, produzioni, recite, teatri, festival e organizzatori, senza duplicati.
- Mappa interattiva dei luoghi e geolocalizzazione facoltativa.
- Raccolta automatica e tracciabile da fonti ufficiali, con controlli di qualità.
- Statistiche sul repertorio e sulla distribuzione geografica e temporale.

## Sviluppo locale

Richiede Python 3.12+ e SQLite con JSON1 (nessuna dipendenza Python esterna per lo storage).

```bash
python -m unittest discover -s tests -v
python -c "from opera_atlas.db import connect, migrate; c=connect('atlas.sqlite3'); migrate(c); c.close()"
```

Il file `atlas.sqlite3` è un artefatto locale di lavorazione, non un dataset pubblico di spettacoli. Vedi [schema, riconciliazione e limitazioni](docs/STORAGE.md), [piano 1.0.0](docs/PROJECT_PLAN.md) e [registro delle fonti](docs/SOURCE_REGISTRY.md).

## Processo

Tutte le modifiche funzionali tramite pull request con test, documentazione nella stessa PR e Semantic Versioning. Licenze e policy di raccolta dati, mappe e materiali di terze parti saranno verificate prima della pubblicazione.

## Registro sorgenti
Gli otto ingressi ufficiali iniziali verificati sono in [data/sources.json](data/sources.json). Per validarli e importarli nel database di lavorazione, dopo la migrazione:
```bash
python -c "from opera_atlas.db import connect,migrate; from opera_atlas.source_registry import seed_sources; c=connect('atlas.sqlite3'); migrate(c); print(seed_sources(c)); c.commit(); c.close()"
```
Le sorgenti sono inizialmente `pending`: nessuna scansione automatica è attivata da questa operazione.

## Importazione offline: primo connettore
Disponibile la pipeline di parsing, riconciliazione ed esportazione JSON per snapshot salvati delle pagine di dettaglio del Teatro Regio di Torino. **Non è ancora attiva una scansione automatica del sito.** Il parser richiede date/ore effettive, opera e compositore canonici, fonte approvata e luogo verificato; ignora i periodi generici delle stagioni. Vedi [guida al connettore](docs/REGIO_CONNECTOR.md) e relativi test.

### Controllo dell'accesso e monitoraggio
Il modulo `opera_atlas.scan_cli` consente una **singola** richiesta HTTP per pagina, solo se il gestore ha già verificato e approvato la fonte nel database. Richiede `--allow-network` e controlla `robots.txt` prima della pagina; indisponibilità o divieto bloccano l'accesso. Nessun crawler periodico è attivato. Gli esiti sono in `source_checks` (solo metadati), migrazione v4. Dettagli in [REGIO_CONNECTOR](docs/REGIO_CONNECTOR.md).

## Esecuzione controllata e audit (migrazione v4)
Il 20/11/2026 il percorso ufficiale `/opera-e-balletto-2026-2027/la-traviata` mostrava 11 righe distinte di recite (dal 26 febbraio al 10 marzo 2027), tra cui recite pomeridiane alle 15:00. Questa verifica è stata fatta consultando la pagina pubblica, **non** eseguendo il crawler della repository. Il parser rimane da confrontare con la sorgente HTML effettivamente scaricabile, che può avere struttura diversa da quella visibile nelle pagine renderizzate.

`robots.txt` non è risultato accessibile dal sistema di verifica; il comportamento necessario è **fail closed** fino a verifica da ambiente operativo. Nessuna approvazione di crawling discende dalla presenza di un URL pubblico.

```sh
# Esegue una singola verifica controllata (solo se fonte già approvata nel DB)
python -m opera_atlas.scan_cli --db atlas.sqlite3 --url https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata --source-id 1 --venue-id 1 --production-id 1 --title "La traviata" --composer "Giuseppe Verdi" --allow-network
# Il comando senza --apply esegue rollback delle modifiche e non conserva il log.
# Con --apply salva recite e metadati di verifica nel database (mai HTML integrale).
```

La verifica rispetta: URL HTTPS e hostname esatto, redirects rifiutati, richiesta robots.txt precedente alla pagina, User-Agent identificabile, response HTML, limite 2 MB, timeout 12 secondi. Nessun retry e nessuna scansione ricorsiva. Lo storico `source_checks` registra esito, impronta SHA-256, dimensione e numero di recite, senza copiare il testo dell'ente. Le scansioni negate registrano solo il motivo tecnico se `--apply` è usato.

**Limiti:** la soluzione non gestisce rate limiting globale tra esecuzioni, ETag/304, parser per altri teatri, errori di import con log persistente o gestione completa degli spostamenti di programma. Prima di abilitare schedulazioni serviranno policy di accesso verificate, monitoraggio delle frequenze e collaudi live. Le fixture di test sono sintesi redatte autonomamente, non copie della pagina.

### Batch di produzioni (Fase 2)
Disponibile `python -m opera_atlas.batch_cli` con manifesto JSON verificato, massimo 20 pagine, preflight delle sorgenti e savepoint di isolamento per pagina. Richiede `--allow-network` per qualsiasi accesso e `--apply` per salvare il risultato. Nessuna scansione periodica o autorizzazione implicita. Vedi [guida al connettore](docs/REGIO_CONNECTOR.md).

### Variazioni di stato delle recite
Le conferme, i rinvii e gli annullamenti verificati possono essere registrati tramite `opera_atlas.changes.set_performance_status` con fonte approvata e motivazione. La cronologia è append-only nella migrazione SQLite v5. Non sono dedotti annullamenti dalle recite scomparse e non è ancora attivo il rilevamento automatico dei cambi data. [Dettagli e collaudi](docs/REGIO_CONNECTOR.md).
