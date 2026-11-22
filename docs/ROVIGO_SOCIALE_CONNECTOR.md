# Rovigo — Teatro Sociale, stagione 2026/27

Fonte istituzionale: https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/teatrosociale-info/stagione-slider-2026-2027

La stagione annunciata comprende *Pagliacci*, *Pimpinone*,
*Il telefono* / *Trouble in Tahiti*, *Il pipistrello*,
*La traviata*, *Aida* e *La Cenerentola*.
La pagina comunale non è risultata leggibile integralmente durante
la verifica iniziale: le singole date/orari di tutte le opere
**non sono attestati**. Non sono quindi caricati orari dedotti dagli
intervalli di date pubblicati dalla stampa.

Questo connettore registra la fonte ufficiale e la associa alla sede.
`identify_season` richiede il titolo della stagione 2026/27, il
Teatro Sociale e almeno un titolo d'opera. `parse_program`
restituisce recite solo in presenza di un blocco specifico
con compositore esplicitamente etichettato e giorno, mese, anno,
ora e minuti. Su un semplice annuncio di cartellone restituisce
zero recite: è una condizione prevista, non un dato fittizio.

Il doppio titolo *Il telefono* / *Trouble in Tahiti* dev'essere
riconciliato come programma misto dalla pipeline nazionale.
Il concerto e le rappresentazioni scolastiche non sono desunte.
Fetch soggetto a robots.txt e origine HTTPS esatta. Nessun FTP
o bypass di blocchi del sito.

## Comportamenti da testare

- `python -m unittest tests.test_rovigo_opera_source -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.source_automation --check`
- Dopo il refresh: verificare in health se il portale comunale
  espone HTML e robots.txt validi.
- Se la pagina contiene soltanto il cartellone senza orari,
  mantenerla configurata senza inventare recite; espandere
  l'adapter solo con nuove evidenze ufficiali verificabili.

## Rinnovo stagioni: fonte regionale

L'indice permanente Cultura Veneto può esporre un nuovo PDF di programma.
L'adapter `rovigo_regional_program` riconosce il nome
`Programma_stagione_YYYY_YY_da_scaricare.pdf` a partire dalla stagione
2026/27, soltanto se gli anni sono consecutivi, la pagina ufficiale
li menziona, il link rimane HTTPS sul dominio documentale atteso e il
nome del documento è riconoscibile anche nel testo dell'ancora.
Un PDF futuro non produce automaticamente recite: occorre ancora estrarre
le singole date e riconciliarle tramite la pipeline centrale. L'URL
comunale relativo al 2026/27 rimane una fonte storica separata.

Test: `python -m unittest tests.test_rovigo_regional_program -v`.
