# Connettore Modena – stagione Opera 2026/27

La [pagina ufficiale del Comune di Modena](https://www.comune.modena.it/vivere-modena/eventi/2026/stagione-opera-2026-2027) pubblica undici titoli della stagione del **Teatro Comunale Pavarotti-Freni** e le relative schede di produzione. Il Comune è fonte istituzionale primaria per i fatti della propria programmazione; l'URL non equivale a un permesso attribuito dal Teatro. Ogni lettura tramite GitHub Actions passa dal controllo robots.txt della stessa origine; nessun bypass o raccolta di testi integrali.

- **Indice**: solo gli undici URL sotto `/vivere-modena/eventi/2026/stagione-opera-2026-2027/<slug>` e sul dominio `www.comune.modena.it`. I link esterni non vengono seguiti.
- **Sede**: ogni dettaglio deve citare esplicitamente il Teatro Comunale Pavarotti-Freni; non basta la sede indicata nella pagina di stagione.
- **Identità**: il titolo principale deve contenere opera e compositore verificabili (es. *Siberia di Umberto Giordano*). I titoli privi di attribuzione esplicita rimangono in revisione, senza compositori dedotti dal nome del link.
- **Recite**: soltanto le righe con giorno, mese e orario puntuale nella sezione ufficiale “Date e orari”. Se la scheda omette l'anno, viene determinato unicamente quando il **giorno della settimana** corrisponde a uno e un solo anno del perimetro ottobre 2026–luglio 2027. Anni o giorni incompatibili bloccano l'estrazione.
- **Riconciliazione**: ogni candidato passa alla pipeline nazionale di identificazione opere, sinossi brevi, locandine storiche e pubblicazione canonica JSON. Nessun deploy SFTP per aggiornamenti del catalogo.
- **Limite**: l'indice 2026/27 non prova copertura di tutte le recite o rinnovo automatico del 2027/28. Una nuova stagione richiede una fonte ufficiale documentata e una revisione dell'allowlist.

Esempi dalle schede comunali ufficiali: *Siberia* l'8 gennaio 2027 alle 20:00 e il 10 gennaio alle 15:30; *Simon Boccanegra* il 12 marzo alle 20:00 e il 14 marzo alle 15:30. Le date sono esemplificative e non affermano pubblicazione già avvenuta sul portale.

## Collaudo

```sh
python -m unittest tests.test_modena_source_connector -v
python -m unittest discover -s tests -v
python -m scripts.source_automation --check
```

Dopo il merge, la scansione effettiva è visibile in `data/season-index-health.json` e le candidate in `data/season-index-candidates.json`. Il feed diagnostico mantiene Modena in `configured_not_operational` fino alla prima scansione riuscita. Il successo dell'indice non è equivalente a tutte le recite pubblicate.

## Perimetro lirico del catalogo (revisione 22/11/2026)

Delle undici proposte del cartellone teatrale, **L'anno che verrà** è
esplicitamente descritta dal Comune come *opera pop* costruita sulle canzoni
di Lucio Dalla: la sorgente resta tracciabile, ma il candidato è classificato
`excluded_nonopera` e non deve entrare nel catalogo lirico.

**I salvatori della mezzanotte** è descritta come opera commissionata a
Daniele Furlati: resta in revisione editoriale per la creazione della sua
identità canonica e della scheda, senza pubblicazione prematura. **Vanishings
– Disparition(s)** fonde musiche di Leoš Janáček e Thomas Adès: prima di
pubblicare occorre accertare se si tratti di un programma composito di opere
liriche autonome; non si deve assegnare arbitrariamente un unico autore o
creare una nuova opera canonica con un credito misto.

La fonte primaria del teatro /opera/ ha dato 11 link verificati nella scansione
del 22/11/2026; la fonte comunale secondaria è risultata indisponibile.
Gli stati di acquisizione non equivalgono a recite pubblicate.

## Rinnovo automatico: indice del teatro

La fonte primaria del teatro `https://www.teatrocomunalemodena.it/opera/`
è un indice permanente. Il parser delle singole pagine-evento supporta
anche le stagioni successive al 2026/27: una data con **anno esplicito**
determina il perimetro ottobre–luglio della stagione osservata e deve
rispettare il giorno della settimana indicato. Date prive d'anno sono
ammissibili per una nuova stagione soltanto se la **stessa scheda ufficiale**
riporta un'etichetta di stagione consecutiva (`2027/2028`, ecc.). Se più
stagioni sono incompatibili, l'acquisizione fallisce senza pubblicare
recite parziali. In assenza di nuove prove rimane il perimetro 2026/27,
non l'anno corrente di esecuzione del workflow.

Il connettore municipale secondario, che utilizza URL specifici della
stagione 2026/27, **non** viene esteso implicitamente alla stagione nuova.
I nuovi titoli continueranno a passare dal classificatore e dal publisher
centrali, senza attribuire compositori o immagini in automatico.

Test: `python -m unittest tests.test_modena_theatre_fallback -v`.
