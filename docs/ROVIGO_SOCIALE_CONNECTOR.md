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

## Perimetro editoriale lirico

`Il pipistrello` (*Die Fledermaus*) di Johann Strauss II è un'**operetta**:
resta fuori dal parser di opere liriche, anche se un cartellone municipale
misto la presenta con data e orario. Il dittico *The Telephone / Trouble in
Tahiti* deve restare un unico evento di programma con componenti d'opera
distinte e non va pubblicato duplicando il biglietto. La scansione regionale
attualmente individua il documento PDF ma non contiene ancora le singole
recite verificate: la copertura del teatro rimane parziale.

## Riscontri di calendario in attesa della fonte primaria

`data/rovigo-season-review-evidence.json` conserva, come **riscontri non
pubblicabili**, le date comunicate da testate del settore per sei programmi:
*Pagliacci*, *Pimpinone*, il dittico *The Telephone / Trouble in Tahiti*,
*La traviata*, *Aida* e *La Cenerentola*. Orari non verificati sono `null`;
la coppia Menotti/Bernstein resta un solo evento composto, non un'opera nuova.
Il file non viene letto dal publisher e **non** attribuisce a una testata
l'autorità del programma ufficiale.

La coda va risolta acquisendo il programma del teatro da fonte primaria e
confrontando separatamente compositore, sede, date e orari; soltanto dopo
le singole recite potranno passare alla pipeline nazionale comune.
Il PDF regionale attualmente individuato non è ancora stato trasformato
in prova strutturata di rappresentazioni. Non utilizzare date stampate
sulle pagine di indice come date delle recite.

## Seconda prova primaria: cartellone del Comune su Art Bonus

La scheda istituzionale https://artbonus.gov.it/1319-comune-di-rovigo.html,
con descrizione inserita dall'ente beneficiario, documenta la stagione
2026/27, i compositori abbreviati, l'identità del dittico Menotti/Bernstein
e la qualificazione espressa di *Die Fledermaus* come operetta.

`opera_atlas/rovigo_artbonus_program.py` riconosce solo il blocco
2026/27 e richiede la lista completa e la qualificazione dei generi. Il
parser restituisce deliberatamente `event_facts: []`: la fonte certifica
il repertorio, **non** le date e gli orari di biglietteria. Rimane perciò
un riscontro per la revisione editoriale, non un'alternativa fittizia
all'acquisizione del programma ufficiale o delle singole pagine-evento.
Quando saranno disponibili le recite sul sito del Teatro, il parser dovrà
consentire di confrontare le identità senza creare una doppia produzione.

Test: `python -m unittest tests.test_rovigo_artbonus_program -v`.

## Isolamento dei pannelli e programmi composti

Il riconoscimento del titolo `Il pipistrello` / `Die Fledermaus` come
**delimitatore**, senza trattarlo come opera pubblicabile, impedisce
che le date dell'operetta vengano attribuite all'opera lirica
precedente. Per il programma `Il telefono / Trouble in Tahiti` il parser
non pubblica due biglietti: omette le componenti di un titolo misto
e, se i titoli sono su pannelli distinti con lo stesso giorno, omette
entrambe le recite ambigue per affidarle al sistema nazionale dei
programmi composti. Altre opere autentiche della stessa pagina
continuano a essere acquisite. Le recite richiedono sempre orari
espliciti sulla fonte municipale ufficiale.

Test: `python -m unittest tests.test_rovigo_opera_source -v`.

## Sede distinta: Ridotto del Teatro Sociale

Le recite dell'intermezzo *Pimpinone* risultano annunciate al **Ridotto del Teatro Sociale di Rovigo** (26 e 28 novembre 2026), una sede da distinguere dalla sala principale. Il parser comunale blocca dunque l'attribuzione automatica alla sede generica `Teatro Sociale` quando il blocco dell'opera contiene il termine `Ridotto`; le altre opere continuano a essere processate. La produzione potrà essere pubblicata soltanto con una corrispondenza verificata tra l'evento ufficiale e l'identità canonica della sede Ridotto. Gli orari riportati da terze parti rimangono in revisione finché non sono acquisiti dalla fonte ufficiale.

Test: `python -m unittest tests.test_rovigo_opera_source -v`.
