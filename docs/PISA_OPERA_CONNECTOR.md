# Teatro Verdi di Pisa — Opera 2026/27

Fonte ufficiale: https://teatrodipisa.it/tipologia-spettacolo/opera/
La pagina include anche produzioni di stagioni precedenti, perciò
l'allowlist è esplicita e limitata alle cinque schede verificate
della stagione 2026/27: Dido and Aeneas, L'occasione fa il ladro,
Otello di Giuseppe Verdi, Aida, La clemenza di Tito.
Per ciascuna scheda il parser controlla il compositore ufficiale
e le due recite con data e ora nella sezione Date, ignorando storia,
prima rappresentazione e produzioni di altri teatri.

Nessun tentativo di indovinare il compositore per titoli omonimi.
Ogni pagina è acquisita solo dopo controllo robots.txt e con host/path
ristretti. L'esito iniziale è configurato, in attesa di scansione;
il successo del parser non prova ancora pubblicazione del catalogo.

## Comportamenti da testare

- python -m unittest tests.test_pisa_opera_source -v
- python -m unittest discover -s tests -v
- python -m scripts.source_automation --check
- Controllare la fonte pisa-verdi-opera-2026-27 nel health del refresh.
- Confrontare le 5 candidate e 10 date verificabili negli evidence JSON.
- Verificare le promozioni canoniche senza pubblicare date o orari
  dedotti da note di coproduzione o descrizioni storiche.
