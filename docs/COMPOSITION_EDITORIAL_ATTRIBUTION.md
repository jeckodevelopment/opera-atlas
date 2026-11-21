# Completamento delle schede prima dell'importazione

Per le opere omonime una sinossi non può essere assegnata solo in base al titolo o allo slug. Il nuovo file `data/verified-work-editorial-attribution.json` associa una scheda editoriale all'esatto identificativo Wikidata della **composizione**, al compositore verificato e alla fonte pubblica utilizzata per il riassunto.

Il sistema può usare materiale già verificato anche quando Wikidata individua più opere con lo stesso titolo, **soltanto** quando tutte queste condizioni sono vere: ID della composizione identico, compositore esatto dalla fonte ufficiale del teatro, compositore esatto dell'autorità e presenza di sinossi e storia validate. Se uno degli elementi non combacia, la scheda non viene pubblicata e viene segnalata tra le incomplete.

Questa modifica predispone le schede complete di *L'esule di Roma* (Gaetano Donizetti), *I Capuleti e i Montecchi* (Vincenzo Bellini) e *Falstaff* (Giuseppe Verdi), utilizzando brevi sinossi originali, storia verificata e fonti autorevoli. Le rappresentazioni già verificate non vengono duplicate e l'assegnazione del manifesto resta affidata al processo automatico di immagini storiche.

Il catalogo JSON viene aggiornato dal workflow standard, prima della pubblicazione, e mantiene intatto il registro delle candidate non ancora verificabili. Non richiede chiavi OpenAI né servizi a pagamento.

## Test e criteri di accettazione

- `python -m unittest discover -s tests -v`.
- Verificare tre schede complete nel feed e nella matrice del catalogo dopo il refresh.
- Verificare che una seconda composizione denominata *Falstaff* con un QID differente non possa ricevere la sinossi di Verdi.
- Verificare che la pagina di dettaglio di un'opera nuova non compaia senza sinossi, dati storici e immagine autentica.
