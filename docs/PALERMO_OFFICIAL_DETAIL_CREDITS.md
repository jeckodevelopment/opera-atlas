# Attribuzione autorevole delle opere dalla scheda ufficiale

Il connettore del Teatro Massimo (Palermo) è stato esteso per leggere titolo dell'opera, compositore esplicitamente dichiarato da `Musiche di` e date/orari dalle schede di biglietteria. L'identità viene osservata **prima** della ricerca di autorità su Wikidata, così una produzione non deve essere già presente nel registro canonico per poter avanzare.

La lettura resta soggetta a robots.txt e all'host ufficiale autorizzato. Il parser controlla: H1 effettivo dell'opera, sezione ufficiale *Lo spettacolo*, credito del compositore unico e delimitato da un'etichetta di genere, riepilogo completo delle date (anche attraversando due mesi), orari singoli e sede. I dati incompleti o in contraddizione sono respinti.

Il medesimo risultato normalizzato passa al motore centrale di identificazione canonica, deduplicazione, ricerca di sinossi/immagine e pubblicazione. Non vengono generati orari o compositori da uno slug. I casi ufficiali che motivano l'intervento sono *Ernani*, *Falstaff* e *Die Zauberflöte*; la logica è riutilizzabile per altre opere con la stessa struttura.

## Collaudi automatici
- `python -m unittest discover -s tests -v`
- Verificare dopo il refresh `data/candidate-detail-health.json` (`facts_found` per pagine ufficiali con scheda completa) e la successiva diagnosi del motore centrale.
- Eventi con titolo, credito, riepilogo o orari mancanti non devono arrivare al catalogo.

La presenza di evidenze ufficiali non comporta da sola la pubblicazione: le nuove opere richiedono ancora identificazione indipendente, breve sinossi verificata, storia essenziale e immagine adatta. Nessun collaudo Joomla o deploy FTP richiesto.
