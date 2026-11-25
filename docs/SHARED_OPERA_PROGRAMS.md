# Programmi misti — regola centrale unica

Gli spettacoli costituiti da più opere non sono nuove opere con un titolo composto. Un programma rappresenta un solo biglietto per data e ora, con un elenco di opere canoniche individuate separatamente mediante titolo e compositore.

La sorgente ufficiale può esporre i crediti mediante H1 con separatori (caso Petruzzelli) oppure mediante dati strutturati accertati dal parser ufficiale (caso Teatro Grande di Brescia). La logica centrale `opera_atlas.programs.program_from_evidence` accetta entrambi i formati, applica le medesime verifiche di fonte, sede e identità e rifiuta date duplicate, orari discordanti o componenti parziali. Non inferisce crediti da URL.

Per il dittico *Cavalleria rusticana / Pagliacci*, il parser del Teatro Grande convalida separatamente Mascagni e Leoncavallo e i due turni ufficiali. Produce `needs_program_review` con entrambe le identità, consentendo al publisher centrale `scripts.publish_programs` di rappresentare due opere con due biglietti complessivi, non quattro eventi indipendenti.

Le eventuali date già registrate nel circuito OperaLombardia non vengono modificate o moltiplicate; la vista programma rimane distinta dal catalogo v2 delle singole opere. La nuova lettura della pagina resta sottoposta a robots.txt e al normale workflow.

## Collaudi

- `python -m unittest discover -s tests -v`
- `python -m scripts.publish_programs --check` dopo la generazione
- Verificare `public/catalog/programs.json`: due componenti per programma, una sola recita di programma per data
- Verificare `data/candidate-detail-health.json` dopo un nuovo refresh: il caso Brescia deve diventare `verified_composite_program`, se la pagina ufficiale conserva i crediti e gli orari
- Nessun evento fittizio, nessun doppio conteggio della biglietteria; le schede canoniche delle opere non sono sostituite dal programma

## Copertine dei programmi composti

La grafica ufficiale dello spettacolo ha priorità, con ID del programma, URL della fonte ufficiale, credito e stato dei diritti. In assenza di grafica specifica, si usa la prima copertina autentica disponibile di una componente identificata tramite ID canonico; la didascalia distingue la copertina dell'opera da quella della produzione. Nessuna immagine generica o fittizia viene spacciata per manifesto. Il resolver condiviso serve homepage, dettaglio, In scena e festival; il prerender usa la stessa priorità per Open Graph. Il registro iniziale contiene i due dittici del Coccia e il dittico del Luglio Musicale Trapanese. Nessuna modifica alle recite o alle identità del repertorio.
