# Ricognizione titoli alternativi — seconda tranche

Riferimento: `docs/CANONICAL_MULTILINGUAL_WORK_TITLES.md`.
La ricerca parte dalle **84 opere gia' presenti** in
`data/identity-registry.json`: non inventa nuove opere e non
rinomina schede esistenti. Il catalogo conserva i rispettivi ID.

Sono stati aggiunti **24 alias verificati**, oltre agli 8
precedenti, tutti qualificati da titolo e compositore.

| Scheda canonica | Alias supportati | Fonte di confronto |
| --- | --- | --- |
| Les Pêcheurs de perles — Bizet | I pescatori di perle; The Pearl Fishers; Les Pecheurs de perles | [Metropolitan Opera](https://www.metopera.org/about/press-releases/pretty-yende-javier-camarena-and-mariusz-kwiecien-star-in-bizets-les-pecheurs-de-perles/) |
| Les contes d'Hoffmann — Offenbach | I racconti di Hoffmann; The Tales of Hoffmann | [Operabase](https://www.operabase.com/productions/the-tales-of-hoffmann-494855/en) |
| Hänsel und Gretel — Humperdinck | Hansel e Gretel; Hansel and Gretel; Haensel und Gretel | [Opera Online](https://www.opera-online.com/en/items/productions/hansel-and-gretel-met-2014-2015) |
| Don Quichotte — Massenet | Don Chisciotte | [Operabase](https://www.operabase.com/productions/production-2749/en) |
| Iphigénie en Tauride — Gluck | Ifigenia in Tauride | [Operabase](https://www.operabase.com/productions/iphigenie-en-aulide-and-iphigenie-en-tauride-269974/it) |
| Dido and Æneas — Purcell | Didone ed Enea; Dido and Aeneas | [Operabase](https://www.operabase.com/dido-and-aeneas-purcell/en) |
| Il pipistrello — Johann Strauss | Die Fledermaus; The Bat | [Opera Online](https://www.opera-online.com/en/items/productions/die-fledermaus-wiener-staatsoper-2019-2020) |
| Death in Venice — Britten | Morte a Venezia | [Operabase](https://www.operabase.com/productions/death-in-venice-704960/it) |
| La Cenerentola — Rossini | Cinderella; La Cenerentola, ossia La bontà in trionfo | [Operabase](https://www.operabase.com/productions/rossini-la-cenerentola-790723/en) |
| Il barbiere di Siviglia — Rossini | The Barber of Seville | [Operabase](https://www.operabase.com/productions/il-barbiere-di-siviglia-465388/en) |
| Le nozze di Figaro — Mozart | The Marriage of Figaro | Opera di Mozart (traduzione inglese del titolo) |
| The Rake's Progress — Stravinskij | La carriera di un libertino | [Operabase](https://www.operabase.com/productions/the-rakes-progress-647597/it) |
| Il ritorno di Ulisse in patria — Monteverdi | Il ritorno d'Ulisse in patria; The Return of Ulysses to His Homeland | [Operabase](https://www.operabase.com/productions/il-ritorno-dulisse-in-patria-691065/en) |
| Evgenij Onegin — Čajkovskij | Eugene Onegin; Yevgeny Onegin | [Operabase](https://www.operabase.com/productions/yevgeny-onegin-4455/en) |

Le fonti e gli alias sono una **whitelist editoriale**, non un
dizionario che produce equivalenze per somiglianza o per la sola
trama. Il caso del *Barbiere di Siviglia* di Paisiello non
deve convergere su quello di Rossini: cambia il compositore,
quindi cambia l'opera. Lo stesso vale per ogni altra omonimia.

## Esclusioni e limiti

- Nessuna translitterazione generica per opere russe, greche o slave:
  si aggiungono solo grafie verificabili.
- Nessuna unificazione tra versioni musicali diverse o opere omonime
  di compositori differenti.
- Nessun recupero automatico di un titolo quando il compositore non
  e' attendibile: la candidate resta in revisione.
- Gli alias aggiornano il matcher dei dettagli ufficiali gia'
  centralizzato, non dimostrano pubblicazione delle recite e non
  applicano automaticamente redirect URL o titoli localizzati in UI.
- `Samson et Dalida` resta un refuso, non un alias da accettare
  in modo automatico.

## Verifiche

`python -m unittest tests.test_extended_multilingual_work_aliases -v`

`python -m unittest tests.test_canonical_multilingual_work_identity -v`

`python -m unittest discover -s tests -v`

Ripetere inoltre la riconciliazione del catalogo per candidati nuovi
e verificare che il registro di 84 opere non aumenti per effetto
dei soli titoli tradotti.
