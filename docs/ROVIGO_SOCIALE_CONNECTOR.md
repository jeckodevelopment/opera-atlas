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

## Fonte ufficiale per recite: La traviata (2027)

Il Comune pubblica una pagina-evento puntuale nel proprio endpoint
istituzionale `/myportal/C_H620/api/content/share/social/6aa10ea4c4e2c4008be2a957`.
Il parser `rovigo_traviata_official.py` conferma titolo e compositore,
sede, giorno della settimana, data e orario esatti. La scheda distingue
la rappresentazione **TeatroRagazzi** di giovedì 21 gennaio 2027 dalle
recite ordinarie **venerdì 22 gennaio 2027 alle 20:30** e
**domenica 24 gennaio 2027 alle 16:00**. Solo queste due recite
vengono inoltrate alla riconciliazione canonica ordinaria.

Se lo slider storico della stagione non identifica più correttamente
il Teatro Sociale, la scansione prova **una sola** URL-evento fissa del
Comune, attraverso lo stesso controllo robots e l'origin già approvato.
Il fallback non autorizza URL arbitrarie, non legge dati di biglietterie
terze e non certifica il resto del cartellone. La prima scansione con
fallback riuscito dovrà risultare nella diagnostica con
`fallback_official_source=comune.rovigo.it`.

Test: `python -m unittest tests.test_rovigo_official_traviata_fallback -v`.

## Refresh prioritario della fonte ufficiale

Il workflow `refresh-catalog.yml` acquisisce ora il documento-evento
ufficiale della *Traviata* di Rovigo **prima** della lenta coda di scansione
nazionale, tramite `discover_season_indexes --source-key
rovigo-sociale-opera-2026-27`, seguito da `collect_candidate_details
--source-key rovigo-sociale-opera-2026-27`. Non è una scorciatoia del
publisher: la stessa riconciliazione centralizzata controlla titolo,
compositore, sede, data, orario, identità canonica e duplicati.

Il comando `--source-key` convalida l'intera configurazione delle fonti e
accetta soltanto chiavi approvate; non modifica le candidate né gli stati
diagnostici delle altre fonti. I nuovi dati vengono registrati nel checkpoint
iniziale e resi disponibili alla prima transazione di pubblicazione dello
stesso workflow, senza richiedere una seconda esecuzione nazionale.

## Diagnostica effettiva del fallback (novembre 2026)

La scansione successiva alla PR #518 ha mostrato ancora
`rovigo_venue_missing` nonostante il tentativo di consultare la
scheda-evento. Il codice precedente, quando il fallback falliva,
rilanciava erroneamente l'eccezione del vecchio slider: non era possibile
capire se il nuovo endpoint non fosse disponibile oppure se il contenuto
non superasse la verifica delle recite.

Il fallback ufficiale usa ora due codici diagnostici privi di dati remoti:
`rovigo_fallback_fetch_unavailable` (pagina non acquisita)
e `rovigo_fallback_content_unverified` (pagina acquisita ma non
verificabile dal parser). Si prova lo stesso endpoint anche in caso di
`FetchUnavailable` dello slider. Un blocco robots esplicito resta
inviolabile; non vengono inferite date da pagine non verificate.
I dati delle altre fonti e l'eventuale ultimo successo rimangono
preservati. Questa correzione è **diagnostica e di resilienza**:
non equivale all'avvenuta pubblicazione di nuove recite.

## Due endpoint ufficiali per la stessa scheda di Traviata

La pagina comunale di condivisione social può restituire un documento HTML
privo del contenuto richiesto, pur essendo indicizzata in precedenza.
In tal caso la diagnostica segnala `rovigo_fallback_content_unverified`.

La scansione prova ora anche il percorso **esatto** della scheda evento
istituzionale `/teatrosociale/dettaglio-teatro/eventi/la-traviata-2027`.
L'allowlist contiene soltanto questi due URL ufficiali e nessun percorso
simile è accettato. Entrambi attraversano la policy robots ordinaria.
Ogni risposta deve superare lo stesso parser che convalida titolo,
compositore, teatro, le due recite e l'esclusione della sessione scolastica.
Un HTML vuoto, un 404, un URL inatteso o dati incompleti non genera alcuna
pubblicazione. Un divieto robots esplicito blocca il tentativo, senza aggirarlo.

La scheda del teatro non viene sostituita da siti commerciali o da
risultati di ricerca memorizzati: il catalogo continua a richiedere la
prova primaria corrente.

## Diagnostica dei due endpoint (senza pubblicazioni fittizie)

La scansione della stagione 2026/27 restituisce la causa aggregata
`rovigo_fallback_content_unverified` quando almeno un endpoint comunale
risponde, ma nessuno contiene una scheda validabile. Il campo
`fallback_checks` discrimina il risultato di `social_api` e `event_page`
con uno dei codici privi di dati del sito:
`fetch_unavailable`, `title_missing`, `composer_missing`,
`venue_missing`, `dates_unbounded`, `date_invalid`,
`weekday_conflict`, `time_conflict`, `recite_incomplete` o
`content_unverified`. Gli URL completi, l'HTML remoto e gli errori del
server non vengono pubblicati.

In questo modo una pagina comunale che restituisce soltanto lo shell
JavaScript non viene confusa con una recita priva di orario. Resta
obbligatoria la prova primaria completa; un risultato indicizzato da
motori di ricerca non autorizza l'acquisizione né la pubblicazione.

## Riconciliazione con evidenze incrociate: politica controllata

Quando l'endpoint comunale restituisce un HTML vuoto, non viene usato
alcun contenuto indicizzato come falsa prova diretta. Il nuovo
`scripts.corroborate_performances` richiede invece **tutte** le seguenti
pagine recuperate nello stesso ciclo con la normale policy robots:

- la scheda istituzionale Art Bonus, compilata dal Comune, con
  attribuzione *Traviata* di Verdi nella stagione 2026/27;
- due schede distinte ClassicaLive, ciascuna con titolo, autore, Teatro
  Sociale di Rovigo, data e ora, e rimando alla scheda-evento comunale;
- la scheda Piazza in Festa, editata automaticamente da atti comunali,
  che conferma entrambi gli orari pubblici e distingue la prova
  scolastica del 21 gennaio.

**ClassicaLive e Piazza in Festa non sono fonti primarie**, possono
avere un'origine documentale comune e non costituiscono due verifiche
istituzionali indipendenti. Sono registrate come riscontri esterni,
senza affermare di aver letto l'evento HTML del Comune. Un disaccordo,
una pagina non leggibile, un cambio di sede o un'indicazione incompleta
bloccano l'emissione dei fatti. L'operazione produce soltanto la
candidate e l'evidenza con campo `corroboration`; la stessa
`auto_catalogue.promote` crea eventualmente produzione e recite,
controlla il registro canonico e i duplicati. Nessuna scrittura diretta
nel feed pubblico elude la transazione centralizzata.

Le URL consentite sono nella configurazione revisionata
`data/corroborated-performance-config.json`; le osservazioni ricevute
dalle fonti sono convalidate ad ogni refresh. I risultati operativi,
anche quando non pubblicabili, sono registrati in
`data/corroborated-performance-health.json`.

## Decisione editoriale persistente del 22 novembre 2026

La verifica pubblica delle due recite 2027 è conservata in
`data/reviewed-performance-decisions.json`, un registro revisionato
**non generato dallo scanner**. L'evento ufficiale continua a non
restituire HTML utilizzabile, quindi la decisione non ne inventa un
hash né dichiara una lettura primaria inesistente.

La decisione incrocia il repertorio istituzionale Art Bonus curato
dal Comune, le due schede evento ClassicaLive e il riscontro di
Piazza in Festa (che dichiara esplicitamente l'impiego dell'IA e può
derivare dagli stessi atti comunali). I due eventi ClassicaLive
appartengono allo stesso editore. La decisione non li presenta come
tre fonti primarie indipendenti e richiede due sole recite pubbliche.

In esecuzione, `scripts.apply_reviewed_performance_evidence`
applica il record ai **registri correnti** dopo i tentativi di
acquisizione live, preservando ogni eventuale prova primaria più
forte e senza sovrascrivere candidate già pubblicate. Il risultato
entra nel checkpoint iniziale e soltanto `auto_catalogue.promote`
può creare la produzione e i relativi ID canonici. La ripetizione
dello stesso ciclo è idempotente.
