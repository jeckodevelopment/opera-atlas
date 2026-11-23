# F1 — Audit del registro nazionale delle fonti (23 novembre 2026)

> Documento di sola verifica. **Non autorizza né modifica scansioni**, non cambia connettori, parser, ID canonici, catalogo, robots, termini o policy. La fonte operativa dello stato rimane la diagnostica generata, non il vecchio elenco degli otto enti pilota.

## Fonti machine-readable e definizioni

| Fonte | Ambito | Stato riscontrato nel checkpoint |
| --- | --- | --- |
| `data/venue-directory.json` | Anagrafica di sedi fisiche, con organizzatori separati | **70 sedi** e **19 organizzazioni correlate**, ultimo `reviewed_on=2026-11-21` |
| `data/sources.json` | Le **8 fonti pilota storiche**, non il registro nazionale | **8** righe; non è la fonte di verità per la copertura attuale |
| `data/daily-source-config.json` | Monitoraggio delle singole pagine di produzione | **19** fonti configurate |
| `data/season-index-config.json` | Monitoraggio degli indici di stagione per fonte | **87** fonti configurate |
| `data/season-index-health.json` | Esito per indice, prove di scansione, controlli future stagioni | **87** record; checkpoint `2026-11-23T18:30:44Z` |
| `public/catalog/source-automation.json` | Copertura delle sedi tramite fonti configurate/alternative | **69** sedi `operational`, **1** `not_automated`, su **70** sedi |
| `docs/SOURCE_REGISTRY.md` | Elenco editoriale originario di sedi, festival e circuiti | Ha ancora molte note del 20/11 ormai superate; non è un feed di monitoraggio |

Il feed definisce `operational` come scansione approvata riuscita **oppure** acquisizione corroborata con recite già pubblicate e verificate. **Non** prova che ogni sito ufficiale sia accessibile, che le 70 stagioni siano complete o che esistano 70 parser individuali distinti.

## Eccezione reale rispetto ai 70 teatri

- **Trapani — Teatro M° Tonino Pardo** (`oa-vd-000070`): il feed `source-automation.json` lo segnala `not_automated`, `configured_connectors: 0`, `recent_successful_connectors: 0`, `source_attention: not_configured`.
- Questa sede non va confusa con il Teatro all'aperto Giuseppe Di Stefano o con gli organizzatori del Luglio Musicale Trapanese. **Non** associare automaticamente il loro connettore a Tonino Pardo per somiglianza geografica. Prima verificare il calendario e le fonti ufficiali della specifica sede.
- Non creare un nuovo connettore se la venue risulta priva di programmazione operistica verificabile; registrare la situazione con evidenza e motivazione. L'operatività del connettore non si deduce dalla mera esistenza della scheda del teatro.

## Attenzione tecnica distinta dalle venue operative

Il feed `public/catalog/source-automation.json` distingue **87 scansioni-indice**:

| Classificazione ultimo checkpoint | Fonti |
| --- | ---: |
| `verified_success` | 69 |
| `access_blocked` | 2 |
| `fetch_unavailable` | 8 |
| `future_programme_not_verified` | 5 |
| `parser_or_source_validation_failed` | 2 |
| `source_content_not_verified` | 1 |

La somma è 87: sono **fonti-indice**, non teatri. Il fatto che una sede sia operativa tramite un canale alternativo non trasforma in riuscita l'acquisizione di tutte le sue fonti. Diagnosticare e risolvere le anomalie nella [#679](https://github.com/jeckodevelopment/opera-atlas/issues/679); monitorare la copertura effettiva delle stagioni nella [#178](https://github.com/jeckodevelopment/opera-atlas/issues/178).

## Requisiti #1 ancora non dimostrati in modo esaustivo

- Per **ogni** venue, festival e circuito, associare e verificare URL di fonte/calendario, ruolo organizzatore vs sede fisica, disponibilità dell'indice e delle singole recite, modalità e data dell'ultimo controllo; non inventare URL né attribuzioni.
- Conservare l'esito effettivo delle verifiche di policy di accesso e robots/termini, separando `non_verificato`, `errore_di_accesso` e `blocco_esplicito`. Il successo di un fallback non certifica la fonte primaria.
- Campionare manualmente ogni regione e tutti i casi controversi. Questa verifica **non è stata eseguita** con il presente audit documentale e resta un collaudo separato.
- Per le venue multi-località e festival, accertare l'identità di ogni spazio fisico e la relazione con le produzioni; niente fusione basata solo su nome/città.
- La lista `data/venue-directory.json` include 70 sedi in 17 regioni: è il **perimetro censito**, non la prova di copertura esaustiva di tutte le regioni italiane.
- Non confondere completezza del registro F1 (#1), affidabilità degli adapter F2 (#679), copertura delle date F2 (#178) e riconciliazione delle candidate F2 (#685).

## Decisione di governance

**#1 rimane aperta.** Il nucleo del registro esiste già e la diagnostica nazionale è attiva, ma non vi sono prove esaustive per chiudere i criteri relativi a ogni fonte, access policy e verifica manuale dei casi controversi. È un audit con esito parziale, **non** un pretesto per refactoring o riscrittura di 70 connettori.

La prossima implementazione, se necessaria, deve partire da un confronto sistematico `directory ↔ configurazioni ↔ fonti ufficiali ↔ health` con check non invasivi e riportare esclusivamente i gap reali.
