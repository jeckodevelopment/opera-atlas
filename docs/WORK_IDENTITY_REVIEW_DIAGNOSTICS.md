# Diagnostica centralizzata delle identità delle opere

La pagina `diagnostics/index.html` legge ora anche
`public/catalog/work-identity-review.json`, generato a costo zero
da `python -m scripts.work_identity_review`.

Il generatore esamina esclusivamente `data/candidate-detail-evidence.json`
già verificato, insieme al registro canonico e al risolutore condiviso
`opera_atlas/work_identity.py`. Non interroga l'AI, non cerca su fonti
supplementari e non scrive nuove opere o equivalenze.

I casi sono distinti in:
- **Possibile nuova opera o alias**: titolo non riconciliato con compositore
  che compare in catalogo; necessita sempre controllo editoriale.
- **Credito da verificare**: compositore estratto in forma non riconosciuta
  (es. «Giuseppe Verdi Opera»), oppure autore non ancora censito.
- **Compositore mancante**: impossibile ricondurre un titolo omonimo
  a un'opera senza un compositore attendibile.

Il report raggruppa per titolo, compositore e categoria, conteggia
le recite osservate, mantiene i riferimenti alle fonti ufficiali e
agli ID delle candidate, ed espone separatamente gli alias già
riconosciuti. Non crea suggerimenti fuzzy o conflazioni di omonimie.
I titoli di altre stagioni e le candidate senza eventi non sono
automaticamente classificati come alias.

La schermata mostra categoria e ricerca testuale e permette di aprire
la fonte ufficiale. Il report viene rigenerato nei checkpoint di
`collect-candidate-details-fast.yml` e `refresh-catalog.yml`,
senza deploy del sito: la pagina legge direttamente il JSON su GitHub.
Se il report non è stato ancora prodotto, la diagnostica esistente
resta funzionante e la nuova sezione espone uno stato di attesa.

## Verifiche

- `python -m unittest tests.test_work_identity_review -v`
- `python -m unittest discover -s tests -v`
- `python -m scripts.work_identity_review`
- `python -m scripts.work_identity_review --check`
- Controllare che una traduzione già censita venga classificata come
  risolta, una vera opera non registrata sia visibile in revisione e
  un compositore mal estratto **non sia corretto automaticamente**.
- Controllare che il JSON e i link ufficiali si aggiornino al
  checkpoint successivo, senza confondere recite rilevate e pubblicate.
