# Completamento del cache delle opere prima della pubblicazione

Il processo automatico talvolta conserva un'identità Wikidata già verificata, con compositore, date, orari e storia, ma rimane in attesa della sinossi. Dopo l'approvazione di un testo originale e la disponibilità dell'immagine storica, non occorre ripetere il lookup esterno o fare una riconciliazione a posteriori.

La funzione `complete_cached_verified_work_cards` opera **in memoria durante lo stesso import**, prima di `promote_new_works`. Per ciascuna opera confronta:
- identificativo Wikidata della composizione già verificato;
- compositore della composizione e del riferimento editoriale;
- URL e chiave della fonte originale;
- titolo e compositore di tutte le recite acquisite dal teatro;
- sinossi autentica e dati storici validati.

Se uno di questi elementi diverge, la scheda resta invariata e non può venire pubblicata. Se coincidono, la funzione completa i soli campi editoriali mancanti, senza riscrivere un riassunto già verificato. L'immagine resta un prerequisito indipendente del processo di pubblicazione.

Questo sblocca anche le opere storiche già identificate prima che la funzione fosse implementata, come L'esule di Roma, I Capuleti e i Montecchi e Falstaff. Per le nuove candidate le stesse verifiche sono applicate prima della prima pubblicazione. Nessuna API a pagamento e nessuna riconciliazione manuale successiva.
