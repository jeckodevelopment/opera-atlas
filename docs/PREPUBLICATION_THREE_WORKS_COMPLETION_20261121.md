# Chiusura schede nel ciclo di importazione — 21 novembre 2026

Sono state individuate tre produzioni con dati ufficiali e autorità Wikidata già accertati, ma con schede ancora incomplete nell'indice: *Norma* (Bellini, Q320353), *Adriana Lecouvreur* (Cilea, Q375063), *Les contes d'Hoffmann* (Offenbach, Q335012).

Ogni scheda ha nel catalogo editoriale esistente una **breve sinossi originale**, dati di prima rappresentazione con fonti e una copertina storica ospitata su Wikimedia Commons. Il file `data/verified-work-editorial-attribution.json` associa esplicitamente ciascuno di questi contenuti alla sua composizione Wikidata e al compositore.

La funzione centrale `complete_cached_verified_work_cards` verifica nuovamente l'identità della fonte ufficiale, il titolo e il compositore su **tutte le recite** prima di riutilizzare il contenuto. Una scheda iniziale che contiene solo «Consulta le rappresentazioni verificate ...» è ora considerata un segnaposto e sostituita dalla sinossi verificata, mentre una sinossi già completa non viene sovrascritta. La pubblicazione avviene poi esclusivamente tramite il controllo atomico delle nuove opere, che richiede anche storia e immagine affidabili.

Il miglioramento è trasversale ai teatri e non richiede un secondo passaggio editoriale dopo l'importazione. Il controllo di regressione in `tests/test_new_opera_autopromotion.py` include tutte e tre le candidate, la sostituzione del segnaposto e il rifiuto della sinossi quando il compositore della fonte non corrisponde.

Fonti delle immagini storiche già presenti nel registro: manifesto originale di *Norma* (1831); ritratto storico di un'interprete di *Adriana Lecouvreur*; manifesto di *Les contes d'Hoffmann* di L. d'Ausbourg, 1881. Le immagini non rappresentano gli allestimenti correnti.
