# F1 — Esito di verifica mirata degli indici di stagione (23/11/2026)

## Associazioni con evidenza ufficiale

Il controllo su fonti primarie ha verificato **due** relazioni fonte–venue, senza introdurre nuove venue o modificare i connettori:

| Source key | Venue canonica già esistente | Fonte primaria e prova |
| --- | --- | --- |
| `macerata-festival-rolling` | `Macerata|Arena Sferisterio` | Il Macerata Opera Festival presenta ufficialmente il cartellone 2027 **allo Sferisterio**: https://www.sferisterio.it/comunicati-stampa/apertura-biglietteria-2027 |
| `filarmonico-verona-rolling-opera` | `Verona|Teatro Filarmonico` | Fondazione Arena documenta esplicitamente la stagione d'opera **al Teatro Filarmonico**, distinta da quella dell'Arena: https://www.arena.it/magazine/news/fondazione-arena-al-teatro-filarmonico-il-2027-delle-prime-volte-cinque-debutti-assoluti-e-il-requiem-di-brahms-diretto-da/ |

Le voci `INDEX_VENUES` sono impiegate per **attribuire la copertura diagnostica alla sede fisica**. L'aggiunta non modifica URL, robots, esiti degli scan, regole di riconciliazione, stagioni pubblicate o produzione/recita. Una fonte `success` non garantisce il cartellone completo.

## Rimanenti undici indici non associati esplicitamente

I seguenti index restano deliberatamente senza assegnazione, perché sono stagioni future con programma non verificato, URL fetch non disponibile o sorgente non validata:

- `donizetti-opera-2027`
- `chieti-marrucino-season-2027`
- `modena-municipal-opera-2027-28`
- `ferrara-season-opera-2027-28`
- `jesi-opera-season-2027`
- `ancona-opera-season-2027`
- `salerno-verdi-rolling-opera`
- `treviso-del-monaco-season-2027-28`
- `padova-verdi-season-2027`
- `rovigo-sociale-season-2027-28`
- `lecce-provincia-season-2027`

L'assenza del mapping **non indica automaticamente che il teatro non è operativo**. La loro diagnostica tecnica è tracciata in [#679](https://github.com/jeckodevelopment/opera-atlas/issues/679) e la completezza delle stagioni future in [#178](https://github.com/jeckodevelopment/opera-atlas/issues/178).

## Altre sedi

- **Teatro M° Tonino Pardo, Trapani:** già associato in `main` al connettore del Luglio Musicale Trapanese, confermato dal programma ufficiale: https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/. Non creare duplicati.
- **Teatro Nuovo Gian Carlo Menotti, Spoleto:** connettore presente ma scansione bloccata all'ultimo checkpoint; problema di diagnostica F2, non motivo per alterare il mapping F1.
- **Villa Pisani Bonetti, Lonigo:** venue censita e non automatizzata; non attribuire a priori un programma operistico o il connettore di una venue diversa.

## Limiti e criterio di chiusura

Sono state verificate le due associazioni sopra sulla **fonte ufficiale**, non tutte le policy/termini e il campione manuale per regione. I collaudi manuali sono separati e non sono stati eseguiti. Non dichiarare chiusa la issue #1 per il solo passaggio dei test. Il registro può essere considerato implementativamente consolidato nel perimetro provato; le altre associazioni vanno documentate solo quando esiste evidenza specifica, senza riscrivere la rete esistente.
