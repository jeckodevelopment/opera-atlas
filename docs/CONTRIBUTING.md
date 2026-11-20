# Regole di contribuzione e qualità

- Un ramo per modifica e una PR per unità coerente di rilascio.
- Issue con identificazione requisito, priorità P0/P1/P2, fase e criterio di accettazione.
- PR con sezione obbligatoria **Comportamenti da testare**, riferimenti a issue, test, documentazione e impatto SemVer.
- Documentazione, codice, inventario e metriche devono riflettere lo stesso stato reale.
- Le modifiche agli scraper richiedono fixture, test della deduplicazione, controllo dei siti ufficiali e policy di crawling.
- Non aggiungere eventi fittizi ai dati pubblicati; i dati demo vanno isolati e marcati.
- Non inserire segreti, token, dati di geolocalizzazione utenti o contenuti protetti senza autorizzazione.
- Versionamento SemVer: 0.x durante costruzione, 1.0.0 solo dopo soddisfacimento DoD e collaudi.
- Usare le etichette di fase, area, priorità e documentation dove disponibili.

## Checklist PR
- [ ] Issue e criterio di accettazione collegati
- [ ] Codice e test / motivazione assenza test
- [ ] Comportamenti da testare manualmente
- [ ] Documentazione e changelog allineati
- [ ] Verifica regressioni, sicurezza, licenze e protezione dati
- [ ] Impatto SemVer esplicitato
