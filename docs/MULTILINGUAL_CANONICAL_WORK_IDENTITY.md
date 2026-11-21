# Attribuzione multilingue delle nuove opere in fase di importazione

Il parser delle fonti ufficiali può leggere titoli in italiano, francese, inglese e tedesco. Non deve pretendere che la traduzione italiana di Wikidata coincida letteralmente con il titolo usato dal teatro.

`resolve_identity` ricerca prima la corrispondenza esatta nell'indice Wikidata italiano; se non la trova, verifica anche l'indice inglese. La composizione è accettata soltanto se una **etichetta o alias effettivo dell'entità** coincide esattamente con il titolo ufficiale e la sua tipologia Wikidata conferma un'opera lirica. Il compositore viene risolto indipendentemente e, quando presente nella fonte ufficiale, deve combaciare. Se più opere restano possibili non si procede alla pubblicazione.

Gli esempi dei test sono *The Rake's Progress* e *Die Zauberflöte*: servono a verificare la corrispondenza fra titolo straniero ed etichetta italiana senza attribuire per errore un'opera omonima. La modifica vale per **tutti** i teatri, non solo per una sede e non richiede un abbonamento o una chiave API.

Il lavoro resta nello stesso ciclo di importazione, prima delle verifiche di sinossi, dati storici, immagini e pubblicazione.
