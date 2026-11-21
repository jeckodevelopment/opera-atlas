# Macerata Opera Festival 2027 — connettore ufficiale

Fonte: https://www.sferisterio.it/ e le tre schede ufficiali della stagione 2027:
Tosca (quattro recite), La traviata (quattro) e L'elisir d'amore (tre).
Tutti gli orari presenti sulle schede ufficiali sono alle 21:00.
Il parser conserva la sede Arena Sferisterio, verifica il compositore
nel testo della singola scheda e confronta giorno della settimana e data
con il 2027. Non legge le date del footer, comuni ai tre spettacoli.

I collegamenti sono vincolati a tre path esatti del dominio ufficiale.
Il controllo robots.txt è obbligatorio per ogni accesso; in caso di errore
la sede resta configurata, non dichiarata operativa. Il modello centrale
gestisce riconciliazione, identità opere, arricchimento e pubblicazione.
Nessun nuovo deploy FTP è necessario per le recite.

## Comportamenti da testare

1. Eseguire python -m unittest tests.test_macerata_opera_source -v.
2. Eseguire python -m unittest discover -s tests -v.
3. Eseguire python -m scripts.source_automation --check.
4. Dopo il merge verificare macerata-festival-2027 in
   data/season-index-health.json e tre URL ufficiali nella coda candidate.
5. Verificare undici date nei dettagli acquisiti e il numero di recite
   realmente promosse nei JSON canonici; nessuna attestazione preventiva
   di pubblicazione.
6. Per l'edizione successiva verificare il nuovo cartellone e aggiornare
   esplicitamente perimetro e URL approvati: l'annuncio non si presume.
