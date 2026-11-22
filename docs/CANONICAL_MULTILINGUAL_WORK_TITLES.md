# Identità canonica e titoli tradotti delle opere

Il catalogo possiede **una sola opera canonica per identità**, con ID
permanente nel registro `data/identity-registry.json`. Il titolo
riportato da un teatro può essere nella lingua del libretto oppure
tradotto. Questa differenza non deve creare una seconda opera.

Il risolutore comune `opera_atlas/work_identity.py` usa
**titolo alternativo verificato + compositore** e restituisce
la scheda canonica già presente; non usa fuzzy matching né cerca
di dedurre il compositore da titoli omonimi.

Equivalenze iniziali:
- Don Carlo (Verdi) -> Don Carlos, `oa-w-000071`
- Il flauto magico / Die Zauberflote / The Magic Flute (Mozart)
  -> Die Zauberflöte, `oa-w-000056`
- Tristano e Isotta / Tristan and Isolde (Wagner)
  -> Tristan und Isolde, `oa-w-000039`
- Sansone e Dalila / Samson and Delilah (Saint-Saëns)
  -> Samson et Dalila, `oa-w-000017`

Nota: *Samson et Dalida* non è un titolo alternativo accettato,
ma una grafia errata di *Samson et Dalila*. Le differenze ortografiche
non devono essere interpretate automaticamente come equivalenze.

Il riconoscimento è centralizzato nella funzione
`canonical_title` e applicato alle acquisizioni ufficiali con
compositore verificato in `scripts/collect_candidate_details.py`,
incluso Sassari. Il parser di ciascun teatro resta responsabile
dell'evidenza di titolo, compositore, sede, data e ora; il risolutore
non salta queste verifiche e non pubblica autonomamente.

Il registro canonico, gli ID, gli URL e le schede già pubblicate
**non vengono duplicati o rinominati**. Se l'identità non è
univoca, l'acquisizione resta non promossa e richiede revisione.

Questa fase copre i parser dei dettagli con titolo e compositore
verificati. Gli adapter che riconoscono soltanto un'intestazione,
senza compositore accertato, conservano il controllo più restrittivo
e non hanno automaticamente diritto alla traduzione.

## Comportamenti da testare

- `python -m unittest tests.test_canonical_multilingual_work_identity -v`
- `python -m unittest tests.test_sassari_de_carolis_source -v`
- `python -m unittest discover -s tests -v`
- Con una nuova scheda di un teatro in italiano, le rappresentazioni
  di Mozart devono associarsi a `oa-w-000056`, non creare una
  scheda separata *Il flauto magico*.
- Omonimie con compositore diverso, titoli non verificati e doppi
  record ambigui devono restare senza risoluzione automatica.
